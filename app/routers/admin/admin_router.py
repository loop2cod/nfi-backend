"""
Admin Router for Client Dashboard
Provides administrative endpoints for managing end users
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.admin_user import AdminUser
from app.models.admin_login_history import AdminLoginHistory
from app.models.customer_verification_data import CustomerVerificationData
from app.models.verification_audit_log import VerificationAuditLog
from app.models.wallet import Wallet
from app.routers.admin.admin_auth_router import get_current_admin
from app.core.dfns_client import create_user_wallets_batch
from app.models.verification_audit_log import VerificationAuditLog

# Set up logging
logger = logging.getLogger(__name__)
from pydantic import BaseModel, EmailStr
from decimal import Decimal


router = APIRouter()


class CustomerListItem(BaseModel):
    """Response model for customer list item"""
    id: int
    user_id: str
    email: str
    is_active: bool
    is_verified: bool
    verification_status: str
    verification_result: Optional[str] = None
    bvnk_customer_id: Optional[str] = None
    bvnk_customer_created_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Response model for paginated customer list"""
    customers: List[CustomerListItem]
    total: int
    page: int
    size: int
    total_pages: int


class WalletInfo(BaseModel):
    """Response model for wallet information"""
    id: int
    currency: str
    address: str
    balance: float
    available_balance: float
    frozen_balance: float
    network: str
    wallet_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerDetailResponse(BaseModel):
    """Response model for detailed customer information"""
    id: int
    user_id: str
    email: str
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    verification_status: str
    verification_result: Optional[str] = None
    sumsub_applicant_id: Optional[str] = None
    sumsub_inspection_id: Optional[str] = None
    verification_level_name: Optional[str] = None
    verification_completed_at: Optional[datetime] = None
    verification_error_message: Optional[str] = None
    bvnk_customer_id: Optional[str] = None
    bvnk_customer_created_at: Optional[datetime] = None
    wallets: List[WalletInfo] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerStatsResponse(BaseModel):
    """Response model for customer statistics"""
    total_customers: int
    verified_customers: int


class LoginHistoryResponse(BaseModel):
    """Response model for login history"""
    id: int
    login_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    login_method: Optional[str]
    login_status: str
    location: Optional[str]
    device_type: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=None).isoformat() + 'Z' if v else None
        }


class CustomerVerificationDataResponse(BaseModel):
    """Response model for customer verification data"""
    # Personal Info (Step 1)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    state_code: Optional[str] = None
    country: Optional[str] = None

    # Tax Info (Step 3)
    tax_identification_number: Optional[str] = None
    tax_residence_country_code: Optional[str] = None

    # CDD (Step 4)
    employment_status: Optional[str] = None
    source_of_funds: Optional[str] = None
    pep_status: Optional[str] = None
    account_purpose: Optional[str] = None
    expected_monthly_volume_amount: Optional[Decimal] = None
    expected_monthly_volume_currency: Optional[str] = None

    # Progress tracking
    step_1_completed: bool = False
    step_2_completed: bool = False
    step_3_completed: bool = False
    step_4_completed: bool = False
    all_steps_completed: bool = False

    step_1_completed_at: Optional[datetime] = None
    step_2_completed_at: Optional[datetime] = None
    step_3_completed_at: Optional[datetime] = None
    step_4_completed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """Response model for audit log entry"""
    id: int
    user_id: int
    admin_id: Optional[int] = None
    action_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    old_result: Optional[str] = None
    new_result: Optional[str] = None
    step_number: Optional[int] = None
    step_name: Optional[str] = None
    comment: Optional[str] = None
    admin_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response model for paginated audit log list"""
    logs: List[AuditLogResponse]
    total: int
    page: int
    size: int
    total_pages: int


class UpdateVerificationStatusRequest(BaseModel):
    """Request model for updating verification status"""
    verification_status: str
    verification_result: Optional[str] = None
    verification_error_message: Optional[str] = None
    step_number: Optional[int] = None
    step_name: Optional[str] = None


@router.get("/customers", response_model=CustomerListResponse)
def get_customers(
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search by user_id or email"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    has_bvnk_customer: Optional[bool] = Query(None, description="Filter by BVNK customer existence"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of customers with optional filters.

    Supports filtering by:
    - search: user_id or email
    - verification_status: pending, completed, action_required, failed
    - is_verified: true/false
    - has_bvnk_customer: true/false
    """
    # Build base query
    query = db.query(User)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.user_id.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    if verification_status:
        query = query.filter(User.verification_status == verification_status)

    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    if has_bvnk_customer is not None:
        if has_bvnk_customer:
            query = query.filter(User.bvnk_customer_id.isnot(None))
        else:
            query = query.filter(User.bvnk_customer_id.is_(None))

    # Get total count
    total = query.count()

    # Apply pagination
    customers = query.offset(page * size).limit(size).all()

    # Calculate total pages
    total_pages = (total + size - 1) // size  # Ceiling division

    # Convert to response model
    customer_items = []
    for customer in customers:
        customer_dict = {
            "id": customer.id,  # type: ignore
            "user_id": customer.user_id,  # type: ignore
            "email": customer.email,  # type: ignore
            "is_active": customer.is_active,  # type: ignore
            "is_verified": customer.is_verified,  # type: ignore
            "verification_status": customer.verification_status,  # type: ignore
            "verification_result": customer.verification_result,  # type: ignore
            "bvnk_customer_id": customer.bvnk_customer_id,  # type: ignore
            "bvnk_customer_created_at": customer.bvnk_customer_created_at,  # type: ignore
            "created_at": customer.created_at  # type: ignore
        }
        customer_items.append(CustomerListItem(**customer_dict))

    return CustomerListResponse(
        customers=customer_items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )


