from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.schemas import UserCreate, LoginRequest, Token, RefreshTokenRequest
from app.auth.auth import authenticate_user, create_access_token, create_refresh_token, verify_token, get_password_hash
from app.auth.google_auth import get_google_oauth_client, get_google_user_info
from app.auth.sumsub_service import sumsub_service
from app.core.config import settings
import uuid
from datetime import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


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

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


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
        # For Google auth, we don't need password, but set a dummy one
        hashed_password = get_password_hash("google_oauth")
        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)

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


@router.post("/sumsub/init")
def init_sumsub_verification(current_user: User = Depends(get_current_user)):
    """Initialize Sumsub verification session"""
    try:
        # For now, return mock data to test the frontend integration
        # TODO: Implement real Sumsub API calls
        verification_token = "mock_token_123"
        applicant_id = f"applicant_{current_user.id}"

        return {
            "success": True,
            "verification_token": verification_token,
            "applicant_id": applicant_id,
            "sdk_url": "https://api.sumsub.com/idensic/liveness/latest.js",
            "config": {
                "token": verification_token,
                "applicantId": applicant_id,
                "endpoint": "https://api.sumsub.com",
                "locale": "en",
                "theme": "light"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize verification: {str(e)}")


@router.post("/sumsub/webhook")
async def sumsub_webhook(request: Request):
    """Handle Sumsub webhooks for verification status updates"""
    # In production, verify webhook signature
    data = await request.json()

    # Handle different webhook events
    event_type = data.get("type")
    applicant_id = data.get("applicantId")
    review_status = data.get("reviewStatus")

    # Update user verification status based on webhook
    if event_type == "applicantReviewed" and review_status == "completed":
        # Mark user as verified
        pass

    return {"status": "ok"}