import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "investmind"
    # Fallback encryption key/passphrase for server-side key derivation if user doesn't supply one
    SERVER_ENCRYPTION_PASSPHRASE: str = "investmind-default-fallback-encryption-passphrase-change-me"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
