import hashlib

import asyncpg
from aiohttp import ClientSession
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from .secret import Secret
from .settings import Settings
from .logger import LOGGER
from .insights_api_client import get_analytics_sentences
from .openai_client import get_llm_prompt, OpenAIClient

settings = Settings()
secret = Secret()


async def get_db_conn():
    return await asyncpg.connect(
        host=settings.PGHOST,
        port=settings.PGPORT,
        database=settings.PGDATABASE,
        user=settings.PGUSER,
        password=str(secret.PGPASSWORD)
    )


async def get_user_data(app_id: str, auth_token: str) -> dict:
    '''
    get user bio and reference area from UPS
    '''
    headers = {
        'Authorization': auth_token,
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        url = settings.USER_PROFILE_API_URL + '/users/current_user'
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.text())
            user_data = await resp.json()

        url = settings.USER_PROFILE_API_URL + '/apps/' + app_id
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.text())
            app_config = await resp.json()

        url = settings.USER_PROFILE_API_URL + '/features?appId=' + app_id
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.text())
            features = await resp.json()
            if len([x for x in features if x['name'] == 'llm_analytics']) == 0:
                raise HTTPException(status_code=403, detail='llm_analytics is not enabled for the user')

    reference_area = app_config['featuresConfig'].get('reference_area')
    user_data['reference_area'] = reference_area
    return user_data


async def llm_analytics(request: 'Request') -> 'Response':
    '''
    Handles POST requests to /llm-analytics.

    Request format:
        - 'appId' (str): UUID of client application
        - 'features' (dict): A GeoJSON representing the selected area.

    Response format:
        - 'data' (str): analytics for selected area in markdown format
    '''
    # parse input params of original query
    data = await request.json()
    app_id = data.get("appId")
    if not app_id:
        raise HTTPException(status_code=400, detail='missing appId')
    selected_area_geojson = data.get("features") or {}

    LOGGER.debug(f'asking UPS {settings.USER_PROFILE_API_URL} for user data..')
    user_data = await get_user_data(app_id, auth_token=request.headers.get('Authorization') or '')
    bio = user_data.get('bio')
    reference_area = user_data.get('reference_area') or {}
    reference_area_geojson = reference_area.get('referenceAreaGeometry') or {}
    LOGGER.debug('got user data')
    LOGGER.debug('user bio: %s', bio)

    LOGGER.debug(f'asking insights-api {settings.INSIGHTS_API_URL} for advanced analytics..')
    sentences = await get_analytics_sentences(selected_area_geojson, reference_area_geojson)
    LOGGER.debug('got advanced analytics')

    # build cache key from request and check if it's in llm_cache table
    llm_request = get_llm_prompt(sentences, bio, selected_area_geojson, reference_area_geojson)
    llm_instructions = settings.OPENAI_INSTRUCTIONS
    to_cache = f'instructions: {llm_instructions}; prompt: {llm_request}'
    cache_key = hashlib.md5(to_cache.encode("utf-8")).hexdigest()

    openai_client = OpenAIClient()
    llm_model = await openai_client.model

    conn = await get_db_conn()
    if result := await conn.fetchval(
            'select response from llm_cache where hash = $1 and model_name = $2',
            cache_key, llm_model):
        await conn.close()
        LOGGER.debug('found LLM response for %s model in the cache', llm_model)
        return JSONResponse({'data': result})

    LOGGER.debug('\n'.join(llm_request.split(';')))
    LOGGER.debug('asking LLM for commentary..')

    # uncomment to debug only prompt, without querying LLM:
    #return JSONResponse({'data': {}})

    llm_response = await openai_client.get_llm_commentary(llm_request)
    await conn.execute(
        'insert into llm_cache (hash, request, response, model_name) values ($1, $2, $3, $4)',
        cache_key, to_cache, llm_response, llm_model,
    )
    await conn.close()
    LOGGER.debug('saved LLM response')
    return JSONResponse({'data': llm_response})
