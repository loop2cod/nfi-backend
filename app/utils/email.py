"""
Email Utility for sending emails via Zoho SMTP
Handles email sending with HTML templates
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# SMTP Configuration from settings
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USERNAME
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM_EMAIL = settings.SMTP_FROM_EMAIL
SMTP_FROM_NAME = settings.SMTP_FROM_NAME


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> None:
    """
    Send an email via Zoho SMTP

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email
        text_body: Plain text fallback (optional)

    Raises:
        Exception: If email sending fails
    """
    # Check if SMTP is configured
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM_EMAIL:
        logger.error("SMTP not configured. Please set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL environment variables.")
        logger.error(f"SMTP_HOST: {SMTP_HOST}, SMTP_PORT: {SMTP_PORT}")
        logger.error(f"SMTP_FROM_NAME: {SMTP_FROM_NAME}")
        raise Exception("Email service not configured")

    logger.info(f"SMTP Configuration - Host: {SMTP_HOST}, Port: {SMTP_PORT}, Username: {SMTP_USERNAME[:3]}***, From: {SMTP_FROM_EMAIL}")

    try:
        # Test connection first
        logger.info(f"Testing SMTP connection to {SMTP_HOST}:{SMTP_PORT}")

        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Add plain text part if provided
        if text_body:
            text_part = MIMEText(text_body, "plain")
            msg.attach(text_part)

        # Add HTML part
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        logger.info(f"Sending email to {to_email} with subject: {subject}")

        # Connect to SMTP server and send
        # Use SMTP_SSL for port 465, SMTP with STARTTLS for port 587
        if SMTP_PORT == 465:
            logger.info("Using SMTP_SSL (port 465)")
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                logger.info("SMTP_SSL connection established")
                server.login(str(SMTP_USERNAME), str(SMTP_PASSWORD))
                logger.info("SMTP login successful")
                server.send_message(msg)
                logger.info("Email sent via SMTP_SSL")
        else:
            logger.info("Using SMTP with STARTTLS (port 587)")
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                logger.info("SMTP connection established")
                server.starttls()  # Upgrade to secure connection
                logger.info("STARTTLS upgrade successful")
                server.login(str(SMTP_USERNAME), str(SMTP_PASSWORD))
                logger.info("SMTP login successful")
                server.send_message(msg)
                logger.info("Email sent via SMTP with STARTTLS")

        logger.info(f"Email sent successfully to {to_email}")

    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP connection failed: {str(e)}")
        raise Exception(f"SMTP connection failed: {str(e)}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {str(e)}")
        raise Exception(f"SMTP authentication failed: {str(e)}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise Exception(f"SMTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        raise Exception(f"Failed to send email: {str(e)}")


def send_otp_email(to_email: str, otp: str, expires_in_minutes: int = 10) -> None:
    """
    Send OTP verification email

    Args:
        to_email: Recipient email address
        otp: One-time password code
        expires_in_minutes: OTP expiration time in minutes
    """
    subject = "Verify Your Email - NFI Gate"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #84cc16; color: white; padding: 20px; text-align: center; }}
            .otp-code {{ font-size: 32px; font-weight: bold; text-align: center; padding: 20px; background: #f0f0f0; border: 1px solid #ddd; margin: 20px 0; }}
            .footer {{ text-align: center; font-size: 12px; color: #666; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>NFI Gate</h2>
            </div>
            <p>Hello,</p>
            <p>Please use this verification code to complete your registration:</p>
            <div class="otp-code">{otp}</div>
            <p>This code expires in {expires_in_minutes} minutes.</p>
            <p><strong>Security:</strong> Never share this code with anyone.</p>
            <div class="footer">
                <p>© 2024 NFI Gate. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    NFI Gate - Email Verification

    Verification Code: {otp}

    This code expires in {expires_in_minutes} minutes.

    Security: Never share this code with anyone.

    © 2024 NFI Gate. All rights reserved.
    """

    send_email(to_email, subject, html_body, text_body)


