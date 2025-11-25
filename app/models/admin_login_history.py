"""
Admin Login History Model
Tracks each login event for admin users
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AdminLoginHistory(Base):
    """
    Admin Login History Model
    Records each login event for audit and security purposes
    """
    __tablename__ = "admin_login_history"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False, index=True)

    # Login details
    login_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # New fields
    login_method = Column(String, nullable=True)  # email, username
    login_status = Column(String, default="success", nullable=False)  # success, failed
    location = Column(String, nullable=True)  # City, Country
    device_type = Column(String, nullable=True)  # Desktop, Mobile, Tablet

    # Relationship
    admin = relationship("AdminUser", backref="login_history")

    def __repr__(self):
        return f"<AdminLoginHistory(admin_id={self.admin_id}, login_at='{self.login_at}', status='{self.login_status}')>"
