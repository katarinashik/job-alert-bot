"""
APEC scraper — DISABLED.
APEC's internal API (/cms/webservices/rechercheOffre/summary) requires authentication (401).
Their public job search requires a logged-in session which can't be replicated in CI.
France Travail (official API) covers similar French cadre positions.
"""
from typing import Iterator
from notifier import Job


def fetch(keywords, office_locations, max_age_hours) -> Iterator[Job]:
    print("[apec] disabled — requires authentication, use France Travail instead")
    return
    yield  # make this a generator
