"""
Sumsub Webhook Handler
Comprehensive webhook processing for all Sumsub verification events
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hmac
import hashlib
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.verification_event import VerificationEvent
from app.models.customer_verification_data import CustomerVerificationData
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


def verify_sumsub_webhook_signature(payload: str, signature: str) -> bool:
    """Verify that webhook signature is valid"""
    try:
        expected_signature = hmac.new(
            settings.SUMSUB_SECRET_KEY.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def get_user_by_external_id(db: Session, external_user_id: str) -> User | None:
    """
    Get user by external user ID (user_id field, format: NF-MMYYYY###)
    """
    try:
        # External user ID format: "user_NF-012025001"
        if external_user_id.startswith("user_"):
            user_id = external_user_id.replace("user_", "")
            user = db.query(User).filter(User.user_id == user_id).first()
            return user
        return None
    except Exception as e:
        logger.error(f"Error getting user by external ID {external_user_id}: {e}")
        return None


def get_or_create_verification_data(db: Session, user_id: int) -> CustomerVerificationData:
    """
    Get or create customer verification data for a user
    """
    verification_data = db.query(CustomerVerificationData).filter(
        CustomerVerificationData.user_id == user_id
    ).first()

    if not verification_data:
        verification_data = CustomerVerificationData(user_id=user_id)
        db.add(verification_data)
        db.commit()
        db.refresh(verification_data)

    return verification_data


def update_user_verification_status(
    user: User,
    event_type: str,
    review_status: str,
    review_result: dict,
    applicant_id: str,
    inspection_id: str,
    db: Session
) -> None:
    """
    Update user verification status based on webhook event
    """
    try:
        # Store applicant and inspection IDs
        user.sumsub_applicant_id = applicant_id
        user.sumsub_inspection_id = inspection_id

        # Handle different event types
        if event_type in ["applicantCreated", "applicantActivated", "applicantReset"]:
            user.verification_status = "not_started"
            user.is_verified = False
            user.verification_result = None

        elif event_type == "applicantPending":
            user.verification_status = "pending"
            user.is_verified = False

        elif event_type in ["applicantAwaitingUser", "applicantAwaitingService"]:
            user.verification_status = "pending"
            # Keep current is_verified status

        elif event_type == "applicantOnHold":
            user.verification_status = "on_hold"
            user.is_verified = False

        elif event_type in ["applicantReviewed", "applicantWorkflowCompleted"]:
            user.verification_status = "completed"

            # Check review result
            review_answer = review_result.get("reviewAnswer") if review_result else None

            if review_answer == "GREEN":
                user.is_verified = True
                user.verification_result = "GREEN"
                user.verification_completed_at = datetime.now(timezone.utc)
                logger.info(f"User {user.user_id} verified successfully")

                # Automatically mark Step 2 (Sumsub verification) as complete
                try:
                    verification_data = get_or_create_verification_data(db, user.id)
                    if not verification_data.step_2_completed:
                        verification_data.step_2_completed = True
                        verification_data.step_2_completed_at = datetime.now(timezone.utc)
                        db.commit()
                        logger.info(f"Automatically marked Step 2 complete for user {user.user_id}")
                except Exception as e:
                    logger.error(f"Error marking step 2 complete: {e}")
                    # Don't fail the webhook if this fails

                # Automatically create wallets for verified user
                try:
                    from app.core.dfns_client import create_user_wallets_batch
                    from app.models.wallet import Wallet
                    
                    # Check if user already has wallets
                    existing_wallets = db.query(Wallet).filter(Wallet.user_id == user.id).count()
                    
                    if existing_wallets == 0:
                        logger.info(f"Creating wallets for newly verified user {user.user_id}")
                        wallets_created = create_user_wallets_batch(user.id, db)
                        logger.info(f"Successfully created {len(wallets_created)} wallets for user {user.user_id}")
                    else:
                        logger.info(f"User {user.user_id} already has {existing_wallets} wallets, skipping creation")
                except Exception as e:
                    logger.error(f"Error creating wallets for user {user.user_id}: {e}")
                    # Don't fail the webhook if wallet creation fails

            elif review_answer == "RED":
                user.is_verified = False
                user.verification_result = "RED"
                user.verification_completed_at = datetime.now(timezone.utc)

                # Store reject labels if available
                reject_labels = review_result.get("rejectLabels", [])
                if reject_labels:
                    user.verification_error_message = f"Rejected: {', '.join(reject_labels)}"
                logger.info(f"User {user.user_id} verification rejected")

        elif event_type == "applicantWorkflowFailed":
            user.verification_status = "failed"
            user.is_verified = False
            user.verification_result = "RED"

            # Store failure reason
            review_answer = review_result.get("reviewAnswer") if review_result else None
            reject_labels = review_result.get("rejectLabels", []) if review_result else []
            if reject_labels:
                user.verification_error_message = f"Failed: {', '.join(reject_labels)}"

        elif event_type == "applicantDeactivated":
            user.verification_status = "deactivated"
            user.is_verified = False

        elif event_type == "applicantDeleted":
            user.verification_status = "deleted"
            user.is_verified = False

        db.commit()
        logger.info(f"Updated user {user.user_id} verification status: {user.verification_status}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user verification status: {e}")
        raise


def store_verification_event(
    user: User,
    event_data: dict,
    db: Session
) -> None:
    """
    Store verification event in database
    """
    try:
        event = VerificationEvent(
            user_id=user.id,
            event_type=event_data.get("type"),
            applicant_id=event_data.get("applicantId"),
            inspection_id=event_data.get("inspectionId"),
            correlation_id=event_data.get("correlationId"),
            external_user_id=event_data.get("externalUserId"),
            level_name=event_data.get("levelName"),
            review_status=event_data.get("reviewStatus"),
            review_result=event_data.get("reviewResult", {}).get("reviewAnswer") if event_data.get("reviewResult") else None,
            sandbox_mode=event_data.get("sandboxMode", False),
            created_at_ms=event_data.get("createdAtMs"),
            raw_data=event_data,
            processed=True
        )

        db.add(event)
        db.commit()
        logger.info(f"Stored verification event: {event.event_type} for user {user.user_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error storing verification event: {e}")
        # Don't raise - we don't want to fail the webhook if event storage fails


@router.post("/sumsub/webhook")
async def sumsub_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Sumsub webhooks for verification status updates

    Processes all Sumsub webhook event types:
    - applicantCreated: Applicant created
    - applicantPending: Under review
    - applicantReviewed: Review completed (GREEN/RED)
    - applicantOnHold: Review on hold
    - applicantAwaitingUser: Waiting for user action
    - applicantAwaitingService: Waiting for service
    - applicantWorkflowCompleted: Workflow completed
    - applicantWorkflowFailed: Workflow failed
    - applicantReset: Verification reset
    - applicantActivated: Applicant activated
    - applicantDeactivated: Applicant deactivated
    - applicantDeleted: Applicant deleted
    - And more...
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        payload = body.decode('utf-8')

        # Verify webhook signature
        signature = request.headers.get('X-Payload-Digest-Alg-SHA256')
        if signature:
            if not verify_sumsub_webhook_signature(payload, signature):
                logger.warning("Invalid webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )
        else:
            logger.warning("No signature provided in webhook")

        # Parse webhook data
        data = await request.json()

        # Extract webhook fields
        event_type = data.get("type")
        external_user_id = data.get("externalUserId")
        applicant_id = data.get("applicantId")
        inspection_id = data.get("inspectionId")
        review_status = data.get("reviewStatus")
        review_result = data.get("reviewResult")
        sandbox_mode = data.get("sandboxMode", False)

        logger.info(f"Received Sumsub webhook: {event_type} for {external_user_id}")

        # Validate required fields
        if not event_type or not external_user_id:
            logger.error(f"Missing required fields in webhook: {data}")
            return {"status": "error", "message": "Missing required fields"}

        # Get user by external user ID
        user = get_user_by_external_id(db, external_user_id)

        if not user:
            logger.error(f"User not found for external ID: {external_user_id}")
            return {"status": "error", "message": f"User not found: {external_user_id}"}

        # Log sandbox mode if enabled
        if sandbox_mode:
            logger.info(f"Webhook is from sandbox mode")

        # Update user verification status
        update_user_verification_status(
            user=user,
            event_type=event_type,
            review_status=review_status,
            review_result=review_result,
            applicant_id=applicant_id,
            inspection_id=inspection_id,
            db=db
        )

        # Store verification event
        store_verification_event(
            user=user,
            event_data=data,
            db=db
        )

        return {
            "status": "ok",
            "message": f"Processed {event_type} for user {user.user_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/sumsub/webhook/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is accessible"
    }
