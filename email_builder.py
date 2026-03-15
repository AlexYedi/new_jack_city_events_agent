# email_builder.py
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

NYC_TZ = timezone(timedelta(hours=-5))

BUCKET_LABELS = {
    1: "This week",
    2: "Next week",
    3: "In 3 weeks",
    4: "In 4 weeks",
}

BUCKET_CAPS = {1: 2, 2: 3, 3: 5, 4: 10}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _week_range(offset_weeks: int, today: datetime):
    """Return (start, end) datetimes for a week offset_weeks from this Monday."""
    monday = today - timedelta(days=today.weekday())
    start = monday + timedelta(weeks=offset_weeks)
    end = start + timedelta(days=6)
    return start, end


def _fmt_date_range(start: datetime, end: datetime) -> str:
    if start.month == end.month:
        return f"{start.strftime('%b %-d')}–{end.strftime('%-d, %Y')}"
    return f"{start.strftime('%b %-d')} – {end.strftime('%b %-d, %Y')}"


def _fmt_event_date(date_str) -> str:
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(date_str)[:19], fmt)
            return dt.strftime("%a, %b %-d · %-I:%M %p")
        except ValueError:
            continue
    return str(date_str)


def _score_dots(score) -> str:
    try:
        s = max(1, min(10, int(score)))
    except (TypeError, ValueError):
        s = 5
    filled = "●" * s
    empty = "○" * (10 - s)
    return f'<span style="color:#4f46e5;letter-spacing:1px">{filled}</span><span style="color:#d1d5db;letter-spacing:1px">{empty}</span>'


def _cost_badge(cost) -> str:
    cost_str = str(cost or "").strip().lower()
    if not cost_str or cost_str in ("free", "0", "$0"):
        return '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">Free</span>'
    return f'<span style="background:#f3f4f6;color:#374151;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{cost}</span>'


def _type_badge(content_type) -> str:
    t = str(content_type or "").strip()
    colors = {
        "Hands-on": "#dbeafe;color:#1e40af",
        "Demo": "#dbeafe;color:#1e40af",
        "Panel": "#dbeafe;color:#1e40af",
        "Talk": "#dbeafe;color:#1e40af",
    }
    style = colors.get(t, "#f3f4f6;color:#374151")
    return f'<span style="background:{style};padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{t or "Event"}</span>'


def _parse_json_list(val) -> list:
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        parsed = json.loads(val)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# ── Card builders ─────────────────────────────────────────────────────────────

def _standard_card(event: dict) -> str:
    title = event.get("title", "Untitled")
    url = event.get("url", "#")
    date_str = _fmt_event_date(event.get("event_date"))
    location = event.get("location", "")
    cost = event.get("cost", "")
    content_type = event.get("content_type", "")
    score = event.get("score", 5)

    return f"""
<div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px 20px;margin:8px 0;background:#ffffff">
  <div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:6px">{title}</div>
  <div style="font-size:13px;color:#6b7280;margin-bottom:8px">
    {f'<span style="margin-right:12px">📅 {date_str}</span>' if date_str else ''}
    {f'<span>📍 {location}</span>' if location else ''}
  </div>
  <div style="margin-bottom:10px">
    {_cost_badge(cost)}&nbsp;&nbsp;{_type_badge(content_type)}
  </div>
  <div style="font-size:12px;margin-bottom:10px">{_score_dots(score)}</div>
  <a href="{url}" style="color:#4f46e5;font-size:13px;font-weight:600;text-decoration:none">View event →</a>
</div>
""".strip()


def _attending_card(event: dict) -> str:
    title = event.get("title", "Untitled")
    url = event.get("url", "#")
    date_str = _fmt_event_date(event.get("event_date"))
    location = event.get("location", "")
    cost = event.get("cost", "")
    content_type = event.get("content_type", "")
    score = event.get("score", 5)
    description = event.get("description", "")
    speakers = _parse_json_list(event.get("speakers"))
    companies = _parse_json_list(event.get("companies"))

    speakers_html = ""
    if speakers:
        speaker_items = "".join(f"<li>{s}</li>" for s in speakers)
        speakers_html = f'<div style="margin-top:10px"><strong>Speakers:</strong><ul style="margin:4px 0 0 16px;padding:0;color:#374151;font-size:13px">{speaker_items}</ul></div>'

    companies_html = ""
    if companies:
        company_tags = " ".join(
            f'<span style="background:#f0fdf4;color:#166534;padding:2px 8px;border-radius:12px;font-size:11px;margin-right:4px">{c}</span>'
            for c in companies
        )
        companies_html = f'<div style="margin-top:10px"><strong style="font-size:13px">Companies:</strong><div style="margin-top:4px">{company_tags}</div></div>'

    return f"""
<div style="border:2px solid #4f46e5;border-radius:8px;padding:16px 20px;margin:8px 0;background:#fafafe">
  <div style="font-size:11px;font-weight:700;color:#4f46e5;letter-spacing:1px;margin-bottom:6px">✓ ATTENDING</div>
  <div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:6px">{title}</div>
  <div style="font-size:13px;color:#6b7280;margin-bottom:8px">
    {f'<span style="margin-right:12px">📅 {date_str}</span>' if date_str else ''}
    {f'<span>📍 {location}</span>' if location else ''}
  </div>
  <div style="margin-bottom:10px">
    {_cost_badge(cost)}&nbsp;&nbsp;{_type_badge(content_type)}
  </div>
  <div style="font-size:12px;margin-bottom:10px">{_score_dots(score)}</div>
  {f'<div style="font-size:13px;color:#374151;line-height:1.5;margin-bottom:8px">{description}</div>' if description else ''}
  {speakers_html}
  {companies_html}
  <a href="{url}" style="color:#4f46e5;font-size:13px;font-weight:600;text-decoration:none;margin-top:10px;display:inline-block">View event →</a>
</div>
""".strip()


