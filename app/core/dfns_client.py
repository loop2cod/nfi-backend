import requests
import json
import time
import hmac
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.wallet_config import get_wallets_to_create, get_contract_address, CURRENCIES


class DfnsSigner:
    def __init__(self, private_key_pem: str, cred_id: str):
        self.cred_id = cred_id
        self.private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )

    def sign_challenge(self, challenge: str) -> Dict[str, Any]:
        """Sign a Dfns challenge"""
        # Create the signature
        signature = self.private_key.sign(
            challenge.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return {
            "credId": self.cred_id,
            "signature": signature.hex()
        }


class DfnsApiClient:
    def __init__(self, base_url: str, org_id: str, auth_token: str, signer: DfnsSigner):
        self.base_url = base_url
        self.org_id = org_id
        self.auth_token = auth_token
        self.signer = signer
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        })

    def _create_signature_header(self, method: str, path: str, body: str = "") -> str:
        """Create HMAC signature for Dfns API requests"""
        timestamp = str(int(time.time() * 1000))  # milliseconds
        message = f"{method}{path}{timestamp}{body}"
        signature = hmac.new(
            settings.DFNS_PRIVATE_KEY.encode() if settings.DFNS_PRIVATE_KEY else b"",
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"DFNS {signature}:{timestamp}"

    def create_wallet(self, network: str) -> Dict[str, Any]:
        """Create a new wallet for the given network"""
        path = f"/orgs/{self.org_id}/wallets"
        body = json.dumps({"network": network})

        # First, get the challenge
        challenge_response = self.session.post(
            f"{self.base_url}{path}/init",
            data=body,
            headers={"X-DFNS-Signature": self._create_signature_header("POST", f"{path}/init", body)}
        )
        challenge_response.raise_for_status()
        challenge_data = challenge_response.json()

        challenge = challenge_data.get("challenge")
        if not challenge:
            raise ValueError("No challenge received")

        # Sign the challenge
        signed_challenge = self.signer.sign_challenge(challenge)

        # Complete the wallet creation
        complete_body = json.dumps({
            "network": network,
            "signedChallenge": signed_challenge
        })

        response = self.session.post(
            f"{self.base_url}{path}/complete",
            data=complete_body,
            headers={"X-DFNS-Signature": self._create_signature_header("POST", f"{path}/complete", complete_body)}
        )
        response.raise_for_status()
        return response.json()


# Global client instance
dfns_client: Optional[DfnsApiClient] = None


def init_dfns_client():
    global dfns_client
    try:
        if all([settings.DFNS_BASE_URL, settings.DFNS_ORG_ID, settings.DFNS_AUTH_TOKEN, settings.DFNS_PRIVATE_KEY, settings.DFNS_CRED_ID]):
            signer = DfnsSigner(settings.DFNS_PRIVATE_KEY, settings.DFNS_CRED_ID)
            dfns_client = DfnsApiClient(
                settings.DFNS_BASE_URL,
                settings.DFNS_ORG_ID,
                settings.DFNS_AUTH_TOKEN,
                signer
            )
            print("Dfns client initialized successfully")
        else:
            print("Dfns configuration incomplete, wallet creation disabled")
    except Exception as e:
        print(f"Failed to initialize Dfns client: {e}")
        print("Continuing without Dfns wallet functionality")
        dfns_client = None


def create_user_wallet(user_id: int, currency: str, network: str) -> Optional[Dict[str, Any]]:
    """
    Create a wallet for a user on a specific network

    Args:
        user_id: User ID
        currency: Currency symbol (e.g., "USDT", "BTC")
        network: Network name (e.g., "Ethereum", "ArbitrumOne")

    Returns:
        Wallet data dictionary or None if creation fails
    """
    if dfns_client:
        try:
            wallet_data = dfns_client.create_wallet(network)
            return {
                "user_id": user_id,
                "currency": currency,
                "address": wallet_data.get("address"),
                "network": network,
                "wallet_id": wallet_data.get("id"),
                "balance": 0.0,
                "available_balance": 0.0,
                "frozen_balance": 0.0
            }
        except Exception as e:
            print(f"Failed to create {currency} wallet on {network} for user {user_id}: {e}")
            return None
    else:
        # Mock wallet creation for development
        import uuid
        # Generate network-appropriate mock address
        if "Bitcoin" in network:
            mock_address = f"bc1q{uuid.uuid4().hex[:40]}"
        elif "Solana" in network:
            mock_address = f"{uuid.uuid4().hex[:32]}"
        else:  # EVM chains
            mock_address = f"0x{uuid.uuid4().hex[:40]}"

        return {
            "user_id": user_id,
            "currency": currency,
            "address": mock_address,
            "network": network,
            "wallet_id": f"mock-{uuid.uuid4().hex}",
            "balance": 0.0,
            "available_balance": 0.0,
            "frozen_balance": 0.0
        }


def create_user_wallets_batch(user_id: int) -> List[Dict[str, Any]]:
    """
    Create all default wallets for a user based on configuration

    Args:
        user_id: User ID

    Returns:
        List of created wallet data dictionaries
    """
    wallets_to_create = get_wallets_to_create()
    created_wallets = []
    errors = []

    for wallet_spec in wallets_to_create:
        currency = wallet_spec["currency"]
        network = wallet_spec["network"]

        print(f"Creating {currency} wallet on {network} for user {user_id}")
        wallet_data = create_user_wallet(user_id, currency, network)

        if wallet_data:
            created_wallets.append(wallet_data)
        else:
            errors.append(f"Failed to create {currency} wallet on {network}")

    if errors:
        print(f"Wallet creation errors: {', '.join(errors)}")

    return created_wallets