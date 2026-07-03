import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "investmind"
    JWT_SECRET_KEY: str = "investmind-super-secure-jwt-signing-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 1440  # Default 24 hours

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
