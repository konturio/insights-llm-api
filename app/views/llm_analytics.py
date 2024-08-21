import hashlib
from json.decoder import JSONDecodeError

import asyncpg
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.clients.insights_api_client import get_analytics_sentences
from app.clients.openai_client import get_llm_prompt, OpenAIClient
from app.clients.user_profile_client import get_user_data, feature_enabled
from app.db import get_db_conn
from app.logger import LOGGER
from app.settings import Settings

settings = Settings()


async def get_llm_response_from_cache(conn, cache_key, llm_model):
    return await conn.fetchval(
        'select response from llm_cache where hash = $1 and model_name = $2 and response is not null',
        cache_key, llm_model)


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
    try:
        data = await request.json()
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail='malformed request')
    if not (app_id := data.get('appId')):
        raise HTTPException(status_code=400, detail='missing appId')
    if not (selected_area_geojson := data.get('features')):
        raise HTTPException(status_code=400, detail='missing features')

    user_data = await get_user_data(app_id, auth_token=request.headers.get('Authorization'), features_config=True)
    if not feature_enabled('llm_analytics', user_data):
        raise HTTPException(status_code=403, detail='llm_analytics is not enabled for the user')

    bio = user_data['current_user'].get('bio')
    reference_area = user_data['features_config'].get('reference_area') or {}
    reference_area_geojson = reference_area.get('referenceAreaGeometry') or {}
    LOGGER.debug('user bio: %s', bio)

    LOGGER.debug(f'asking insights-api {settings.INSIGHTS_API_URL} for advanced analytics..')
    sentences, indicator_description = await get_analytics_sentences(selected_area_geojson, reference_area_geojson)

    # build cache key from request and check if it's in llm_cache table
    lang = request.headers.get('User-Language')
    llm_request = get_llm_prompt(sentences, indicator_description, bio, lang, selected_area_geojson, reference_area_geojson)
    llm_instructions = settings.OPENAI_INSTRUCTIONS
    to_cache = f'instructions: {llm_instructions}; prompt: {llm_request}'
    LOGGER.debug('\n'.join(llm_request.split(';')).replace('"', '\\"'))
    cache_key = hashlib.md5(to_cache.encode("utf-8")).hexdigest()

    openai_client = OpenAIClient()
    llm_model = await openai_client.model

    conn = await get_db_conn()
    if result := await get_llm_response_from_cache(conn, cache_key, llm_model):
        await conn.close()
        LOGGER.debug('found LLM response for %s model in the cache', llm_model)
        return JSONResponse({'data': result})

    tr = conn.transaction()
    await tr.start()
    try:
        # two equal queries will block, the second will fail with duplicate key error
        await conn.execute(
            'insert into llm_cache (hash, request, response, model_name) values ($1, $2, $3, $4)',
            cache_key, to_cache, None, llm_model,
        )
    except asyncpg.exceptions.UniqueViolationError:
        # other transaction saved an LLM response first, return it
        await tr.rollback()
        LOGGER.debug('return response committed by other transaction')
        result = await get_llm_response_from_cache(conn, cache_key, llm_model)
        await conn.close()
        return JSONResponse({'data': result})

    LOGGER.debug('asking LLM for commentary..')
    llm_response = await openai_client.get_llm_commentary(llm_request)
    await conn.execute(
        'update llm_cache set response = $1 where hash = $2 and model_name = $3',
        llm_response, cache_key, llm_model,
    )
    await tr.commit()
    await conn.close()
    LOGGER.debug('saved LLM response for hash = %s and model_name = %s', cache_key, llm_model)
    return JSONResponse({'data': llm_response})
