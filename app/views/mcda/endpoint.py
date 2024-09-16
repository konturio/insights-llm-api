from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.clients.user_profile_client import get_app_data, feature_enabled
from .mcda import get_mcda_suggestion


async def mcda_suggestion(request: 'Request') -> 'Response':
    '''
    Handles GET requests to /mcda_suggestion

    Request format:
        - 'appId' (str): UUID of client application
        - 'query' (str): user search query

    Response format:
        - MCDA json
    '''
    data = request.query_params
    if not (app_id := data.get('appId')):
        raise HTTPException(status_code=400, detail='missing appId')
    if not (query := data.get('query').strip()):
        raise HTTPException(status_code=400, detail='missing query')

    app_data = await get_app_data(app_id, auth_token=request.headers.get('Authorization'))
    if feature_enabled('llm_mcda', app_data):
        bio = app_data['current_user'].get('bio')
        llm_mcda = await get_mcda_suggestion(query, bio)

    return JSONResponse(llm_mcda)
