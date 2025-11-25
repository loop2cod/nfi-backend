from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import logging
import hmac
import hashlib
import os
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.core.bvnk_client import get_bvnk_client
from app.models.user import User
from app.models.verification_event import VerificationEvent
from app.models.schemas import SumsubWebhookEvent, WebhookProcessingResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Sumsub webhook signature for security.
    
    Sumsub signs webhook payloads with HMAC SHA256 using your webhook secret.
    The signature is sent in the X-Sumsub-Signature header.
    """
    if not secret:
        logger.warning("Webhook signature verification skipped - no secret configured")
        return True  # Allow in development
    
    if not signature:
        logger.error("Missing webhook signature")
        return False
    
    # Sumsub sends signature in format: "sha256=<signature>"
    if signature.startswith("sha256="):
        signature = signature[7:]
    
    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures securely
    return hmac.compare_digest(signature, expected_signature)


@router.post("/sumsub", response_model=WebhookProcessingResponse)
async def handle_sumsub_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Sumsub webhook events.
    
    This endpoint receives webhook notifications from Sumsub when verification
    status changes occur. It processes the event and updates the user's 
    verification status accordingly.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature for security
        signature = request.headers.get("x-sumsub-signature", "")
        webhook_secret = settings.SUMSUB_WEBHOOK_SECRET or ""
        
        if not verify_webhook_signature(body, signature, webhook_secret):
            logger.error("Webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse JSON payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        logger.info(f"Received Sumsub webhook: {payload.get('type', 'unknown')} for applicant {payload.get('applicantId', 'unknown')}")
        
        # Validate required fields
        if not payload.get('applicantId') or not payload.get('type'):
            logger.error("Missing required fields in webhook payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: applicantId, type"
            )
        
        # Find user by applicant ID
        user = db.query(User).filter(User.sumsub_applicant_id == payload.get('applicantId')).first()
        
        if not user:
            logger.warning(f"User not found for applicant ID: {payload.get('applicantId')}")
            # Still return success but don't process
            return WebhookProcessingResponse(
                success=True,
                message=f"User not found for applicant ID: {payload.get('applicantId')}",
                event_processed=False
            )
        
        # Create verification event record
        verification_event = VerificationEvent(
            user_id=user.id,
            event_type=payload.get('type'),
            event_data=payload,
            applicant_id=payload.get('applicantId'),
            inspection_id=payload.get('inspectionId'),
            correlation_id=payload.get('correlationId'),
            review_status=payload.get('reviewStatus'),
            review_result=payload.get('reviewResult', {}).get('reviewAnswer') if payload.get('reviewResult') else None,
            level_name=payload.get('levelName'),
            external_user_id=payload.get('externalUserId'),
            sandbox_mode=str(payload.get('sandboxMode', False)),
            client_id=payload.get('clientId'),
            processed=False
        )
        
        db.add(verification_event)
        
        # Process the webhook event
        processing_result = await process_verification_event(db, user, payload)
        
        # Update event as processed
        verification_event.processed = True
        if not processing_result.get('success'):
            verification_event.error_message = processing_result.get('error_message')
        
        db.commit()
        
        logger.info(f"Successfully processed webhook event {payload.get('type')} for user {user.id}")
        
        return WebhookProcessingResponse(
            success=True,
            message="Webhook processed successfully",
            user_id=user.id,
            event_processed=True
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


async def process_verification_event(db: Session, user: User, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process different types of verification events and update user status accordingly.
    """
    event_type = payload.get('type')
    review_status = payload.get('reviewStatus')
    review_result = payload.get('reviewResult', {}).get('reviewAnswer') if payload.get('reviewResult') else None
    
    try:
        # Update common fields
        if payload.get('applicantId') and not user.sumsub_applicant_id:
            user.sumsub_applicant_id = payload.get('applicantId')
        
        if payload.get('inspectionId'):
            user.sumsub_inspection_id = payload.get('inspectionId')
            
        if payload.get('levelName'):
            user.verification_level_name = payload.get('levelName')
        
        # Process based on event type
        if event_type == "applicantCreated":
            user.verification_status = "pending"
            logger.info(f"User {user.id} verification started - applicant created")
            
        elif event_type == "applicantPending":
            user.verification_status = "pending"
            logger.info(f"User {user.id} verification pending review")
            
        elif event_type == "applicantReviewed":
            user.verification_status = "completed"
            user.verification_result = review_result
            user.verification_completed_at = datetime.utcnow()
            
            if review_result == "GREEN":
                user.is_verified = True
                user.verification_error_message = None
                logger.info(f"User {user.id} verification completed successfully")

                # Create BVNK customer after successful KYC
                if not user.bvnk_customer_id:
                    try:
                        bvnk_client = get_bvnk_client()
                        customer_data = bvnk_client.create_customer(
                            external_reference=user.user_id,
                            email=user.email,
                            metadata={
                                "user_id": user.user_id,
                                "verified_at": datetime.utcnow().isoformat(),
                                "verification_level": user.verification_level_name or "basic"
                            }
                        )
                        user.bvnk_customer_id = customer_data.get('id')
                        user.bvnk_customer_created_at = datetime.utcnow()
                        logger.info(f"BVNK customer created for user {user.id}: {user.bvnk_customer_id}")
                    except Exception as e:
                        logger.error(f"Failed to create BVNK customer for user {user.id}: {str(e)}")
                        # Don't fail the entire process if BVNK creation fails
                        user.verification_error_message = f"KYC approved but BVNK customer creation pending: {str(e)}"
            elif review_result == "RED":
                user.is_verified = False
                reject_labels = payload.get('reviewResult', {}).get('rejectLabels', [])
                user.verification_error_message = f"Verification rejected: {', '.join(reject_labels)}"
                logger.info(f"User {user.id} verification rejected: {reject_labels}")
                
        elif event_type == "applicantOnHold":
            user.verification_status = "on_hold"
            logger.info(f"User {user.id} verification on hold")
            
        elif event_type == "applicantAwaitingUser":
            user.verification_status = "awaiting_user"
            logger.info(f"User {user.id} verification awaiting user action")
            
        elif event_type == "applicantAwaitingService":
            user.verification_status = "awaiting_service"
            logger.info(f"User {user.id} verification awaiting service")
            
        elif event_type in ["applicantWorkflowCompleted", "applicantWorkflowFailed"]:
            user.verification_status = "completed"
            user.verification_result = review_result
            user.verification_completed_at = datetime.utcnow()
            
            if review_result == "GREEN":
                user.is_verified = True
                user.verification_error_message = None

                # Create BVNK customer after successful KYC workflow
                if not user.bvnk_customer_id:
                    try:
                        bvnk_client = get_bvnk_client()
                        customer_data = bvnk_client.create_customer(
                            external_reference=user.user_id,
                            email=user.email,
                            metadata={
                                "user_id": user.user_id,
                                "verified_at": datetime.utcnow().isoformat(),
                                "verification_level": user.verification_level_name or "basic"
                            }
                        )
                        user.bvnk_customer_id = customer_data.get('id')
                        user.bvnk_customer_created_at = datetime.utcnow()
                        logger.info(f"BVNK customer created for user {user.id}: {user.bvnk_customer_id}")
                    except Exception as e:
                        logger.error(f"Failed to create BVNK customer for user {user.id}: {str(e)}")
                        user.verification_error_message = f"KYC approved but BVNK customer creation pending: {str(e)}"
            else:
                user.is_verified = False
                reject_labels = payload.get('reviewResult', {}).get('rejectLabels', [])
                user.verification_error_message = f"Workflow failed: {', '.join(reject_labels)}"
                
        elif event_type == "applicantReset":
            user.verification_status = "not_started"
            user.verification_result = None
            user.is_verified = False
            user.verification_completed_at = None
            user.verification_error_message = None
            logger.info(f"User {user.id} verification reset")
            
        # Update verification steps tracking
        if not user.verification_steps:
            user.verification_steps = {}
        
        user.verification_steps[event_type] = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': review_status,
            'result': review_result,
            'data': payload
        }
        
        db.commit()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Error processing verification event: {str(e)}")
        db.rollback()
        return {'success': False, 'error_message': str(e)}