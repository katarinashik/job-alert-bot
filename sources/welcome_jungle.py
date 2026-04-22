"""
Welcome to the Jungle scraper via Algolia internal API.
App ID and search-only key are embedded in window.env on the public site — no auth required.
"""
import requests
from datetime import datetime, timedelta, date as date_type
from typing import Iterator
from notifier import Job

ALGOLIA_APP = "CSEKHVMS53"
ALGOLIA_KEY = "4bd8f6215d0cc52b26430765769e65a0"
INDEX = "wttj_jobs_production_fr"
ALGOLIA_URL = f"https://{ALGOLIA_APP}-dsn.algolia.net/1/indexes/{INDEX}/query"
JOB_URL = "https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP,
    "X-Algolia-API-Key": ALGOLIA_KEY,
    "Referer": "https://www.welcometothejungle.com/",
    "Origin": "https://www.welcometothejungle.com",
}


def fetch(
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    cutoff = int((datetime.utcnow() - timedelta(hours=max_age_hours)).timestamp())
    seen_ids: set[str] = set()

    for keyword in keywords:
        # Remote jobs anywhere (fulltime or hybrid)
        yield from _query(
            keyword, cutoff, seen_ids,
            extra_filters="(remote:fulltime OR remote:hybrid)",
            is_remote=True,
        )

        # Office jobs in target cities
        for loc in office_locations:
            yield from _query(
                keyword, cutoff, seen_ids,
                facet_filters=[f"offices.city:{loc}"],
                is_remote=False,
            )


def _query(
    keyword: str,
    cutoff: int,
    seen_ids: set,
    extra_filters: str = "",
    facet_filters: list = None,
    is_remote: bool = False,
) -> Iterator[Job]:
    base_filter = f"published_at_timestamp > {cutoff}"
    filters = f"{base_filter} AND {extra_filters}" if extra_filters else base_filter

    params = {
        "query": keyword,
        "hitsPerPage": 50,
        "filters": filters,
    }
    if facet_filters:
        params["facetFilters"] = [facet_filters]

    try:
        r = requests.post(ALGOLIA_URL, json=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])

        label = "remote" if is_remote else (facet_filters[0].split(":")[1] if facet_filters else "")
        if hits:
            print(f"[wttj] {len(hits)} results for '{keyword}' ({label})")

        for hit in hits:
            job_id = f"wttj_{hit.get('objectID', '')}"
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            org = hit.get("organization", {})
            org_slug = org.get("slug", "")
            slug = hit.get("slug", "")
            url = JOB_URL.format(org_slug=org_slug, slug=slug)

            offices = hit.get("offices", [])
            if offices:
                o = offices[0]
                parts = [o.get("city"), o.get("state"), o.get("country")]
                location = ", ".join(p for p in parts if p)
            else:
                location = "France"

            date_str = hit.get("published_at", "")
            try:
                date_posted = date_type.fromisoformat(date_str[:10]) if date_str else None
            except ValueError:
                date_posted = None

            sal_min = hit.get("salary_minimum")
            sal_max = hit.get("salary_maximum")
            sal_currency = hit.get("salary_currency", "EUR")
            sal_period = hit.get("salary_period", "")
            salary = None
            if sal_min and sal_max and sal_min != sal_max:
                salary = f"{int(sal_min):,}–{int(sal_max):,} {sal_currency}/{sal_period}"
            elif sal_min:
                salary = f"From {int(sal_min):,} {sal_currency}/{sal_period}"

            # Map numeric experience level to a label is_valid_experience can filter
            exp = hit.get("experience_level_minimum")
            exp_label = None
            if exp is not None and exp >= 5:
                exp_label = "mid-senior level"

            yield Job(
                id=job_id,
                title=hit.get("name", ""),
                company=org.get("name", "N/A"),
                location=location,
                url=url,
                salary=salary,
                source="Welcome to the Jungle",
                remote=is_remote or hit.get("has_remote", False),
                date_posted=date_posted,
                experience_level=exp_label,
            )
    except Exception as e:
        print(f"[wttj] error for '{keyword}': {e}")
