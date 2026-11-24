from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg://dac_app:local@localhost:5434/dac'
    secret_key: str = Field(min_length=32)
    cookie_secure: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)
    environment: str = 'development'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache
def settings():
    return Settings()
