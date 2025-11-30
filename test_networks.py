#!/usr/bin/env python3
"""
Test script for user networks functionality
"""

import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all models to ensure they are registered
from app.models import user, verification_event, wallet, admin_user, admin_login_history, login_activity, verification_audit_log, customer_verification_data, user_counter

from app.core.database import SessionLocal
from app.models.user import User
from app.models.wallet import Wallet

def test_networks():
    """Test user networks functionality"""
    db = SessionLocal()

    try:
        # Get first user
        user = db.query(User).first()
        if not user:
            print("No users found in database. Creating a test user...")

            # Create a test user
            from app.auth.auth import get_password_hash
            from app.models.user_counter import UserCounter

            # Use a simple test user ID
            user_id = "NF-TEST001"

            test_user = User(
                user_id=user_id,
                email="test@example.com",
                hashed_password=get_password_hash("testpass123"),
                is_active=True,
                is_verified=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            user = test_user
            print(f"Created test user: {user.email} (ID: {user.id})")

        print(f"Testing with user: {user.email} (ID: {user.id})")

        # Check existing wallets
        existing_wallets = db.query(Wallet).filter(Wallet.user_id == user.id).all()
        print(f"Existing wallets: {len(existing_wallets)}")

        # Add some test wallets if none exist (this simulates admin creating wallets)
        if not existing_wallets:
            test_wallets = [
                {"currency": "BTC", "network": "Bitcoin", "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "wallet_id": "wa-test-btc"},
                {"currency": "ETH", "network": "Ethereum", "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e", "wallet_id": "wa-test-eth"},
                {"currency": "SOL", "network": "Solana", "address": "7xKXtg2CW87Qx5T6jzKL8Qm12bpoJVpXsjf8J6KVrpk", "wallet_id": "wa-test-sol"},
                {"currency": "USDT", "network": "ArbitrumOne", "address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "wallet_id": "wa-test-usdt"},
            ]

            for wallet_config in test_wallets:
                wallet = Wallet(
                    user_id=user.id,
                    user_nf_id=user.user_id,
                    currency=wallet_config["currency"],
                    address=wallet_config["address"],
                    network=wallet_config["network"],
                    wallet_id=wallet_config["wallet_id"]
                )
                db.add(wallet)
                print(f"Created wallet: {wallet_config['currency']} on {wallet_config['network']}")

            db.commit()

        # Query wallets again
        wallets = db.query(Wallet).filter(Wallet.user_id == user.id).all()

        print(f"Wallets for user {user.id}:")
        for wallet in wallets:
            print(f"  - {wallet.currency} on {wallet.network}")

        # Test the available tokens endpoint logic
        from app.routers.dashboard.dashboard_router import get_available_tokens
        available_tokens = get_available_tokens(user, db)
        print(f"Available tokens: {available_tokens}")

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"Error during test: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_networks()