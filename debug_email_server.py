#!/usr/bin/env python3
"""
Server-side email debugging script for Digital Ocean droplet.
Run this script on your server to diagnose email issues.
"""

import os
import sys
import socket
import subprocess
from app.core.config import settings
from app.utils.email import test_smtp_connection

def check_environment():
    """Check environment variables and configuration."""
    print("=== Environment Check ===\n")

    # Check if .env file exists
    env_file = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_file):
        print(f"✅ .env file found at: {env_file}")
        with open(env_file, 'r') as f:
            content = f.read()
            if 'SMTP_USERNAME=' in content:
                print("✅ SMTP_USERNAME found in .env")
            else:
                print("❌ SMTP_USERNAME not found in .env")

            if 'SMTP_PASSWORD=' in content:
                print("✅ SMTP_PASSWORD found in .env")
            else:
                print("❌ SMTP_PASSWORD not found in .env")

            if 'SMTP_FROM_EMAIL=' in content:
                print("✅ SMTP_FROM_EMAIL found in .env")
            else:
                print("❌ SMTP_FROM_EMAIL not found in .env")
    else:
        print(f"❌ .env file not found at: {env_file}")
        print("   Make sure to create .env file with SMTP credentials")

    print(f"\nCurrent working directory: {os.getcwd()}")
    print(f"Python path: {sys.executable}")

def check_network_connectivity():
    """Check network connectivity to SMTP server."""
    print("\n=== Network Connectivity Check ===\n")

    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT

    print(f"Testing connection to {smtp_host}:{smtp_port}")

    try:
        # Test basic connectivity
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((smtp_host, smtp_port))
        sock.close()

        if result == 0:
            print(f"✅ Port {smtp_port} is open on {smtp_host}")
        else:
            print(f"❌ Cannot connect to {smtp_host}:{smtp_port}")
            print("   Possible causes:")
            print("   - Firewall blocking outbound connections")
            print("   - DNS resolution issues")
            print("   - SMTP server down")

    except Exception as e:
        print(f"❌ Network test failed: {str(e)}")

def check_smtp_configuration():
    """Check SMTP configuration and test connection."""
    print("\n=== SMTP Configuration Check ===\n")

    smtp_status = test_smtp_connection()

    print("SMTP Status:")
    print(f"  Configured: {'✅' if smtp_status['smtp_configured'] else '❌'}")
    print(f"  Connection: {'✅' if smtp_status['connection_test'] else '❌'}")
    print(f"  Authentication: {'✅' if smtp_status['auth_test'] else '❌'}")

    if smtp_status['error']:
        print(f"  Error: {smtp_status['error']}")

    print("\nSMTP Configuration:")
    config = smtp_status['config']
    for key, value in config.items():
        print(f"  {key}: {value}")

def check_server_setup():
    """Check server setup and permissions."""
    print("\n=== Server Setup Check ===\n")

    # Check if running as correct user
    current_user = os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
    print(f"Current user: {current_user}")

    # Check Python version
    print(f"Python version: {sys.version}")

    # Check if required packages are installed
    try:
        import smtplib
        print("✅ smtplib available")
    except ImportError:
        print("❌ smtplib not available")

    try:
        import ssl
        print("✅ ssl available")
    except ImportError:
        print("❌ ssl not available")

def run_system_diagnostics():
    """Run system-level diagnostics."""
    print("\n=== System Diagnostics ===\n")

    # Check DNS resolution
    try:
        import socket
        ip = socket.gethostbyname(settings.SMTP_HOST)
        print(f"DNS resolution: {settings.SMTP_HOST} -> {ip}")
    except Exception as e:
        print(f"DNS resolution failed: {str(e)}")

    # Check outbound connections (if curl is available)
    try:
        result = subprocess.run(
            ['curl', '-I', f'https://{settings.SMTP_HOST}', '--connect-timeout', '10'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            print("✅ HTTPS connection to SMTP host successful")
        else:
            print("❌ HTTPS connection to SMTP host failed")
            print(f"   curl output: {result.stderr.strip()}")
    except FileNotFoundError:
        print("⚠️  curl not available for HTTPS testing")
    except Exception as e:
        print(f"⚠️  HTTPS test failed: {str(e)}")

def main():
    """Main diagnostic function."""
    print("NFI Platform - Server Email Diagnostics")
    print("=" * 50)

    check_environment()
    check_server_setup()
    check_network_connectivity()
    check_smtp_configuration()
    run_system_diagnostics()

    print("\n" + "=" * 50)
    print("Diagnostics complete. Check the results above for issues.")

    # Provide recommendations
    print("\n=== Recommendations ===")
    print("1. Ensure .env file exists with correct SMTP credentials")
    print("2. Check firewall settings allow outbound SMTP connections")
    print("3. Verify SMTP credentials are correct for production")
    print("4. Test with: curl -X GET http://your-server/auth/smtp-status")
    print("5. Check server logs for detailed error messages")

if __name__ == "__main__":
    main()