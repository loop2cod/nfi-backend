from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class VerificationEvent(Base):
    __tablename__ = "verification_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String, nullable=False)  # applicantCreated, applicantReviewed, etc.
    event_data = Column(JSON, nullable=False)    # Full webhook payload
    applicant_id = Column(String, nullable=True)
    inspection_id = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)
    review_status = Column(String, nullable=True)  # init, pending, completed, etc.
    review_result = Column(String, nullable=True)  # GREEN, RED, null
    level_name = Column(String, nullable=True)
    external_user_id = Column(String, nullable=True)
    sandbox_mode = Column(String, nullable=True)
    client_id = Column(String, nullable=True)
    processed = Column(String, default=False)     # Whether this event has been processed
    error_message = Column(Text, nullable=True)   # Any error during processing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="verification_events")