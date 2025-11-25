#!/usr/bin/env python3
"""
Test script for Sumsub webhook endpoint.
This script sends test webhook payloads to the local server.
"""

import requests
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBHOOK_URL = "http://localhost:8000/webhook/sumsub"  # Change to your deployed URL
WEBHOOK_SECRET = os.getenv("SUMSUB_WEBHOOK_SECRET", "test-secret")  # Use actual secret

def create_signature(payload: str, secret: str) -> str:
    """Create HMAC SHA256 signature for webhook."""
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def send_webhook_test(event_type: str, payload: dict):
    """Send a test webhook payload."""
    # Convert payload to JSON string
    payload_json = json.dumps(payload, separators=(',', ':'))

    # Create signature
    signature = create_signature(payload_json, WEBHOOK_SECRET)

    # Headers
    headers = {
        "Content-Type": "application/json",
        "X-Sumsub-Signature": signature
    }

    print(f"Sending {event_type} webhook...")
    print(f"Payload: {payload_json}")
    print(f"Signature: {signature}")

    try:
        response = requests.post(WEBHOOK_URL, data=payload_json, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 50)

# Test payloads based on the provided examples
test_payloads = [
    {
        "type": "applicantCreated",
        "applicantId": "5c9e177b0a975a6eeccf5960",
        "inspectionId": "5c9e177b0a975a6eeccf5961",
        "correlationId": "req-63f92830-4d68-4eee-98d5-875d53a12258",
        "levelName": "id-and-liveness",
        "externalUserId": "12672",
        "sandboxMode": True,
        "reviewStatus": "init",
        "createdAtMs": "2020-02-21 13:23:19.002",
        "clientId": "coolClientId"
    },
    {
        "type": "applicantReviewed",
        "applicantId": "5cb56e8e0a975a35f333cb83",
        "inspectionId": "5cb56e8e0a975a35f333cb84",
        "correlationId": "req-a260b669-4f14-4bb5-a4c5-ac0218acb9a4",
        "externalUserId": "externalUserId",
        "levelName": "id-and-liveness",
        "reviewResult": {
            "reviewAnswer": "GREEN"
        },
        "reviewStatus": "completed",
        "createdAtMs": "2020-02-21 13:23:19.321"
    },
    {
        "type": "applicantActionPending",
        "applicantId": "5dc158b109494c3cbf431e28",
        "applicantActionId": "5dc2d80ce3cc9b1c1e389c4c",
        "externalApplicantActionId": "id122424234-random-r7otyykndi",
        "inspectionId": "5dc158b109494c3cbf431e29",
        "applicantType": "individual",
        "correlationId": "req-8fbf5a81-339f-43b6-a9a7-290080e9039c",
        "levelName": "basic-action-level",
        "externalUserId": "pid122424235",
        "reviewStatus": "completed",
        "createdAtMs": "2020-02-21 13:23:16.001"
    }
]

if __name__ == "__main__":
    print("Testing Sumsub Webhook Endpoint")
    print("=" * 50)

    for payload in test_payloads:
        send_webhook_test(payload["type"], payload)

    print("Test completed!")