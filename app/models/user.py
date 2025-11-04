from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_2fa_enabled = Column(Boolean, default=False)
    two_fa_email = Column(String, nullable=True)
    two_fa_otp = Column(String, nullable=True)
    two_fa_otp_expiry = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Sumsub verification fields
    verification_status = Column(String, default="not_started")  # not_started, pending, completed, failed
    verification_result = Column(String, nullable=True)          # GREEN, RED, null
    sumsub_applicant_id = Column(String, nullable=True)
    sumsub_inspection_id = Column(String, nullable=True)
    verification_level_name = Column(String, nullable=True)
    verification_completed_at = Column(DateTime(timezone=True), nullable=True)
    verification_steps = Column(JSON, nullable=True)             # Track individual verification steps
    verification_error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    verification_events = relationship("VerificationEvent", back_populates="user")
    wallets = relationship("Wallet", back_populates="user")