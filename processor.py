# processor.py
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

NYC_TZ = timezone(timedelta(hours=-5))  # EST; adjust for EDT as needed

BUCKET_CAPS = {
    4: 10,  # 22-28 days out
    3: 5,   # 15-21 days out
    2: 3,   # 8-14 days out
    1: 2,   # 1-7 days out
}

def _parse_date(date_str):
    """Try multiple ISO 8601 formats."""
    if not date_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(str(date_str)[:19], fmt[:len(fmt)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=NYC_TZ)
            return dt
        except ValueError:
            continue
    return None

def process_events(events: list) -> list:
    """Filter, bucket, cap, and sort events by score.

    Args:
        events: raw event list from Gemini

    Returns:
        flat list of processed events with week_bucket and days_until fields
    """
    now = datetime.now(tz=NYC_TZ)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    buckets = {1: [], 2: [], 3: [], 4: []}
    skipped = 0

    for event in events:
        event_date = _parse_date(event.get("event_date"))
        if not event_date:
            logger.warning("Could not parse date for event: %s", event.get("title"))
            skipped += 1
            continue

        days_until = (event_date.replace(tzinfo=NYC_TZ) - today).days

        if days_until < 1 or days_until > 28:
            skipped += 1
            continue

        if days_until <= 7:
            bucket = 1
        elif days_until <= 14:
            bucket = 2
        elif days_until <= 21:
            bucket = 3
        else:
            bucket = 4

        try:
            score = int(event.get("score", 5))
            score = max(1, min(10, score))
        except (ValueError, TypeError):
            score = 5

        speakers = event.get("speakers", [])
        companies = event.get("companies", [])
        if isinstance(speakers, list):
            speakers = json.dumps(speakers)
        if isinstance(companies, list):
            companies = json.dumps(companies)

        enriched = dict(event)
        enriched["score"] = score
        enriched["days_until"] = days_until
        enriched["week_bucket"] = bucket
        enriched["speakers"] = speakers
        enriched["companies"] = companies

        buckets[bucket].append(enriched)

    result = []
    for bucket_num in sorted(buckets.keys(), reverse=True):
        cap = BUCKET_CAPS[bucket_num]
        sorted_events = sorted(buckets[bucket_num], key=lambda e: e["score"], reverse=True)
        capped = sorted_events[:cap]
        result.extend(capped)
        logger.info("Bucket %d: %d events (cap %d, included %d)", bucket_num, len(buckets[bucket_num]), cap, len(capped))

    logger.info("Processed %d events total (%d skipped)", len(result), skipped)
    return result
