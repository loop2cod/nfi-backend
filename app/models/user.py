from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from .roles import UserRole, UserTier

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_KYC = "pending_kyc"
    KYC_REJECTED = "kyc_rejected"

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: UserRole
    tenant_id: Optional[str] = None  # Client ID for client users, SubClient ID for subclient users
    parent_id: Optional[str] = None  # Parent tenant (Client for SubClient, SubClient for EndUser)

class User(UserBase):
    id: str
    role: UserRole
    tier: UserTier
    tenant_id: Optional[str] = None  # Multi-tenant identifier
    parent_id: Optional[str] = None  # Hierarchical parent reference
    status: UserStatus = UserStatus.ACTIVE
    is_verified: bool = False
    kyc_status: Optional[str] = None  # "pending", "approved", "rejected"
    kyc_provider: Optional[str] = None  # "sumsub", "onfido"
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    role: UserRole
    tier: UserTier
    tenant_id: Optional[str] = None
    parent_id: Optional[str] = None
    status: UserStatus
    is_verified: bool
    kyc_status: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    status: Optional[UserStatus] = None

class TenantInfo(BaseModel):
    """Information about a tenant (Client or SubClient)"""
    id: str
    name: str
    type: str  # "client" or "subclient"
    parent_id: Optional[str] = None
    status: str
    created_at: datetime
