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
        password=secret.PGPASSWORD
    )


async def get_user_data(auth_token: str) -> dict:
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
                raise HTTPException(status_code=resp.status)
            user_data = await resp.json()

        url = settings.USER_PROFILE_API_URL + '/apps/' + settings.CLIENT_APP_UUID
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status)
            app_config = await resp.json()

    reference_area = app_config['featuresConfig'].get('reference_area')
    user_data['reference_area'] = reference_area
    return user_data


async def llm_analytics(request: 'Request') -> 'Response':
    '''
    Handles POST requests to /llm-analytics.

    Request format:
        - 'area' (dict): A GeoJSON representing the selected area.

    Response format:
        - 'data' (str): analytics for selected area in markdown format
    '''
    LOGGER.debug(f'asking UPS {settings.USER_PROFILE_API_URL} for user data..')
    user_data = await get_user_data(auth_token=request.headers.get('Authorization') or '')
    bio = user_data.get('bio')
    reference_area = user_data.get('reference_area') or {}
    reference_area_geojson = reference_area.get('referenceAreaGeometry')
    LOGGER.debug('got user data')
    LOGGER.debug('user bio: %s', bio)

    # parse input params of original query
    data = await request.json()
    LOGGER.debug(f'asking insights-api {settings.INSIGHTS_API_URL} for advanced analytics..')
    sentences = await get_analytics_sentences(selected_area=data.get("area"), reference_area=reference_area_geojson)
    LOGGER.debug('got advanced analytics')

    # build cache key from request and check if it's in llm_cache table
    llm_request = get_llm_prompt(sentences, bio, reference_area_geojson)
    cache_key = hashlib.md5(llm_request.encode("utf-8")).hexdigest()

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
    #return JSONResponse({'data': {}})

    llm_response = await openai_client.get_llm_commentary(llm_request)
    await conn.execute(
        'insert into llm_cache (hash, request, response, model_name) values ($1, $2, $3, $4)',
        cache_key, llm_request, llm_response, llm_model,
    )
    await conn.close()
    LOGGER.debug('saved LLM response')
    return JSONResponse({'data': llm_response})
