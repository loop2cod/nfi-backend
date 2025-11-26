"""
Admin Router for Client Dashboard
Provides administrative endpoints for managing end users
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.admin_user import AdminUser
from app.models.admin_login_history import AdminLoginHistory
from app.models.customer_verification_data import CustomerVerificationData
from app.routers.admin.admin_auth_router import get_current_admin
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


@router.get("/customers", response_model=CustomerListResponse)
def list_customers(
    page: int = Query(0, ge=0, description="Page number (starts from 0)"),
    size: int = Query(20, ge=1, le=100, description="Number of records per page"),
    search: Optional[str] = Query(None, description="Search by email or user ID"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    has_bvnk_customer: Optional[bool] = Query(None, description="Filter by BVNK customer status"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all customers with pagination and filtering.
    Accessible by authenticated admin users.
    """
    # Build query
    query = db.query(User)

    # Apply search filter
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.user_id.ilike(f"%{search}%")
            )
        )

    # Apply verification status filter
    if verification_status:
        query = query.filter(User.verification_status == verification_status)

    # Apply verified filter
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    # Apply BVNK customer filter
    if has_bvnk_customer is not None:
        if has_bvnk_customer:
            query = query.filter(User.bvnk_customer_id.isnot(None))
        else:
            query = query.filter(User.bvnk_customer_id.is_(None))

    # Get total count
    total = query.count()

    # Calculate total pages
    total_pages = (total + size - 1) // size if total > 0 else 0

    # Apply pagination
    customers = query.order_by(User.created_at.desc()).offset(page * size).limit(size).all()

    return CustomerListResponse(
        customers=customers,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
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

    return customer


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

    # Convert date_of_birth to string if it exists
    response_data = CustomerVerificationDataResponse.from_orm(verification_data)
    if verification_data.date_of_birth:
        response_data.date_of_birth = verification_data.date_of_birth.isoformat()

    return response_data


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
                "verified_at": customer.verification_completed_at.isoformat() if customer.verification_completed_at else datetime.utcnow().isoformat(),
                "verification_level": customer.verification_level_name or "basic"
            }
        )
        customer.bvnk_customer_id = customer_data.get('id')
        customer.bvnk_customer_created_at = datetime.utcnow()
        customer.verification_error_message = None
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
