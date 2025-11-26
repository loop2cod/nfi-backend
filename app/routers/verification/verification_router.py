"""
Verification Router - Multi-step KYC Verification Flow

Handles customer verification in 4 steps:
1. Personal Information
2. Sumsub Liveness Check
3. Tax Information
4. CDD (Customer Due Diligence)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any, List
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.routers.auth.auth_router import get_current_user
from app.models.user import User
from app.models.customer_verification_data import CustomerVerificationData
from app.models.verification_event import VerificationEvent
from app.models.verification_audit_log import VerificationAuditLog
from app.schemas.verification_schemas import (
    PersonalInformationSchema,
    TaxInformationSchema,
    CDDInformationSchema,
    VerificationStepResponse,
    VerificationProgressResponse,
    CustomerVerificationDataResponse
)
from app.models.schemas import (
    VerificationStatusResponse,
    VerificationStepResponse as LegacyVerificationStepResponse,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================

def get_or_create_verification_data(db: Session, user_id: int) -> CustomerVerificationData:
    """Get existing verification data or create new one"""
    verification_data = db.query(CustomerVerificationData).filter(
        CustomerVerificationData.user_id == user_id
    ).first()

    if not verification_data:
        verification_data = CustomerVerificationData(user_id=user_id)
        db.add(verification_data)
        db.commit()
        db.refresh(verification_data)

    return verification_data


def get_current_step(verification_data: CustomerVerificationData) -> int:
    """Determine the current verification step"""
    if not verification_data.step_1_completed:
        return 1
    elif not verification_data.step_2_completed:
        return 2
    elif not verification_data.step_3_completed:
        return 3
    elif not verification_data.step_4_completed:
        return 4
    else:
        return 5  # All steps completed


def check_all_steps_completed(verification_data: CustomerVerificationData) -> bool:
    """Check if all verification steps are completed"""
    return (
        verification_data.step_1_completed and
        verification_data.step_2_completed and
        verification_data.step_3_completed and
        verification_data.step_4_completed
    )


# ============================================================================
# Legacy Endpoints (Compatibility)
# ============================================================================

@router.get("/status", response_model=VerificationStatusResponse)
@limiter.limit("30/minute")
def get_verification_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current verification status for the authenticated user."""
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


@router.get("/steps", response_model=List[LegacyVerificationStepResponse])
def get_verification_steps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed verification steps for the authenticated user."""
    try:
        steps = []

        if current_user.verification_steps:
            for step_name, step_data in current_user.verification_steps.items():
                steps.append(LegacyVerificationStepResponse(
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
    """Get verification events history for the authenticated user."""
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
@limiter.limit("5/hour")
def retry_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset verification status to allow retry."""
    try:
        if current_user.verification_status not in ["failed", "error"] and not current_user.verification_error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification retry not allowed for current status"
            )

        current_user.verification_status = "not_started"
        current_user.verification_result = None
        current_user.verification_error_message = None
        current_user.verification_completed_at = None
        current_user.is_verified = False

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


# ============================================================================
# Step 1: Personal Information
# ============================================================================

