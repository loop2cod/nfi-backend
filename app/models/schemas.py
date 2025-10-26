from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool

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


class Send2FAOTPResponse(BaseModel):
    success: bool
    message: str
    two_fa_enabled: bool


class Verify2FAOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class Verify2FAOTPResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class LoginWith2FAResponse(BaseModel):
    two_fa_required: bool
    two_fa_email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None