from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.schemas import Enable2FARequest, Enable2FAResponse
from app.routers.auth.auth_router import get_current_user

router = APIRouter()

@router.post("/enable-2fa", response_model=Enable2FAResponse)
def enable_2fa(
    request: Enable2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA for the current user"""
    try:
        # Update user's 2FA settings
        current_user.is_2fa_enabled = True
        current_user.two_fa_email = request.email
        
        db.commit()
        db.refresh(current_user)
        
        return Enable2FAResponse(
            success=True,
            message="2FA enabled successfully",
            is_2fa_enabled=True,
            two_fa_email=request.email
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable 2FA: {str(e)}"
        )

@router.post("/disable-2fa")
def disable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA for the current user"""
    try:
        current_user.is_2fa_enabled = False
        current_user.two_fa_email = None
        current_user.two_fa_otp = None
        current_user.two_fa_otp_expiry = None
        
        db.commit()
        
        return {"success": True, "message": "2FA disabled successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable 2FA: {str(e)}"
        )

@router.get("/2fa-status")
def get_2fa_status(current_user: User = Depends(get_current_user)):
    """Get 2FA status for the current user"""
    return {
        "is_2fa_enabled": current_user.is_2fa_enabled,
        "two_fa_email": current_user.two_fa_email
    }