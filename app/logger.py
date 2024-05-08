import logging

from .settings import Settings


settings = Settings()
LOGGER = logging.getLogger('uvicorn')
LOGGER.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
