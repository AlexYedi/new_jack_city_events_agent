# observability.py
import os
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def _posthog_client():
    from posthog import Posthog
    key = os.environ.get("POSTHOG_API_KEY", "")
    host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
    if not key:
        return None
    return Posthog(project_api_key=key, host=host)

def track_run(stats: dict) -> None:
    """Track a completed agent run in PostHog."""
    try:
        client = _posthog_client()
        if client:
            client.capture(
                event="agent_run_completed",
                distinct_id="events-agent",
                properties={
                    "events_found": stats.get("events_found", 0),
                    "jobs_found": stats.get("jobs_found", 0),
                    "email_sent": stats.get("email_sent", False),
                    "sources_succeeded": stats.get("sources_succeeded", 0),
                    "sources_failed": stats.get("sources_failed", 0),
                    "run_duration_seconds": stats.get("run_duration_seconds", 0),
                },
            )
            client.flush()
            logger.info("Tracked run in PostHog")
    except Exception as e:
        logger.error("track_run failed: %s", e)

def track_error(error: str, context: str) -> None:
    """Track a run failure in PostHog and create a Linear issue."""
    try:
        client = _posthog_client()
        if client:
            client.capture(
                event="agent_run_failed",
                distinct_id="events-agent",
                properties={
                    "error_message": error,
                    "context": context,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                },
            )
            client.flush()
    except Exception as e:
        logger.error("track_error PostHog failed: %s", e)

    try:
        _create_linear_issue(context, error)
    except Exception as e:
        logger.error("track_error Linear failed: %s", e)

def _create_linear_issue(context: str, error: str) -> None:
    """Create a Linear bug issue for a failed agent run."""
    import httpx

    api_key = os.environ.get("LINEAR_API_KEY", "")
    team_id = os.environ.get("LINEAR_TEAM_ID", "")

    if not api_key or not team_id:
        logger.warning("LINEAR_API_KEY or LINEAR_TEAM_ID not set — skipping issue creation")
        return

    query = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id title }
      }
    }
    """
    variables = {
        "input": {
            "title": f"[Events Agent] {context} failed",
            "description": f"**Error:** {error}\n\n**Context:** {context}\n\n**Timestamp:** {datetime.now(tz=timezone.utc).isoformat()}",
            "teamId": team_id,
        }
    }

    resp = httpx.post(
        "https://api.linear.app/graphql",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("Created Linear issue for %s", context)
