"""
APEC scraper — DISABLED.
APEC targets "cadres" (managers/executives, 3+ years experience).
Junior data analyst positions are almost never posted there.
Their search page is a JS SPA that requires a headless browser to render,
and their internal API requires authentication (401).
The bot already covers junior positions via France Travail, LinkedIn, Indeed, and WTTJ.
"""
from typing import Iterator
from notifier import Job


def fetch(keywords, office_locations, max_age_hours) -> Iterator[Job]:
    return
    yield
