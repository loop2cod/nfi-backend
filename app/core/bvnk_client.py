"""
BVNK API Client
Handles authentication and API calls to BVNK payment service
Uses Hawk Authentication (HMAC-SHA256)
"""

import hashlib
import hmac
import time
import random
import string
from urllib.parse import urlparse
from typing import Optional, Dict, Any
import requests
from app.core.config import settings


def generate_nonce(length: int = 6) -> str:
    """Generate a random alphanumeric nonce"""
    possible = string.ascii_letters + string.digits
    return ''.join(random.choices(possible, k=length))


def generate_normalized_string(
    header_type: str,
    timestamp: int,
    nonce: str,
    method: str,
    resource: str,
    host: str,
    port: str,
    hash_value: str = ""
) -> str:
    """
    Generate normalized string for HMAC calculation

    Args:
        header_type: Type of header (usually "header")
        timestamp: Unix timestamp in seconds
        nonce: Random nonce
        method: HTTP method (GET, POST, etc.)
        resource: URL path with query string
        host: Hostname
        port: Port number
        hash_value: Payload hash (empty for GET requests)

    Returns:
        Normalized string for HMAC calculation
    """
    header_version = "1"

    return (
        f"hawk.{header_version}.{header_type}\n"
        f"{timestamp}\n"
        f"{nonce}\n"
        f"{method.upper()}\n"
        f"{resource}\n"
        f"{host.lower()}\n"
        f"{port}\n"
        f"{hash_value}\n"
        f"\n"
    )


def generate_hawk_header(url: str, method: str, hawk_id: str, secret_key: str) -> str:
    """
    Generate Hawk authentication header

    Args:
        url: Full URL of the request
        method: HTTP method (GET, POST, PUT, DELETE)
        hawk_id: Hawk Auth ID
        secret_key: Hawk Secret Key

    Returns:
        Hawk authorization header value
    """
    # Generate timestamp and nonce
    timestamp = int(time.time())
    nonce = generate_nonce(6)

    # Parse URL
    parsed_url = urlparse(url)
    host = parsed_url.hostname
    port = str(parsed_url.port) if parsed_url.port else ("80" if parsed_url.scheme == "http" else "443")
    resource = parsed_url.path + (f"?{parsed_url.query}" if parsed_url.query else "")

    # Generate normalized string
    normalized_string = generate_normalized_string(
        "header",
        timestamp,
        nonce,
        method,
        resource,
        host,
        port,
        ""
    )

    # Generate MAC using HMAC-SHA256
    mac = hmac.new(
        secret_key.encode('utf-8'),
        normalized_string.encode('utf-8'),
        hashlib.sha256
    ).digest()

    # Base64 encode the MAC
    import base64
    mac_base64 = base64.b64encode(mac).decode('utf-8')

    # Construct Hawk header
    return f'Hawk id="{hawk_id}", ts="{timestamp}", nonce="{nonce}", mac="{mac_base64}"'


