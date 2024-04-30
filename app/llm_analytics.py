import hashlib

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


def md5_to_uuid(s):
    return '-'.join([s[:8], s[8:12], s[12:16], s[16:20], s[20:]])


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
    conn = await get_db_conn()
    llm_request = f"generated request for some polygon, analytics and {bio}"
    cache_key = md5_to_uuid(hashlib.md5(llm_request.encode("utf-8")).hexdigest())

    if result := await conn.fetchval(
            'select response from llm_cache where hash = $1 and model_name = $2',
            cache_key, settings.LLM_MODEL_NAME):
        await conn.close()
        return JSONResponse({'data': result})

    llm_response = f'personalized analytics summary for {user} with bio {bio}'
    await conn.execute(
        'insert into llm_cache (hash, request, response, model_name) values ($1, $2, $3, $4)',
        cache_key, llm_request, llm_response, settings.LLM_MODEL_NAME,
    )
    await conn.close()
    return JSONResponse({'data': llm_response})

