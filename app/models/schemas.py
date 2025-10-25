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