class BVNKClient:
    """BVNK API Client with Hawk Authentication"""

    def __init__(self):
        self.base_url = settings.BVNK_BASE_URL
        self.hawk_auth_id = settings.BVNK_HAWK_AUTH_ID
        self.secret_key = settings.BVNK_SECRET_KEY

        if not self.hawk_auth_id or not self.secret_key:
            raise ValueError("BVNK credentials not configured. Please set BVNK_HAWK_AUTH_ID and BVNK_SECRET_KEY in .env")

    def _get_headers(self, url: str, method: str, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        """
        Generate headers for BVNK API request

        Args:
            url: Full URL of the request
            method: HTTP method
            idempotency_key: Optional idempotency key for POST/PUT requests

        Returns:
            Dictionary of headers
        """
        headers = {
            "Authorization": generate_hawk_header(url, method, self.hawk_auth_id, self.secret_key),
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Add idempotency key if provided
        if idempotency_key:
            # Use X-Idempotency-Key for v1 endpoints, Idempotency-Key for v2
            if "/v2/" in url:
                headers["Idempotency-Key"] = idempotency_key
            else:
                headers["X-Idempotency-Key"] = idempotency_key

        return headers

    def create_customer(
        self,
        external_reference: str,
        email: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a customer in BVNK

        Args:
            external_reference: External user reference (e.g., user_id from your system)
            email: Customer email
            metadata: Optional metadata (max 5 key-value pairs)

        Returns:
            Customer data from BVNK

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/api/customer"

        payload = {
            "externalReference": external_reference,
            "email": email
        }

        # Add metadata if provided
        if metadata:
            payload["metadata"] = metadata

        # Generate idempotency key for customer creation
        import uuid
        idempotency_key = str(uuid.uuid4())

        headers = self._get_headers(url, "POST", idempotency_key)

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Get customer details from BVNK

        Args:
            customer_id: BVNK customer UUID

        Returns:
            Customer data
        """
        url = f"{self.base_url}/api/customer/{customer_id}"
        headers = self._get_headers(url, "GET")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def list_customers(self, page: int = 0, size: int = 20) -> Dict[str, Any]:
        """
        List customers with pagination

        Args:
            page: Page number (starts from 0)
            size: Number of records per page (max 100)

        Returns:
            Paginated customer list
        """
        url = f"{self.base_url}/api/customer?page={page}&size={size}"
        headers = self._get_headers(url, "GET")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def create_wallet(
        self,
        customer_id: str,
        currency: str,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a wallet for a customer

        Args:
            customer_id: BVNK customer UUID
            currency: Currency code (e.g., "USD", "EUR", "BTC")
            description: Optional wallet description
            idempotency_key: Optional idempotency key

        Returns:
            Wallet data
        """
        url = f"{self.base_url}/ledger/v1/wallets"

        payload = {
            "customerId": customer_id,
            "currency": currency
        }

        if description:
            payload["description"] = description

        # Generate idempotency key if not provided
        if not idempotency_key:
            import uuid
            idempotency_key = str(uuid.uuid4())

        headers = self._get_headers(url, "POST", idempotency_key)

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_merchant_info(self) -> Dict[str, Any]:
        """
        Get merchant information

        Returns:
            Merchant data
        """
        url = f"{self.base_url}/api/v1/merchant"
        headers = self._get_headers(url, "GET")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def create_agreement_session(
        self,
        country_code: str,
        customer_type: str,
        use_case: str
    ) -> Dict[str, Any]:
        """
        Create an agreement signing session for an Embedded Partner Customer

        Args:
            country_code: ISO country code (e.g., "US", "GB")
            customer_type: "INDIVIDUAL" or "COMPANY"
            use_case: Agreement use case - one of:
                     "STABLECOIN_PAYOUTS"
                     "EMBEDDED_STABLECOIN_WALLETS"
                     "EMBEDDED_FIAT_ACCOUNTS"

        Returns:
            Agreement session data with 'reference' field needed for customer creation

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/platform/v1/customers/agreement/sessions"

        payload = {
            "countryCode": country_code,
            "customerType": customer_type,
            "useCase": use_case
        }

        headers = self._get_headers(url, "POST")

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_agreement_session(self, reference: str) -> Dict[str, Any]:
        """
        Get the status of an agreement session

        Args:
            reference: Agreement session reference

        Returns:
            Agreement session data including status

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/platform/v1/customers/agreement/sessions/{reference}"
        headers = self._get_headers(url, "GET")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def update_agreement_session(
        self,
        reference: str,
        status: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Update agreement session status (for Direct API approach)

        Args:
            reference: Agreement session reference
            status: New status - typically "SIGNED"
            ip_address: IP address of the user signing the agreement

        Returns:
            Updated agreement session data

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/platform/v1/customers/agreement/sessions/{reference}"

        payload = {
            "status": status,
            "ipAddress": ip_address
        }

        headers = self._get_headers(url, "PUT")

        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_agreements(self) -> Dict[str, Any]:
        """
        Fetch all required agreement documents needed to onboard an Embedded Partner Merchant

        Returns:
            List of agreement documents

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/api/v1/agreement"
        headers = self._get_headers(url, "GET")

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    def create_customer_individual(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: str,
        birth_country_code: str,
        document_number: str,
        address_line1: str,
        city: str,
        post_code: str,
        country_code: str,
        signed_agreement_session_reference: Optional[str] = None,
        email: Optional[str] = None,
        risk_score: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an INDIVIDUAL customer in BVNK

        Args:
            first_name: Customer's first name
            last_name: Customer's last name
            date_of_birth: Date of birth in YYYY-MM-DD format
            birth_country_code: ISO 3166-1 alpha-2 country code of birth
            document_number: ID document number
            address_line1: Street address
            city: City name
            post_code: Postal/ZIP code
            country_code: ISO 3166-1 alpha-2 country code
            signed_agreement_session_reference: Agreement session reference (optional)
            email: Customer email (optional)
            risk_score: Risk score - "LOW", "MEDIUM", "HIGH" (optional)

        Returns:
            Customer creation response with customer ID and status

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/platform/v1/customers"

        payload = {
            "type": "INDIVIDUAL",
            "individual": {
                "firstName": first_name,
                "lastName": last_name,
                "dateOfBirth": date_of_birth,
                "birthCountryCode": birth_country_code,
                "documentNumber": document_number,
                "address": {
                    "addressLine1": address_line1,
                    "city": city,
                    "postCode": post_code,
                    "countryCode": country_code
                }
            }
        }

        # Add optional fields
        if signed_agreement_session_reference:
            payload["signedAgreementSessionReference"] = signed_agreement_session_reference

        if email:
            payload["individual"]["email"] = email

        if risk_score:
            payload["riskScore"] = risk_score

        # Generate idempotency key
        import uuid
        idempotency_key = str(uuid.uuid4())

        headers = self._get_headers(url, "POST", idempotency_key)

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()


# Initialize client (can be used throughout the app)
def get_bvnk_client() -> BVNKClient:
    """Get BVNK client instance"""
    return BVNKClient()
