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

    def sign_challenge(self, challenge: str, credential_id: str) -> Dict[str, Any]:
        """Sign a Dfns challenge using RSA-PSS following DFNS documentation"""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from typing import cast
        import base64

        # Ensure we have an RSA private key
        rsa_key = cast(rsa.RSAPrivateKey, self.private_key)

        # Create client data as per DFNS documentation
        # Use the challenge string directly as received from /auth/action/init
        client_data = {
            "type": "key.get",
            "challenge": challenge,  # Use the full challenge string
            "origin": "https://api.dfns.io",
            "crossOrigin": False
        }

        # Convert to JSON and encode as base64url
        client_data_json = json.dumps(client_data, separators=(',', ':'))
        client_data_b64 = base64.urlsafe_b64encode(client_data_json.encode()).decode().rstrip('=')

        # Sign the client data JSON using PKCS#1 v1.5 padding (more common for WebAuthn)
        signature = rsa_key.sign(
            client_data_json.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

        return {
            "kind": "Key",
            "credentialAssertion": {
                "credId": credential_id,
                "clientData": client_data_b64,
                "signature": signature_b64
            }
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



    def create_delegated_registration_challenge(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a delegated registration challenge for end user registration"""
        payload = {
            "user": {
                "kind": "EndUser",
                "externalId": user_info.get("external_id"),
                "email": user_info.get("email"),
                "displayName": user_info.get("display_name"),
                "firstName": user_info.get("first_name"),
                "lastName": user_info.get("last_name"),
                "dateOfBirth": user_info.get("date_of_birth"),
                "nationality": user_info.get("nationality")
            }
        }

        response = self.session.post(
            f"{self.base_url}/auth/delegated-registration/init",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()

    def complete_end_user_registration(self, challenge_identifier: str, signed_challenge: Dict[str, Any], user_info: Dict[str, Any], wallets: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Complete end user registration with optional wallet creation"""
        payload = {
            "challengeIdentifier": challenge_identifier,
            "firstFactor": signed_challenge,
            "user": {
                "kind": "EndUser",
                "externalId": user_info.get("external_id"),
                "email": user_info.get("email"),
                "displayName": user_info.get("display_name"),
                "firstName": user_info.get("first_name"),
                "lastName": user_info.get("last_name"),
                "dateOfBirth": user_info.get("date_of_birth"),
                "nationality": user_info.get("nationality")
            }
        }

        if wallets:
            payload["wallets"] = wallets

        response = self.session.post(
            f"{self.base_url}/auth/delegated-registration",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()

    def create_wallet(self, network: str, user_id: int, dfns_user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new wallet for the given network using proper DFNS signing flow"""
        # Step 1: Initialize user action challenge
        # The payload should describe the actual API call we want to make
        wallet_payload = {
            "network": network,
            "name": f"{user_id}_{network}",
            "externalId": f"{user_id}"
        }

        # Add delegateTo only if a valid DFNS user ID is provided
        # Note: delegateTo requires the target to be an existing DFNS end user
        if dfns_user_id:
            wallet_payload["delegateTo"] = dfns_user_id

        wallet_payload_json = json.dumps(wallet_payload)

        init_payload = {
            "userActionHttpMethod": "POST",
            "userActionHttpPath": "/wallets",
            "userActionPayload": wallet_payload_json
        }

        init_response = self.session.post(
            f"{self.base_url}/auth/action/init",
            json=init_payload,
            headers={"Content-Type": "application/json"}
        )
        init_response.raise_for_status()
        challenge_data = init_response.json()

        # Step 2: Sign the challenge
        challenge = challenge_data.get("challenge")
        if not challenge:
            raise ValueError("No challenge received from DFNS")

        # Get the credential ID from allowed credentials
        allow_credentials = challenge_data.get("allowCredentials", {})
        key_credentials = allow_credentials.get("key", [])
        if not key_credentials:
            raise ValueError("No key credentials available for signing")

        credential_id = key_credentials[0]["id"]  # Use the first available key credential

        signed_challenge = self.signer.sign_challenge(challenge, credential_id)

        # Step 3: Complete user action to get token
        action_payload = {
            "challengeIdentifier": challenge_data.get("challengeIdentifier"),
            "firstFactor": signed_challenge
        }

        action_response = self.session.post(
            f"{self.base_url}/auth/action",
            json=action_payload,
            headers={"Content-Type": "application/json"}
        )
        action_response.raise_for_status()
        action_data = action_response.json()

        user_action_token = action_data.get("userAction")
        if not user_action_token:
            raise ValueError("No user action token received from DFNS")

        # Step 4: Create the wallet with the user action token
        wallet_response = self.session.post(
            f"{self.base_url}/wallets",
            json=wallet_payload,
            headers={
                "Content-Type": "application/json",
                "X-DFNS-USERACTION": user_action_token
            }
        )
        wallet_response.raise_for_status()
        return wallet_response.json()

    def list_wallets(self, owner_id: Optional[str] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List wallets, optionally filtered by owner or user_id via externalId"""
        params = {}
        if owner_id:
            params["owner"] = owner_id  # Use 'owner' instead of deprecated 'ownerId'

        response = self.session.get(
            f"{self.base_url}/wallets",
            params=params,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        all_wallets = response.json().get("items", [])

        # If user_id is provided, filter wallets by externalId pattern
        if user_id:
            filtered_wallets = []
            for wallet in all_wallets:
                external_id = wallet.get("externalId", "")
                if external_id.startswith(f"user_{user_id}_"):
                    filtered_wallets.append(wallet)
            return filtered_wallets

        return all_wallets

    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific wallet by ID from DFNS"""
        response = self.session.get(
            f"{self.base_url}/wallets/{wallet_id}",
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # Wallet not found
        else:
            response.raise_for_status()
            return None

    def sync_wallet_status(self, user_id: int, db_wallets: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Sync wallet status with DFNS API
        Returns dict with 'active' and 'deleted' wallet IDs
        """
        active_wallets = []
        deleted_wallets = []

        # Get wallets from DFNS for this user
        dfns_wallets = self.list_wallets(user_id=user_id)
        dfns_wallet_ids = {wallet["id"] for wallet in dfns_wallets}

        # Check each database wallet
        for db_wallet in db_wallets:
            wallet_id = db_wallet.get("wallet_id")
            if wallet_id:
                if wallet_id in dfns_wallet_ids:
                    active_wallets.append(wallet_id)
                else:
                    # Double-check by trying to get the wallet directly
                    wallet_details = self.get_wallet_by_id(wallet_id)
                    if wallet_details:
                        active_wallets.append(wallet_id)
                    else:
                        deleted_wallets.append(wallet_id)

        return {
            "active": active_wallets,
            "deleted": deleted_wallets
        }


# Global client instance
dfns_client: Optional[DfnsApiClient] = None


def init_dfns_client():
    global dfns_client
    try:
        base_url = settings.DFNS_BASE_URL
        org_id = settings.DFNS_ORG_ID
        auth_token = settings.DFNS_AUTH_TOKEN
        private_key = settings.DFNS_PRIVATE_KEY
        cred_id = settings.DFNS_CRED_ID

        if base_url and org_id and auth_token and private_key and cred_id:
            signer = DfnsSigner(private_key, cred_id)
            dfns_client = DfnsApiClient(
                base_url,
                org_id,
                auth_token,
                signer
            )
            print("Dfns client initialized successfully")
        else:
            print("Dfns configuration incomplete, wallet creation disabled")
    except Exception as e:
        print(f"Failed to initialize Dfns client: {e}")
        print("Continuing without Dfns wallet functionality")
        dfns_client = None


def create_user_wallet(user_id: int, user_nf_id: int, currency: str, network: str, dfns_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Create a wallet for a user on a specific network

    Args:
        user_id: User ID
        currency: Currency symbol (e.g., "USDT", "BTC")
        network: Network name (e.g., "Ethereum", "ArbitrumOne")

    Returns:
        Wallet data dictionary or None if creation fails
    """
    if not dfns_client:
        print(f"DFNS client not initialized, cannot create {currency} wallet on {network} for user {user_id}")
        return None

    try:
        print(f"Creating {currency} wallet on {network} for user {user_id} via DFNS API")

        # Create wallet using DFNS API
        wallet_response = dfns_client.create_wallet(network, user_nf_id, dfns_user_id)

        # Extract wallet information
        wallet_id = wallet_response.get("id")
        address = wallet_response.get("address")
        network_name = wallet_response.get("network")

        if not wallet_id or not address:
            print(f"Invalid wallet response from DFNS: {wallet_response}")
            return None

        return {
            "user_id": user_id,
            "user_nf_id": user_nf_id,
            "currency": currency,
            "address": address,
            "network": network_name,
            "wallet_id": wallet_id,
            "balance": 0.0,
            "available_balance": 0.0,
            "frozen_balance": 0.0
        }

    except Exception as e:
        print(f"Failed to create {currency} wallet on {network} for user {user_id}: {e}")
        return None



def create_user_wallets_batch(user_id: int, dfns_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Create all default wallets for a user based on configuration

    Args:
        user_id: User ID
        dfns_user_id: DFNS end user ID for delegation (optional)

    Returns:
        List of created wallet data dictionaries
    """
    wallets_to_create = get_wallets_to_create()
    created_wallets = []
    errors = []

    for wallet_spec in wallets_to_create:
        currency = wallet_spec["currency"]
        network = wallet_spec["network"]

        if dfns_user_id:
            print(f"Creating {currency} wallet on {network} for user {user_id} with delegation to {dfns_user_id}")
            wallet_data = create_user_wallet(user_id, user_id, currency, network, dfns_user_id)
        else:
            print(f"Creating {currency} wallet on {network} for user {user_id} (no delegation)")
            wallet_data = create_user_wallet(user_id, user_id, currency, network, None)

        if wallet_data:
            created_wallets.append(wallet_data)
        else:
            errors.append(f"Failed to create {currency} wallet on {network}")

    if errors:
        print(f"Wallet creation errors: {', '.join(errors)}")

    return created_wallets