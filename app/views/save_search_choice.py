import ujson as json
from json.decoder import JSONDecodeError

from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.clients.user_profile_client import get_app_data, feature_enabled
from app.db import get_db_conn
from app.logger import LOGGER


async def save_search_choice(request: 'Request') -> 'Response':
    '''
    Handles POST requests to /search/click.

    Request format:
        - 'appId' (str): UUID of client application
        - 'query' (str): user query
        - 'searchResults' (list[tuple[str, FeatureCollection]]): search results
        - 'selectedFeature' (Feature): user choice
        - 'selectedFeatureType' (str): locations | layers | indicators | ...
    '''
    try:
        data = await request.json()
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail='malformed request')

    if not (app_id := data.get('appId')):
        raise HTTPException(status_code=400, detail='missing appId')
    app_data = await get_app_data(app_id, auth_token=request.headers.get('Authorization'), user_data=False)
    if not feature_enabled('search_bar', app_data):
        raise HTTPException(status_code=403, detail='search is not enabled for the user')

    if not (query := data.get('query').strip()):
        raise HTTPException(status_code=400, detail='missing query')
    if not (search_results := data.get('searchResults')):
        raise HTTPException(status_code=400, detail='missing searchResults')
    if not (feature := data.get('selectedFeature')):
        raise HTTPException(status_code=400, detail='missing selectedFeature')
    if not (feature_type := data.get('selectedFeatureType')):
        raise HTTPException(status_code=400, detail='missing selectedFeatureType')

    conn = await get_db_conn()
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog',
    )
    await conn.execute('''
        insert into search_history
        (app_id, query, search_results, selected_feature, selected_feature_type)
        values ($1, $2, $3, $4, $5)''',
        app_id, query, search_results, feature, feature_type
    )
    await conn.close()
    LOGGER.debug('saved user choice for query = %s', query)

    return JSONResponse({})
