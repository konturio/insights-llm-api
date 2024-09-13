import hashlib
import ujson as json

import asyncpg
from aiohttp import ClientSession
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.clients.user_profile_client import get_user_data, feature_enabled
from app.db import get_db_conn
from app.logger import LOGGER
from app.secret import Secret
from app.settings import Settings

settings = Settings()
secret = Secret()


async def get_nominatim_response_from_cache(conn, cache_key: str) -> dict | None:
    return await conn.fetchval(
        'select response from nominatim_cache where query_hash = $1 and response is not null',
        cache_key)


async def search_locations(query: str, lang: str) -> dict:
    '''
    search location in nominatim.
    returns results as FeatureCollection - each location is geojson with properties, bbox and geometry
    '''
    url = f'search?q={query}&format=geojson&polygon_geojson=1'
    if lang:
        url += f'&accept-language={lang}'
    cache_key = hashlib.md5(url.encode("utf-8")).hexdigest()

    conn = await get_db_conn()
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog',
    )
    if result := await get_nominatim_response_from_cache(conn, cache_key):
        await conn.close()
        LOGGER.debug('found response in cache')
        return result

    tr = conn.transaction()
    await tr.start()
    try:
        await conn.execute(
            'insert into nominatim_cache (query_hash, query, response) values ($1, $2, $3)',
            cache_key, url, None,
        )
    except asyncpg.exceptions.UniqueViolationError:
        # other transaction saved nominatim response first, return it
        await tr.rollback()
        LOGGER.debug('return nominatim response committed by other transaction')
        result = await get_nominatim_response_from_cache(conn, cache_key)
        await conn.close()
        return result

    async with ClientSession() as session:
        async with session.get('https://nominatim.openstreetmap.org/' + url) as response:
            nominatim_response = await response.json()
    await conn.execute(
        'update nominatim_cache set response = $1 where query_hash = $2',
        nominatim_response, cache_key,
    )
    await tr.commit()
    await conn.close()
    LOGGER.debug('saved nominatim response for query = %s', url)
    return nominatim_response


async def search(request: 'Request') -> 'Response':
    '''
    Handles GET requests to /search.

    Request format:
        - 'appId' (str): UUID of client application
        - 'query' (str): user search query

    Response format:
        - 'locations' (FeatureCollection): locations found by nominatim
    '''
    data = request.query_params
    if not (app_id := data.get('appId')):
        raise HTTPException(status_code=400, detail='missing appId')
    if not (query := data.get('query').strip()):
        raise HTTPException(status_code=400, detail='missing query')

    lang = request.headers.get('User-Language')
    search_results = {}

    user_data = await get_user_data(app_id, auth_token=request.headers.get('Authorization'))
    if feature_enabled('search_locations', user_data):
        locations = await search_locations(query, lang)
        for feature in locations['features']:
            feature['properties']['bbox'] = feature['bbox']
        search_results['locations'] = locations

    return JSONResponse(search_results)
