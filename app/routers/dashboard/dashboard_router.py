from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.routers.auth.auth_router import get_current_user
from app.models.user import User
from app.models.wallet import Wallet
from app.core.database import get_db

router = APIRouter()


@router.get("/stat", response_model=dict)
def get_dashboard(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Welcome to your dashboard, {current_user.email}!",
        "user_id": current_user.id,
        "features": [
            "Virtual accounts",
            "Accept payments",
            "Send payments",
            "Instant transfers"
        ]
    }


@router.get("/available-tokens", response_model=list)
def get_available_tokens(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get available tokens for the current user based on their wallet networks
    """
    # Get user's wallets
    user_wallets = db.query(Wallet).filter(Wallet.user_id == current_user.id).all()

    # Extract unique networks from user's wallets
    user_networks = list(set(wallet.network for wallet in user_wallets))

    # Define token mapping based on networks
    token_map = {
        "Bitcoin": ["BTC"],
        "Ethereum": ["ETH", "USDT", "USDC"],
        "Solana": ["SOL"],
        "ArbitrumOne": ["USDT"],
        "Base": ["USDT"],
        "Tron": ["USDT"],
        "Optimism": ["USDT"],
    }

    # Collect available tokens
    available_tokens = set()
    for network in user_networks:
        if network in token_map:
            available_tokens.update(token_map[network])

    # Return sorted list of available tokens
    return sorted(list(available_tokens))


