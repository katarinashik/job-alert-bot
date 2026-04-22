"""
APEC (Association Pour l'Emploi des Cadres) scraper.
Targets junior/débutant positions in data analytics for France.
"""
import requests
from typing import Iterator
from notifier import Job

SEARCH_URL = "https://www.apec.fr/cms/webservices/rechercheOffre/summary"
JOB_URL = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/{id}"

MONTPELLIER_CODE = 105769  # APEC location code for Montpellier
LYON_CODE = 105707          # APEC location code for Lyon

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.apec.fr/",
}


def fetch(
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    seen_ids: set[str] = set()

    lieu_codes = []
    if "Montpellier" in office_locations:
        lieu_codes.append(MONTPELLIER_CODE)
    if "Lyon" in office_locations:
        lieu_codes.append(LYON_CODE)

    # search remote + office locations
    location_params = [{}]  # {} = all France (includes remote)
    for code in lieu_codes:
        location_params.append({"lieu": [code], "rayonRecherche": 30})

    for keyword in keywords:
        for loc_params in location_params:
            try:
                payload = {
                    "motsCles": keyword,
                    "niveauxExperience": [1],  # 1 = débutant (0-1 year)
                    "nbResultatsParPage": 50,
                    "numeroPage": 0,
                    **loc_params,
                }
                r = requests.post(
                    SEARCH_URL,
                    json=payload,
                    headers=HEADERS,
                    timeout=15,
                )
                if r.status_code != 200:
                    continue
                data = r.json()
                for item in data.get("resultats", []):
                    job_id = f"apec_{item.get('numOffre', '')}"
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    lieu = item.get("lieu", {})
                    location = lieu.get("libelle", "France")
                    is_remote = "télétravail" in item.get("texte", "").lower()

                    salary_info = item.get("salaireLibelle") or None

                    yield Job(
                        id=job_id,
                        title=item.get("intitule", ""),
                        company=item.get("nomEntreprise", "N/A"),
                        location=location,
                        url=JOB_URL.format(id=item.get("numOffre", "")),
                        salary=salary_info,
                        source="APEC",
                        remote=is_remote,
                    )
            except Exception as e:
                print(f"[apec] {keyword}: {e}")
