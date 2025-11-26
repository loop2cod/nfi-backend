"""
Admin User Model
Separate model for platform administrators who access the nfi-client-dashboard
This is completely separate from the User model (end users/customers)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class AdminRole(str, enum.Enum):
    """Admin role types"""
    SUPER_ADMIN = "super_admin"        # Full system access, can manage admins
    STAFF = "staff"                    # Staff access, cannot manage other admins


class AdminUser(Base):
    """
    Admin User Model
    For administrators who manage the platform via nfi-client-dashboard
    Completely separate from end-user customers
    """
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)  # Admin username
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    # Admin specific fields
    role = Column(SQLEnum(AdminRole, values_callable=lambda obj: [e.value for e in obj]), default=AdminRole.STAFF, nullable=False)
    is_active = Column(Boolean, default=True)
    is_super_admin = Column(Boolean, default=False)

    # Login tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # Admin ID who created this admin

    # Relationships
    login_activities = relationship("AdminLoginHistory", back_populates="admin_user", lazy="dynamic")
    verification_audit_logs = relationship("VerificationAuditLog", back_populates="admin", lazy="dynamic")

    def __repr__(self):
        return f"<AdminUser(username='{self.username}', email='{self.email}', role='{self.role}')>"
