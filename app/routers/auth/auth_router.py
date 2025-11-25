from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.schemas import UserCreate, LoginRequest, Token, RefreshTokenRequest, SumsubInitRequest, SumsubInitResponse, SumsubStatusResponse, LoginWith2FAResponse, Send2FAOTPRequest, Send2FAOTPResponse, Verify2FAOTPRequest, Verify2FAOTPResponse
from app.auth.auth import authenticate_user, create_access_token, create_refresh_token, verify_token, get_password_hash
from app.auth.google_auth import get_google_oauth_client, get_google_user_info
from app.auth.sumsub_service import generate_websdk_config
from app.core.config import settings
from app.core.dfns_client import init_dfns_client, create_user_wallet
from app.core.user_id_generator import generate_user_id
from app.models.wallet import Wallet
import requests
import hmac
import hashlib
import time
import json
from urllib.parse import urlparse
import random
import string
from datetime import datetime, timedelta

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email: str, otp: str):
    """Send OTP via email - placeholder for actual email service"""
    # TODO: Implement actual email sending logic
    print(f"Sending OTP {otp} to {email}")
    # This would integrate with your email service (SendGrid, SES, etc.)
    pass


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


@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # Generate unique user ID
        user_id = generate_user_id(db)

        # Create new user
        hashed_password = get_password_hash(user.password)
        db_user = User(
            user_id=user_id,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Create tokens
        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=LoginWith2FAResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if 2FA is enabled
    if user.is_2fa_enabled:
        return LoginWith2FAResponse(
            two_fa_required=True,
            two_fa_email=user.two_fa_email
        )

    # If 2FA not enabled, return tokens directly
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    # Check if user has wallets, if not create them on first login
    if not user.wallets:
        init_dfns_client()
        currencies_networks = [
            ("USDT", "EthereumSepolia"),
            ("USDC", "EthereumSepolia"),
            ("ETH", "EthereumSepolia"),
            ("BTC", "BitcoinTestnet")
        ]
        for currency, network in currencies_networks:
            wallet_data = create_user_wallet(user.id, currency, network)
            if wallet_data:
                db_wallet = Wallet(**wallet_data)
                db.add(db_wallet)
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
        "created_at": current_user.created_at,
    }


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
        external_user_id = f"user_{current_user.id}"
        config = generate_websdk_config(external_user_id, request.level_name)

        return SumsubInitResponse(**config)

    except Exception as e:
        print(f"Failed to initialize Sumsub verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Sumsub verification: {str(e)}"
        )


def verify_sumsub_webhook_signature(payload: str, signature: str) -> bool:
    """Verify that webhook signature is valid"""
    try:
        expected_signature = hmac.new(
            settings.SUMSUB_SECRET_KEY.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


@router.post("/sumsub/webhook")
async def sumsub_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Sumsub webhooks for verification status updates"""
    try:
        # Get raw body for signature verification
        body = await request.body()
        payload = body.decode('utf-8')
        
        # Verify webhook signature if present
        signature = request.headers.get('X-Payload-Digest-Alg-SHA256')
        if signature and not verify_sumsub_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        data = await request.json()
        print(f"Received Sumsub webhook: {data}")

        # Handle different webhook events
        event_type = data.get("type")
        review_status = data.get("reviewStatus")
        external_user_id = data.get("externalUserId")

        # Update user verification status based on webhook
        if event_type == "applicantReviewed" and external_user_id:
            # Extract user ID from external_user_id (format: "user_123")
            if external_user_id.startswith("user_"):
                user_id = int(external_user_id.replace("user_", ""))
                user = db.query(User).filter(User.id == user_id).first()
                
                if user:
                    if review_status in ["completed", "approved"]:
                        user.is_verified = True
                        db.commit()
                        print(f"User {user_id} marked as verified")
                    elif review_status in ["rejected", "onHold"]:
                        user.is_verified = False
                        db.commit()
                        print(f"User {user_id} verification status: {review_status}")

        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/sumsub/status", response_model=SumsubStatusResponse)
def get_verification_status(current_user: User = Depends(get_current_user)):
    """Get current user's verification status"""
    try:
        external_user_id = f"user_{current_user.id}"
        
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
    """Send 2FA OTP to user's registered email"""
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
    
    # Generate OTP and set expiry (5 minutes from now)
    otp = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    
    # Update user with OTP and expiry
    user.two_fa_otp = otp
    user.two_fa_otp_expiry = otp_expiry
    db.commit()
    
    # Send OTP via email
    send_otp_email(user.two_fa_email or user.email, otp)
    
    return Send2FAOTPResponse(
        success=True,
        message="OTP sent successfully",
        two_fa_enabled=True
    )


@router.post("/verify-2fa-otp", response_model=Verify2FAOTPResponse)
def verify_2fa_otp(request: Verify2FAOTPRequest, db: Session = Depends(get_db)):
    """Verify 2FA OTP and complete login"""
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # OTP is correct, clear it and generate tokens
    user.two_fa_otp = None
    user.two_fa_otp_expiry = None
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