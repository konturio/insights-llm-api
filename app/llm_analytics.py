import asyncpg
from aiohttp import ClientSession
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from secret import Secret
from settings import Settings


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


async def llm_analytics(request: 'Request') -> 'Response':
    url = settings.USER_PROFILE_API_URL + '/users/current_user'
    headers = {
        'Authorization': request.headers.get('Authorization') or '',
        'User-Agent': settings.USER_AGENT,
    }
    async with ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status)
            data = await resp.json()
    user = data['username']
    bio = data['bio']
    data = {'data': f'personalized analytics summary for {user} with bio {bio}'}
    return JSONResponse(data)

