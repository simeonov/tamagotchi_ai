# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Tamagotchi"
    API_V1_STR: str = "/api/v1"

    MONGO_CONNECTION_URI: str
    MONGO_DATABASE_NAME: str

    GLOBAL_TICK_INTERVAL_SECONDS: int = 10  # Default value if not in.env
    LOG_LEVEL: str = "INFO"  # Default log level

    model_config = SettingsConfigDict(env_file=".env", extra="ignore",
                                      case_sensitive=False)  # case_sensitive=False for env vars


settings = Settings()