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
            "wallet_id": wallet.wallet_id
        }
        for wallet in wallets
    ]