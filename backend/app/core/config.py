from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_access_token_minutes: int = Field(default=20, gt=0, le=60)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    docs_enabled: bool = True
    environment: str = "development"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment == "production":
            if len(self.jwt_secret) < 32:
                raise ValueError("Production JWT_SECRET must be a unique secret of at least 32 characters")
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("Production CORS origins must be explicitly configured")
            if not self.database_url.startswith(("postgresql://", "postgresql+")):
                raise ValueError("Production database configuration must use PostgreSQL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
