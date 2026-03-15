# jobs.py
import logging

logger = logging.getLogger(__name__)

def scrape_jobs(companies: list) -> list:
    """Scrape sales job listings from sponsoring/speaking companies.

    Args:
        companies: list of company name strings

    Returns:
        list of job dicts with title, company, url, description fields
    """
    # Phase 2: implement job scraping (LinkedIn, Greenhouse, Lever, etc.)
    logger.info("jobs: stub — returning empty list for %d companies", len(companies))
    return []
