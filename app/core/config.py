from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "GateTix"
    environment: str = "development"

    database_url: str
    test_database_url: str | None = None

    secret_key: str
    algorithm:str = "HS256"
    access_token_expire_minutes: int = 60

    reservation_hold_minutes: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()