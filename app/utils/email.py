"""
Email Utility for sending emails via Zoho SMTP
Handles email sending with HTML templates
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings

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

        # Connect to SMTP server and send
        # Use SMTP_SSL for port 465, SMTP with STARTTLS for port 587
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)

    except Exception as e:
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
            .otp-box {{
                background: #f3f4f6;
                border: 2px dashed #84cc16;
                border-radius: 8px;
                padding: 24px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: 700;
                letter-spacing: 8px;
                color: #84cc16;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
            }}
            .otp-label {{
                font-size: 12px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }}
            .expiry-notice {{
                font-size: 14px;
                color: #ef4444;
                margin-top: 8px;
            }}
            .message {{
                color: #0a0b0d;
                font-size: 16px;
                margin-bottom: 20px;
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
            .security-notice {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 12px 16px;
                margin: 20px 0;
                border-radius: 4px;
                font-size: 14px;
                color: #92400e;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>NFI Gate</h1>
            </div>
            <div class="content">
                <p class="message">Hello,</p>
                <p class="message">Thank you for signing up with NFI Gate. Please use the verification code below to complete your registration:</p>

                <div class="otp-box">
                    <div class="otp-label">Your Verification Code</div>
                    <div class="otp-code">{otp}</div>
                    <div class="expiry-notice">⏱️ Expires in {expires_in_minutes} minutes</div>
                </div>

                <div class="security-notice">
                    <strong>⚠️ Security Notice:</strong> Never share this code with anyone. NFI Gate will never ask for your verification code via phone or email.
                </div>

                <p class="message">If you didn't request this verification code, please ignore this email or contact our support team.</p>
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
    NFI Gate - Email Verification

    Hello,

    Thank you for signing up with NFI Gate. Please use the verification code below to complete your registration:

    Verification Code: {otp}

    This code will expire in {expires_in_minutes} minutes.

    Security Notice: Never share this code with anyone. NFI Gate will never ask for your verification code via phone or email.

    If you didn't request this verification code, please ignore this email or contact our support team.

    © 2024 NFI Gate. All rights reserved.
    Need help? Contact us at {SMTP_FROM_EMAIL}
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
