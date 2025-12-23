import resend
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Resend with API key
if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY


def send_resend_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email via Resend API
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email
        text_body: Plain text fallback (optional)
        from_email: Sender email (defaults to settings.SMTP_FROM_EMAIL if not provided)
        from_name: Sender name (defaults to settings.SMTP_FROM_NAME if not provided)
        
    Returns:
        Dict response from Resend API
        
    Raises:
        Exception: If Resend API key is missing or sending fails
    """
    if not settings.RESEND_API_KEY:
        raise Exception("Resend API key not configured")
        
    # Determine sender
    sender_email = from_email or settings.SMTP_FROM_EMAIL
    sender_name = from_name or settings.SMTP_FROM_NAME
    
    if not sender_email:
        raise Exception("Sender email not configured")
        
    # Format sender field
    # If sender_email already contains <>, use it as is
    # Otherwise format as "Name <email>" or just "email"
    if "<" in sender_email and ">" in sender_email:
        from_field = sender_email
    elif sender_name:
        from_field = f"{sender_name} <{sender_email}>"
    else:
        from_field = sender_email
        
    # Prepare params
    params = {
        "from": from_field,
        "to": [to_email],
        "subject": subject,
        "html": html_body
    }
    
    if text_body:
        params["text"] = text_body
        
    try:
        logger.info(f"Sending email via Resend to {to_email} with subject: {subject}")
        response = resend.Emails.send(params)
        logger.info(f"Resend response: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to send email via Resend: {str(e)}")
        raise e
