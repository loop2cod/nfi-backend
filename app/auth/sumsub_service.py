import hmac
import hashlib
import time
import requests
from app.core.config import settings


class SumsubService:
    def __init__(self):
        # Temporarily hardcode for testing
        self.api_token = "pjRs8KgzcYmnOIr5hHGMKWJa.hHiMgM4qzVsbmJ4odl9Cj8PevEBwaTuP"
        self.api_secret = "mailMdNZRQT2QFeEkh2jlaDbJAFf9jfy"
        self.base_url = "https://api.sandbox.sumsub.com"

        print(f"Sumsub config loaded - token: {self.api_token[:10]}..., url: {self.base_url}")

        if not self.api_token or not self.api_secret:
            raise ValueError("Sumsub API credentials not configured")

    def _generate_signature(self, method: str, path: str, body: str = "") -> tuple[str, str]:
        """Generate HMAC signature for Sumsub API requests"""
        timestamp = str(int(time.time() * 1000))
        # Sumsub signature format: timestamp + method + path + body
        signature_data = f"{timestamp}{method.upper()}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp

    def create_applicant(self, external_user_id: str, email: str = None) -> dict:
        """Create a new applicant in Sumsub"""
        endpoint = "/resources/applicants"
        url = f"{self.base_url}{endpoint}"
        body = {
            "externalUserId": external_user_id,
        }
        if email:
            body["email"] = email

        import json
        body_str = json.dumps(body, separators=(',', ':'))  # Compact JSON

        signature, timestamp = self._generate_signature("POST", endpoint, body_str)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-App-Token": self.api_token,
            "X-App-Access-Sig": signature,
            "X-App-Access-Ts": timestamp,
        }

        response = requests.post(url, headers=headers, data=body_str)
        response.raise_for_status()
        return response.json()

    def get_access_token(self, external_user_id: str, level_name: str = "basic-kyc-level") -> dict:
        """Generate access token for Sumsub SDK"""
        url = f"{self.base_url}/resources/accessTokens"
        body = {
            "userId": external_user_id,
            "levelName": level_name,
            "ttlInSecs": 600,  # 10 minutes
        }

        import json
        body_str = json.dumps(body)

        signature, timestamp = self._generate_signature("POST", "/resources/accessTokens", body_str)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-App-Token": self.api_token,
            "X-App-Access-Sig": signature,
            "X-App-Access-Ts": timestamp,
        }

        response = requests.post(url, headers=headers, data=body_str)
        response.raise_for_status()
        return response.json()

    def get_applicant_status(self, applicant_id: str) -> dict:
        """Get applicant verification status"""
        url = f"{self.base_url}/resources/applicants/{applicant_id}/status"

        signature, timestamp = self._generate_signature("GET", f"/resources/applicants/{applicant_id}/status")

        headers = {
            "Accept": "application/json",
            "X-App-Token": self.api_token,
            "X-App-Access-Sig": signature,
            "X-App-Access-Ts": timestamp,
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


# Global instance
sumsub_service = SumsubService()