from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal


# ============================================================================
# Step 1: Personal Information
# ============================================================================

class AddressSchema(BaseModel):
    """Address information schema"""
    address_line1: str = Field(..., min_length=1, max_length=255, description="Street address")
    address_line2: Optional[str] = Field(None, max_length=255, description="Apartment, suite, etc.")
    postal_code: str = Field(..., min_length=1, max_length=20, description="Postal/ZIP code")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    state_code: Optional[str] = Field(None, max_length=10, description="State/Province code")
    country: str = Field(..., min_length=1, max_length=100, description="Country name")

    @validator('country_code', 'state_code')
    def uppercase_codes(cls, v):
        return v.upper() if v else v


class PersonalInformationSchema(BaseModel):
    """Step 1: Personal Information"""
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    date_of_birth: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    nationality: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 nationality code")
    email_address: EmailStr = Field(..., description="Email address")
    phone_number: str = Field(..., min_length=7, max_length=20, description="Phone number with country code")
    address: AddressSchema

    @validator('nationality')
    def uppercase_nationality(cls, v):
        return v.upper()

    @validator('date_of_birth')
    def validate_age(cls, v):
        """Ensure user is at least 18 years old"""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('You must be at least 18 years old')
        if age > 120:
            raise ValueError('Invalid date of birth')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "nationality": "US",
                "email_address": "john.doe@example.com",
                "phone_number": "+1234567890",
                "address": {
                    "address_line1": "123 Main Street",
                    "address_line2": "Apt 4B",
                    "postal_code": "10001",
                    "city": "New York",
                    "country_code": "US",
                    "state_code": "NY",
                    "country": "United States"
                }
            }
        }


# ============================================================================
# Step 2: Sumsub Liveness Check
# ============================================================================

class SumsubVerificationSchema(BaseModel):
    """Step 2: Sumsub liveness check status"""
    sumsub_applicant_id: str = Field(..., description="Sumsub applicant ID")
    sumsub_inspection_id: Optional[str] = Field(None, description="Sumsub inspection ID")
    verification_status: str = Field(..., description="Verification status")

    class Config:
        json_schema_extra = {
            "example": {
                "sumsub_applicant_id": "5cb56e8e0a975a35f333cb83",
                "sumsub_inspection_id": "5cb56e8e0a975a35f333cb84",
                "verification_status": "completed"
            }
        }


# ============================================================================
# Step 3: Tax Information
# ============================================================================

class TaxInformationSchema(BaseModel):
    """Step 3: Tax Information"""
    tax_identification_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="SSN/ITIN for US citizens, or tax ID number for other countries"
    )
    tax_residence_country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 tax residence country code"
    )

    @validator('tax_residence_country_code')
    def uppercase_country_code(cls, v):
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "tax_identification_number": "123-45-6789",
                "tax_residence_country_code": "US"
            }
        }


# ============================================================================
# Step 4: CDD (Customer Due Diligence)
# ============================================================================

class CDDInformationSchema(BaseModel):
    """Step 4: Customer Due Diligence (CDD)"""
    employment_status: Literal[
        "SELF_EMPLOYED",
        "SALARIED",
        "UNEMPLOYED",
        "RETIRED",
        "NOT_PROVIDED"
    ] = Field(..., description="Employment status")

    source_of_funds: Literal[
        "SALARY",
        "PENSION",
        "SAVINGS",
        "SELF_EMPLOYMENT",
        "CRYPTO_TRADING",
        "GAMBLING",
        "REAL_ESTATE"
    ] = Field(..., description="Source of funds")

    pep_status: Literal[
        "NOT_PEP",
        "FORMER_PEP_2_YEARS",
        "FORMER_PEP_OLDER",
        "DOMESTIC_PEP",
        "FOREIGN_PEP",
        "CLOSE_ASSOCIATES",
        "FAMILY_MEMBERS"
    ] = Field(..., description="Politically Exposed Person (PEP) status")

    account_purpose: Literal[
        "TRANSFERS_OWN_WALLET",
        "TRANSFERS_FAMILY_FRIENDS",
        "INVESTMENTS",
        "GOODS_SERVICES",
        "DONATIONS"
    ] = Field(..., description="Primary account purpose")

    expected_monthly_volume_amount: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Expected monthly transaction volume"
    )
    expected_monthly_volume_currency: Literal["USD", "EUR"] = Field(
        ...,
        description="Currency for expected monthly volume"
    )

    @validator('expected_monthly_volume_amount')
    def validate_volume(cls, v):
        if v < 0:
            raise ValueError('Expected monthly volume must be non-negative')
        if v > 10_000_000:
            raise ValueError('Expected monthly volume exceeds maximum allowed')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "employment_status": "SALARIED",
                "source_of_funds": "SALARY",
                "pep_status": "NOT_PEP",
                "account_purpose": "INVESTMENTS",
                "expected_monthly_volume_amount": 5000.00,
                "expected_monthly_volume_currency": "USD"
            }
        }


# ============================================================================
# Complete Verification Data (All Steps Combined)
# ============================================================================

class CompleteVerificationDataSchema(BaseModel):
    """Complete verification data from all steps"""
    # Step 1
    personal_info: PersonalInformationSchema
    # Step 2 (tracked separately in User model)
    # Step 3
    tax_info: TaxInformationSchema
    # Step 4
    cdd_info: CDDInformationSchema


# ============================================================================
# Response Schemas
# ============================================================================

class VerificationStepResponse(BaseModel):
    """Response after completing a verification step"""
    success: bool
    message: str
    step_number: int
    step_completed: bool
    next_step: Optional[int] = None
    all_steps_completed: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Personal information saved successfully",
                "step_number": 1,
                "step_completed": True,
                "next_step": 2,
                "all_steps_completed": False
            }
        }


class VerificationProgressResponse(BaseModel):
    """Current verification progress"""
    step_1_completed: bool
    step_2_completed: bool
    step_3_completed: bool
    step_4_completed: bool
    all_steps_completed: bool
    current_step: int
    completed_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "step_1_completed": True,
                "step_2_completed": True,
                "step_3_completed": False,
                "step_4_completed": False,
                "all_steps_completed": False,
                "current_step": 3,
                "completed_at": None
            }
        }


class CustomerVerificationDataResponse(BaseModel):
    """Complete customer verification data response"""
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    date_of_birth: Optional[date]
    nationality: Optional[str]
    email_address: Optional[str]
    phone_number: Optional[str]

    # Address
    address_line1: Optional[str]
    address_line2: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]
    country_code: Optional[str]
    state_code: Optional[str]
    country: Optional[str]

    # Tax
    tax_identification_number: Optional[str]
    tax_residence_country_code: Optional[str]

    # CDD
    employment_status: Optional[str]
    source_of_funds: Optional[str]
    pep_status: Optional[str]
    account_purpose: Optional[str]
    expected_monthly_volume_amount: Optional[Decimal]
    expected_monthly_volume_currency: Optional[str]

    # Progress
    step_1_completed: bool
    step_2_completed: bool
    step_3_completed: bool
    step_4_completed: bool
    all_steps_completed: bool

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
