from typing import Dict
from dataclasses import dataclass, field, fields, replace, asdict
from starlette.config import Config


@dataclass
class Settings:
    SENTRY_ENV: str = 'test'
    SENTRY_ENABLED: bool = True

    PORT: int = 8000
    DEBUG: bool = False

    INSIGHTS_API_URL: str = None
    USER_PROFILE_API_URL: str = None

    PGHOST: str = None
    PGPORT: int = 5432
    PGDATABASE: str = None
    PGUSER: str = None

    USER_AGENT: str = 'insights-llm-api'
    OPENAI_INSTRUCTIONS: str = None
    OPENAI_CONTEXT_LENGTH: int = 32000
    OPENAI_ASSISTANT: str = None

    @property
    def LOG_CONFIG(self):
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    '()': 'uvicorn.logging.DefaultFormatter',
                    'fmt': '{"level":"%(levelname)s", "timestamp":"%(asctime)s", "message":"%(message)s", "logger":"%(name)s"}'
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
