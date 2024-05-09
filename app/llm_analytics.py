import hashlib

import asyncpg
from aiohttp import ClientSession
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from .secret import Secret
from .settings import Settings
from .logger import LOGGER
from .insights_api_client import get_analytics_sentences
from .openai_client import get_llm_commentary, get_llm_prompt

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


def md5_to_uuid(s):
    return '-'.join([s[:8], s[8:12], s[12:16], s[16:20], s[20:]])


async def get_user_data(auth_token: str) -> dict:
    url = settings.USER_PROFILE_API_URL + '/users/current_user'
    headers = {
        'Authorization': auth_token,
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status)
            return await resp.json()


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
    LOGGER.debug('got user data')
    bio = user_data.get('bio')

    data = await request.json()
    LOGGER.debug(f'asking insights-api {settings.INSIGHTS_API_URL} for advanced analytics..')
    sentences = await get_analytics_sentences(selected_area=data.get("area"), aoi=None)
    LOGGER.debug('got advanced analytics')

    # build cache key from request and check if it's in llm_cache table
    llm_request = get_llm_prompt(sentences, bio)
    cache_key = md5_to_uuid(hashlib.md5(llm_request.encode("utf-8")).hexdigest())

    conn = await get_db_conn()
    if result := await conn.fetchval(
            'select response from llm_cache where hash = $1 and model_name = $2',
            cache_key, settings.LLM_MODEL_NAME):
        await conn.close()
        LOGGER.debug('found LLM response in the cache')
        return JSONResponse({'data': result})

    LOGGER.debug('asking LLM for commentary..')
    llm_response = await get_llm_commentary(llm_request)
    await conn.execute(
        'insert into llm_cache (hash, request, response, model_name) values ($1, $2, $3, $4)',
        cache_key, llm_request, llm_response, settings.LLM_MODEL_NAME,
    )
    await conn.close()
    LOGGER.debug('saved LLM response')
    return JSONResponse({'data': llm_response})
