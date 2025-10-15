#!/usr/bin/env python3
"""
Initialize the database with schema and optionally create a super admin user
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connection import init_db, get_db
from app.db.repositories import UserRepository
from app.core.security import get_password_hash
from app.models.roles import UserRole

def create_super_admin():
    """Create initial super admin user"""
    db = get_db()
    user_repo = UserRepository(db)

    # Check if super admin already exists
    existing_admin = user_repo.get_by_email("admin@nfigate.com")
    if existing_admin:
        print("✓ Super admin already exists")
        return

    # Create super admin
    admin_data = {
        "email": "admin@nfigate.com",
        "password_hash": get_password_hash("Admin123!Change"),
        "first_name": "Super",
        "last_name": "Admin",
        "phone": "+1234567890",
        "role": UserRole.SUPER_ADMIN.value,
        "tenant_id": None,
        "parent_id": None,
        "status": "active",
    }

    user_repo.create(admin_data)
    print("✓ Super admin created")
    print("  Email: admin@nfigate.com")
    print("  Password: Admin123!Change")
    print("  ⚠️  IMPORTANT: Change this password immediately!")

if __name__ == "__main__":
    print("🚀 Initializing NFI Platform Database...\n")

    # Initialize schema
    print("📋 Creating database schema...")
    init_db()
    print()

    # Create super admin
    print("👤 Creating super admin user...")
    create_super_admin()
    print()

    print("✅ Database initialization complete!")
    print("\nNext steps:")
    print("1. Change the super admin password")
    print("2. Start the API server: uvicorn main:app --reload")
    print("3. Visit http://localhost:8000/docs for API documentation")
