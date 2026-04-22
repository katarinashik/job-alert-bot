import requests
from typing import Iterator
from notifier import Job

# Welcome to the Jungle uses Algolia internally
ALGOLIA_APP = "RQKBSBE2WA"
ALGOLIA_KEY = "a6f0ac79ca2d3fc56b0d3a213b527b7b"  # public read-only search key
ALGOLIA_URL = f"https://{ALGOLIA_APP}-dsn.algolia.net/1/indexes/jobs/query"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP,
    "X-Algolia-API-Key": ALGOLIA_KEY,
    "Content-Type": "application/json",
}

JOB_URL = "https://www.welcometothejungle.com/fr/companies/{company_slug}/jobs/{job_slug}"


def fetch(
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    seen_ids: set[str] = set()
    location_filter = _build_location_filter(office_locations)

    for keyword in keywords:
        try:
            payload = {
                "query": keyword,
                "hitsPerPage": 50,
                "filters": location_filter,
                "attributesToRetrieve": [
                    "objectID", "name", "organization", "contract_type",
                    "salary", "office", "remote", "slug",
                ],
            }
            r = requests.post(ALGOLIA_URL, headers=HEADERS, json=payload, timeout=15)
            r.raise_for_status()
            for hit in r.json().get("hits", []):
                job_id = f"wtj_{hit['objectID']}"
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                org = hit.get("organization", {})
                office = hit.get("office", {})
                remote_policy = hit.get("remote", {}).get("enabled", False)
                company_slug = org.get("slug", "")
                job_slug = hit.get("slug", "")

                salary_info = hit.get("salary")
                salary_str = None
                if salary_info:
                    lo = salary_info.get("min")
                    hi = salary_info.get("max")
                    currency = salary_info.get("currency", "€")
                    if lo and hi:
                        salary_str = f"{lo:,}–{hi:,} {currency}/an"

                location = office.get("city") or "France"

                yield Job(
                    id=job_id,
                    title=hit.get("name", ""),
                    company=org.get("name", "N/A"),
                    location=location,
                    url=JOB_URL.format(company_slug=company_slug, job_slug=job_slug),
                    salary=salary_str,
                    source="Welcome to the Jungle",
                    remote=bool(remote_policy),
                )
        except Exception as e:
            print(f"[welcome_jungle] {keyword}: {e}")


def _build_location_filter(office_locations: list[str]) -> str:
    city_filters = [f'office.city:"{loc}"' for loc in office_locations]
    city_filters.append('remote.enabled:true')
    return " OR ".join(city_filters)