@router.post("/customers/{user_id}/update-verification-status")
def update_customer_verification_status(
    user_id: str,
    request: UpdateVerificationStatusRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update customer verification status (admin only).

    Allowed statuses:
    - "completed" with result "GREEN" → Mark as verified
    - "completed" with result "RED" → Mark as rejected
    - "action_required" → Request additional information (optionally specify step)

    Parameters:
    - step_number: Optional 1-4 to indicate which step needs action
    - step_name: Optional human-readable step name
    """
    from datetime import datetime, timezone

    customer = db.query(User).filter(User.user_id == user_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with user_id {user_id} not found"
        )

    # Store old values for audit log
    old_status = customer.verification_status
    old_result = customer.verification_result

    # Extract parameters from request
    verification_status = request.verification_status
    verification_result = request.verification_result
    verification_error_message = request.verification_error_message
    step_number = request.step_number
    step_name = request.step_name

    # Validate status
    valid_statuses = ["completed", "action_required", "pending", "failed"]
    if verification_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification status. Must be one of: {', '.join(valid_statuses)}"
        )

    # Determine action type for audit log
    action_type = "status_change"

    # Update verification status
    customer.verification_status = verification_status

    if verification_status == "completed":
        if verification_result == "GREEN":
            customer.is_verified = True
            customer.verification_result = "GREEN"
            customer.verification_completed_at = datetime.now(timezone.utc)
            customer.verification_error_message = None
            message = f"Customer {user_id} marked as verified"
            action_type = "approved"
        elif verification_result == "RED":
            customer.is_verified = False
            customer.verification_result = "RED"
            customer.verification_completed_at = datetime.now(timezone.utc)
            customer.verification_error_message = verification_error_message or "Verification rejected by admin"
            message = f"Customer {user_id} marked as rejected"
            action_type = "rejected"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="verification_result must be 'GREEN' or 'RED' when status is 'completed'"
            )
    elif verification_status == "action_required":
        customer.is_verified = False
        customer.verification_result = None
        customer.verification_error_message = verification_error_message or "Additional information required"
        message = f"Customer {user_id} requires action"
        action_type = "action_requested"
    elif verification_status == "pending":
        customer.is_verified = False
        customer.verification_result = None
        customer.verification_error_message = None
        message = f"Customer {user_id} status set to pending"
    else:  # failed
        customer.is_verified = False
        customer.verification_result = "RED"
        customer.verification_error_message = verification_error_message or "Verification failed"
        message = f"Customer {user_id} marked as failed"

    try:
        db.commit()
        db.refresh(customer)

        # Create audit log entry
        audit_log = VerificationAuditLog(
            user_id=customer.id,
            admin_id=current_admin.id,
            action_type=action_type,
            old_status=old_status,
            new_status=verification_status,
            old_result=old_result,
            new_result=customer.verification_result,
            step_number=step_number,
            step_name=step_name,
            admin_message=verification_error_message,
            comment=message
        )
        db.add(audit_log)
        db.commit()

        return {
            "success": True,
            "message": message,
            "verification_status": customer.verification_status,
            "is_verified": customer.is_verified,
            "verification_result": customer.verification_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update verification status: {str(e)}"
        )


@router.get("/customers/{user_id}", response_model=CustomerDetailResponse)
def get_customer_detail(
    user_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific customer.
    Accessible by authenticated admin users.
    """
    customer = db.query(User).filter(User.user_id == user_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with user_id {user_id} not found"
        )

    # Get customer's wallets
    db_wallets = db.query(Wallet).filter(Wallet.user_id == customer.id).all()

    # Sync wallet status with DFNS
    wallet_status = {"active": [], "deleted": []}
    wallets_to_show = []

    if db_wallets:
        from app.core.dfns_client import dfns_client
        if dfns_client:
            # Convert db wallets to dict format for sync
            db_wallets_dict = [
                {
                    "id": w.id,
                    "wallet_id": w.wallet_id,
                    "currency": w.currency,
                    "network": w.network,
                    "address": w.address
                }
                for w in db_wallets
            ]

            # Sync with DFNS
            wallet_status = dfns_client.sync_wallet_status(customer.id, db_wallets_dict)

            # Mark deleted wallets in database
            for wallet in db_wallets:
                if wallet.wallet_id in wallet_status["deleted"]:
                    # Update wallet status in database
                    db.query(Wallet).filter(Wallet.id == wallet.id).update({"status": "deleted"})
            db.commit()

            # Prepare wallets for response with status
            for wallet in db_wallets:
                wallet_dict = {
                    "id": wallet.id,
                    "currency": wallet.currency,
                    "address": wallet.address,
                    "balance": wallet.balance,
                    "available_balance": wallet.available_balance,
                    "frozen_balance": wallet.frozen_balance,
                    "network": wallet.network,
                    "wallet_id": wallet.wallet_id,
                    "status": "active" if wallet.wallet_id in wallet_status["active"] else "deleted",
                    "created_at": wallet.created_at
                }
                wallets_to_show.append(wallet_dict)
        else:
            # DFNS not available, show all wallets as active
            wallets_to_show = [
                {
                    "id": w.id,
                    "currency": w.currency,
                    "address": w.address,
                    "balance": w.balance,
                    "available_balance": w.available_balance,
                    "frozen_balance": w.frozen_balance,
                    "network": w.network,
                    "wallet_id": w.wallet_id,
                    "status": "active",
                    "created_at": w.created_at
                }
                for w in db_wallets
            ]

    # Get available wallet types that can be created
    from app.core.wallet_config import get_wallets_to_create
    available_wallet_types = get_wallets_to_create()

    # Check which wallets are missing (check by currency+network combination)
    existing_wallet_pairs = {
        (w["currency"], w["network"]) 
        for w in wallets_to_show 
        if w["status"] == "active"
    }
    missing_wallets = [
        {"currency": config["currency"], "network": config["network"]}
        for config in available_wallet_types
        if (config["currency"], config["network"]) not in existing_wallet_pairs
    ]

    # Create response with wallets and creation options
    customer_dict = {
        "id": customer.id,
        "user_id": customer.user_id,
        "email": customer.email,
        "is_active": customer.is_active,
        "is_verified": customer.is_verified,
        "is_2fa_enabled": customer.is_2fa_enabled,
        "verification_status": customer.verification_status,
        "verification_result": customer.verification_result,
        "sumsub_applicant_id": customer.sumsub_applicant_id,
        "sumsub_inspection_id": customer.sumsub_inspection_id,
        "verification_level_name": customer.verification_level_name,
        "verification_completed_at": customer.verification_completed_at,
        "verification_error_message": customer.verification_error_message,
        "bvnk_customer_id": customer.bvnk_customer_id,
        "bvnk_customer_created_at": customer.bvnk_customer_created_at,
        "wallets": wallets_to_show,
        "missing_wallets": missing_wallets,
        "wallet_sync_status": wallet_status,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
    }

    return customer_dict


@router.get("/customers/{user_id}/verification-data", response_model=CustomerVerificationDataResponse)
def get_customer_verification_data(
    user_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed verification data for a specific customer.
    Returns all information collected during the multi-step verification process.
    Accessible by authenticated admin users only.
    """
    # First, verify the customer exists
    customer = db.query(User).filter(User.user_id == user_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with user_id {user_id} not found"
        )

    # Get verification data
    verification_data = db.query(CustomerVerificationData).filter(
        CustomerVerificationData.user_id == customer.id
    ).first()

    # If no verification data exists yet, return empty structure
    if not verification_data:
        return CustomerVerificationDataResponse()

    # Convert to dict and handle date_of_birth conversion before validation
    data_dict = {
        # Personal Info (Step 1)
        "first_name": verification_data.first_name,
        "last_name": verification_data.last_name,
        "date_of_birth": verification_data.date_of_birth.isoformat() if verification_data.date_of_birth else None,
        "nationality": verification_data.nationality,
        "email_address": verification_data.email_address,
        "phone_number": verification_data.phone_number,
        "address_line1": verification_data.address_line1,
        "address_line2": verification_data.address_line2,
        "city": verification_data.city,
        "postal_code": verification_data.postal_code,
        "country_code": verification_data.country_code,
        "state_code": verification_data.state_code,
        "country": verification_data.country,
        # Tax Info (Step 3)
        "tax_identification_number": verification_data.tax_identification_number,
        "tax_residence_country_code": verification_data.tax_residence_country_code,
        # CDD (Step 4)
        "employment_status": verification_data.employment_status,
        "source_of_funds": verification_data.source_of_funds,
        "pep_status": verification_data.pep_status,
        "account_purpose": verification_data.account_purpose,
        "expected_monthly_volume_amount": verification_data.expected_monthly_volume_amount,
        "expected_monthly_volume_currency": verification_data.expected_monthly_volume_currency,
        # Progress tracking
        "step_1_completed": verification_data.step_1_completed,
        "step_2_completed": verification_data.step_2_completed,
        "step_3_completed": verification_data.step_3_completed,
        "step_4_completed": verification_data.step_4_completed,
        "all_steps_completed": verification_data.all_steps_completed,
        "step_1_completed_at": verification_data.step_1_completed_at,
        "step_2_completed_at": verification_data.step_2_completed_at,
        "step_3_completed_at": verification_data.step_3_completed_at,
        "step_4_completed_at": verification_data.step_4_completed_at,
        "completed_at": verification_data.completed_at,
        "created_at": verification_data.created_at,
        "updated_at": verification_data.updated_at,
    }

    return CustomerVerificationDataResponse(**data_dict)


@router.get("/customers/stats/summary", response_model=CustomerStatsResponse)
def get_customer_stats(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for all customers.
    Accessible by authenticated admin users.
    """
    total_customers = db.query(func.count(User.id)).scalar()
    verified_customers = db.query(func.count(User.id)).filter(User.is_verified == True).scalar()

    return CustomerStatsResponse(
        total_customers=total_customers,
        verified_customers=verified_customers
    )


@router.get("/my-login-history", response_model=List[LoginHistoryResponse])
def get_my_login_history(
    limit: int = Query(15, ge=1, le=50, description="Number of records to return"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get current admin's login history.
    Returns login events for the authenticated admin user.
    """
    login_history = db.query(AdminLoginHistory).filter(
        AdminLoginHistory.admin_id == current_admin.id
    ).order_by(AdminLoginHistory.login_at.desc()).limit(limit).all()

    return login_history


@router.post("/customers/{user_id}/retry-bvnk")
def retry_bvnk_customer_creation(
    user_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Manually retry BVNK customer creation for a verified user.
    Useful if BVNK creation failed during webhook processing.
    """
    from app.core.bvnk_client import get_bvnk_client
    from datetime import datetime, timezone

    customer = db.query(User).filter(User.user_id == user_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with user_id {user_id} not found"
        )

    if not customer.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer must be verified before creating BVNK account"
        )

    if customer.bvnk_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BVNK customer already exists for this user"
        )

    try:
        bvnk_client = get_bvnk_client()
        customer_data = bvnk_client.create_customer(
            external_reference=customer.user_id,
            email=customer.email,
            metadata={
                "user_id": customer.user_id,
                "verified_at": customer.verification_completed_at.isoformat() if customer.verification_completed_at else datetime.now(timezone.utc).isoformat(),
                "verification_level": customer.verification_level_name or "basic"
            }
        )
        customer.bvnk_customer_id = customer_data.get('id')
        customer.bvnk_customer_created_at = datetime.now(timezone.utc)
        customer.verification_error_message = None
        db.commit()

        # Create audit log entry
        audit_log = VerificationAuditLog(
            user_id=customer.id,
            admin_id=current_admin.id,
            action_type="bvnk_retry",
            comment=f"BVNK customer created successfully by admin {current_admin.username}"
        )
        db.add(audit_log)
        db.commit()

        return {
            "success": True,
            "message": "BVNK customer created successfully",
            "bvnk_customer_id": customer.bvnk_customer_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create BVNK customer: {str(e)}"
        )


@router.get("/customers/{user_id}/audit-logs", response_model=AuditLogListResponse)
def get_customer_audit_logs(
    user_id: str,
    page: int = Query(0, ge=0, description="Page number (starts from 0)"),
    size: int = Query(20, ge=1, le=100, description="Number of records per page"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit logs for a specific customer with pagination.
    Shows all verification-related actions and changes.
    """
    # First verify customer exists
    customer = db.query(User).filter(User.user_id == user_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with user_id {user_id} not found"
        )

    # Build query for audit logs
    query = db.query(VerificationAuditLog).filter(
        VerificationAuditLog.user_id == customer.id
    ).order_by(VerificationAuditLog.created_at.desc())

    # Get total count
    total = query.count()

    # Calculate total pages
    total_pages = (total + size - 1) // size if total > 0 else 0

    # Apply pagination
    logs = query.offset(page * size).limit(size).all()

    return AuditLogListResponse(
        logs=logs,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )


@router.post("/customers/{user_id}/create-wallets")
def create_customer_wallets(
    user_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """

    Create wallets for a specific customer
    """
    try:
        # Validate user_id format
        if not user_id.startswith("NF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format. Must start with 'NF-'"
            )

        # Get customer from database
        customer = db.query(User).filter(User.user_id == user_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with user_id {user_id} not found"
            )

        # Check if customer is verified
        if not customer.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer must be verified before creating wallets"
            )

        # Check if wallets already exist
        existing_wallets = db.query(Wallet).filter(Wallet.user_id == customer.id).all()
        if existing_wallets:
            return {
                "success": False,
                "message": f"Customer already has {len(existing_wallets)} wallets",
                "wallets": [
                    {
                        "id": wallet.id,
                        "currency": wallet.currency,
                        "address": wallet.address,
                        "network": wallet.network,
                        "wallet_id": wallet.wallet_id
                    }
                    for wallet in existing_wallets
                ]
             }

        logger.info(f"Admin {current_admin.username} creating wallets for user {user_id}")

        # Prepare user info for DFNS registration if needed
        user_info = None
        if not customer.dfns_user_id and customer.first_name and customer.last_name and customer.email:
            user_info = {
                "external_id": f"user_{customer.id}",
                "email": customer.email,
                "display_name": f"{customer.first_name} {customer.last_name}",
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "date_of_birth": customer.date_of_birth,
                "nationality": customer.nationality
            }

        # Create wallets using the batch function
        created_wallets = create_user_wallets_batch(customer.id, customer.dfns_user_id, user_info)

        if created_wallets:
            # Check if DFNS end user was registered during wallet creation
            # The function returns created_wallets, but we need to check if dfns_user_id was set
            # For now, we'll check the customer record again after wallet creation
            db.refresh(customer)  # Refresh to get any updates

            # Save wallet data to database
            saved_wallets = []
            for wallet_data in created_wallets:
                db_wallet = Wallet(**wallet_data)
                db.add(db_wallet)
                db.flush()  # Get the ID and created_at
                saved_wallets.append({
                    "id": db_wallet.id,
                    "currency": db_wallet.currency,
                    "address": db_wallet.address,
                    "balance": db_wallet.balance,
                    "available_balance": db_wallet.available_balance,
                    "frozen_balance": db_wallet.frozen_balance,
                    "network": db_wallet.network,
                    "wallet_id": db_wallet.wallet_id,
                    "status": db_wallet.status,
                    "created_at": db_wallet.created_at
                })

            db.commit()
            logger.info(f"Successfully created {len(created_wallets)} wallets for user {user_id}")

            # Create audit log entry for wallet creation
            audit_log = VerificationAuditLog(
                user_id=customer.id,
                admin_id=current_admin.id,
                action_type="wallets_created",
                comment=f"Admin {current_admin.username} manually created {len(saved_wallets)} wallets"
            )
            db.add(audit_log)
            db.commit()

            return {
                "success": True,
                "message": f"Successfully created {len(saved_wallets)} wallets",
                "wallets": saved_wallets
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create wallets"
            )

    except Exception as e:
        logger.error(f"Error creating wallets for user {user_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wallets: {str(e)}"
        )


@router.post("/customers/{user_id}/create-wallet")
def create_specific_wallet(
    user_id: str,
    wallet_request: dict,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a specific wallet for a customer.
    Body: {"currency": "BTC", "network": "Bitcoin"}
    """
    from app.core.dfns_client import create_user_wallet
    import logging
    logger = logging.getLogger(__name__)

    customer = db.query(User).filter(User.user_id == user_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with user_id {user_id} not found"
        )

    currency = wallet_request.get("currency")
    network = wallet_request.get("network")

    if not currency or not network:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency and network are required"
        )

    # Check if wallet already exists
    existing_wallet = db.query(Wallet).filter(
        Wallet.user_id == customer.id,
        Wallet.currency == currency,
        Wallet.network == network
    ).first()

    if existing_wallet:
        return {
            "success": False,
            "message": f"Wallet {currency} on {network} already exists",
            "wallet": {
                "id": existing_wallet.id,
                "currency": existing_wallet.currency,
                "address": existing_wallet.address,
                "network": existing_wallet.network,
                "wallet_id": existing_wallet.wallet_id
            }
        }

    try:
        logger.info(f"Admin {current_admin.username} creating {currency} wallet on {network} for user {user_id}")

        # Create the specific wallet
        wallet_data = create_user_wallet(customer.id,customer.user_id, currency, network)

        if wallet_data:
            # Save to database
            db_wallet = Wallet(**wallet_data)
            db.add(db_wallet)
            db.commit()

            logger.info(f"Successfully created {currency} wallet for user {user_id}")

            # Create audit log
            audit_log = VerificationAuditLog(
                user_id=customer.id,
                admin_id=current_admin.id,
                action_type="wallet_created",
                comment=f"Admin {current_admin.username} created {currency} wallet on {network}"
            )
            db.add(audit_log)
            db.commit()

            return {
                "success": True,
                "message": f"Successfully created {currency} wallet on {network}",
                "wallet": {
                    "id": db_wallet.id,
                    "currency": db_wallet.currency,
                    "address": db_wallet.address,
                    "balance": db_wallet.balance,
                    "available_balance": db_wallet.available_balance,
                    "frozen_balance": db_wallet.frozen_balance,
                    "network": db_wallet.network,
                    "wallet_id": db_wallet.wallet_id,
                    "status": db_wallet.status,
                    "created_at": db_wallet.created_at
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {currency} wallet on {network}"
            )

    except Exception as e:
        logger.error(f"Error creating {currency} wallet for user {user_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wallet: {str(e)}"
        )

    # Check if customer is verified
    if not customer.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer must be verified before creating wallets"
        )

    # Check if wallets already exist
    existing_wallets = db.query(Wallet).filter(Wallet.user_id == customer.id).all()
    if existing_wallets:
        return {
            "success": False,
            "message": f"Customer already has {len(existing_wallets)} wallets",
            "wallets": [
                {
                    "id": wallet.id,
                    "currency": wallet.currency,
                    "address": wallet.address,
                    "network": wallet.network,
                    "wallet_id": wallet.wallet_id
                }
                for wallet in existing_wallets
            ]
        }

    try:
        logger.info(f"Admin {current_admin.username} creating wallets for user {user_id}")

        # Prepare user info for DFNS registration if needed
        user_info = None
        if not customer.dfns_user_id and customer.first_name and customer.last_name and customer.email:
            user_info = {
                "external_id": f"user_{customer.id}",
                "email": customer.email,
                "display_name": f"{customer.first_name} {customer.last_name}",
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "date_of_birth": customer.date_of_birth,
                "nationality": customer.nationality
            }

        # Create wallets using the batch function
        created_wallets = create_user_wallets_batch(customer.id, customer.dfns_user_id, user_info)

        if created_wallets:
            # Save wallet data to database
            for wallet_data in created_wallets:
                db_wallet = Wallet(**wallet_data)
                db.add(db_wallet)

            db.commit()
            logger.info(f"Successfully created {len(created_wallets)} wallets for user {user_id}")

            # Create audit log entry for wallet creation
            audit_log = VerificationAuditLog(
                user_id=customer.id,
                admin_id=current_admin.id,
                action_type="wallets_created",
                comment=f"Admin {current_admin.username} manually created {len(created_wallets)} wallets"
            )
            db.add(audit_log)
            db.commit()

            return {
                "success": True,
                "message": f"Successfully created {len(created_wallets)} wallet(s)",
                "wallets": [
                    {
                        "currency": wallet_data["currency"],
                        "address": wallet_data["address"],
                        "network": wallet_data["network"],
                        "wallet_id": wallet_data["wallet_id"],
                        "status": "CREATED"
                    }
                    for wallet_data in created_wallets
                ]
            }
        else:
            return {
                "success": False,
                "message": "No wallets were created",
                "wallets": []
            }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating wallets for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wallets: {str(e)}"
        )
