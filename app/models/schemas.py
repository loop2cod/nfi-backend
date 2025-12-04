from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    user_id: str
    is_active: bool
    is_verified: bool
    verification_status: str
    verification_result: Optional[str] = None
    sumsub_applicant_id: Optional[str] = None
    bvnk_customer_id: Optional[str] = None
    verification_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SumsubInitRequest(BaseModel):
    level_name: Optional[str] = "id-and-liveness"


class SumsubInitResponse(BaseModel):
    success: bool
    verification_token: str
    applicant_id: str
    sdk_url: str
    config: dict


class SumsubStatusResponse(BaseModel):
    user_id: int
    is_verified: bool
    sumsub_status: str
    email: str


class Enable2FARequest(BaseModel):
    email: EmailStr


class Enable2FAResponse(BaseModel):
    success: bool
    message: str
    is_2fa_enabled: bool
    two_fa_email: str


class Send2FAOTPRequest(BaseModel):
    email: EmailStr
    method: Optional[str] = None  # Optional: 'email', 'sms', or 'totp' to override preferred method


class Send2FAOTPResponse(BaseModel):
    success: bool
    message: str
    two_fa_enabled: bool


class Verify2FAOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    method: Optional[str] = None  # 'email', 'sms', or 'totp' - helps verify the right way


class Verify2FAOTPResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class LoginWith2FAResponse(BaseModel):
    two_fa_required: bool
    two_fa_email: Optional[str] = None
    preferred_2fa_method: Optional[str] = None
    available_2fa_methods: Optional[List[str]] = None  # List of available fallback methods
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


# Verification Schemas
class VerificationStatusResponse(BaseModel):
    verification_status: str
    verification_result: Optional[str] = None
    sumsub_applicant_id: Optional[str] = None
    verification_completed_at: Optional[datetime] = None
    verification_steps: Optional[Dict[str, Any]] = None
    verification_error_message: Optional[str] = None


class VerificationStepResponse(BaseModel):
    step_name: str
    status: str
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SumsubWebhookEvent(BaseModel):
    applicantId: str
    inspectionId: Optional[str] = None
    correlationId: Optional[str] = None
    externalUserId: Optional[str] = None
    levelName: Optional[str] = None
    type: str
    reviewStatus: Optional[str] = None
    reviewResult: Optional[Dict[str, Any]] = None
    sandboxMode: Optional[bool] = None
    createdAtMs: Optional[str] = None
    clientId: Optional[str] = None


class WebhookProcessingResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    event_processed: bool = False


# Profile Management Schemas
class UserProfileResponse(BaseModel):
    id: int
    user_id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_2fa_enabled: bool
    totp_enabled: Optional[bool] = False
    profile_picture_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    verification_status: str

    class Config:
        from_attributes = True


class SendEmailOTPRequest(BaseModel):
    new_email: EmailStr


class SendEmailOTPResponse(BaseModel):
    success: bool
    message: str


class VerifyEmailOTPRequest(BaseModel):
    new_email: EmailStr
    otp: str


class VerifyEmailOTPResponse(BaseModel):
    success: bool
    message: str


class UpdatePhoneRequest(BaseModel):
    phone_number: str


class UpdatePhoneResponse(BaseModel):
    success: bool
    message: str
    phone_number: str


class Update2FARequest(BaseModel):
    is_2fa_enabled: bool
    preferred_method: Optional[str] = None  # 'email', 'sms', or 'totp'
    methods_priority: Optional[List[str]] = None  # Priority order of methods


class Update2FAResponse(BaseModel):
    success: bool
    message: str
    is_2fa_enabled: bool


class UpdateNameRequest(BaseModel):
    first_name: str
    last_name: str


class UpdateNameResponse(BaseModel):
    success: bool
    message: str
    first_name: str
    last_name: str


# Registration Email Verification Schemas
class RegistrationResponse(BaseModel):
    success: bool
    message: str
    email: EmailStr
    requires_verification: bool = True


class VerifyRegistrationOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class VerifyRegistrationOTPResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class ResendRegistrationOTPRequest(BaseModel):
    email: EmailStr


class ResendRegistrationOTPResponse(BaseModel):
    success: bool
    message: str