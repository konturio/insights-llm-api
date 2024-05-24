from typing import TYPE_CHECKING

import sentry_sdk
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from .settings import Settings
from .secret import Secret
from .llm_analytics import llm_analytics


settings = Settings()
secret = Secret()

if TYPE_CHECKING:
    from starlette.requests import Request

if settings.SENTRY_ENABLED:
    sentry_sdk.init(
        dsn=secret.SENTRY_DSN,
        enable_tracing=True,
        environment=settings.SENTRY_ENV,
    )


async def health(request: 'Request') -> 'Response':
    return PlainTextResponse('ok')


routes = [
    Route("/llm-analytics", methods=['POST'], endpoint=llm_analytics),
    Route("/health", endpoint=health),
]

app = Starlette(routes=routes)


def create_app():
    # sentry sdk wrapps the app into factory, so uvicorn should receive a callable
    return app

if __name__ == '__main__':
    import uvicorn

    uvicorn.run("app.main:create_app", host="0.0.0.0", port=settings.PORT, factory=True, log_config=settings.LOG_CONFIG, workers=settings.WORKERS)
