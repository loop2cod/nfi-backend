#!/usr/bin/env python3
"""
Test script to verify email configuration and sending functionality.
Run this script to test if emails can be sent successfully.
"""

import os
import sys
from app.core.config import settings
from app.utils.email import send_otp_email

def test_email_config():
    """Test if email configuration is properly set up."""
    print("=== Email Configuration Test ===\n")

    # Check SMTP settings
    smtp_config = {
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
        "SMTP_USERNAME": settings.SMTP_USERNAME,
        "SMTP_PASSWORD": "***" if settings.SMTP_PASSWORD else None,
        "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
        "SMTP_FROM_NAME": settings.SMTP_FROM_NAME,
    }

    print("SMTP Configuration:")
    for key, value in smtp_config.items():
        status = "✓ Set" if value else "✗ Not set"
        print(f"  {key}: {status}")
        if key == "SMTP_PASSWORD" and value:
            print("    (Password is configured)")
        elif value:
            print(f"    Value: {value}")

    # Check if all required settings are configured
    required_settings = ["SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"]
    missing = [s for s in required_settings if not getattr(settings, s)]

    if missing:
        print(f"\n❌ Missing required SMTP settings: {', '.join(missing)}")
        print("\nTo fix this:")
        print("1. Create a .env file in the project root")
        print("2. Add the following variables:")
        print("   SMTP_USERNAME=your-email@domain.com")
        print("   SMTP_PASSWORD=your-app-password")
        print("   SMTP_FROM_EMAIL=your-email@domain.com")
        print("\nFor Zoho Mail:")
        print("   SMTP_HOST=smtp.zoho.in")
        print("   SMTP_PORT=465")
        return False
    else:
        print("\n✅ All required SMTP settings are configured")
        return True

def test_email_sending():
    """Test sending an actual email."""
    print("\n=== Email Sending Test ===\n")

    # Get test email from environment or use a default
    test_email = os.getenv("TEST_EMAIL", "test@example.com")

    print(f"Attempting to send test email to: {test_email}")
    print("Note: If this is not your email, set TEST_EMAIL environment variable")

    try:
        # Send a test OTP email
        send_otp_email(test_email, "123456", expires_in_minutes=5)
        print("✅ Email sent successfully!")
        print("Check your inbox (and spam folder) for the test email.")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

def main():
    """Main test function."""
    print("NFI Platform Email Testing Tool\n")

    # Test configuration
    config_ok = test_email_config()

    if not config_ok:
        print("\n❌ Email configuration is incomplete. Please fix the settings above.")
        sys.exit(1)

    # Test sending (only if user wants to)
    if len(sys.argv) > 1 and sys.argv[1] == "--send":
        success = test_email_sending()
        if success:
            print("\n✅ Email test completed successfully!")
        else:
            print("\n❌ Email test failed!")
            sys.exit(1)
    else:
        print("\nTo test actual email sending, run:")
        print("  python test_email.py --send")
        print("\nMake sure to set TEST_EMAIL environment variable to your email address:")
        print("  TEST_EMAIL=your-email@example.com python test_email.py --send")

if __name__ == "__main__":
    main()