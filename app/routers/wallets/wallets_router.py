from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.wallet import Wallet
from app.routers.auth.auth_router import get_current_user
from app.models.user import User
from typing import List


router = APIRouter()


@router.get("", response_model=List[dict])
def get_user_wallets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all wallets for the current user"""
    wallets = db.query(Wallet).filter(Wallet.user_id == current_user.id).all()
    return [
        {
            "id": wallet.id,
            "currency": wallet.currency,
            "address": wallet.address,
            "balance": wallet.balance,
            "available_balance": wallet.available_balance,
            "frozen_balance": wallet.frozen_balance,
            "network": wallet.network,
            "wallet_id": wallet.wallet_id,
            "status": wallet.status
        }
        for wallet in wallets
    ]


@router.post("/create-default-wallets")
def create_default_wallets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create default wallets for the current user"""
    from app.core.dfns_client import create_user_wallets_batch
    
    # Check if user is verified
    if not current_user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="User must be verified before creating wallets"
        )
    
    # Check if user already has wallets
    existing_wallets = db.query(Wallet).filter(Wallet.user_id == current_user.id).count()
    
    if existing_wallets > 0:
        raise HTTPException(
            status_code=400,
            detail=f"User already has {existing_wallets} wallets"
        )
    
    try:
        # Prepare user info for DFNS registration if needed
        user_info = None
        if not current_user.dfns_user_id and current_user.first_name and current_user.last_name and current_user.email:
            user_info = {
                "external_id": f"user_{current_user.id}",
                "email": current_user.email,
                "display_name": f"{current_user.first_name} {current_user.last_name}",
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "date_of_birth": current_user.date_of_birth,
                "nationality": current_user.nationality
            }

        wallets = create_user_wallets_batch(current_user.id, current_user.dfns_user_id, user_info)
        return {
            "success": True,
            "message": f"Successfully created {len(wallets)} wallets",
            "wallets": [
                {
                    "currency": w.currency,
                    "network": w.network,
                    "address": w.address
                }
                for w in wallets
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create wallets: {str(e)}")