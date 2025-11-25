from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class LoginActivity(Base):
    """Login activity tracking for End User Customers (nfi-end_user)"""
    __tablename__ = "login_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Login details
    login_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String, nullable=False)  # success, failed, 2fa_pending, 2fa_success
    method = Column(String, nullable=False)  # email_password, google_oauth, etc.

    # Location and device info
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    device_type = Column(String, nullable=True)  # mobile, desktop, tablet
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)

    # Location (can be derived from IP or provided)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    location = Column(String, nullable=True)  # Combined location string

    # Additional metadata
    is_new_device = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    failure_reason = Column(String, nullable=True)  # For failed login attempts

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="login_activities")
