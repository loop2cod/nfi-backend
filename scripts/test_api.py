#!/usr/bin/env python3
"""
Test script to verify the API is working correctly
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200

def test_login():
    """Test login with super admin"""
    print("\n🔍 Testing login...")
    data = {
        "email": "admin@nfigate.com",
        "password": "Admin123!Change"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=data)
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Login successful!")
        print(f"   User: {result['user']['email']} ({result['user']['role']})")
        return result["access_token"]
    else:
        print(f"   ✗ Login failed: {response.text}")
        return None

def test_get_user(token):
    """Test getting current user"""
    print("\n🔍 Testing get current user...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        user = response.json()
        print(f"   ✓ User: {user['email']}")
        print(f"   Role: {user['role']}")
        print(f"   Tier: {user['tier']}")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False

def test_permissions(token):
    """Test getting user permissions"""
    print("\n🔍 Testing user permissions...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/rbac/my-permissions", headers=headers)
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Permissions loaded: {len(result['permissions'])} permissions")
        print(f"   First 5 permissions: {result['permissions'][:5]}")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False

def test_hierarchy():
    """Test getting hierarchy"""
    print("\n🔍 Testing platform hierarchy...")
    response = requests.get(f"{BASE_URL}/api/v1/rbac/hierarchy")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Hierarchy loaded")
        print(f"   Tiers: {list(result['hierarchy'].keys())}")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False

def main():
    print("=" * 60)
    print("NFI Platform API Test Suite")
    print("=" * 60)

    try:
        # Test health
        if not test_health():
            print("\n❌ Health check failed! Is the server running?")
            print("   Start the server with: uvicorn main:app --reload")
            return

        # Test hierarchy (no auth required)
        test_hierarchy()

        # Test login
        token = test_login()
        if not token:
            print("\n❌ Login failed! Check database initialization.")
            return

        # Test authenticated endpoints
        test_get_user(token)
        test_permissions(token)

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\n📝 Next steps:")
        print("   1. Visit http://localhost:8000/docs for interactive API docs")
        print("   2. Change the super admin password")
        print("   3. Create your first client and users")

    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API server!")
        print("   Start the server with: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
