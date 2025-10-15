from typing import Optional, Dict, Any
from app.db.base import Database
import uuid

class AuthRepository:
    """Repository for authentication-related database operations"""

    def __init__(self, db: Database):
        self.db = db

    def create_refresh_token(self, user_id: str, token: str, expires_at: int) -> str:
        """Store a refresh token"""
        token_id = str(uuid.uuid4())
        now = self.db.now()

        query = """
            INSERT INTO refresh_tokens (id, user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
        """

        self.db.execute(query, (token_id, user_id, token, expires_at, now))
        return token_id

    def get_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token details"""
        query = """
            SELECT * FROM refresh_tokens
            WHERE token = ? AND revoked = 0 AND expires_at > ?
        """
        now = self.db.now()
        row = self.db.fetch_one(query, (token, now))
        return self.db.row_to_dict(row) if row else None

    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token"""
        query = """
            UPDATE refresh_tokens
            SET revoked = 1, revoked_at = ?
            WHERE token = ?
        """
        self.db.execute(query, (self.db.now(), token))
        return True

    def revoke_all_user_tokens(self, user_id: str) -> bool:
        """Revoke all refresh tokens for a user"""
        query = """
            UPDATE refresh_tokens
            SET revoked = 1, revoked_at = ?
            WHERE user_id = ? AND revoked = 0
        """
        self.db.execute(query, (self.db.now(), user_id))
        return True

    def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens"""
        query = "DELETE FROM refresh_tokens WHERE expires_at < ?"
        cursor = self.db.execute(query, (self.db.now(),))
        return cursor.rowcount

    def get_user_active_tokens(self, user_id: str) -> int:
        """Count active refresh tokens for a user"""
        query = """
            SELECT COUNT(*) FROM refresh_tokens
            WHERE user_id = ? AND revoked = 0 AND expires_at > ?
        """
        return self.db.fetch_value(query, (user_id, self.db.now()))
