from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
import uuid
from app.models.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ResetPasswordRequest
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
from app.models.auth import TokenData

router = APIRouter()

# Mock database (replace with actual database)
users_db = {}
refresh_tokens_db = {}  # Store valid refresh tokens

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
    # Check if user already exists
    for existing_user in users_db.values():
        if existing_user["email"] == user.email:
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

    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    tier = get_user_tier_from_role(user.role)

    # End users start with PENDING_KYC status
    user_status = "pending_kyc" if user.role == UserRole.END_USER else "active"

    new_user = {
        "id": user_id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "password": hashed_password,
        "role": user.role.value,
        "tier": tier.value,
        "tenant_id": user.tenant_id,
        "parent_id": user.parent_id,
        "status": user_status,
        "is_verified": False,
        "kyc_status": "pending" if user.role == UserRole.END_USER else None,
        "kyc_provider": None,
        "last_login": None,
        "created_at": datetime.now(),
    }

    users_db[user_id] = new_user

    return UserResponse(**{k: v for k, v in new_user.items() if k != "password"})

@router.post("/login", response_model=LoginResponse, summary="Login")
async def login(credentials: LoginRequest):
    """
    Authenticate user and return access tokens.

    Returns JWT access token and refresh token for authenticated users.
    """
    # Find user by email
    user = None
    for u in users_db.values():
        if u["email"] == credentials.email:
            user = u
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(credentials.password, user["password"]):
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
    users_db[user["id"]]["last_login"] = datetime.now()

    # Create tokens
    tokens = create_token_pair(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        tenant_id=user.get("tenant_id")
    )

    # Store refresh token
    refresh_tokens_db[tokens["refresh_token"]] = {
        "user_id": user["id"],
        "created_at": datetime.now()
    }

    return LoginResponse(
        **tokens,
        user={k: v for k, v in user.items() if k != "password"}
    )

@router.post("/refresh", summary="Refresh access token")
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using a valid refresh token.
    """
    # Verify refresh token exists
    if request.refresh_token not in refresh_tokens_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Decode token
    payload = decode_token(request.refresh_token)
    if not payload:
        # Remove invalid token
        refresh_tokens_db.pop(request.refresh_token, None)
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
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    user = users_db[user_id]

    # Create new token pair
    tokens = create_token_pair(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        tenant_id=user.get("tenant_id")
    )

    # Remove old refresh token and store new one
    refresh_tokens_db.pop(request.refresh_token, None)
    refresh_tokens_db[tokens["refresh_token"]] = {
        "user_id": user["id"],
        "created_at": datetime.now()
    }

    return tokens

@router.post("/logout", summary="Logout")
async def logout(
    request: RefreshTokenRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Logout user by invalidating refresh token.
    """
    # Remove refresh token
    refresh_tokens_db.pop(request.refresh_token, None)

    return {"message": "Successfully logged out"}

@router.post("/change-password", summary="Change password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Change password for authenticated user.
    """
    user = users_db.get(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify old password
    if not verify_password(request.old_password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )

    # Update password
    users_db[user["id"]]["password"] = get_password_hash(request.new_password)

    return {"message": "Password changed successfully"}

@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    user = users_db.get(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(**{k: v for k, v in user.items() if k != "password"})
