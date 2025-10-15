from pydantic import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    """Application settings"""
    # App
    APP_NAME: str = "NFI Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: Optional[str] = None
    DATABASE_TYPE: str = "sqlite"  # "sqlite" or "d1"

    # Cloudflare D1 Configuration (when DATABASE_TYPE="d1")
    D1_ACCOUNT_ID: Optional[str] = None
    D1_DATABASE_ID: Optional[str] = None
    D1_API_TOKEN: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # KYC Providers
    SUMSUB_API_KEY: Optional[str] = None
    SUMSUB_SECRET_KEY: Optional[str] = None
    ONFIDO_API_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
