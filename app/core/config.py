from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GateTix"
    environment: str = "development"

    database_url: str
    test_database_url: str | None = None

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    reservation_hold_minutes: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", "test_database_url")
    @classmethod
    def use_the_psycopg2_driver(cls, value: str | None) -> str | None:
        """Hosting platforms hand out 'postgres://' or 'postgresql://' URLs.
        SQLAlchemy needs the driver named explicitly."""
        if value is None:
            return value
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix):]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()