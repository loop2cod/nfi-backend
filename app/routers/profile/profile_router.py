from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.schemas import (
    UserProfileResponse,
    SendEmailOTPRequest,
    SendEmailOTPResponse,
    VerifyEmailOTPRequest,
    VerifyEmailOTPResponse,
    UpdatePhoneRequest,
    UpdatePhoneResponse,
    Update2FARequest,
    Update2FAResponse,
    UpdateNameRequest,
    UpdateNameResponse
)
from app.routers.auth.auth_router import get_current_user
import random
import string
from datetime import datetime, timedelta

router = APIRouter()


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email: str, otp: str):
    """Send OTP via email - placeholder for actual email service"""
    # TODO: Implement actual email sending logic
    print(f"[EMAIL OTP] Sending OTP {otp} to {email}")
    # This would integrate with your email service (SendGrid, SES, etc.)
    pass


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's profile"""
    return current_user


@router.post("/profile/send-email-otp", response_model=SendEmailOTPResponse)
async def send_email_otp(
    request: SendEmailOTPRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send OTP to new email for verification"""
    # Check if email is already in use
    existing_user = db.query(User).filter(User.email == request.new_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use"
        )

    # Generate OTP
    otp = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    # Store OTP temporarily (using two_fa_otp field)
    current_user.two_fa_otp = otp
    current_user.two_fa_otp_expiry = otp_expiry
    current_user.two_fa_email = request.new_email  # Temporarily store new email
    db.commit()

    # Send OTP via email
    send_otp_email(request.new_email, otp)

    return SendEmailOTPResponse(
        success=True,
        message="OTP sent to new email"
    )


@router.post("/profile/verify-email-otp", response_model=VerifyEmailOTPResponse)
async def verify_email_otp(
    request: VerifyEmailOTPRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify OTP and update email"""
    # Check if OTP exists and is valid
    if not current_user.two_fa_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP found. Please request a new one."
        )

    # Check if OTP has expired
    if current_user.two_fa_otp_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    # Verify OTP
    if current_user.two_fa_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    # Verify the new email matches what was stored
    if current_user.two_fa_email != request.new_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email mismatch"
        )

    # Update email
    current_user.email = request.new_email

    # Clear OTP fields
    current_user.two_fa_otp = None
    current_user.two_fa_otp_expiry = None
    current_user.two_fa_email = None

    db.commit()

    return VerifyEmailOTPResponse(
        success=True,
        message="Email updated successfully"
    )


@router.put("/profile/phone", response_model=UpdatePhoneResponse)
async def update_phone(
    request: UpdatePhoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's phone number"""
    # Basic validation
    if not request.phone_number or len(request.phone_number) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number"
        )

    # Update phone number
    current_user.phone_number = request.phone_number
    db.commit()

    return UpdatePhoneResponse(
        success=True,
        message="Phone number updated successfully",
        phone_number=request.phone_number
    )


@router.put("/profile/2fa", response_model=Update2FAResponse)
async def update_2fa(
    request: Update2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle 2FA on or off"""
    current_user.is_2fa_enabled = request.is_2fa_enabled

    # If enabling 2FA, set the 2FA email to current email
    if request.is_2fa_enabled:
        current_user.two_fa_email = current_user.email
    else:
        # Clear 2FA related fields when disabling
        current_user.two_fa_email = None
        current_user.two_fa_otp = None
        current_user.two_fa_otp_expiry = None

    db.commit()

    return Update2FAResponse(
        success=True,
        message=f"2FA {'enabled' if request.is_2fa_enabled else 'disabled'} successfully",
        is_2fa_enabled=request.is_2fa_enabled
    )


@router.put("/profile/name", response_model=UpdateNameResponse)
async def update_name(
    request: UpdateNameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's first and last name"""
    # Basic validation
    if not request.first_name or not request.last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name and last name are required"
        )

    if len(request.first_name) < 2 or len(request.last_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Names must be at least 2 characters long"
        )

    # Update names
    current_user.first_name = request.first_name.strip()
    current_user.last_name = request.last_name.strip()
    db.commit()

    return UpdateNameResponse(
        success=True,
        message="Name updated successfully",
        first_name=request.first_name,
        last_name=request.last_name
    )
