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
        raise Exception("Email service not configured")

    try:
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
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(str(SMTP_USERNAME), str(SMTP_PASSWORD))
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(str(SMTP_USERNAME), str(SMTP_PASSWORD))
                server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
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
