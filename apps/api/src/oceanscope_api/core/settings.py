from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OCEANSCOPE_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    public_base_url: str | None = None
    cors_origins: str = ""
    data_directory: Path = Path("data")
    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None
    pelyr_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="PELYR_API_KEY",
    )
    live_ais_origins: str = ""
    aisstream_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="AISSTREAM_API_KEY",
    )

    @field_validator("public_base_url")
    @classmethod
    def reject_blank_url(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value

    @field_validator("pelyr_api_key", mode="before")
    @classmethod
    def reject_blank_pelyr_key(cls, value: object) -> object:
        if value is None:
            return None
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        return None if not raw_value.strip() else value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def live_ais_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.live_ais_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
