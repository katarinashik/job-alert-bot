"""
APEC (Association Pour l'Emploi des Cadres) scraper.
Targets junior/débutant positions in data analytics for France.
"""
import requests
from typing import Iterator
from notifier import Job

# APEC internal search API — tested working as of 2025
SEARCH_URL = "https://www.apec.fr/cms/webservices/rechercheOffre/summary"
JOB_URL = "https://www.apec.fr/candidat/recherche-emploi.html/emploi/{id}"

MONTPELLIER_CODE = 105769
LYON_CODE = 105707

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.apec.fr",
    "Referer": "https://www.apec.fr/candidat/recherche-emploi.html/emploi",
}

_diagnosed = False


def fetch(
    keywords: list[str],
    office_locations: list[str],
    max_age_hours: int,
) -> Iterator[Job]:
    global _diagnosed
    seen_ids: set[str] = set()

    lieu_codes = []
    if "Montpellier" in office_locations:
        lieu_codes.append(MONTPELLIER_CODE)
    if "Lyon" in office_locations:
        lieu_codes.append(LYON_CODE)

    location_params = [{}]
    for code in lieu_codes:
        location_params.append({"lieu": [code], "rayonRecherche": 30})

    for keyword in keywords[:2]:  # limit keywords for diagnosis
        for loc_params in location_params[:1]:
            try:
                payload = {
                    "motsCles": keyword,
                    "niveauxExperience": [1],
                    "nbResultatsParPage": 20,
                    "numeroPage": 0,
                    **loc_params,
                }
                r = requests.post(SEARCH_URL, json=payload, headers=HEADERS, timeout=15)

                if not _diagnosed:
                    print(f"[apec] status={r.status_code} for '{keyword}'")
                    if r.status_code != 200:
                        print(f"[apec] response: {r.text[:300]}")
                    else:
                        data = r.json()
                        total = data.get("totalCount", data.get("nbResultats", "?"))
                        print(f"[apec] OK — {total} results found")
                    _diagnosed = True

                if r.status_code != 200:
                    break

                data = r.json()
                for item in data.get("resultats", []):
                    job_id = f"apec_{item.get('numOffre', '')}"
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    lieu = item.get("lieu", {})
                    location = lieu.get("libelle", "France")
                    is_remote = "télétravail" in str(item.get("texte", "")).lower()

                    yield Job(
                        id=job_id,
                        title=item.get("intitule", ""),
                        company=item.get("nomEntreprise", "N/A"),
                        location=location,
                        url=JOB_URL.format(id=item.get("numOffre", "")),
                        salary=item.get("salaireLibelle") or None,
                        source="APEC",
                        remote=is_remote,
                    )

            except Exception as e:
                print(f"[apec] error for '{keyword}': {e}")
                break
