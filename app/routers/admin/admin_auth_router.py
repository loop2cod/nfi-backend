"""
Admin Authentication Router
Handles authentication for platform administrators (nfi-client-dashboard)
Completely separate from end-user authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.database import get_db
from app.models.admin_user import AdminUser, AdminRole
from app.models.admin_login_history import AdminLoginHistory
from app.auth.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password
)
from app.utils.login_tracker import extract_login_info
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/auth/login")


# Pydantic Models
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    admin: dict


class AdminRefreshRequest(BaseModel):
    refresh_token: str


class AdminTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AdminUser:
    """Get current authenticated admin user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token, "access")
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    user_type: str = payload.get("user_type")

    if email is None or user_type != "admin":
        raise credentials_exception

    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if admin is None:
        raise credentials_exception

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )

    return admin


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint
    Returns JWT tokens for admin dashboard access
    """
    # Extract login information from request
    login_info = await extract_login_info(http_request)

    # Find admin by email
    admin = db.query(AdminUser).filter(AdminUser.email == request.email).first()

    if not admin:
        # Record failed login attempt (no admin found)
        # We don't record admin_id since we don't know who it is
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(request.password, admin.hashed_password):
        # Record failed login attempt
        failed_login = AdminLoginHistory(
            admin_id=admin.id,
            login_at=datetime.now(timezone.utc),
            login_status="failed",
            login_method="email_password",
            failure_reason="Incorrect password",
            **login_info
        )
        db.add(failed_login)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if admin is active
    if not admin.is_active:
        # Record failed login attempt (inactive account)
        failed_login = AdminLoginHistory(
            admin_id=admin.id,
            login_at=datetime.now(timezone.utc),
            login_status="failed",
            login_method="email_password",
            failure_reason="Account inactive",
            **login_info
        )
        db.add(failed_login)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )

    # Update last login
    admin.last_login = datetime.now(timezone.utc)
    admin.login_count += 1

    # Record successful login in history
    login_history = AdminLoginHistory(
        admin_id=admin.id,
        login_at=datetime.now(timezone.utc),
        login_status="success",
        login_method="email_password",
        **login_info
    )
    db.add(login_history)
    db.commit()

    # Create tokens with user_type=admin field
    access_token = create_access_token(data={"sub": admin.email, "user_type": "admin"})
    refresh_token = create_refresh_token(data={"sub": admin.email, "user_type": "admin"})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "full_name": admin.full_name,
            "role": admin.role,
            "is_super_admin": admin.is_super_admin,
        }
    }


@router.post("/refresh", response_model=AdminTokenResponse)
def admin_refresh_token(request: AdminRefreshRequest, db: Session = Depends(get_db)):
    """Refresh admin access token"""
    payload = verify_token(request.refresh_token, "refresh")

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    email = payload.get("sub")
    user_type = payload.get("user_type")

    if email is None or user_type != "admin":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Verify admin still exists and is active
    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account not found or inactive")

    access_token = create_access_token(data={"sub": email, "user_type": "admin"})
    refresh_token = create_refresh_token(data={"sub": email, "user_type": "admin"})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me")
def get_admin_me(current_admin: AdminUser = Depends(get_current_admin)):
    """Get current authenticated admin information"""
    return {
        "id": current_admin.id,
        "username": current_admin.username,
        "email": current_admin.email,
        "full_name": current_admin.full_name,
        "role": current_admin.role,
        "is_active": current_admin.is_active,
        "is_super_admin": current_admin.is_super_admin,
        "last_login": current_admin.last_login,
        "login_count": current_admin.login_count,
        "created_at": current_admin.created_at,
    }


@router.post("/logout")
def admin_logout(current_admin: AdminUser = Depends(get_current_admin)):
    """
    Admin logout endpoint
    Client should remove tokens from localStorage
    """
    return {"message": "Logged out successfully"}


@router.get("/login-history")
def get_admin_login_history(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Get login history for the current admin"""
    history = db.query(AdminLoginHistory)\
        .filter(AdminLoginHistory.admin_id == current_admin.id)\
        .order_by(AdminLoginHistory.login_at.desc())\
        .limit(limit)\
        .all()

    return [{
        "id": record.id,
        "login_time": record.login_at,
        "status": record.login_status,
        "method": record.login_method,
        "ip_address": record.ip_address,
        "location": record.location or f"{record.city}, {record.country}" if record.city and record.country else "Unknown",
        "device_type": record.device_type,
        "browser": record.browser,
        "os": record.os,
        "is_new_device": record.is_new_device,
        "is_suspicious": record.is_suspicious,
        "failure_reason": record.failure_reason
    } for record in history]
