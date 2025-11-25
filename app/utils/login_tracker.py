"""
Utility functions for tracking login activity
Extracts device, browser, OS, and location information from requests
"""

from fastapi import Request
from user_agents import parse
from typing import Dict, Optional
import httpx


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request
    Handles X-Forwarded-For header for proxied requests
    """
    # Check for X-Forwarded-For header (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to client host
    if request.client:
        return request.client.host

    return "Unknown"


def parse_user_agent(user_agent_string: str) -> Dict[str, str]:
    """
    Parse user agent string to extract device, browser, and OS information
    """
    user_agent = parse(user_agent_string)

    # Determine device type
    if user_agent.is_mobile:
        device_type = "mobile"
    elif user_agent.is_tablet:
        device_type = "tablet"
    elif user_agent.is_pc:
        device_type = "desktop"
    else:
        device_type = "unknown"

    return {
        "device_type": device_type,
        "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
        "os": f"{user_agent.os.family} {user_agent.os.version_string}",
        "is_mobile": user_agent.is_mobile,
        "is_tablet": user_agent.is_tablet,
        "is_pc": user_agent.is_pc,
    }


async def get_location_from_ip(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Get location information from IP address using ip-api.com (free tier)
    Returns country, city, and combined location string

    Note: For production, consider using a paid service like ipstack.com or MaxMind
    """
    if ip_address == "Unknown" or ip_address.startswith("127.") or ip_address.startswith("192.168."):
        return {
            "country": "Local",
            "city": "Local",
            "location": "Local Network"
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    country = data.get("country", "Unknown")
                    city = data.get("city", "Unknown")
                    location = f"{city}, {country}"

                    return {
                        "country": country,
                        "city": city,
                        "location": location
                    }
    except Exception as e:
        print(f"Error fetching location for IP {ip_address}: {str(e)}")

    return {
        "country": None,
        "city": None,
        "location": None
    }


async def extract_login_info(request: Request) -> Dict[str, any]:
    """
    Extract all login information from request
    Returns a dictionary with IP, user agent details, and location
    """
    ip_address = get_client_ip(request)
    user_agent_string = request.headers.get("User-Agent", "Unknown")

    # Parse user agent
    ua_info = parse_user_agent(user_agent_string)

    # Get location (async)
    location_info = await get_location_from_ip(ip_address)

    return {
        "ip_address": ip_address,
        "user_agent": user_agent_string,
        "device_type": ua_info["device_type"],
        "browser": ua_info["browser"],
        "os": ua_info["os"],
        "country": location_info["country"],
        "city": location_info["city"],
        "location": location_info["location"],
    }
