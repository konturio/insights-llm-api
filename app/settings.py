from typing import Dict
from dataclasses import dataclass, field, fields, replace, asdict
try:
    from starlette.config import Config
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    import os

    class Config:
        def __init__(self, env_file: str):
            self.env_file = env_file

        def __call__(self, key: str, cast=str, default=None):
            return cast(os.getenv(key, default))


@dataclass
class Settings:
    SENTRY_ENV: str = 'test'
    SENTRY_ENABLED: bool = True

    WORKERS: int = 4
    PORT: int = 8000
    DEBUG: bool = False

    INSIGHTS_API_URL: str = None
    USER_PROFILE_API_URL: str = None

    PGHOST: str = None
    PGPORT: int = 5432
    PGDATABASE: str = None
    PGUSER: str = None

    USER_AGENT: str = 'insights-llm-api'
    OPENAI_ANALYTICS_INSTRUCTIONS: str = None
    # how many analytics sentences we want to include into prompt:
    MAX_ANALYTICS_SENTENCES: int = 400
    OPENAI_ANALYTICS_ASSISTANT: str = None
    OPENAI_MCDA_ASSISTANT: str = None
    OPENAI_MCDA_INSTRUCTIONS: str = None

    @property
    def LOG_CONFIG(self):
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    '()': 'uvicorn.logging.DefaultFormatter',
                    'fmt': '{"level":"%(levelname)s", "pid":"%(process)s", "timestamp":"%(asctime)s", "message":"%(message)s", "logger":"%(name)s"}'
                }
            },
            'handlers': {
                'default': {
                    'formatter': 'json',
                    'class': 'logging.StreamHandler'
                }
            },
            'loggers': {
                'uvicorn': {
                    'handlers': ['default'],
                    'level': 'DEBUG' if self.DEBUG else 'INFO'
                }
            }
        }

    def __post_init__(self):
        config = Config('../.env')
        for field in fields(self):
            value = getattr(self, field.name)
            if value == field.default:
                setattr(self, field.name, config(field.name, cast=field.type, default=field.default))
            elif not isinstance(value, field.type):
                setattr(self, field.name, field.type(value))

    def copy(self) -> 'Settings':
        return replace(self)

    def asdict(self) -> Dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}
