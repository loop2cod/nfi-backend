"""
TOTP (Time-based One-Time Password) Router
Handles authenticator app setup and verification
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.routers.auth.auth_router import get_current_user
import pyotp
import qrcode
import io
import base64
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class TOTPSetupResponse(BaseModel):
    success: bool
    secret: str
    qr_code: str  # Base64 encoded QR code image
    provisioning_uri: str
    message: str
    account_name: str
    issuer: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPVerifyResponse(BaseModel):
    success: bool
    message: str
    totp_enabled: bool


class TOTPStatusResponse(BaseModel):
    totp_enabled: bool
    totp_configured: bool


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate TOTP secret and QR code for authenticator app setup
    """
    # Generate a new TOTP secret
    secret = pyotp.random_base32()

    # Create provisioning URI for QR code
    # Format: otpauth://totp/Issuer:AccountName?secret=SECRET&issuer=Issuer
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="NFI Platform"
    )

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Store secret temporarily (will be confirmed after verification)
    current_user.totp_secret = secret
    db.commit()

    return TOTPSetupResponse(
        success=True,
        secret=secret,
        qr_code=qr_code_base64,
        provisioning_uri=provisioning_uri,
        message="Scan the QR code with your authenticator app or enter the secret key manually",
        account_name=current_user.email,
        issuer="NFI Platform"
    )


@router.post("/totp/verify", response_model=TOTPVerifyResponse)
async def verify_totp_setup(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify TOTP code and enable TOTP for the user
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP setup not initiated. Please call /totp/setup first"
        )

    # Verify the TOTP code
    totp = pyotp.TOTP(current_user.totp_secret)
    is_valid = totp.verify(request.code, valid_window=2)  # Allow 2 time steps (±60 seconds) for clock drift

    # Debug logging
    print(f"[TOTP DEBUG] Verifying code: {request.code}")
    print(f"[TOTP DEBUG] Expected code: {totp.now()}")
    print(f"[TOTP DEBUG] Is valid: {is_valid}")

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please try again"
        )

    # Enable TOTP for the user
    current_user.totp_enabled = True
    db.commit()

    return TOTPVerifyResponse(
        success=True,
        message="Authenticator app successfully configured",
        totp_enabled=True
    )


@router.post("/totp/verify-code", response_model=TOTPVerifyResponse)
async def verify_totp_code(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify TOTP code during login (for already configured TOTP)
    """
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled for this user"
        )

    # Verify the TOTP code
    totp = pyotp.TOTP(current_user.totp_secret)
    is_valid = totp.verify(request.code, valid_window=1)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    return TOTPVerifyResponse(
        success=True,
        message="Code verified successfully",
        totp_enabled=True
    )


@router.delete("/totp/disable")
async def disable_totp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable and remove TOTP configuration
    """
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled"
        )

    # Remove TOTP configuration
    current_user.totp_secret = None
    current_user.totp_enabled = False

    # Remove TOTP from methods priority if present
    if current_user.two_fa_methods_priority and 'totp' in current_user.two_fa_methods_priority:
        current_user.two_fa_methods_priority = [
            m for m in current_user.two_fa_methods_priority if m != 'totp'
        ]

    db.commit()

    return {
        "success": True,
        "message": "Authenticator app disabled successfully"
    }


@router.get("/totp/status", response_model=TOTPStatusResponse)
async def get_totp_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get TOTP configuration status for current user
    """
    return TOTPStatusResponse(
        totp_enabled=current_user.totp_enabled or False,
        totp_configured=bool(current_user.totp_secret and current_user.totp_enabled)
    )
