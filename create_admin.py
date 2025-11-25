#!/usr/bin/env python3
"""
Create Admin User Script
Creates an admin user for the NFI Client Dashboard
"""

import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.auth.auth import get_password_hash
from app.models.admin_user import AdminUser, AdminRole

# Import all models to ensure they are registered with SQLAlchemy
import app.models.admin_login_history
import app.models.admin_user
import app.models.login_activity
import app.models.user
import app.models.user_counter
import app.models.verification_event
import app.models.wallet

def create_admin_user(email: str, password: str, username: str = None, full_name: str = None, is_super_admin: bool = False):
    """Create an admin user for the nfi-client-dashboard"""

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if admin already exists
        existing_admin = db.query(AdminUser).filter(AdminUser.email == email).first()
        if existing_admin:
            print(f"❌ Error: Admin with email '{email}' already exists!")
            print(f"   Username: {existing_admin.username}")
            return False

        # Generate username from email if not provided
        if not username:
            username = email.split('@')[0]

        # Check if username already exists
        existing_username = db.query(AdminUser).filter(AdminUser.username == username).first()
        if existing_username:
            print(f"❌ Error: Admin with username '{username}' already exists!")
            return False

        # Hash password
        hashed_password = get_password_hash(password)

        # Determine role
        role = AdminRole.SUPER_ADMIN if is_super_admin else AdminRole.STAFF

        # Create admin user
        admin_user = AdminUser(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name or username.title(),
            role=role,
            is_active=True,
            is_super_admin=is_super_admin,
            login_count=0
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("=" * 60)
        print("✅ Admin User Created Successfully!")
        print("=" * 60)
        print(f"ID:            {admin_user.id}")
        print(f"Username:      {admin_user.username}")
        print(f"Email:         {admin_user.email}")
        print(f"Full Name:     {admin_user.full_name}")
        print(f"Password:      {password}")
        print(f"Role:          {admin_user.role}")
        print(f"Super Admin:   {'Yes' if admin_user.is_super_admin else 'No'}")
        print(f"Status:        Active")
        print(f"Created At:    {admin_user.created_at}")
        print("=" * 60)
        print("\n📝 Login Credentials for NFI Client Dashboard:")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print(f"\n   OR")
        print(f"\n   Username: {username}")
        print(f"   Password: {password}")
        print("\n🌐 Dashboard URL: http://localhost:3000")
        print("\n⚠️  IMPORTANT: This is an ADMIN user for the dashboard,")
        print("   NOT an end-user customer account!")
        print("=" * 60)

        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Main function"""
    print("=" * 60)
    print("NFI Platform - Create Admin User")
    print("=" * 60)
    print()

    # Get email
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Enter admin email: ").strip()

    if not email:
        print("❌ Error: Email is required!")
        sys.exit(1)

    # Get password
    if len(sys.argv) > 2:
        password = sys.argv[2]
    else:
        password = input("Enter admin password: ").strip()

    if not password:
        print("❌ Error: Password is required!")
        sys.exit(1)

    if len(password) < 6:
        print("❌ Error: Password must be at least 6 characters!")
        sys.exit(1)

    print()

    # Create admin user
    success = create_admin_user(email, password)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
