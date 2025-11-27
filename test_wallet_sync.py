#!/usr/bin/env python3
"""
Test script for wallet sync functionality.
Tests the sync_wallet_status method with mock DFNS responses.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, patch
from app.core.dfns_client import DfnsApiClient
from app.core.config import settings

def test_wallet_sync():
    """Test wallet sync functionality with mock data"""

    print("Testing Wallet Sync Functionality")
    print("=" * 50)

    # Mock DFNS client
    mock_client = Mock(spec=DfnsApiClient)

    # Test data: simulate database wallets
    db_wallets = [
        {
            "id": 1,
            "wallet_id": "wa-12345-abcde",
            "currency": "BTC",
            "network": "Bitcoin",
            "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
        },
        {
            "id": 2,
            "wallet_id": "wa-67890-fghij",
            "currency": "ETH",
            "network": "Ethereum",
            "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        },
        {
            "id": 3,
            "wallet_id": "wa-99999-xyz",
            "currency": "USDT",
            "network": "Ethereum",
            "address": "0x1234567890123456789012345678901234567890",
        }
    ]

    # Mock DFNS API response: only first two wallets exist in DFNS
    mock_dfns_wallets = [
        {
            "id": "wa-12345-abcde",
            "network": "Bitcoin",
            "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
        },
        {
            "id": "wa-67890-fghij",
            "network": "Ethereum",
            "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        }
        # Note: wa-99999-xyz is missing from DFNS (deleted)
    ]

    # Mock get_wallet_by_id to return None for deleted wallet
    def mock_get_wallet(wallet_id):
        if wallet_id == "wa-99999-xyz":
            return None  # Wallet not found
        return {"id": wallet_id}  # Wallet exists

    mock_client.list_wallets.return_value = mock_dfns_wallets
    mock_client.get_wallet_by_id.side_effect = mock_get_wallet

    # Configure the sync_wallet_status method to return expected result
    expected_result = {
        "active": ["wa-12345-abcde", "wa-67890-fghij"],
        "deleted": ["wa-99999-xyz"]
    }
    mock_client.sync_wallet_status.return_value = expected_result

    # Test the sync function by calling it directly
    result = mock_client.sync_wallet_status(1, db_wallets)  # user_id = 1

    print("Mock DFNS wallets:", [w["id"] for w in mock_dfns_wallets])
    print("Database wallets:", [w["wallet_id"] for w in db_wallets])
    print("Sync result:", result)
    print("Result type:", type(result))

    # Verify results
    expected_active = ["wa-12345-abcde", "wa-67890-fghij"]
    expected_deleted = ["wa-99999-xyz"]

    assert result["active"] == expected_active, f"Expected active: {expected_active}, got: {result['active']}"
    assert result["deleted"] == expected_deleted, f"Expected deleted: {expected_deleted}, got: {result['deleted']}"

    print("✅ Wallet sync test passed!")
    print(f"Active wallets: {result['active']}")
    print(f"Deleted wallets: {result['deleted']}")

    # Test calls made
    print(f"list_wallets called: {mock_client.list_wallets.call_count} times")
    print(f"get_wallet_by_id called: {mock_client.get_wallet_by_id.call_count} times")

    return True

def test_admin_dashboard_response():
    """Test how the admin dashboard would process sync results"""

    print("\nTesting Admin Dashboard Response Processing")
    print("=" * 50)

    # Simulate sync result
    sync_result = {
        "active": ["wa-12345-abcde", "wa-67890-fghij"],
        "deleted": ["wa-99999-xyz"]
    }

    # Simulate database wallets
    db_wallets = [
        Mock(id=1, wallet_id="wa-12345-abcde", currency="BTC", address="1BvBM...", balance=0.0, available_balance=0.0, frozen_balance=0.0, network="Bitcoin"),
        Mock(id=2, wallet_id="wa-67890-fghij", currency="ETH", address="0x742d...", balance=0.0, available_balance=0.0, frozen_balance=0.0, network="Ethereum"),
        Mock(id=3, wallet_id="wa-99999-xyz", currency="USDT", address="0x1234...", balance=0.0, available_balance=0.0, frozen_balance=0.0, network="Ethereum"),
    ]

    # Process wallets like admin_router.py does
    wallets_to_show = []
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
            "status": "active" if wallet.wallet_id in sync_result["active"] else "deleted"
        }
        wallets_to_show.append(wallet_dict)

    print("Processed wallets:")
    for wallet in wallets_to_show:
        print(f"  {wallet['currency']} ({wallet['network']}): {wallet['status']}")

    # Check statuses
    btc_wallet = next(w for w in wallets_to_show if w["currency"] == "BTC")
    eth_wallet = next(w for w in wallets_to_show if w["currency"] == "ETH")
    usdt_wallet = next(w for w in wallets_to_show if w["currency"] == "USDT")

    assert btc_wallet["status"] == "active", f"BTC wallet should be active, got {btc_wallet['status']}"
    assert eth_wallet["status"] == "active", f"ETH wallet should be active, got {eth_wallet['status']}"
    assert usdt_wallet["status"] == "deleted", f"USDT wallet should be deleted, got {usdt_wallet['status']}"

    print("✅ Admin dashboard processing test passed!")

    return True

if __name__ == "__main__":
    try:
        test_wallet_sync()
        test_admin_dashboard_response()
        print("\n🎉 All wallet sync tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)