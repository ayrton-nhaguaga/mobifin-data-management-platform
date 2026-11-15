from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='../.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://mobifin:mobifin@localhost:5432/mobifin'
    jwt_secret: str = Field(min_length=32)
    token_minutes: int = 60
    cors_origins: str = 'http://localhost:5173,http://localhost:8080'
    demo_password: str = Field(min_length=12)
    upload_limit: int = 10 * 1024 * 1024
    report_deadline_days: int = Field(default=1, ge=0, le=30)


@lru_cache
def settings():
    return Settings()
