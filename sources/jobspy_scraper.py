from typing import Iterator
from datetime import date
from notifier import Job

OFFICE_SEARCH_LOCATIONS = {
    "Montpellier": "Montpellier, France",
    "Lyon": "Lyon, France",
}
REMOTE_LOCATION = "France"


def fetch(
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("[jobspy] not installed, skipping")
        return

    seen_ids: set[str] = set()
    locations_to_search = [REMOTE_LOCATION] + [
        OFFICE_SEARCH_LOCATIONS[loc]
        for loc in office_locations
        if loc in OFFICE_SEARCH_LOCATIONS
    ]

    for keyword in keywords:
        for location in locations_to_search:
            is_remote_search = location == REMOTE_LOCATION
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed"],
                    search_term=keyword,
                    location=location,
                    results_wanted=25,
                    hours_old=max_age_hours,
                    country_indeed="France",
                    linkedin_fetch_description=False,
                    verbose=0,
                )
                if df is None or df.empty:
                    continue
                for _, row in df.iterrows():
                    job_id = f"spy_{row.get('id', '')}_{row.get('site', '')}"
                    if not row.get("id") or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    location_str = _location_str(row)
                    remote = is_remote_search or str(row.get("job_type", "")).lower() == "remote"

                    dp = row.get("date_posted")
                    date_posted = dp.date() if hasattr(dp, "date") else (dp if isinstance(dp, date) else None)

                    yield Job(
                        id=job_id,
                        title=str(row.get("title", "")),
                        company=str(row.get("company", "N/A")),
                        location=location_str,
                        url=str(row.get("job_url", "")),
                        salary=_salary_str(row),
                        source=str(row.get("site", "")).capitalize(),
                        remote=remote,
                        date_posted=date_posted,
                    )
            except Exception as e:
                print(f"[jobspy] {keyword} @ {location}: {e}")


def _location_str(row) -> str:
    parts = [row.get("city"), row.get("country")]
    return ", ".join(str(p) for p in parts if p and str(p) != "nan")


def _salary_str(row) -> str | None:
    lo = row.get("min_amount")
    hi = row.get("max_amount")
    currency = row.get("currency", "€")
    interval = row.get("interval", "")
    if lo and hi:
        return f"{int(lo):,}–{int(hi):,} {currency}/{interval}"
    if lo:
        return f"From {int(lo):,} {currency}/{interval}"
    return None
