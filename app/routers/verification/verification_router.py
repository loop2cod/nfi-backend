from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import List
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.verification_event import VerificationEvent
from app.models.schemas import (
    VerificationStatusResponse, 
    VerificationStepResponse,
    SumsubInitRequest,
    SumsubInitResponse
)
from app.routers.auth.auth_router import get_current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/status", response_model=VerificationStatusResponse)
@limiter.limit("30/minute")  # Allow 30 requests per minute per IP
def get_verification_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current verification status for the authenticated user.
    """
    try:
        return VerificationStatusResponse(
            verification_status=current_user.verification_status,
            verification_result=current_user.verification_result,
            sumsub_applicant_id=current_user.sumsub_applicant_id,
            verification_completed_at=current_user.verification_completed_at,
            verification_steps=current_user.verification_steps,
            verification_error_message=current_user.verification_error_message
        )
    except Exception as e:
        logger.error(f"Error getting verification status for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving verification status"
        )


@router.get("/steps", response_model=List[VerificationStepResponse])
def get_verification_steps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed verification steps for the authenticated user.
    """
    try:
        steps = []
        
        if current_user.verification_steps:
            for step_name, step_data in current_user.verification_steps.items():
                steps.append(VerificationStepResponse(
                    step_name=step_name,
                    status=step_data.get('status', 'unknown'),
                    completed_at=step_data.get('timestamp'),
                    error_message=step_data.get('error_message')
                ))
        
        return steps
    except Exception as e:
        logger.error(f"Error getting verification steps for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving verification steps"
        )


@router.get("/events")
def get_verification_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """
    Get verification events history for the authenticated user.
    """
    try:
        events = db.query(VerificationEvent)\
                   .filter(VerificationEvent.user_id == current_user.id)\
                   .order_by(VerificationEvent.created_at.desc())\
                   .limit(limit)\
                   .all()
        
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "review_status": event.review_status,
                "review_result": event.review_result,
                "created_at": event.created_at,
                "processed": event.processed,
                "error_message": event.error_message
            }
            for event in events
        ]
    except Exception as e:
        logger.error(f"Error getting verification events for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving verification events"
        )


@router.post("/retry")
@limiter.limit("5/hour")  # Limited retries - 5 per hour per IP
def retry_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset verification status to allow retry.
    """
    try:
        # Only allow retry if verification failed or has errors
        if current_user.verification_status not in ["failed", "error"] and not current_user.verification_error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification retry not allowed for current status"
            )
        
        # Reset verification status
        current_user.verification_status = "not_started"
        current_user.verification_result = None
        current_user.verification_error_message = None
        current_user.verification_completed_at = None
        current_user.is_verified = False
        
        # Keep the applicant ID for continuation
        # current_user.sumsub_applicant_id = None  # Uncomment if you want fresh start
        
        db.commit()
        
        logger.info(f"Verification retry initiated for user {current_user.id}")
        
        return {"success": True, "message": "Verification reset for retry"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying verification for user {current_user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrying verification"
        )