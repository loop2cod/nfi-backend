from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from app.models.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from app.models.user import UserCreate, UserResponse
from app.models.roles import UserRole, get_user_tier_from_role
from app.core.security import (
    verify_password,
    get_password_hash,
    create_token_pair,
    decode_token
)
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.auth import TokenData
from app.db.connection import get_db
from app.db.repositories import UserRepository, AuthRepository

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(user: UserCreate):
    """
    Register a new user in the system.

    **Role-based registration:**
    - Super Admin can create any user type
    - Client Admin can create SubClient and EndUser accounts
    - SubClient Admin can create EndUser accounts
    - Public registration creates EndUser accounts (requires approval)

    **Multi-tenant fields:**
    - `tenant_id`: Required for Client/SubClient/EndUser roles
    - `parent_id`: Required for SubClient (Client ID) and EndUser (SubClient ID)
    """
    db = get_db()
    user_repo = UserRepository(db)

    # Check if user already exists
    if user_repo.exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate tenant hierarchy
    if user.role in [UserRole.CLIENT_ADMIN, UserRole.CLIENT_OFFICER, UserRole.CLIENT_STAFF, UserRole.CLIENT_ACCOUNTS]:
        if not user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id is required for client users"
            )

    if user.role in [UserRole.SUBCLIENT_ADMIN, UserRole.SUBCLIENT_STAFF]:
        if not user.tenant_id or not user.parent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id and parent_id are required for sub-client users"
            )

    if user.role == UserRole.END_USER:
        if not user.parent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parent_id (SubClient ID) is required for end users"
            )

    # Hash password
    hashed_password = get_password_hash(user.password)

    # End users start with PENDING_KYC status
    user_status = "pending_kyc" if user.role == UserRole.END_USER else "active"

    # Prepare user data
    user_data = {
        "email": user.email,
        "password_hash": hashed_password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "role": user.role.value,
        "tenant_id": user.tenant_id,
        "parent_id": user.parent_id,
        "status": user_status,
        "kyc_status": "pending" if user.role == UserRole.END_USER else None,
        "kyc_provider": None,
    }

    # Create user in database
    created_user = user_repo.create(user_data)

    return UserResponse(**created_user)

@router.post("/login", response_model=LoginResponse, summary="Login")
async def login(credentials: LoginRequest):
    """
    Authenticate user and return access tokens.

    Returns JWT access token and refresh token for authenticated users.
    """
    db = get_db()
    user_repo = UserRepository(db)
    auth_repo = AuthRepository(db)

    # Find user by email
    user = user_repo.get_by_email(credentials.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if user["status"] not in ["active", "pending_kyc"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user['status']}"
        )

    # Update last login
    user_repo.update_last_login(user["id"])

    # Create tokens
    tokens = create_token_pair(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        tenant_id=user.get("tenant_id")
    )

    # Store refresh token in database
    expires_at = db.now() + (settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 * 1000)
    auth_repo.create_refresh_token(
        user_id=user["id"],
        token=tokens["refresh_token"],
        expires_at=expires_at
    )

    # Remove password hash from response
    user_response = {k: v for k, v in user.items() if k != "password_hash"}

    return LoginResponse(
        **tokens,
        user=user_response
    )

@router.post("/refresh", summary="Refresh access token")
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using a valid refresh token.
    """
    db = get_db()
    user_repo = UserRepository(db)
    auth_repo = AuthRepository(db)

    # Verify refresh token exists in database
    stored_token = auth_repo.get_refresh_token(request.refresh_token)
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Decode token
    payload = decode_token(request.refresh_token)
    if not payload:
        # Revoke invalid token
        auth_repo.revoke_refresh_token(request.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Verify token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new token pair
    tokens = create_token_pair(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        tenant_id=user.get("tenant_id")
    )

    # Revoke old refresh token
    auth_repo.revoke_refresh_token(request.refresh_token)

    # Store new refresh token
    expires_at = db.now() + (settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 * 1000)
    auth_repo.create_refresh_token(
        user_id=user["id"],
        token=tokens["refresh_token"],
        expires_at=expires_at
    )

    return tokens

@router.post("/logout", summary="Logout")
async def logout(
    request: RefreshTokenRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Logout user by invalidating refresh token.
    """
    db = get_db()
    auth_repo = AuthRepository(db)

    # Revoke refresh token
    auth_repo.revoke_refresh_token(request.refresh_token)

    return {"message": "Successfully logged out"}

@router.post("/change-password", summary="Change password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Change password for authenticated user.
    """
    db = get_db()
    user_repo = UserRepository(db)

    user = user_repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify old password
    if not verify_password(request.old_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )

    # Update password
    new_password_hash = get_password_hash(request.new_password)
    user_repo.update(user["id"], {"password_hash": new_password_hash})

    return {"message": "Password changed successfully"}

@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    db = get_db()
    user_repo = UserRepository(db)

    user = user_repo.get_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Remove password hash
    user_response = {k: v for k, v in user.items() if k != "password_hash"}
    return UserResponse(**user_response)
