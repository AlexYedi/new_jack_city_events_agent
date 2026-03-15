# calendar_client.py
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "calendar_token.json")

MATCH_THRESHOLD = 70


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
        logger.info("Calendar OAuth token saved to %s", TOKEN_FILE)
    return creds


def _fuzzy_score(a, b):
    """Return similarity ratio 0-100 between two strings."""
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def _find_professional_calendar(service):
    """Return the calendar ID for 'Professional' or fall back to 'primary'."""
    calendars = service.calendarList().list().execute()
    for cal in calendars.get("items", []):
        if cal.get("summary", "").lower() == "professional":
            logger.info("Found 'Professional' calendar: %s", cal["id"])
            return cal["id"]
    logger.info("'Professional' calendar not found — using primary")
    return "primary"


def _fetch_supabase_events():
    """Fetch event titles + IDs from Supabase for fuzzy matching."""
    try:
        from supabase import create_client
        client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
        resp = client.table("events").select("id, title").execute()
        return resp.data or []
    except Exception as e:
        logger.error("Failed to fetch Supabase events for matching: %s", e)
        return []


def get_attending_events(start_date=None, end_date=None):
    """Fetch events from Google Calendar and fuzzy-match against Supabase events.

    Args:
        start_date: datetime — defaults to now
        end_date: datetime — defaults to now + 28 days

    Returns:
        list of matched event dicts with event_id, calendar_title,
        matched_title, and match_confidence
    """
    try:
        if not os.path.exists(TOKEN_FILE):
            logger.warning("calendar_token.json not found — skipping calendar fetch")
            return []

        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now(tz=timezone.utc)
        start = start_date or now
        end = end_date or (now + timedelta(days=28))

        calendar_id = _find_professional_calendar(service)

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        cal_events = events_result.get("items", [])
        logger.info("Google Calendar: found %d events in range", len(cal_events))

        supabase_events = _fetch_supabase_events()
        logger.info("Supabase: loaded %d events for matching", len(supabase_events))

        matched = []
        for cal_event in cal_events:
            cal_title = cal_event.get("summary", "")
            if not cal_title:
                continue

            best_score = 0
            best_match = None
            for sb_event in supabase_events:
                score = _fuzzy_score(cal_title, sb_event.get("title", ""))
                if score > best_score:
                    best_score = score
                    best_match = sb_event

            if best_score >= MATCH_THRESHOLD and best_match:
                matched.append({
                    "event_id": best_match["id"],
                    "calendar_title": cal_title,
                    "matched_title": best_match["title"],
                    "match_confidence": best_score,
                })
                logger.info(
                    "Matched: '%s' → '%s' (%d%%)",
                    cal_title, best_match["title"], best_score,
                )
            else:
                logger.debug(
                    "No match for calendar event '%s' (best score: %d%%)",
                    cal_title, best_score,
                )

        logger.info(
            "Calendar: %d events found, %d matched to Supabase events",
            len(cal_events), len(matched),
        )
        return matched

    except Exception as e:
        logger.error("get_attending_events failed: %s", e)
        return []


def trigger_calendar_oauth():
    """Run the OAuth flow to generate calendar_token.json."""
    _get_credentials()
    print("Calendar OAuth complete")
