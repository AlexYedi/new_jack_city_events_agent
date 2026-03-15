# gmail_sender.py
import logging

logger = logging.getLogger(__name__)

def send_email(subject: str, body: str, to: str) -> bool:
    """Send HTML email via Gmail API.

    Args:
        subject: email subject line
        body: HTML email body
        to: recipient email address

    Returns:
        True if sent successfully, False otherwise
    """
    # Phase 2: implement Gmail send via Gmail API with write scope
    logger.info("gmail_sender: stub — would send '%s' to %s", subject, to)
    return False
