"""
Admin Management Router
Endpoints for managing admin users and passwords
Only accessible to SUPER_ADMIN users
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.admin_user import AdminUser, AdminRole
from app.auth.auth import get_password_hash, verify_password
from app.routers.admin.admin_auth_router import get_current_admin

router = APIRouter()


# Pydantic Models
class CreateAdminRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: AdminRole = AdminRole.STAFF


class AdminResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: AdminRole
    is_active: bool
    is_super_admin: bool
    last_login: Optional[datetime]
    login_count: int
    created_at: datetime


class ChangeOwnPasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetAdminPasswordRequest(BaseModel):
    admin_id: int
    new_password: str


def require_super_admin(current_admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Dependency to require super admin access"""
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can perform this action"
        )
    return current_admin


@router.get("/admins", response_model=List[AdminResponse])
def list_admins(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all admin users"""
    admins = db.query(AdminUser).all()
    return admins


@router.post("/admins", response_model=AdminResponse)
def create_admin(
    request: CreateAdminRequest,
    current_admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new admin user (super admin only)"""

    # Check if username already exists
    existing_username = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email already exists
    existing_email = db.query(AdminUser).filter(AdminUser.email == request.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Validate password length
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    # Create new admin
    new_admin = AdminUser(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name or request.username.title(),
        role=request.role,
        is_active=True,
        is_super_admin=(request.role == AdminRole.SUPER_ADMIN),
        login_count=0,
        created_by=current_admin.id
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return new_admin


@router.get("/admins/{admin_id}", response_model=AdminResponse)
def get_admin(
    admin_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific admin user"""
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )

    return admin


@router.post("/admins/change-password")
def change_own_password(
    request: ChangeOwnPasswordRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Change current admin's own password"""

    # Verify current password
    if not verify_password(request.current_password, current_admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Validate new password length
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )

    # Update password
    current_admin.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/admins/reset-password")
def reset_admin_password(
    request: ResetAdminPasswordRequest,
    current_admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Reset another admin's password (super admin only)"""

    # Get target admin
    target_admin = db.query(AdminUser).filter(AdminUser.id == request.admin_id).first()

    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )

    # Don't allow resetting own password this way
    if target_admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use change-password endpoint to change your own password"
        )

    # Validate new password length
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )

    # Update password
    target_admin.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return {"message": f"Password reset successfully for {target_admin.username}"}


@router.patch("/admins/{admin_id}/toggle-status")
def toggle_admin_status(
    admin_id: int,
    current_admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Toggle admin active status (super admin only)"""

    target_admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()

    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )

    # Don't allow disabling own account
    if target_admin.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )

    # Toggle status
    target_admin.is_active = not target_admin.is_active
    db.commit()

    return {
        "message": f"Admin {'activated' if target_admin.is_active else 'deactivated'} successfully",
        "is_active": target_admin.is_active
    }
