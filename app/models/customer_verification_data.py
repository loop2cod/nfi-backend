from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Date, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CustomerVerificationData(Base):
    """
    Stores customer verification data collected across multiple steps.
    This data is used to create a BVNK customer after all verification steps are complete.
    """
    __tablename__ = "customer_verification_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Step 1: Personal Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2 country code
    email_address = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)

    # Address fields
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    postal_code = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    country_code = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    state_code = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)

    # Step 2: Sumsub Liveness Check (tracked in main User model)
    # sumsub_completed = Column(Boolean, default=False)
    # sumsub_applicant_id is already in User model

    # Step 3: Tax Information
    tax_identification_number = Column(String(50), nullable=True)  # SSN/ITIN for US, tax number for others
    tax_residence_country_code = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2

    # Step 4: CDD (Customer Due Diligence)
    employment_status = Column(String(50), nullable=True)
    # Options: SELF_EMPLOYED, SALARIED, UNEMPLOYED, RETIRED, NOT_PROVIDED

    source_of_funds = Column(String(50), nullable=True)
    # Options: SALARY, PENSION, SAVINGS, SELF_EMPLOYMENT, CRYPTO_TRADING, GAMBLING, REAL_ESTATE

    pep_status = Column(String(50), nullable=True)
    # Options: NOT_PEP, FORMER_PEP_2_YEARS, FORMER_PEP_OLDER, DOMESTIC_PEP, FOREIGN_PEP,
    #          CLOSE_ASSOCIATES, FAMILY_MEMBERS

    account_purpose = Column(String(50), nullable=True)
    # Options: TRANSFERS_OWN_WALLET, TRANSFERS_FAMILY_FRIENDS, INVESTMENTS, GOODS_SERVICES, DONATIONS

    expected_monthly_volume_amount = Column(Numeric(10, 2), nullable=True)
    expected_monthly_volume_currency = Column(String(3), nullable=True)  # USD or EUR

    # Step tracking
    step_1_completed = Column(Boolean, default=False)
    step_1_completed_at = Column(DateTime(timezone=True), nullable=True)

    step_2_completed = Column(Boolean, default=False)
    step_2_completed_at = Column(DateTime(timezone=True), nullable=True)

    step_3_completed = Column(Boolean, default=False)
    step_3_completed_at = Column(DateTime(timezone=True), nullable=True)

    step_4_completed = Column(Boolean, default=False)
    step_4_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Overall completion
    all_steps_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    step_data = Column(JSON, nullable=True)  # Store any additional step-specific data

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="verification_data")
