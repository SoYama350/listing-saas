from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_secret_key: str = "dev-insecure-secret-change-me"
    database_url: str = "sqlite+aiosqlite:///./listingsaas.db"
    base_url: str = "http://localhost:8000"

    telegram_bot_token: str = ""
    owner_telegram_id: int | None = None

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"

    credential_encryption_key: str = ""

    @property
    def fernet(self) -> Fernet:
        return _fernet(self.credential_encryption_key)


@lru_cache
def _fernet(key: str) -> Fernet:
    if not key:
        # generate an ephemeral key for dev if none set (creds won't survive restart)
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode())


settings = Settings()
BASE_DIR = Path(__file__).resolve().parent


def encrypt(plain: str) -> str:
    return settings.fernet.encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return settings.fernet.decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""
