"""
Welcome to the Jungle scraper via Algolia internal API.
STATUS: DISABLED — Algolia app ID needs to be updated.

To find the current key:
1. Open welcometothejungle.com in Chrome
2. Open DevTools → Network tab → search for "algolia"
3. Find a request to *.algolia.net — copy X-Algolia-Application-Id and X-Algolia-API-Key
4. Update ALGOLIA_APP and ALGOLIA_KEY below and re-enable
"""
from typing import Iterator
from notifier import Job

ALGOLIA_APP = ""   # update with current key from DevTools
ALGOLIA_KEY = ""   # update with current key from DevTools
ENABLED = bool(ALGOLIA_APP and ALGOLIA_KEY)


def fetch(
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    if not ENABLED:
        print("[welcome_jungle] disabled — update Algolia keys in sources/welcome_jungle.py")
        return
    yield from []
