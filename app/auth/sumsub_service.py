import os
import hmac
import hashlib
import time
import requests
from typing import Dict, Any, Optional
from app.core.config import settings

SUMSUB_APP_TOKEN = os.getenv('SUMSUB_APP_TOKEN') or settings.SUMSUB_TOKEN
SUMSUB_SECRET_KEY = os.getenv('SUMSUB_SECRET_KEY') or settings.SUMSUB_SECRET_KEY
SUMSUB_BASE_URL = settings.SUMSUB_BASE_URL

if not SUMSUB_APP_TOKEN or not SUMSUB_SECRET_KEY:
    raise ValueError("SUMSUB_APP_TOKEN and SUMSUB_SECRET_KEY must be set")

def create_signature(url: str, method: str, data: Optional[str] = None) -> Dict[str, str]:
    ts = int(time.time())
    signature = hmac.new(
        SUMSUB_SECRET_KEY.encode('utf-8'),
        f"{ts}{method.upper()}{url}".encode('utf-8'),
        hashlib.sha256
    )
    if data is not None:
        signature.update(str(data).encode('utf-8'))  # type: ignore

    headers = {
        'X-App-Access-Ts': str(ts),
        'X-App-Access-Sig': signature.hexdigest(),
        'X-App-Token': SUMSUB_APP_TOKEN,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    return headers

def get_access_token(user_id: str, level_name: str) -> Dict[str, Any]:
    url = f"/resources/accessTokens?userId={user_id}&levelName={level_name}&ttlInSecs=600"
    method = 'POST'

    headers = create_signature(url, method)

    response = requests.post(SUMSUB_BASE_URL + url, headers=headers)

    if not response.ok:
        raise Exception(f"Failed to get access token: {response.text}")

    return response.json()

def reset_user_profile(applicant_id: str) -> Dict[str, Any]:
    url = f"/resources/applicants/{applicant_id}/reset"
    method = 'POST'

    headers = create_signature(url, method)

    response = requests.post(SUMSUB_BASE_URL + url, headers=headers)

    if not response.ok:
        raise Exception(f"Failed to reset user profile: {response.text}")

    return response.json()

def check_user_status(user_id: str) -> Dict[str, Any]:
    url = f"/resources/applicants/-;externalUserId={user_id}/one"
    method = 'GET'

    headers = create_signature(url, method)

    response = requests.get(SUMSUB_BASE_URL + url, headers=headers)

    if not response.ok:
        raise Exception(f"Failed to check user status: {response.text}")

    return response.json()

def generate_websdk_config(user_id: str, level_name: str = 'basic-kyc-level') -> Dict[str, Any]:
    try:
        token_data = get_access_token(user_id, level_name)
        return {
            "success": True,
            "verification_token": token_data.get('token'),
            "applicant_id": user_id,
            "sdk_url": f"{SUMSUB_BASE_URL}/websdk/",
            "config": {
                "token": token_data.get('token'),
                "applicantId": user_id,
                "endpoint": SUMSUB_BASE_URL,
                "locale": "en",
                "theme": "light"
            }
        }
    except Exception as e:
        raise Exception(f"Failed to generate WebSDK config: {str(e)}")

def regenerate_websdk_config(user_id: str, level_name: str = 'basic-kyc-level') -> Dict[str, Any]:
    try:
        user_data = check_user_status(user_id)
        if user_data.get('id'):
            reset_user_profile(user_data['id'])
        return generate_websdk_config(user_id, level_name)
    except Exception as e:
        raise Exception(f"Failed to regenerate WebSDK config: {str(e)}")