"""
Watched-company source — fetches ALL postings from the watchlist companies
(any role, not only analyst keywords), so the bot can alert on every job they
publish. Queries Welcome to the Jungle (Algolia) and LinkedIn/Indeed (jobspy)
by company name, then yields only jobs whose company actually matches the
watchlist (drops unrelated hits like road-construction jobs for "roads").
"""
import re
from typing import Iterator

from notifier import Job
from sources import welcome_jungle, jobspy_scraper


def _matches(company: str, watched: list[str]) -> bool:
    c = (company or "").lower()
    return any(re.search(rf"\b{re.escape(w)}\b", c) for w in watched)


def fetch(watched_companies: list[str], max_age_hours: int) -> Iterator[Job]:
    if not watched_companies:
        return

    # ── Welcome to the Jungle (Algolia full-text search by company name) ──
    try:
        from datetime import datetime, timedelta
        cutoff = int((datetime.utcnow() - timedelta(hours=max_age_hours)).timestamp())
        algolia_key = welcome_jungle._fetch_algolia_key()
        headers = {
            "X-Algolia-Application-Id": welcome_jungle.ALGOLIA_APP,
            "X-Algolia-API-Key": algolia_key,
            "Referer": "https://www.welcometothejungle.com/",
            "Origin": "https://www.welcometothejungle.com",
        }
        seen: set[str] = set()
        for name in watched_companies:
            for job in welcome_jungle._query(name, cutoff, seen, headers):
                if _matches(job.company, watched_companies):
                    print(f"[watched:wttj] {job.title} @ {job.company}")
                    yield job
    except Exception as e:
        print(f"[watched:wttj] error: {e}")

    # ── LinkedIn / Indeed (jobspy search by company name) ──
    try:
        from jobspy import scrape_jobs
    except ImportError:
        scrape_jobs = None
    if scrape_jobs is not None:
        seen_ids: set[str] = set()
        for name in watched_companies:
            try:
                for job in jobspy_scraper._scrape(
                    scrape_jobs, name, "France", max_age_hours,
                    seen_ids, is_remote_search=False,
                ):
                    if _matches(job.company, watched_companies):
                        print(f"[watched:jobspy] {job.title} @ {job.company}")
                        yield job
            except Exception as e:
                print(f"[watched:jobspy] {name}: {e}")
