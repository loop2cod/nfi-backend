from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
import logging


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
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/auth/google/callback"

    # -------------------------
    # KYC Providers
    # -------------------------
    SUMSUB_TOKEN: Optional[str] = None
    SUMSUB_SECRET_KEY: Optional[str] = None
    SUMSUB_BASE_URL: str = "https://api.sumsub.com"
    SUMSUB_APP_TOKEN: Optional[str] = None
    SUMSUB_API_KEY: Optional[str] = None
    SUMSUB_WEBHOOK_SECRET: Optional[str] = None  # Webhook signature verification
    ONFIDO_API_TOKEN: Optional[str] = None

    # -------------------------
    # Dfns Wallet Service
    # -------------------------
    DFNS_BASE_URL: str = "https://api.dfns.io"
    DFNS_ORG_ID: Optional[str] = None
    DFNS_AUTH_TOKEN: Optional[str] = None
    DFNS_PRIVATE_KEY: Optional[str] = None
    DFNS_CRED_ID: Optional[str] = None

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

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator('GOOGLE_CLIENT_ID')
    @classmethod
    def validate_google_client_id(cls, v):
        if v is None:
            return v
        if not v:
            raise ValueError("GOOGLE_CLIENT_ID cannot be empty if provided")
        return v

    def validate_production_config(self):
        """Validate configuration for production deployment"""
        logger = logging.getLogger(__name__)
        
        if not self.DEBUG:
            warnings = []
            
            if not self.SUMSUB_WEBHOOK_SECRET:
                warnings.append("SUMSUB_WEBHOOK_SECRET not set - webhook signature verification disabled")
            
            if not self.SUMSUB_APP_TOKEN:
                warnings.append("SUMSUB_APP_TOKEN not set - Sumsub integration may not work")
                
            if self.SECRET_KEY == "your-secret-key-here-change-in-production":
                raise ValueError("SECRET_KEY must be changed in production")
            
            for warning in warnings:
                logger.warning(f"Production config warning: {warning}")

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore extra env vars not defined here


# Create a settings instance
settings = Settings()

# Validate production configuration
settings.validate_production_config()
