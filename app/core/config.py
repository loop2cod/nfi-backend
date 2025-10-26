from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # -------------------------
    # Application Info
    # -------------------------
    APP_NAME: str = "NFI Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # -------------------------
    # Security / JWT
    # -------------------------
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -------------------------
    # Database
    # -------------------------
    DATABASE_URL: Optional[str] = "sqlite:///./nfi.db"
    DATABASE_TYPE: Optional[str] = "sqlite"  # e.g., "sqlite" or "d1" for Cloudflare D1
    D1_ACCOUNT_ID: Optional[str] = None
    D1_DATABASE_ID: Optional[str] = None
    D1_API_TOKEN: Optional[str] = None

    # -------------------------
    # Google OAuth
    # -------------------------
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/auth/google/callback"

    # -------------------------
    # KYC Providers
    # -------------------------
    SUMSUB_TOKEN: Optional[str] = None
    SUMSUB_SECRET_KEY: Optional[str] = None
    SUMSUB_BASE_URL: str = "https://api.sumsub.com"
    SUMSUB_APP_TOKEN: Optional[str] = None
    SUMSUB_API_KEY: Optional[str] = None
    ONFIDO_API_TOKEN: Optional[str] = None

    # -------------------------
    # CORS
    # -------------------------
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005"
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore extra env vars not defined here


# Create a settings instance
settings = Settings()
