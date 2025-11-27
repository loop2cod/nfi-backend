"""
BVNK Agreement Router
Handles agreement signing session creation and management for Embedded Partner Customers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.core.database import get_db
from app.models.user import User
from app.routers.auth.auth_router import get_current_user
from app.core.bvnk_client import get_bvnk_client, BVNKClient
from app.models.customer_verification_data import CustomerVerificationData

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class CreateAgreementSessionRequest(BaseModel):
    """Request model for creating an agreement session"""
    country_code: str = Field(..., description="ISO country code (e.g., 'US', 'GB')")
    customer_type: str = Field(..., description="'INDIVIDUAL' or 'COMPANY'")
    use_case: str = Field(
        ...,
        description="Use case: 'STABLECOIN_PAYOUTS', 'EMBEDDED_STABLECOIN_WALLETS', or 'EMBEDDED_FIAT_ACCOUNTS'"
    )


class AgreementSessionResponse(BaseModel):
    """Response model for agreement session"""
    success: bool
    reference: Optional[str] = None
    hosted_url: Optional[str] = None
    status: Optional[str] = None
    message: str


class UpdateAgreementSessionRequest(BaseModel):
    """Request model for updating agreement session"""
    status: str = Field(..., description="Status - typically 'SIGNED'")


class AgreementSessionStatusResponse(BaseModel):
    """Response model for agreement session status"""
    success: bool
    reference: str
    status: str
    message: str


@router.post("/agreement/session/create", response_model=AgreementSessionResponse)
async def create_agreement_session(
    request: CreateAgreementSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    bvnk_client: BVNKClient = Depends(get_bvnk_client)
):
    """
    Create an agreement signing session for the current user

    This endpoint creates a BVNK agreement session which must be signed before
    creating a BVNK customer account. Returns a reference and hosted URL.

    Workflow:
    1. Create session via BVNK API
    2. Return reference and hosted URL
    3. Frontend redirects user to hosted URL to sign agreements
    4. User is redirected back after signing
    5. Frontend calls verify endpoint to confirm signature
    """
    try:
        logger.info(f"Creating agreement session for user {current_user.user_id}")

        # Validate customer type
        if request.customer_type not in ["INDIVIDUAL", "COMPANY"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="customer_type must be 'INDIVIDUAL' or 'COMPANY'"
            )

        # Validate use case
        valid_use_cases = [
            "STABLECOIN_PAYOUTS",
            "EMBEDDED_STABLECOIN_WALLETS",
            "EMBEDDED_FIAT_ACCOUNTS"
        ]
        if request.use_case not in valid_use_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"use_case must be one of {valid_use_cases}"
            )

        # Create agreement session via BVNK
        response = bvnk_client.create_agreement_session(
            country_code=request.country_code,
            customer_type=request.customer_type,
            use_case=request.use_case
        )

        # Extract reference from response
        reference = response.get("reference")

        if not reference:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get agreement session reference from BVNK"
            )

        # Store reference in user's verification data
        verification_data = db.query(CustomerVerificationData).filter(
            CustomerVerificationData.user_id == current_user.id
        ).first()

        if verification_data and verification_data.step_data is None:
            verification_data.step_data = {}

        if verification_data:
            step_data = verification_data.step_data or {}
            step_data["bvnk_agreement_reference"] = reference
            step_data["bvnk_country_code"] = request.country_code
            step_data["bvnk_customer_type"] = request.customer_type
            step_data["bvnk_use_case"] = request.use_case
            verification_data.step_data = step_data
            db.commit()

        # Construct hosted URL for agreement signing
        # Format: https://signup.sandbox.bvnk.com/agreements?session={reference}&redirectUri={callback}
        base_url = "https://signup.sandbox.bvnk.com" if "sandbox" in bvnk_client.base_url else "https://signup.bvnk.com"
        # Frontend will provide its own redirect URI
        hosted_url = f"{base_url}/agreements?session={reference}"

        logger.info(f"Agreement session created for user {current_user.user_id}: {reference}")

        return AgreementSessionResponse(
            success=True,
            reference=reference,
            hosted_url=hosted_url,
            status=response.get("status", "CREATED"),
            message="Agreement session created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agreement session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agreement session: {str(e)}"
        )


@router.get("/agreement/session/{reference}", response_model=AgreementSessionStatusResponse)
async def get_agreement_session_status(
    reference: str,
    current_user: User = Depends(get_current_user),
    bvnk_client: BVNKClient = Depends(get_bvnk_client)
):
    """
    Get the status of an agreement signing session

    Use this endpoint to verify that the user has successfully signed the agreements
    before proceeding to create a BVNK customer account.

    Statuses:
    - CREATED: Session created, not yet signed
    - SIGNED: User has signed the agreements
    - EXPIRED: Session has expired
    """
    try:
        logger.info(f"Getting agreement session status for user {current_user.user_id}: {reference}")

        # Get session status from BVNK
        response = bvnk_client.get_agreement_session(reference)

        session_status = response.get("status", "UNKNOWN")

        logger.info(f"Agreement session {reference} status: {session_status}")

        return AgreementSessionStatusResponse(
            success=True,
            reference=reference,
            status=session_status,
            message=f"Agreement session status: {session_status}"
        )

    except Exception as e:
        logger.error(f"Error getting agreement session status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agreement session status: {str(e)}"
        )


@router.put("/agreement/session/{reference}/sign", response_model=AgreementSessionStatusResponse)
async def sign_agreement_session(
    reference: str,
    request: UpdateAgreementSessionRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    bvnk_client: BVNKClient = Depends(get_bvnk_client)
):
    """
    Sign an agreement session directly via API (Direct API approach)

    This is an alternative to the hosted URL approach. Use this if you want to
    handle agreement display and acceptance in your own UI.

    Note: Most implementations should use the hosted URL approach instead.
    """
    try:
        logger.info(f"Signing agreement session for user {current_user.user_id}: {reference}")

        # Get user's IP address
        client_ip = http_request.client.host

        # Update agreement session status
        response = bvnk_client.update_agreement_session(
            reference=reference,
            status=request.status,
            ip_address=client_ip
        )

        session_status = response.get("status", "UNKNOWN")

        logger.info(f"Agreement session {reference} updated to status: {session_status}")

        return AgreementSessionStatusResponse(
            success=True,
            reference=reference,
            status=session_status,
            message=f"Agreement session updated to: {session_status}"
        )

    except Exception as e:
        logger.error(f"Error updating agreement session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agreement session: {str(e)}"
        )


@router.get("/agreements")
async def get_agreements(
    current_user: User = Depends(get_current_user),
    bvnk_client: BVNKClient = Depends(get_bvnk_client)
):
    """
    Fetch all required agreement documents

    Returns a list of agreement documents that need to be signed.
    Useful for the Direct API approach where you display agreements in your own UI.
    """
    try:
        logger.info(f"Fetching agreements for user {current_user.user_id}")

        # Get agreements from BVNK
        response = bvnk_client.get_agreements()

        return {
            "success": True,
            "agreements": response,
            "message": "Agreements fetched successfully"
        }

    except Exception as e:
        logger.error(f"Error fetching agreements: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agreements: {str(e)}"
        )
