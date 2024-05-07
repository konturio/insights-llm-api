from typing import Dict
from dataclasses import dataclass, fields, replace, asdict
from starlette.config import Config


@dataclass
class Settings:
    SENTRY_ENV: str = 'test'
    SENTRY_ENABLED: bool = True

    DEBUG: bool = False

    INSIGHTS_API_URL: str = None
    USER_PROFILE_API_URL: str = None

    PGHOST: str = None
    PGPORT: int = 5432
    PGDATABASE: str = None
    PGUSER: str = None

    USER_AGENT: str = 'insights-llm-api'
    LLM_MODEL_NAME: str = None
    OPENAI_INSTRUCTIONS: str = None
    OPENAI_CONTEXT_LENGTH: int = 32000

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
