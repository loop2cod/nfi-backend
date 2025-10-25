from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./nfi.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = "83042478166-jmc7bpouu0jpqsp1dbkqtqfpi3ls46t9.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "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"
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/auth/google/callback"

    # Sumsub KYC
    SUMSUB_API_TOKEN: str = "pjRs8KgzcYmnOIr5hHGMKWJa.hHiMgM4qzVsbmJ4odl9Cj8PevEBwaTuP"  # Remove sbx: prefix
    SUMSUB_API_SECRET: str = "mailMdNZRQT2QFeEkh2jlaDbJAFf9jfy"
    SUMSUB_BASE_URL: str = "https://api.sandbox.sumsub.com"  # Use sandbox URL

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        env_file = ".env"


settings = Settings()