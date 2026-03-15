# email_builder.py
import logging

logger = logging.getLogger(__name__)

def build_digest(events: list, jobs: list) -> str:
    """Build HTML digest email from processed events and jobs.

    Args:
        events: processed event list from processor.process_events()
        jobs: job list from jobs.scrape_jobs()

    Returns:
        HTML string for the email body
    """
    # Phase 2: implement rich HTML digest builder
    logger.info("email_builder: stub — building plain text digest for %d events", len(events))
    lines = [f"<h1>Events Digest</h1>", f"<p>{len(events)} events found.</p>"]
    for event in events:
        lines.append(f"<p><b>{event.get('title', 'Unknown')}</b> — {event.get('event_date', '')} (score: {event.get('score', '')})</p>")
    return "\n".join(lines)
