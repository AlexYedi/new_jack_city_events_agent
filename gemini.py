# gemini.py
import os
import json
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def extract_events(email_data: dict) -> list:
    """Extract structured event data from raw email content using Gemini.

    Args:
        email_data: dict with 'emails' list from gmail_reader.fetch_event_emails()

    Returns:
        list of event dicts
    """
    emails = email_data.get("emails", [])
    if not emails:
        logger.info("No emails to process")
        return []

    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        combined_text = "\n\n---EMAIL BREAK---\n\n".join(
            f"Subject: {e['subject']}\nFrom: {e['sender']}\nDate: {e['date']}\n\n{e['body_text']}"
            for e in emails
        )
        combined_text = combined_text[:80000]

        prompt = f"""You are an AI event curator for New York City.
Extract ALL AI, ML, LLM, agentic AI, and tech events from the following email content.

Scoring rules:
- hands-on building = 10
- live demo = 8
- expert panel = 6
- conference/expo = 5
- talk/lecture = 4
- networking only = 3

Filtering rules:
- In-person events in NYC 5 boroughs only
- Include Hoboken/Jersey City ONLY if score >= 8
- Exclude virtual/remote events entirely
- Exclude low-signal recurring meetups with no notable speakers or agenda
- Only include events from today up to 28 days out
- Deduplicate: if same event appears in multiple emails return it once only

Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.

Each object must have:
- title (string)
- url (string)
- event_date (string, ISO 8601)
- location (string)
- cost (string: "free" or dollar amount)
- content_type (string: hands-on/demo/panel/talk/conference/networking)
- description (string, 2-3 sentences)
- speakers (array of strings)
- companies (array of strings)
- score (integer 1-10)

EMAIL CONTENT:
{combined_text}"""

        models_to_try = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
        response_text = None
        for model_name in models_to_try:
            try:
                logger.info("Trying Gemini model: %s", model_name)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                response_text = response.text.strip()
                logger.info("Gemini model succeeded: %s", model_name)
                break
            except Exception as model_err:
                logger.warning("Model %s failed: %s", model_name, model_err)

        if response_text is None:
            logger.error("All Gemini models failed")
            return []

        events = json.loads(response_text)

        if not isinstance(events, list):
            logger.error("Gemini returned non-list response: %s", type(events))
            return []

        logger.info("Gemini extracted %d events", len(events))
        return events

    except Exception as e:
        logger.error("extract_events failed: %s", e)
        return []
