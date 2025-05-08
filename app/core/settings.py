# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Tamagotchi"
    API_V1_STR: str = "/api/v1"

    MONGO_CONNECTION_URI: str
    MONGO_DATABASE_NAME: str

    # model_config allows pydantic-settings to load from.env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()