# app/core/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Tamagotchi"
    API_V1_STR: str = "/api/v1"

    # Add other settings here later, like database URLs, secret keys, etc.

    class Config:
        case_sensitive = True
        # env_file = ".env" # If you use a.env file

settings = Settings()