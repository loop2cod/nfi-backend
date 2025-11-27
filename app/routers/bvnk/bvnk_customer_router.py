"""
BVNK Customer Router
Handles BVNK customer creation for verified users (Admin use)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.customer_verification_data import CustomerVerificationData
from app.routers.admin.admin_auth_router import get_current_admin
from app.core.bvnk_client import get_bvnk_client, BVNKClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class CreateBvnkCustomerResponse(BaseModel):
    """Response model for BVNK customer creation"""
    success: bool
    message: str
    bvnk_customer_id: Optional[str] = None
    bvnk_customer_status: Optional[str] = None
    agreement_reference: Optional[str] = None


@router.post("/customer/create/{user_id}", response_model=CreateBvnkCustomerResponse)
async def create_bvnk_customer(
    user_id: str,
    admin_user=Depends(get_current_admin),
    db: Session = Depends(get_db),
    bvnk_client: BVNKClient = Depends(get_bvnk_client)
):
    """
    Create a BVNK customer account for a verified user (Admin only)

    Flow:
    1. Validate user exists and is verified
    2. Check all verification steps are completed
    3. Create/verify agreement session exists
    4. Create BVNK INDIVIDUAL customer
    5. Store BVNK customer ID in database

    Requirements:
    - User must be verified (is_verified = True)
    - All 4 verification steps must be completed
    - User must have complete personal information
    """
    try:
        logger.info(f"Admin {admin_user.username} initiating BVNK customer creation for user {user_id}")

        # Get user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Check if BVNK customer already exists
        if user.bvnk_customer_id:
            logger.info(f"User {user_id} already has BVNK customer ID: {user.bvnk_customer_id}")
            return CreateBvnkCustomerResponse(
                success=True,
                message=f"BVNK customer already exists",
                bvnk_customer_id=user.bvnk_customer_id,
                bvnk_customer_status="EXISTING"
            )

        # Check if user is verified
        if not user.is_verified or user.verification_result != "GREEN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must complete KYC verification before creating BVNK customer"
            )

        # Get verification data
        verification_data = db.query(CustomerVerificationData).filter(
            CustomerVerificationData.user_id == user.id
        ).first()

        if not verification_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification data found for user"
            )

        # Check all steps are completed
        if not verification_data.all_steps_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must complete all verification steps first"
            )

        # Validate required data exists
        if not all([
            verification_data.first_name,
            verification_data.last_name,
            verification_data.date_of_birth,
            verification_data.nationality,
            verification_data.address_line1,
            verification_data.city,
            verification_data.postal_code,
            verification_data.country_code
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required personal information. User must complete all verification steps."
            )

        # Get or create agreement session reference
        step_data = verification_data.step_data or {}
        agreement_reference = step_data.get("bvnk_agreement_reference")

        if not agreement_reference:
            # Create agreement session
            logger.info(f"Creating agreement session for user {user_id}")
            try:
                agreement_response = bvnk_client.create_agreement_session(
                    country_code=verification_data.country_code,
                    customer_type="INDIVIDUAL",
                    use_case="EMBEDDED_STABLECOIN_WALLETS"
                )
                agreement_reference = agreement_response.get("reference")

                # Store reference in verification data
                step_data["bvnk_agreement_reference"] = agreement_reference
                step_data["bvnk_country_code"] = verification_data.country_code
                step_data["bvnk_customer_type"] = "INDIVIDUAL"
                step_data["bvnk_use_case"] = "EMBEDDED_STABLECOIN_WALLETS"
                verification_data.step_data = step_data
                db.commit()

                logger.info(f"Agreement session created for user {user_id}: {agreement_reference}")
            except Exception as e:
                logger.error(f"Error creating agreement session: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create agreement session: {str(e)}"
                )

        # Note: We're assuming the agreement is auto-signed in sandbox/for admin creation
        # In production, you might need to check if agreement is actually SIGNED

        # Create BVNK customer
        logger.info(f"Creating BVNK INDIVIDUAL customer for user {user_id}")

        try:
            # Get document number from Sumsub applicant ID as fallback
            document_number = user.sumsub_applicant_id or f"DOC-{user.user_id}"

            bvnk_response = bvnk_client.create_customer_individual(
                first_name=verification_data.first_name,
                last_name=verification_data.last_name,
                date_of_birth=verification_data.date_of_birth.strftime("%Y-%m-%d"),
                birth_country_code=verification_data.nationality,
                document_number=document_number,
                address_line1=verification_data.address_line1,
                city=verification_data.city,
                post_code=verification_data.postal_code,
                country_code=verification_data.country_code,
                signed_agreement_session_reference=agreement_reference,
                email=verification_data.email_address or user.email,
                risk_score="LOW"  # Default to LOW for verified customers
            )

            # Extract customer ID and status from response
            bvnk_customer_id = bvnk_response.get("id") or bvnk_response.get("customerId")
            bvnk_customer_status = bvnk_response.get("status", "CREATED")

            if not bvnk_customer_id:
                logger.error(f"No customer ID in BVNK response: {bvnk_response}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="BVNK did not return a customer ID"
                )

            # Store BVNK customer ID in user record
            user.bvnk_customer_id = bvnk_customer_id
            user.bvnk_customer_created_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"BVNK customer created successfully for user {user_id}: {bvnk_customer_id}")

            return CreateBvnkCustomerResponse(
                success=True,
                message=f"BVNK customer created successfully",
                bvnk_customer_id=bvnk_customer_id,
                bvnk_customer_status=bvnk_customer_status,
                agreement_reference=agreement_reference
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating BVNK customer: {e}", exc_info=True)
            # Store error in user record
            user.bvnk_customer_error = str(e)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create BVNK customer: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_bvnk_customer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
