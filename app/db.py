import asyncpg

from app.secret import Secret
from app.settings import Settings

settings = Settings()
secret = Secret()


async def get_db_conn():
    return await asyncpg.connect(
        host=settings.PGHOST,
        port=settings.PGPORT,
        database=settings.PGDATABASE,
        user=settings.PGUSER,
        password=str(secret.PGPASSWORD)
    )
