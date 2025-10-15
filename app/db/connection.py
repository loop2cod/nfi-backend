from typing import Optional, Union
from app.db.base import Database
from app.db.d1_http_client import D1HTTPClient
from app.core.config import settings

# Global database instance
_db: Optional[Union[Database, D1HTTPClient]] = None

def get_db() -> Union[Database, D1HTTPClient]:
    """
    Get database instance (singleton pattern)

    Returns SQLite Database or D1HTTPClient based on configuration.

    Configuration via environment variables:
    - DATABASE_TYPE="sqlite" (default) - Uses local SQLite
    - DATABASE_TYPE="d1" - Uses Cloudflare D1 via HTTP API
    """
    global _db
    if _db is None:
        if settings.DATABASE_TYPE == "d1":
            # Use Cloudflare D1 via HTTP API
            if not all([settings.D1_ACCOUNT_ID, settings.D1_DATABASE_ID, settings.D1_API_TOKEN]):
                raise ValueError(
                    "D1 configuration incomplete. Required: D1_ACCOUNT_ID, D1_DATABASE_ID, D1_API_TOKEN"
                )

            _db = D1HTTPClient(
                account_id=settings.D1_ACCOUNT_ID,
                database_id=settings.D1_DATABASE_ID,
                api_token=settings.D1_API_TOKEN
            )
            print("📊 Connected to Cloudflare D1 via HTTP API")
        else:
            # Use local SQLite
            db_path = settings.DATABASE_URL or "nfi_platform.db"
            _db = Database(db_path)
            print(f"📊 Connected to SQLite: {db_path}")

    return _db

def init_db(schema_path: str = "database/schema.sql") -> None:
    """
    Initialize database with schema

    This should be run once during application startup
    or when setting up a new database.
    """
    db = get_db()
    db.init_schema(schema_path)

def close_db() -> None:
    """Close database connection"""
    global _db
    if _db:
        if hasattr(_db, 'close'):
            _db.close()
        _db = None
