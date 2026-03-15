# main.py
import os
import sys
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

import gmail_reader
import gemini
import processor
import db
import observability
import calendar_client
import email_builder
import gmail_sender

SEND_MODE = os.environ.get("SEND_MODE", "false").lower()


def build_stats(processed, email_data, duration):
    return {
        "events_found": len(processed),
        "email_sent": SEND_MODE == "true",
        "sources_succeeded": 1 if email_data.get("count", 0) > 0 else 0,
        "sources_failed": 1 if email_data.get("error") else 0,
        "run_duration_seconds": round(duration, 2),
        "notes": f"emails={email_data.get('count', 0)} error={email_data.get('error')}",
    }


def run():
    start = time.time()
    logger.info("=== Events Agent run starting at %s ===", datetime.now(tz=timezone.utc).isoformat())

    try:
        # 1. Fetch event emails from Gmail
        logger.info("Step 1: Fetching event emails from Gmail...")
        email_data = gmail_reader.fetch_event_emails()
        logger.info("Fetched %d emails (error=%s)", email_data.get("count", 0), email_data.get("error"))

        # 2. Extract events via Gemini
        logger.info("Step 2: Extracting events with Gemini...")
        raw_events = gemini.extract_events(email_data)
        logger.info("Extracted %d raw events", len(raw_events))

        # 3. Process and bucket events
        logger.info("Step 3: Processing events...")
        processed = processor.process_events(raw_events)
        logger.info("Processed %d events after filtering and capping", len(processed))

        # 4. Upsert events to Supabase
        logger.info("Step 4: Upserting events to Supabase...")
        upserted = db.upsert_events(processed)
        logger.info("Upserted %d events", upserted)

        # 5. Get calendar events being attended
        logger.info("Step 5: Fetching attending events from Google Calendar...")
        attending = calendar_client.get_attending_events()
        logger.info("Found %d attending events", len(attending))

        # 6. Mark attended events
        logger.info("Step 6: Marking attending events in DB...")
        attending_ids = [e.get("event_id") for e in attending if e.get("event_id")]
        db.mark_attending(attending_ids)

        # Annotate in-memory processed list so email builder renders expanded cards
        attended_titles = {a["matched_title"] for a in attending}
        for event in processed:
            if event.get("title") in attended_titles:
                event["is_attending"] = True
                logger.info("Flagged as attending in-memory: %s", event.get("title"))

        # 7. Build digest email
        logger.info("Step 7: Building digest email...")
        subject, html_body = email_builder.build_digest(processed)
        logger.info("Digest subject: %s", subject)

        # 8. Send email if SEND_MODE=true
        if SEND_MODE == "true":
            logger.info("Step 8: Sending digest email...")
            sent = gmail_sender.send_email(
                subject=subject,
                body=html_body,
                to="alex.e.yedi@gmail.com",
            )
            logger.info("Email sent: %s", sent)
        else:
            logger.info("Step 8: SEND_MODE=%s — skipping send. Subject: %s", SEND_MODE, subject)

        # 9. Track run stats
        duration = time.time() - start
        stats = build_stats(processed, email_data, duration)
        logger.info("Step 9: Tracking run stats: %s", stats)

        observability.track_run(stats)
        db.log_run(stats)

        logger.info("=== Run complete in %.2fs ===", duration)

    except Exception as e:
        logger.error("Run failed: %s", e, exc_info=True)
        observability.track_error(str(e), "main.run")
        raise


def main():
    from apscheduler.schedulers.blocking import BlockingScheduler
    import pytz

    scheduler = BlockingScheduler(timezone=pytz.timezone("America/New_York"))
    scheduler.add_job(run, "cron", day_of_week="sun", hour=7, minute=0)

    next_run = None
    for job in scheduler.get_jobs():
        try:
            next_run = job.next_run_time
        except AttributeError:
            next_run = "scheduled (check APScheduler logs)"
    logger.info("Scheduler started. Next run: %s", next_run)

    if "--now" in sys.argv:
        logger.info("--now flag detected — running immediately")
        run()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
