from typing import Optional, List, Dict, Any
from app.db.base import Database
from app.models.roles import UserRole, get_user_tier_from_role
import uuid

class UserRepository:
    """Repository for user database operations"""

    def __init__(self, db: Database):
        self.db = db

    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        now = self.db.now()

        # Get tier from role
        tier = get_user_tier_from_role(UserRole(user_data['role']))

        query = """
            INSERT INTO users (
                id, email, password_hash, first_name, last_name, phone,
                role, tier, tenant_id, parent_id, status, is_verified, email_verified,
                kyc_status, kyc_provider, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            user_id,
            user_data['email'],
            user_data['password_hash'],
            user_data['first_name'],
            user_data['last_name'],
            user_data['phone'],
            user_data['role'],
            tier.value,
            user_data.get('tenant_id'),
            user_data.get('parent_id'),
            user_data.get('status', 'active'),
            0,  # is_verified
            0,  # email_verified
            user_data.get('kyc_status'),
            user_data.get('kyc_provider'),
            now,
            now
        )

        self.db.execute(query, params)
        return self.get_by_id(user_id)

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = ?"
        row = self.db.fetch_one(query, (user_id,))
        return self.db.row_to_dict(row) if row else None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = ?"
        row = self.db.fetch_one(query, (email,))
        return self.db.row_to_dict(row) if row else None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all users with pagination"""
        query = "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?"
        rows = self.db.fetch_all(query, (limit, offset))
        return [self.db.row_to_dict(row) for row in rows]

    def get_by_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all users in a tenant"""
        query = "SELECT * FROM users WHERE tenant_id = ? ORDER BY created_at DESC"
        rows = self.db.fetch_all(query, (tenant_id,))
        return [self.db.row_to_dict(row) for row in rows]

    def get_by_parent(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all users under a parent"""
        query = "SELECT * FROM users WHERE parent_id = ? ORDER BY created_at DESC"
        rows = self.db.fetch_all(query, (parent_id,))
        return [self.db.row_to_dict(row) for row in rows]

    def get_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all users with a specific role"""
        query = "SELECT * FROM users WHERE role = ? ORDER BY created_at DESC"
        rows = self.db.fetch_all(query, (role,))
        return [self.db.row_to_dict(row) for row in rows]

    def update(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user"""
        update_data['updated_at'] = self.db.now()

        # Build dynamic UPDATE query
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        query = f"UPDATE users SET {set_clause} WHERE id = ?"

        params = tuple(update_data.values()) + (user_id,)
        self.db.execute(query, params)

        return self.get_by_id(user_id)

    def update_last_login(self, user_id: str) -> None:
        """Update last login timestamp"""
        query = "UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?"
        now = self.db.now()
        self.db.execute(query, (now, now, user_id))

    def update_kyc_status(self, user_id: str, kyc_status: str, kyc_provider: str = None) -> Optional[Dict[str, Any]]:
        """Update KYC status"""
        now = self.db.now()
        query = """
            UPDATE users
            SET kyc_status = ?, kyc_provider = ?, status = ?, updated_at = ?
            WHERE id = ?
        """

        # Update user status based on KYC status
        user_status = 'active' if kyc_status == 'approved' else 'kyc_rejected' if kyc_status == 'rejected' else 'pending_kyc'

        self.db.execute(query, (kyc_status, kyc_provider, user_status, now, user_id))
        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> bool:
        """Delete user (soft delete by setting status to inactive)"""
        query = "UPDATE users SET status = 'inactive', updated_at = ? WHERE id = ?"
        self.db.execute(query, (self.db.now(), user_id))
        return True

    def hard_delete(self, user_id: str) -> bool:
        """Permanently delete user"""
        query = "DELETE FROM users WHERE id = ?"
        self.db.execute(query, (user_id,))
        return True

    def exists(self, email: str) -> bool:
        """Check if user with email exists"""
        query = "SELECT COUNT(*) FROM users WHERE email = ?"
        count = self.db.fetch_value(query, (email,))
        return count > 0

    def count(self) -> int:
        """Get total user count"""
        query = "SELECT COUNT(*) FROM users"
        return self.db.fetch_value(query)

    def count_by_role(self, role: str) -> int:
        """Count users by role"""
        query = "SELECT COUNT(*) FROM users WHERE role = ?"
        return self.db.fetch_value(query, (role,))

    def count_by_status(self, status: str) -> int:
        """Count users by status"""
        query = "SELECT COUNT(*) FROM users WHERE status = ?"
        return self.db.fetch_value(query, (status,))
