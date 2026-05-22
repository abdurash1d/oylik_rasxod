from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Oylik Rasxot Bot"
    app_base_url: str = "http://localhost:8000"
    secret_key: str = "change-me"

    bot_token: str = ""
    owner_telegram_id: int = 0
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rasxot_bot"
    webapp_url: str = "http://localhost:8000/app"

    timezone: str = "Asia/Tashkent"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value


settings = Settings()
