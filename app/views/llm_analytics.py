from json.decoder import JSONDecodeError

from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.clients.insights_api_client import get_analytics_sentences
from app.clients.openai_client import get_analytics_prompt, OpenAIClient
from app.clients.user_profile_client import get_user_data, feature_enabled
from app.logger import LOGGER
from app.settings import Settings

settings = Settings()


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
    prompt = get_analytics_prompt(sentences, indicator_description, bio, lang, selected_area_geojson, reference_area_geojson)
    openai_client = OpenAIClient(
        assistant_name=settings.OPENAI_ANALYTICS_ASSISTANT,
        instructions=settings.OPENAI_ANALYTICS_INSTRUCTIONS,
        override_instructions=True)
    llm_response = await openai_client.get_cached_llm_commentary(prompt)
    return JSONResponse({'data': llm_response})
