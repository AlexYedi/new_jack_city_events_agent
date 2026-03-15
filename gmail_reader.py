# gmail_reader.py
import os
import base64
import json
import logging
from datetime import datetime, timedelta
from email import message_from_bytes
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "gmail_read_token.json")

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
            creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        logger.info("Gmail OAuth token saved to %s", TOKEN_FILE)
    return creds

def _strip_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def _decode_part(part):
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""

def _extract_body(payload):
    mime_type = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if mime_type == "text/plain":
        return _decode_part(payload)
    if mime_type == "text/html":
        return _strip_html(_decode_part(payload))

    plain_text = ""
    html_text = ""
    for part in parts:
        sub_mime = part.get("mimeType", "")
        if sub_mime == "text/plain":
            plain_text += _decode_part(part)
        elif sub_mime == "text/html":
            html_text += _strip_html(_decode_part(part))
        elif sub_mime.startswith("multipart/"):
            result = _extract_body(part)
            if result:
                plain_text += result

    return plain_text if plain_text else html_text

def fetch_event_emails():
    """Fetch event-related emails from Gmail for the last GMAIL_EVENTS_SEARCH_DAYS days.

    Returns:
        dict with keys: emails (list), count (int), error (str or None)
    """
    try:
        creds = _get_credentials()
        service = build("gmail", "v1", credentials=creds)

        lookback_days = int(os.environ.get("GMAIL_EVENTS_SEARCH_DAYS", "28"))
        since_date = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y/%m/%d")

        sender_query = (
            "from:meetup.com OR from:lu.ma OR from:luma.com OR "
            "from:garysguide.com OR from:greyjournal.net OR "
            "from:betaworks.com OR from:eventbrite.com OR "
            "from:supermomos.com OR from:aicamp.ai OR "
            "from:mindstone.com OR from:partiful.com"
        )
        subject_query = (
            "subject:(AI event) OR subject:(artificial intelligence) OR "
            "subject:(RSVP) OR subject:(register now) OR "
            "subject:(you're invited) OR subject:(LLM) OR "
            "subject:(agent) OR subject:(machine learning) OR "
            "subject:(NYC event) OR subject:(New York event) OR "
            "subject:(agentic) OR subject:(demo day)"
        )
        full_query = f"({sender_query} OR {subject_query}) after:{since_date}"

        logger.info("Gmail search query: %s", full_query)

        result = service.users().messages().list(
            userId="me",
            q=full_query,
            maxResults=50,
            includeSpamTrash=True,
        ).execute()

        messages = result.get("messages", [])
        logger.info("Found %d messages matching query", len(messages))

        emails = []
        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="full",
                ).execute()

                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = headers.get("Subject", "(no subject)")
                sender = headers.get("From", "(unknown sender)")
                date = headers.get("Date", "")
                body_text = _extract_body(msg.get("payload", {}))

                emails.append({
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "body_text": body_text[:5000],  # cap per email
                })
            except Exception as e:
                logger.warning("Failed to fetch message %s: %s", msg_ref["id"], e)
                continue

        return {"emails": emails, "count": len(emails), "error": None}

    except Exception as e:
        logger.error("fetch_event_emails failed: %s", e)
        return {"emails": [], "count": 0, "error": str(e)}
