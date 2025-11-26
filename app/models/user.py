from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)  # Format: NF-MMYYYY### (e.g., NF-012025001)
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

    # BVNK integration fields
    bvnk_customer_id = Column(String, nullable=True, unique=True, index=True)  # BVNK customer UUID
    bvnk_customer_created_at = Column(DateTime(timezone=True), nullable=True)
    bvnk_customer_status = Column(String, nullable=True)  # ACTIVE, SUSPENDED, CLOSED

    # Customer information (synced with BVNK)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(String, nullable=True)  # ISO 8601 date format
    nationality = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    phone_number = Column(String(20), nullable=True)

    # Address (synced with BVNK)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    postal_code = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    country_code = Column(String(2), nullable=True)
    state_code = Column(String(10), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships (lazy loading to avoid circular imports)
    verification_events = relationship("VerificationEvent", back_populates="user", lazy="dynamic")
    wallets = relationship("Wallet", back_populates="user", lazy="dynamic")
    login_activities = relationship("LoginActivity", back_populates="user", lazy="dynamic")
    verification_data = relationship("CustomerVerificationData", back_populates="user", uselist=False)