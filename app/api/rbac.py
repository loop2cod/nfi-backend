from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.roles import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    has_permission,
    get_user_tier_from_role
)
from app.core.dependencies import get_current_user, require_super_admin
from app.models.auth import TokenData

router = APIRouter()

@router.get("/roles", summary="Get all user roles")
async def get_all_roles():
    """
    Get list of all available user roles in the system.

    **Tier Hierarchy:**
    - **Platform (Tier 0)**: Super Admin, Admin Staff, Admin Officer
    - **Client (Tier 1)**: Client Admin, Client Officer, Client Staff, Client Accounts
    - **SubClient (Tier 2)**: SubClient Admin, SubClient Staff
    - **End User (Tier 3)**: End User
    """
    roles_by_tier = {
        "platform": [
            {"role": UserRole.SUPER_ADMIN.value, "description": "Platform administrator with full access"},
            {"role": UserRole.ADMIN_STAFF.value, "description": "Platform staff with limited access"},
            {"role": UserRole.ADMIN_OFFICER.value, "description": "Platform officer with operational access"},
        ],
        "client": [
            {"role": UserRole.CLIENT_ADMIN.value, "description": "Company/Bank administrator"},
            {"role": UserRole.CLIENT_OFFICER.value, "description": "Company operations manager"},
            {"role": UserRole.CLIENT_STAFF.value, "description": "Company staff member"},
            {"role": UserRole.CLIENT_ACCOUNTS.value, "description": "Company accounts/finance role"},
        ],
        "subclient": [
            {"role": UserRole.SUBCLIENT_ADMIN.value, "description": "Financial institution administrator"},
            {"role": UserRole.SUBCLIENT_STAFF.value, "description": "Financial institution staff"},
        ],
        "end_user": [
            {"role": UserRole.END_USER.value, "description": "Individual customer"},
        ]
    }
    return roles_by_tier

@router.get("/permissions", summary="Get all permissions")
async def get_all_permissions(current_user: TokenData = Depends(require_super_admin)):
    """
    Get list of all available permissions in the system.
    Only accessible by Super Admin.
    """
    permissions = [
        {
            "permission": perm.value,
            "category": perm.value.split(":")[0],
            "action": perm.value.split(":")[1]
        }
        for perm in Permission
    ]
    return {"permissions": permissions}

@router.get("/role/{role}/permissions", summary="Get permissions for a role")
async def get_role_permissions(role: UserRole):
    """
    Get all permissions assigned to a specific role.
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    return {
        "role": role.value,
        "tier": get_user_tier_from_role(role).value,
        "permissions": [p.value for p in permissions]
    }

@router.get("/my-permissions", summary="Get current user permissions")
async def get_my_permissions(current_user: TokenData = Depends(get_current_user)):
    """
    Get permissions for the current authenticated user.
    """
    try:
        user_role = UserRole(current_user.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role"
        )

    permissions = ROLE_PERMISSIONS.get(user_role, [])

    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": user_role.value,
        "tier": get_user_tier_from_role(user_role).value,
        "tenant_id": current_user.tenant_id,
        "permissions": [p.value for p in permissions]
    }

@router.post("/check-permission", summary="Check if user has permission")
async def check_user_permission(
    permission: Permission,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Check if the current user has a specific permission.
    """
    try:
        user_role = UserRole(current_user.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role"
        )

    has_perm = has_permission(user_role, permission)

    return {
        "user_id": current_user.user_id,
        "role": user_role.value,
        "permission": permission.value,
        "has_permission": has_perm
    }

@router.get("/access-matrix", summary="Get complete access control matrix")
async def get_access_matrix(current_user: TokenData = Depends(require_super_admin)):
    """
    Get the complete role-permission matrix.
    Only accessible by Super Admin.

    Shows which roles have which permissions across the entire platform.
    """
    matrix = {}
    for role, permissions in ROLE_PERMISSIONS.items():
        matrix[role.value] = {
            "tier": get_user_tier_from_role(role).value,
            "permissions": [p.value for p in permissions]
        }

    return {"access_matrix": matrix}

@router.get("/hierarchy", summary="Get user hierarchy structure")
async def get_user_hierarchy():
    """
    Get the hierarchical structure of the platform.

    **4-Tier Architecture:**
    1. **Platform (Super Admin)** - Manages entire platform
    2. **Client (Company/Bank)** - Manages sub-clients and end users
    3. **SubClient (Financial Institution)** - Manages end users
    4. **End User (Customer)** - Individual account holder
    """
    hierarchy = {
        "tier_0_platform": {
            "name": "Platform Administration",
            "description": "Super Admin Dashboard - Platform owner",
            "roles": [UserRole.SUPER_ADMIN.value, UserRole.ADMIN_STAFF.value, UserRole.ADMIN_OFFICER.value],
            "manages": ["clients", "system_configuration", "billing"],
            "child_tier": "tier_1_client"
        },
        "tier_1_client": {
            "name": "Client Dashboard",
            "description": "Company/Bank Administration",
            "roles": [
                UserRole.CLIENT_ADMIN.value,
                UserRole.CLIENT_OFFICER.value,
                UserRole.CLIENT_STAFF.value,
                UserRole.CLIENT_ACCOUNTS.value
            ],
            "manages": ["sub_clients", "end_users", "kyt_settings", "risk_rules"],
            "parent_tier": "tier_0_platform",
            "child_tier": "tier_2_subclient"
        },
        "tier_2_subclient": {
            "name": "Sub-Client Dashboard",
            "description": "Financial Institution Operations",
            "roles": [UserRole.SUBCLIENT_ADMIN.value, UserRole.SUBCLIENT_STAFF.value],
            "manages": ["end_users", "transactions", "customer_service"],
            "parent_tier": "tier_1_client",
            "child_tier": "tier_3_enduser"
        },
        "tier_3_enduser": {
            "name": "End User Portal",
            "description": "Individual Customer Banking",
            "roles": [UserRole.END_USER.value],
            "manages": ["own_account", "transactions", "profile"],
            "parent_tier": "tier_2_subclient"
        }
    }

    return {"hierarchy": hierarchy}
