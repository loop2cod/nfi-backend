from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.core.security import decode_token
from app.models.roles import UserRole, Permission, has_permission
from app.models.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    email: str = payload.get("email")
    role: str = payload.get("role")
    tenant_id: Optional[str] = payload.get("tenant_id")

    if user_id is None or email is None or role is None:
        raise credentials_exception

    return TokenData(
        user_id=user_id,
        email=email,
        role=role,
        tenant_id=tenant_id
    )

async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Get current active user (can add additional checks here)"""
    return current_user

class RoleChecker:
    """Dependency to check if user has required role"""
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: TokenData = Depends(get_current_user)) -> TokenData:
        try:
            user_role = UserRole(current_user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )

        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in self.allowed_roles]}"
            )
        return current_user

class PermissionChecker:
    """Dependency to check if user has required permission"""
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission

    def __call__(self, current_user: TokenData = Depends(get_current_user)) -> TokenData:
        try:
            user_role = UserRole(current_user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )

        if not has_permission(user_role, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {self.required_permission.value}"
            )
        return current_user

# Tier-specific role checkers
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])

require_admin_tier = RoleChecker([
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN_STAFF,
    UserRole.ADMIN_OFFICER
])

require_client_tier = RoleChecker([
    UserRole.SUPER_ADMIN,
    UserRole.CLIENT_ADMIN,
    UserRole.CLIENT_OFFICER,
    UserRole.CLIENT_STAFF,
    UserRole.CLIENT_ACCOUNTS
])

require_subclient_tier = RoleChecker([
    UserRole.SUPER_ADMIN,
    UserRole.CLIENT_ADMIN,
    UserRole.SUBCLIENT_ADMIN,
    UserRole.SUBCLIENT_STAFF
])

require_any_admin = RoleChecker([
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN_OFFICER,
    UserRole.CLIENT_ADMIN,
    UserRole.CLIENT_OFFICER,
    UserRole.SUBCLIENT_ADMIN
])
