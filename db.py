# db.py
import os
import json
import logging
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_client = None

def _get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _client

EVENTS_TABLE_COLUMNS = {
    "title", "source", "url", "event_date", "location",
    "cost", "content_type", "score", "week_bucket", "raw_data",
}

def _prepare_event_row(event: dict) -> dict:
    """Map processed event dict to events table columns.
    Extra fields (companies, speakers, description, days_until) go into raw_data JSON.
    """
    extras = {k: v for k, v in event.items() if k not in EVENTS_TABLE_COLUMNS}
    row = {k: v for k, v in event.items() if k in EVENTS_TABLE_COLUMNS}
    if extras:
        row["raw_data"] = json.dumps(extras)
    return row

def upsert_events(events: list) -> int:
    """Upsert events to Supabase events table on url conflict.

    Returns:
        count of rows upserted
    """
    if not events:
        return 0
    try:
        client = _get_client()
        seen = {}
        for event in events:
            url = event.get("url")
            if url:
                seen[url] = event
        deduped = list(seen.values())
        logger.info("upsert_events: %d events after dedup (was %d)", len(deduped), len(events))
        rows = [_prepare_event_row(e) for e in deduped]
        response = client.table("events").upsert(rows, on_conflict="url").execute()
        count = len(response.data) if response.data else 0
        logger.info("Upserted %d events", count)
        return count
    except Exception as e:
        logger.error("upsert_events failed: %s", e)
        return 0

def mark_attending(event_ids: list) -> None:
    """Mark events as attending in Supabase."""
    if not event_ids:
        return
    try:
        client = _get_client()
        client.table("events").update({"is_attending": True}).in_("id", event_ids).execute()
        logger.info("Marked %d events as attending", len(event_ids))
    except Exception as e:
        logger.error("mark_attending failed: %s", e)


def get_events_for_email() -> list:
    """Fetch all events from current run, joining jobs for attended events."""
    try:
        client = _get_client()
        response = client.table("events").select("*, jobs(*)").eq("is_attending", True).execute()
        return response.data or []
    except Exception as e:
        logger.error("get_events_for_email failed: %s", e)
        return []

def log_run(stats: dict) -> None:
    """Insert run stats to run_log table."""
    try:
        client = _get_client()
        client.table("run_log").insert({
            "events_found": stats.get("events_found", 0),
            "email_sent": stats.get("email_sent", False),
            "notes": stats.get("notes", ""),
        }).execute()
        logger.info("Logged run stats to Supabase")
    except Exception as e:
        logger.error("log_run failed: %s", e)
