from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Food Delivery Voice Support Agent"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security
    JWT_SECRET: str = "insecure-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./voice_agent.db"

    # LLM / Voice providers
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    STT_MODEL: str = "whisper-1"
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"

    # Guardrails
    MAX_INPUT_CHARS: int = 2000
    ENABLE_PII_REDACTION: bool = True
    GUARDRAIL_LLM_JUDGE: bool = False

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