def send_welcome_email(to_email: str, user_name: str) -> None:
    """
    Send welcome email after successful registration

    Args:
        to_email: Recipient email address
        user_name: User's name or email
    """
    subject = "Welcome to NFI Gate!"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #0a0b0d;
                background-color: #f8faf9;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #84cc16 0%, #a3e635 100%);
                padding: 40px 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                color: #000000;
                font-size: 28px;
                font-weight: 700;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .message {{
                color: #0a0b0d;
                font-size: 16px;
                margin-bottom: 20px;
            }}
            .cta-button {{
                display: inline-block;
                background: #84cc16;
                color: #000000;
                padding: 14px 28px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                margin: 20px 0;
            }}
            .footer {{
                background: #f3f4f6;
                padding: 20px 30px;
                text-align: center;
                font-size: 13px;
                color: #6b7280;
            }}
            .footer a {{
                color: #84cc16;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to NFI Gate! 🎉</h1>
            </div>
            <div class="content">
                <p class="message">Hello {user_name},</p>
                <p class="message">Your email has been successfully verified! Welcome to NFI Gate, your trusted financial gateway.</p>
                <p class="message">You can now log in and explore all the features we have to offer.</p>
                <div style="text-align: center;">
                    <a href="#" class="cta-button">Get Started</a>
                </div>
            </div>
            <div class="footer">
                <p>© 2024 NFI Gate. All rights reserved.</p>
                <p>Need help? Contact us at <a href="mailto:{SMTP_FROM_EMAIL}">{SMTP_FROM_EMAIL}</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Welcome to NFI Gate!

    Hello {user_name},

    Your email has been successfully verified! Welcome to NFI Gate, your trusted financial gateway.

    You can now log in and explore all the features we have to offer.

    © 2024 NFI Gate. All rights reserved.
    Need help? Contact us at {SMTP_FROM_EMAIL}
    """

    send_email(to_email, subject, html_body, text_body)


def send_email_background(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> None:
    """
    Background task for sending emails with proper error handling.
    This function is designed to be used with FastAPI BackgroundTasks.
    """
    try:
        send_email(to_email, subject, html_body, text_body)
        logger.info(f"Background email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Background email failed to {to_email}: {str(e)}")
        # In a production system, you might want to:
        # - Store failed emails in a queue for retry
        # - Send alerts to administrators
        # - Update user status to indicate email delivery failure


def test_smtp_connection() -> dict:
    """
    Test SMTP connection and return diagnostic information.
    """
    result = {
        "smtp_configured": False,
        "connection_test": False,
        "auth_test": False,
        "error": None,
        "config": {}
    }

    try:
        # Check configuration
        result["config"] = {
            "host": SMTP_HOST,
            "port": SMTP_PORT,
            "username": SMTP_USERNAME[:3] + "***" if SMTP_USERNAME else None,
            "from_email": SMTP_FROM_EMAIL,
            "from_name": SMTP_FROM_NAME
        }

        if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM_EMAIL:
            result["error"] = "SMTP credentials not configured"
            return result

        result["smtp_configured"] = True

        # Test connection
        logger.info(f"Testing SMTP connection to {SMTP_HOST}:{SMTP_PORT}")
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.starttls()

        result["connection_test"] = True
        logger.info("SMTP connection successful")

        # Test authentication
        server.login(str(SMTP_USERNAME), str(SMTP_PASSWORD))
        result["auth_test"] = True
        logger.info("SMTP authentication successful")

        server.quit()

    except smtplib.SMTPConnectError as e:
        result["error"] = f"Connection failed: {str(e)}"
        logger.error(f"SMTP connection test failed: {str(e)}")
    except smtplib.SMTPAuthenticationError as e:
        result["error"] = f"Authentication failed: {str(e)}"
        logger.error(f"SMTP auth test failed: {str(e)}")
    except Exception as e:
        result["error"] = f"Test failed: {str(e)}"
        logger.error(f"SMTP test failed: {str(e)}")

    return result
