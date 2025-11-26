"""
Verification Audit Log Model
Tracks all changes and actions related to customer verification
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class VerificationAuditLog(Base):
    """
    Audit log for tracking all verification-related actions
    Includes admin actions, status changes, and user updates
    """
    __tablename__ = "verification_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True, index=True)

    # Action tracking
    action_type = Column(String(50), nullable=False, index=True)
    # Possible values:
    # - "status_change" - Verification status was changed
    # - "action_requested" - Admin requested additional action
    # - "data_updated" - User updated verification data
    # - "approved" - Admin approved verification
    # - "rejected" - Admin rejected verification
    # - "bvnk_created" - BVNK customer was created
    # - "bvnk_retry" - BVNK creation was retried

    # Verification details
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    old_result = Column(String(20), nullable=True)
    new_result = Column(String(20), nullable=True)

    # Step-specific tracking (for action requests)
    step_number = Column(Integer, nullable=True)  # 1, 2, 3, or 4
    step_name = Column(String(100), nullable=True)  # e.g., "Personal Information", "Tax Info"

    # Comments and messages
    comment = Column(Text, nullable=True)
    admin_message = Column(Text, nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="verification_audit_logs")
    admin = relationship("AdminUser", back_populates="verification_audit_logs")

    def __repr__(self):
        return f"<VerificationAuditLog(id={self.id}, user_id={self.user_id}, action_type={self.action_type})>"
