from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.login_activity import LoginActivity
from app.models.schemas import (
    UserCreate, LoginRequest, Token, RefreshTokenRequest,
    SumsubInitRequest, SumsubInitResponse, SumsubStatusResponse,
    LoginWith2FAResponse, Send2FAOTPRequest, Send2FAOTPResponse,
    Verify2FAOTPRequest, Verify2FAOTPResponse,
    RegistrationResponse, VerifyRegistrationOTPRequest, VerifyRegistrationOTPResponse,
    ResendRegistrationOTPRequest, ResendRegistrationOTPResponse
)
from app.auth.auth import authenticate_user, create_access_token, create_refresh_token, verify_token, get_password_hash
from app.auth.google_auth import get_google_oauth_client, get_google_user_info
from app.auth.sumsub_service import generate_websdk_config
from app.core.config import settings
from app.core.dfns_client import init_dfns_client
from app.core.user_id_generator import generate_user_id
from app.models.wallet import Wallet
from app.utils.login_tracker import extract_login_info
from app.utils.email import send_otp_email, send_welcome_email
import requests
import hmac
import hashlib
import time
import json
from urllib.parse import urlparse
import random
import string
from datetime import datetime, timedelta
import pyotp

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token, "access")
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=RegistrationResponse)
async def register(user: UserCreate, http_request: Request, db: Session = Depends(get_db)):
    # Extract login information from request
    login_info = await extract_login_info(http_request)

    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # Generate unique user ID
        user_id = generate_user_id(db)

        # Generate OTP for email verification
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)  # OTP valid for 10 minutes

        # Create new user (not verified yet)
        hashed_password = get_password_hash(user.password)
        db_user = User(
            user_id=user_id,
            email=user.email,
            hashed_password=hashed_password,
            is_verified=False,
            email_verification_otp=otp,
            email_verification_otp_expiry=otp_expiry
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Track registration attempt as login activity
        login_activity = LoginActivity(
            user_id=db_user.id,
            status="pending",
            method="registration",
            **login_info
        )
        db.add(login_activity)
        db.commit()

        # Send OTP email
        try:
            send_otp_email(user.email, otp, expires_in_minutes=10)
        except Exception as email_error:
            print(f"Failed to send OTP email: {str(email_error)}")
            # Don't fail registration if email fails, but log it
            # User can request resend

        return {
            "success": True,
            "message": "Registration successful. Please check your email for the verification code.",
            "email": user.email,
            "requires_verification": True
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/verify-registration-otp", response_model=VerifyRegistrationOTPResponse)
async def verify_registration_otp(
    request: VerifyRegistrationOTPRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Verify email with OTP after registration"""
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already verified
    if user.is_verified and user.email_verified_at:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Check if OTP exists
    if not user.email_verification_otp:
        raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")

    # Check if OTP is expired
    if user.email_verification_otp_expiry and datetime.utcnow() > user.email_verification_otp_expiry:
        raise HTTPException(status_code=400, detail="Verification code expired. Please request a new one.")

    # Verify OTP
    if user.email_verification_otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    try:
        # Mark email as verified
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_otp = None  # Clear OTP
        user.email_verification_otp_expiry = None

        db.commit()
        db.refresh(user)

        # Update login activity to success
        login_info = await extract_login_info(http_request)
        login_activity = LoginActivity(
            user_id=user.id,
            status="success",
            method="email_verification",
            **login_info
        )
        db.add(login_activity)
        db.commit()

        # Send welcome email
        try:
            send_welcome_email(user.email, user.email.split('@')[0])
        except Exception as email_error:
            print(f"Failed to send welcome email: {str(email_error)}")

        # Create tokens
        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})

        return {
            "success": True,
            "message": "Email verified successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/resend-registration-otp", response_model=ResendRegistrationOTPResponse)
async def resend_registration_otp(
    request: ResendRegistrationOTPRequest,
    db: Session = Depends(get_db)
):
    """Resend OTP for email verification"""
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already verified
    if user.is_verified and user.email_verified_at:
        raise HTTPException(status_code=400, detail="Email already verified")

    try:
        # Generate new OTP
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        # Update user with new OTP
        user.email_verification_otp = otp
        user.email_verification_otp_expiry = otp_expiry

        db.commit()

        # Send OTP email
        try:
            send_otp_email(user.email, otp, expires_in_minutes=10)
        except Exception as email_error:
            print(f"Failed to send OTP email: {str(email_error)}")
            raise HTTPException(status_code=500, detail="Failed to send verification email")

        return {
            "success": True,
            "message": "Verification code sent successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resend code: {str(e)}")


@router.post("/login", response_model=LoginWith2FAResponse)
async def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    # Extract login information from request
    login_info = await extract_login_info(http_request)

    user = authenticate_user(db, request.email, request.password)
    if user is None:
        # Track failed login attempt - user not found
        login_activity = LoginActivity(
            user_id=0,  # Unknown user
            status="failed",
            method="email_password",
            failure_reason="User not found",
            **login_info
        )
        db.add(login_activity)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )
    if not user:
        # Track failed login attempt - incorrect password
        login_activity = LoginActivity(
            user_id=user.id if user else 0,
            status="failed",
            method="email_password",
            failure_reason="Incorrect password",
            **login_info
        )
        db.add(login_activity)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified
    if not user.is_verified:
        # Track failed login attempt - email not verified
        login_activity = LoginActivity(
            user_id=user.id,
            status="failed",
            method="email_password",
            failure_reason="Email not verified",
            **login_info
        )
        db.add(login_activity)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for the verification code.",
        )

    # Check if 2FA is enabled
    if user.is_2fa_enabled:
        # Track 2FA pending
        login_activity = LoginActivity(
            user_id=user.id,
            status="2fa_pending",
            method="email_password",
            **login_info
        )
        db.add(login_activity)
        db.commit()

        # Get available 2FA methods based on user's configuration
        available_methods = []
        if user.two_fa_methods_priority:
            # Use stored priority
            available_methods = user.two_fa_methods_priority
        else:
            # Build available methods dynamically
            available_methods = ['email']  # Email is always available
            if user.phone_number:
                available_methods.append('sms')
            if user.totp_enabled:
                available_methods.append('totp')

        return LoginWith2FAResponse(
            two_fa_required=True,
            two_fa_email=user.two_fa_email,
            preferred_2fa_method=user.preferred_2fa_method or 'email',
            available_2fa_methods=available_methods
        )

    # If 2FA not enabled, return tokens directly
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    # Note: Wallets are now created automatically after verification completion
    # No longer creating wallets on login

    # Track successful login
    login_activity = LoginActivity(
        user_id=user.id,
        status="success",
        method="email_password",
        **login_info
    )
    db.add(login_activity)
    db.commit()

    return LoginWith2FAResponse(
        two_fa_required=False,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
def refresh_token(request: RefreshTokenRequest):
    payload = verify_token(request.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "id": current_user.id,
        "user_id": current_user.user_id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "verification_status": current_user.verification_status,
        "verification_result": current_user.verification_result,
        "sumsub_applicant_id": current_user.sumsub_applicant_id,
        "bvnk_customer_id": current_user.bvnk_customer_id,
        "verification_completed_at": current_user.verification_completed_at,
        "profile_picture_url": current_user.profile_picture_url,
        "created_at": current_user.created_at,
    }


@router.get("/login-activity")
def get_login_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Get login activity history for the current user"""
    activities = db.query(LoginActivity)\
        .filter(LoginActivity.user_id == current_user.id)\
        .order_by(LoginActivity.login_time.desc())\
        .limit(limit)\
        .all()

    return [{
        "id": activity.id,
        "login_time": activity.login_time,
        "status": activity.status,
        "method": activity.method,
        "ip_address": activity.ip_address,
        "location": activity.location or f"{activity.city}, {activity.country}" if activity.city and activity.country else "Unknown",
        "device_type": activity.device_type,
        "browser": activity.browser,
        "os": activity.os,
        "is_new_device": activity.is_new_device,
        "is_suspicious": activity.is_suspicious,
        "failure_reason": activity.failure_reason
    } for activity in activities]


@router.get("/google/login")
async def google_login():
    client = get_google_oauth_client()
    authorization_url, state = client.create_authorization_url(
        "https://accounts.google.com/o/oauth2/auth",
        scope=["openid", "email", "profile"],
    )
    return {"authorization_url": authorization_url, "state": state}


@router.get("/google/callback")
async def google_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    # Extract login information
    login_info = await extract_login_info(request)

    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")

    client = get_google_oauth_client()
    try:
        token = await client.fetch_token(
            "https://oauth2.googleapis.com/token",
            code=code,
        )
        user_info = await get_google_user_info(token["access_token"])
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to authenticate with Google")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    # Check if user exists, if not create
    user = db.query(User).filter(User.email == email).first()
    if not user:
        try:
            # Generate unique user ID
            user_id = generate_user_id(db)
            # For Google auth, we don't need password, but set a dummy one
            hashed_password = get_password_hash("google_oauth")
            user = User(user_id=user_id, email=email, hashed_password=hashed_password)
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

    # Track successful Google OAuth login
    login_activity = LoginActivity(
        user_id=user.id,
        status="success",
        method="google_oauth",
        **login_info
    )
    db.add(login_activity)
    db.commit()

    # Create tokens
    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})

    # Redirect to frontend callback page with tokens
    frontend_url = f"http://localhost:3001/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
    return RedirectResponse(url=frontend_url)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token, "access")
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def create_sumsub_signature(method: str, url: str, body: str = "") -> tuple[str, str]:
    """Create HMAC signature for Sumsub API requests"""
    timestamp = str(int(time.time()))
    
    # Parse the URL to get the path
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Create the string to sign
    string_to_sign = f"{timestamp}{method.upper()}{path}{body}"
    
    # Create HMAC signature
    signature = hmac.new(
        settings.SUMSUB_SECRET_KEY.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return timestamp, signature


@router.post("/sumsub/init", response_model=SumsubInitResponse)
def initialize_sumsub_verification(
    request: SumsubInitRequest,
    current_user: User = Depends(get_current_user)
):
    """Initialize Sumsub verification session for the current user"""
    try:
        external_user_id = f"user_{current_user.user_id}"
        config = generate_websdk_config(external_user_id, request.level_name)

        return SumsubInitResponse(**config)

    except Exception as e:
        print(f"Failed to initialize Sumsub verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Sumsub verification: {str(e)}"
        )


# NOTE: Sumsub webhook endpoint has been moved to /webhook/sumsub/webhook
# See app/routers/webhook/sumsub_webhook.py for the comprehensive webhook handler


@router.get("/sumsub/status", response_model=SumsubStatusResponse)
def get_verification_status(current_user: User = Depends(get_current_user)):
    """Get current user's verification status"""
    try:
        external_user_id = f"user_{current_user.user_id}"

        # Try to get status from Sumsub
        try:
            url = f"{settings.SUMSUB_BASE_URL}/resources/applicants/{external_user_id}/status"
            timestamp, signature = create_sumsub_signature("GET", url)
            
            headers = {
                "X-App-Token": settings.SUMSUB_TOKEN,
                "X-App-Access-Sig": signature,
                "X-App-Access-Ts": timestamp
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                status_response = response.json()
                sumsub_status = status_response.get("reviewStatus", "init")
            else:
                sumsub_status = "init"
        except Exception as e:
            print(f"Error getting Sumsub status: {e}")
            sumsub_status = "unknown"

        return SumsubStatusResponse(
            user_id=current_user.id,
            is_verified=current_user.is_verified,
            sumsub_status=sumsub_status,
            email=current_user.email
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get verification status: {str(e)}")


@router.get("/sumsub/health")
def check_sumsub_health():
    """Check if Sumsub service is properly configured and accessible"""
    try:
        # Basic configuration check
        if not settings.SUMSUB_TOKEN:
            return {
                "status": "error",
                "message": "Sumsub token not configured",
                "configured": False
            }
        
        return {
            "status": "ok",
            "message": "Sumsub service is configured",
            "configured": True,
            "base_url": settings.SUMSUB_BASE_URL
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Health check failed: {str(e)}",
            "configured": False
        }


# enable 2FA payload email


@router.post("/send-2fa-otp", response_model=Send2FAOTPResponse)
def send_2fa_otp(request: Send2FAOTPRequest, db: Session = Depends(get_db)):
    """Send 2FA OTP to user based on their preferred method or specified method"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this user"
        )

    # Use specified method or fall back to preferred method
    method_to_use = request.method if request.method else (user.preferred_2fa_method or 'email')

    # Validate the method
    if method_to_use not in ['email', 'sms', 'totp']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA method"
        )

    # Validate method availability
    if method_to_use == 'sms' and not user.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMS method not available. Phone number not configured."
        )

    # Generate OTP and set expiry (5 minutes from now)
    otp = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=5)

    # Update user with OTP and expiry
    user.two_fa_otp = otp
    user.two_fa_otp_expiry = otp_expiry
    db.commit()

    # Send OTP based on the method
    if method_to_use == 'email':
        send_otp_email(user.two_fa_email or user.email, otp)
    elif method_to_use == 'sms':
        # TODO: Implement SMS sending
        print(f"[SMS OTP] Sending OTP {otp} to {user.phone_number}")
        pass
    elif method_to_use == 'totp':
        # TOTP doesn't need to send OTP, it's generated by the app
        # But we still generate it for fallback purposes
        pass

    return Send2FAOTPResponse(
        success=True,
        message=f"OTP sent successfully via {method_to_use}",
        two_fa_enabled=True
    )


@router.post("/verify-2fa-otp", response_model=Verify2FAOTPResponse)
async def verify_2fa_otp(request: Verify2FAOTPRequest, http_request: Request, db: Session = Depends(get_db)):
    """Verify 2FA OTP and complete login"""
    # Extract login information
    login_info = await extract_login_info(http_request)

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this user"
        )

    # Handle TOTP verification differently
    if request.method == 'totp':
        if not user.totp_enabled or not user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TOTP is not configured for this user"
            )

        # Verify TOTP code
        totp = pyotp.TOTP(user.totp_secret)
        is_valid = totp.verify(request.otp, valid_window=2)  # Allow 2 time steps (±60 seconds)

        if not is_valid:
            # Track failed 2FA attempt
            login_activity = LoginActivity(
                user_id=user.id,
                status="failed",
                method="2fa_totp",
                failure_reason="Invalid TOTP code",
                **login_info
            )
            db.add(login_activity)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
    else:
        # Handle email/SMS OTP verification
        # Check if OTP exists
        if not user.two_fa_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OTP found. Please request a new OTP."
            )

        # Check if OTP has expired
        if user.two_fa_otp_expiry and datetime.utcnow() > user.two_fa_otp_expiry:
            # Clear expired OTP
            user.two_fa_otp = None
            user.two_fa_otp_expiry = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new OTP."
            )

        # Verify OTP
        if user.two_fa_otp != request.otp:
            # Track failed 2FA attempt
            login_activity = LoginActivity(
                user_id=user.id,
                status="failed",
                method="2fa_verification",
                failure_reason="Invalid OTP",
                **login_info
            )
            db.add(login_activity)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP"
            )

        # Clear OTP after successful verification
        user.two_fa_otp = None
        user.two_fa_otp_expiry = None

    # Verification successful, commit changes
    db.commit()

    # Track successful 2FA login
    login_activity = LoginActivity(
        user_id=user.id,
        status="2fa_success",
        method="2fa_verification",
        **login_info
    )
    db.add(login_activity)
    db.commit()

    # Generate tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    return Verify2FAOTPResponse(
        success=True,
        message="2FA verification successful",
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )