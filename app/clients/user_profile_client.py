from aiohttp import ClientSession
from starlette.exceptions import HTTPException

from app.logger import LOGGER
from app.settings import Settings

settings = Settings()


def feature_enabled(feature, user_data) -> bool:
    return feature in user_data['features_enabled']


async def get_user_data(app_id: str, auth_token: str, features_config=False) -> dict:
    '''
    get info about user and app features from UPS.
    features_config flag indicates if it's necessary to request app configuration
    '''
    headers = {
        'Authorization': auth_token or '',
        'User-Agent': settings.USER_AGENT,
    }
    result = {}
    LOGGER.debug(f'asking UPS {settings.USER_PROFILE_API_URL} for user data..')
    async with ClientSession(headers=headers) as session:
        url = settings.USER_PROFILE_API_URL + '/users/current_user'
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.text())
            result['current_user'] = await resp.json()

        if features_config:
            url = settings.USER_PROFILE_API_URL + '/apps/' + app_id
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail=await resp.text())
                app_config = await resp.json()
                result['features_config'] = app_config['featuresConfig']

        url = settings.USER_PROFILE_API_URL + '/features?appId=' + app_id
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.text())
            features = await resp.json()
            result['features_enabled'] = frozenset(x['name'] for x in features)

    return result