# ── Main builder ──────────────────────────────────────────────────────────────

def build_digest(events: list):
    """Build HTML digest email from processed events.

    Args:
        events: processed event list from processor.process_events()

    Returns:
        (subject, html_body) tuple
    """
    try:
        now = datetime.now(tz=NYC_TZ)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Group events by bucket (ascending order for display)
        buckets = {1: [], 2: [], 3: [], 4: []}
        for event in events:
            b = event.get("week_bucket")
            if b in buckets:
                buckets[b].append(event)

        total_events = sum(len(v) for v in buckets.values())
        non_empty_buckets = sum(1 for v in buckets.values() if v)

        # Subject
        week_start, _ = _week_range(1, today)  # next Monday = "this week" start
        subject = (
            f"NYC AI Events \u2014 Week of {week_start.strftime('%b %-d, %Y')} "
            f"({total_events} events across {non_empty_buckets} week{'s' if non_empty_buckets != 1 else ''})"
        )

        # Header
        run_date = now.strftime("%B %-d, %Y")
        header = f"""
<div style="background:#1e1b4b;padding:24px 32px;border-radius:8px 8px 0 0">
  <div style="color:#ffffff;font-size:20px;font-weight:800;letter-spacing:-0.5px">NYC AI Events</div>
  <div style="color:#a5b4fc;font-size:13px;margin-top:4px">{run_date} · {total_events} events across {non_empty_buckets} week{'s' if non_empty_buckets != 1 else ''}</div>
</div>
""".strip()

        # Sections
        sections_html = ""
        for bucket_num in [1, 2, 3, 4]:
            bucket_events = buckets[bucket_num]
            if not bucket_events:
                continue

            week_offset = bucket_num  # bucket 1 = 1 week out, etc.
            w_start, w_end = _week_range(week_offset, today)
            date_range = _fmt_date_range(w_start, w_end)
            label = BUCKET_LABELS[bucket_num]
            count = len(bucket_events)

            section_header = f"""
<div style="margin:24px 0 12px 0">
  <div style="font-size:17px;font-weight:800;color:#1e1b4b">{label}</div>
  <div style="font-size:12px;color:#6b7280;margin-top:2px">{date_range} · {count} event{'s' if count != 1 else ''}</div>
</div>
""".strip()

            cards_html = ""
            for event in bucket_events:
                is_attending = event.get("is_attending", False)
                if is_attending:
                    cards_html += "\n" + _attending_card(event)
                else:
                    cards_html += "\n" + _standard_card(event)

            sections_html += f"\n{section_header}\n{cards_html}"

        if not sections_html:
            sections_html = '<p style="color:#6b7280;font-size:14px">No events found for the next 4 weeks.</p>'

        # Footer
        timestamp = now.strftime("%Y-%m-%d %H:%M ET")
        footer = f"""
<div style="margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb;text-align:center">
  <div style="font-size:12px;color:#9ca3af">Generated by Events Agent · {timestamp}</div>
  <div style="margin-top:6px"><a href="#" style="font-size:12px;color:#9ca3af;text-decoration:none">Unsubscribe</a></div>
</div>
""".strip()

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:24px;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
  {header}
  <div style="padding:24px 32px 32px">
    {sections_html}
    {footer}
  </div>
</div>
</body>
</html>"""

        logger.info(
            "email_builder: built digest — subject='%s' buckets=%s",
            subject,
            {k: len(v) for k, v in buckets.items()},
        )
        return subject, html_body

    except Exception as e:
        logger.error("build_digest failed: %s", e)
        subject = f"NYC AI Events — {datetime.now().strftime('%b %-d, %Y')}"
        html_body = f"<p>Error building digest: {e}</p>"
        return subject, html_body
