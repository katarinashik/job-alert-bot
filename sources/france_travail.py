import requests
from datetime import datetime, timedelta
from typing import Iterator
from notifier import Job

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
JOB_URL = "https://candidat.francetravail.fr/offres/recherche/detail/{id}"

MONTPELLIER_CODE = "34172"
LYON_CODE = "69123"
DISTANCE_KM = 30


def _get_token(client_id: str, client_secret: str) -> str:
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch(
    client_id: str,
    client_secret: str,
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    if not client_id or not client_secret:
        return

    try:
        token = _get_token(client_id, client_secret)
    except Exception as e:
        print(f"[france_travail] auth failed: {e}")
        return
    headers = {"Authorization": f"Bearer {token}"}
    min_date = (datetime.utcnow() - timedelta(hours=max_age_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    commune_codes = []
    if "Montpellier" in office_locations:
        commune_codes.append(MONTPELLIER_CODE)
    if "Lyon" in office_locations:
        commune_codes.append(LYON_CODE)

    seen_ids: set[str] = set()

    for keyword in keywords:
        # remote (télétravail) anywhere in France
        params_remote = {
            "motsCles": keyword,
            "experienceExigence": "D",  # débutant
            "modeSelectionNaf": "INCLUS",
            "tempsPlein": True,
            "minCreationDate": min_date,
            "range": "0-49",
        }
        yield from _query(headers, params_remote, seen_ids, remote=True)

        # office jobs near Montpellier / Lyon
        for code in commune_codes:
            params_office = {
                "motsCles": keyword,
                "experienceExigence": "D",
                "commune": code,
                "distance": DISTANCE_KM,
                "minCreationDate": min_date,
                "range": "0-49",
            }
            yield from _query(headers, params_office, seen_ids, remote=False)


def _query(
    headers: dict, params: dict, seen_ids: set, remote: bool
) -> Iterator[Job]:
    try:
        r = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)
        if r.status_code == 204:
            return
        r.raise_for_status()
        for item in r.json().get("resultats", []):
            job_id = f"ft_{item['id']}"
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            salaire = item.get("salaire", {})
            salary_str = salaire.get("libelle") or None

            lieu = item.get("lieuTravail", {})
            location = lieu.get("libelle", "France")

            is_remote = remote or "télétravail" in item.get("description", "").lower()

            yield Job(
                id=job_id,
                title=item.get("intitule", ""),
                company=item.get("entreprise", {}).get("nom", "N/A"),
                location=location,
                url=JOB_URL.format(id=item["id"]),
                salary=salary_str,
                source="France Travail",
                remote=is_remote,
            )
    except Exception as e:
        print(f"[france_travail] error: {e}")
