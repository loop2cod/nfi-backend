"""
IP Geolocation Utility
Get location information from IP address
"""

import requests
from typing import Optional
from fastapi import Request


def get_real_ip_address(request: Request) -> Optional[str]:
    """
    Extract the real IP address from the request, checking forwarded headers first.
    This handles cases where the app is behind a proxy or load balancer.
    """
    # Check X-Forwarded-For header (standard for proxies)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one (client IP)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (used by nginx and others)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return None


def get_location_from_ip(ip_address: str) -> Optional[str]:
    """
    Get location (State) from IP address using ipapi.co
    Returns state/region name like "California" or None if failed
    """
    if not ip_address or ip_address == "127.0.0.1" or ip_address.startswith("192.168."):
        return "Local Network"

    try:
        # Using ipapi.co free API (up to 1000 requests/day)
        response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=2)

        if response.status_code == 200:
            data = response.json()
            region = data.get("region")  # State/Province
            country = data.get("country_name")

            if region:
                return region
            elif country:
                return country

        return "Unknown"
    except Exception as e:
        print(f"Geolocation error for {ip_address}: {str(e)}")
        return "Unknown"


def get_device_type_from_user_agent(user_agent: Optional[str]) -> str:
    """
    Determine device type from user agent string
    Returns: Desktop, Mobile, Tablet, or Unknown
    """
    if not user_agent:
        return "Unknown"

    user_agent_lower = user_agent.lower()

    # Check for mobile devices
    if any(mobile in user_agent_lower for mobile in ["iphone", "android", "mobile", "phone"]):
        return "Mobile"

    # Check for tablets
    if any(tablet in user_agent_lower for tablet in ["ipad", "tablet"]):
        return "Tablet"

    # Default to desktop
    if any(desktop in user_agent_lower for desktop in ["windows", "macintosh", "linux", "x11"]):
        return "Desktop"

    return "Unknown"
