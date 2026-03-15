# gmail_sender.py
import os
import base64
import logging
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "gmail_send_token.json")
FROM_ADDRESS = "alex.e.yedi@gmail.com"


def _get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = {
                "installed": {
                    "client_id": os.environ["GOOGLE_CLIENT_ID"],
                    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        logger.info("Gmail send OAuth token saved to %s", TOKEN_FILE)
    return creds


def send_email(subject: str, body: str, to: str) -> bool:
    """Send an HTML email via Gmail API.

    Args:
        subject: email subject line
        body: HTML email body
        to: recipient email address

    Returns:
        True on success, False on failure
    """
    try:
        creds = _get_credentials()
        service = build("gmail", "v1", credentials=creds)

        msg = MIMEText(body, "html")
        msg["From"] = FROM_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()

        logger.info("Email sent — id=%s to=%s subject='%s'", result.get("id"), to, subject)
        return True

    except Exception as e:
        logger.error("send_email failed: %s", e)
        return False


def trigger_send_oauth():
    """Run the OAuth flow to generate gmail_send_token.json."""
    _get_credentials()
    print("Gmail send OAuth complete")