@router.post("/step-1/personal-info", response_model=VerificationStepResponse)
async def save_personal_information(
    personal_info: PersonalInformationSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1: Save personal information

    Collects: firstName, lastName, dateOfBirth, nationality, email, phone, address
    """
    try:
        logger.info(f"Step 1: Saving personal info for user {current_user.user_id}")

        # Get or create verification data
        verification_data = get_or_create_verification_data(db, current_user.id)

        # Update personal information
        verification_data.first_name = personal_info.first_name
        verification_data.last_name = personal_info.last_name
        verification_data.date_of_birth = personal_info.date_of_birth
        verification_data.nationality = personal_info.nationality
        verification_data.email_address = personal_info.email_address
        verification_data.phone_number = personal_info.phone_number

        # Update address
        verification_data.address_line1 = personal_info.address.address_line1
        verification_data.address_line2 = personal_info.address.address_line2
        verification_data.postal_code = personal_info.address.postal_code
        verification_data.city = personal_info.address.city
        verification_data.country_code = personal_info.address.country_code
        verification_data.state_code = personal_info.address.state_code
        verification_data.country = personal_info.address.country

        # Mark step 1 as completed
        verification_data.step_1_completed = True
        verification_data.step_1_completed_at = datetime.now(timezone.utc)

        # Also update User model fields
        current_user.first_name = personal_info.first_name
        current_user.last_name = personal_info.last_name
        current_user.date_of_birth = personal_info.date_of_birth.isoformat()
        current_user.nationality = personal_info.nationality
        current_user.phone_number = personal_info.phone_number
        current_user.address_line1 = personal_info.address.address_line1
        current_user.address_line2 = personal_info.address.address_line2
        current_user.postal_code = personal_info.address.postal_code
        current_user.city = personal_info.address.city
        current_user.country_code = personal_info.address.country_code
        current_user.state_code = personal_info.address.state_code

        db.commit()
        db.refresh(verification_data)

        # Create audit log entry
        audit_log = VerificationAuditLog(
            user_id=current_user.id,
            admin_id=None,  # User action, no admin
            action_type="data_updated",
            step_number=1,
            step_name="Personal Information",
            comment="User updated personal information (Step 1)"
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Step 1 completed for user {current_user.user_id}")

        return VerificationStepResponse(
            success=True,
            message="Personal information saved successfully",
            step_number=1,
            step_completed=True,
            next_step=2,
            all_steps_completed=False
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving personal info for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save personal information: {str(e)}"
        )


# ============================================================================
# Step 2: Sumsub Liveness Check
# ============================================================================

@router.post("/step-2/sumsub-complete", response_model=VerificationStepResponse)
async def mark_sumsub_completed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 2: Mark Sumsub liveness check as completed

    This endpoint is called after Sumsub verification is successfully completed.
    The actual verification is handled by Sumsub webhook.
    """
    try:
        logger.info(f"Step 2: Marking Sumsub complete for user {current_user.user_id}")

        # Check if user has completed Sumsub verification
        if current_user.verification_status != "completed" or current_user.verification_result != "GREEN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sumsub verification not completed or not approved"
            )

        # Get verification data
        verification_data = get_or_create_verification_data(db, current_user.id)

        # Check if step 1 is completed
        if not verification_data.step_1_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete Step 1 (Personal Information) first"
            )

        # Mark step 2 as completed
        verification_data.step_2_completed = True
        verification_data.step_2_completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(verification_data)

        # Create audit log entry
        audit_log = VerificationAuditLog(
            user_id=current_user.id,
            admin_id=None,
            action_type="data_updated",
            step_number=2,
            step_name="Document Verification (Sumsub)",
            comment="User completed Sumsub document verification (Step 2)"
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Step 2 completed for user {current_user.user_id}")

        return VerificationStepResponse(
            success=True,
            message="Sumsub verification completed successfully",
            step_number=2,
            step_completed=True,
            next_step=3,
            all_steps_completed=False
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking Sumsub complete for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark Sumsub as completed: {str(e)}"
        )


# ============================================================================
# Step 3: Tax Information
# ============================================================================

@router.post("/step-3/tax-info", response_model=VerificationStepResponse)
async def save_tax_information(
    tax_info: TaxInformationSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 3: Save tax information

    Collects: Tax ID number, tax residence country
    """
    try:
        logger.info(f"Step 3: Saving tax info for user {current_user.user_id}")

        # Get verification data
        verification_data = get_or_create_verification_data(db, current_user.id)

        # Check if previous steps are completed
        if not verification_data.step_1_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete Step 1 (Personal Information) first"
            )
        if not verification_data.step_2_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete Step 2 (Sumsub Verification) first"
            )

        # Update tax information
        verification_data.tax_identification_number = tax_info.tax_identification_number
        verification_data.tax_residence_country_code = tax_info.tax_residence_country_code

        # Mark step 3 as completed
        verification_data.step_3_completed = True
        verification_data.step_3_completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(verification_data)

        # Create audit log entry
        audit_log = VerificationAuditLog(
            user_id=current_user.id,
            admin_id=None,
            action_type="data_updated",
            step_number=3,
            step_name="Tax Information",
            comment="User updated tax information (Step 3)"
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Step 3 completed for user {current_user.user_id}")

        return VerificationStepResponse(
            success=True,
            message="Tax information saved successfully",
            step_number=3,
            step_completed=True,
            next_step=4,
            all_steps_completed=False
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving tax info for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save tax information: {str(e)}"
        )


# ============================================================================
# Step 4: CDD Information
# ============================================================================

@router.post("/step-4/cdd-info", response_model=VerificationStepResponse)
async def save_cdd_information(
    cdd_info: CDDInformationSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 4: Save CDD (Customer Due Diligence) information

    Collects: Employment status, source of funds, PEP status, account purpose,
              expected monthly volume
    """
    try:
        logger.info(f"Step 4: Saving CDD info for user {current_user.user_id}")

        # Get verification data
        verification_data = get_or_create_verification_data(db, current_user.id)

        # Check if previous steps are completed
        if not verification_data.step_1_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete Step 1 (Personal Information) first"
            )
        if not verification_data.step_2_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete Step 2 (Sumsub Verification) first"
            )
        if not verification_data.step_3_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete Step 3 (Tax Information) first"
            )

        # Update CDD information
        verification_data.employment_status = cdd_info.employment_status
        verification_data.source_of_funds = cdd_info.source_of_funds
        verification_data.pep_status = cdd_info.pep_status
        verification_data.account_purpose = cdd_info.account_purpose
        verification_data.expected_monthly_volume_amount = cdd_info.expected_monthly_volume_amount
        verification_data.expected_monthly_volume_currency = cdd_info.expected_monthly_volume_currency

        # Mark step 4 as completed
        verification_data.step_4_completed = True
        verification_data.step_4_completed_at = datetime.now(timezone.utc)

        # Check if all steps are completed
        all_steps_completed = check_all_steps_completed(verification_data)
        if all_steps_completed:
            verification_data.all_steps_completed = True
            verification_data.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(verification_data)

        # Create audit log entry
        audit_log = VerificationAuditLog(
            user_id=current_user.id,
            admin_id=None,
            action_type="data_updated",
            step_number=4,
            step_name="Customer Due Diligence (CDD)",
            comment="User updated CDD information (Step 4)" + (" - All steps completed!" if all_steps_completed else "")
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Step 4 completed for user {current_user.user_id}")

        # TODO: Trigger BVNK customer creation if all steps completed
        next_step = None if all_steps_completed else 5

        return VerificationStepResponse(
            success=True,
            message="CDD information saved successfully. All verification steps completed!" if all_steps_completed else "CDD information saved successfully",
            step_number=4,
            step_completed=True,
            next_step=next_step,
            all_steps_completed=all_steps_completed
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving CDD info for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save CDD information: {str(e)}"
        )


# ============================================================================
# Progress and Data Retrieval
# ============================================================================

@router.get("/progress", response_model=VerificationProgressResponse)
async def get_verification_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current verification progress"""
    try:
        verification_data = get_or_create_verification_data(db, current_user.id)
        current_step = get_current_step(verification_data)

        return VerificationProgressResponse(
            step_1_completed=verification_data.step_1_completed,
            step_2_completed=verification_data.step_2_completed,
            step_3_completed=verification_data.step_3_completed,
            step_4_completed=verification_data.step_4_completed,
            all_steps_completed=verification_data.all_steps_completed,
            current_step=current_step,
            completed_at=verification_data.completed_at
        )

    except Exception as e:
        logger.error(f"Error getting verification progress for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get verification progress: {str(e)}"
        )


@router.get("/data", response_model=CustomerVerificationDataResponse)
async def get_verification_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete verification data"""
    try:
        verification_data = get_or_create_verification_data(db, current_user.id)
        return CustomerVerificationDataResponse.from_orm(verification_data)

    except Exception as e:
        logger.error(f"Error getting verification data for user {current_user.user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get verification data: {str(e)}"
        )
