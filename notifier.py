import requests
from dataclasses import dataclass
from typing import Optional
from datetime import date

MONTHS_FR = ["jan.", "fév.", "mar.", "avr.", "mai", "juin",
             "juil.", "août", "sep.", "oct.", "nov.", "déc."]


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    salary: Optional[str] = None
    source: str = ""
    remote: bool = False
    date_posted: Optional[date] = None
    experience_level: Optional[str] = None
    description: Optional[str] = None
    company_size: Optional[str] = None


# map LinkedIn job_level values to short French labels
LEVEL_LABELS = {
    "entry level": "Junior (0-2 ans)",
    "associate": "Junior / 1-3 ans",
    "mid-senior level": "2-5 ans d'expérience",
    "director": None,
    "executive": None,
}

# Skills to detect in description — longer/more specific patterns first
# Each entry: (search_string, display_name)
# search_string is matched against " {description.lower()} " (padded with spaces)
SKILL_PATTERNS = [
    # Multi-word first (most specific)
    ("looker studio",        "Looker Studio"),
    ("google data studio",   "Google Data Studio"),
    ("google analytics",     "Google Analytics"),
    ("google sheets",        "Google Sheets"),
    ("power bi",             "Power BI"),
    ("qlik sense",           "QlikSense"),
    ("qlik view",            "QlikView"),
    ("big query",            "BigQuery"),
    ("bigquery",             "BigQuery"),
    ("apache spark",         "Spark"),
    ("apache airflow",       "Airflow"),
    # Single-word (padded so "sql" won't match "mysql" twice etc.)
    (" postgresql ",         "PostgreSQL"),
    (" mysql ",              "MySQL"),
    (" snowflake ",          "Snowflake"),
    (" databricks ",         "Databricks"),
    (" python ",             "Python"),
    (" sql ",                "SQL"),
    (" excel ",              "Excel"),
    (" tableau ",            "Tableau"),
    (" looker ",             "Looker"),
    (" qlik ",               "Qlik"),
    (" metabase ",           "Metabase"),
    (" salesforce ",         "Salesforce"),
    (" hubspot ",            "HubSpot"),
    (" vba ",                "VBA"),
    (" sas ",                "SAS"),
    (" spss ",               "SPSS"),
    (" airflow ",            "Airflow"),
    (" spark ",              "Spark"),
    (" dbt ",                "dbt"),
    (" aws ",                "AWS"),
    (" gcp ",                "GCP"),
    (" azure ",              "Azure"),
    (" jira ",               "Jira"),
    (" confluence ",         "Confluence"),
    (" amplitude ",          "Amplitude"),
    (" mixpanel ",           "Mixpanel"),
    (" pandas ",             "pandas"),
    (" hadoop ",             "Hadoop"),
    (" powerpoint ",         "PowerPoint"),
    (" r ",                  "R"),       # kept last — short pattern, catches "R" skills
]


def extract_skills(description: str) -> list[str]:
    """Extract known tool/skill mentions from job description text."""
    if not description:
        return []
    import re
    # Replace punctuation with spaces so "Python," and "SQL." still match
    clean = re.sub(r"[^\w\s]", " ", description.lower())
    padded = f" {clean} "
    seen: set[str] = set()
    found: list[str] = []
    for pattern, display in SKILL_PATTERNS:
        if display in seen:
            continue
        if pattern in padded:
            seen.add(display)
            found.append(display)
        if len(found) >= 7:
            break
    # Remove skills that are substrings of a more specific skill already found
    # e.g. drop "Looker" if "Looker Studio" is present
    return [s for s in found if not any(s != o and s in o for o in found)]


def _stars(job_score: int) -> str:
    if job_score <= 0:
        return ""
    if job_score == 1:
        return "⭐ "
    if job_score == 2:
        return "⭐⭐ "
    return "⭐⭐⭐ "


def send(token: str, chat_id: str, job: Job, job_score: int = 0) -> None:
    stars = _stars(job_score)
    company_line = f"🏢 {_esc(job.company)}"
    if job.company_size:
        company_line += f"  👥 {_esc(job.company_size)}"
    lines = [f"{stars}*{_esc(job.title)}*", company_line]

    if job.location:
        lines.append(f"📍 {_esc(job.location)}")
    if job.remote:
        lines.append("🌍 Remote / Télétravail")

    level_label = LEVEL_LABELS.get((job.experience_level or "").lower())
    if level_label:
        lines.append(f"👤 {level_label}")
    elif job.experience_level and job.experience_level.lower() not in LEVEL_LABELS:
        lines.append(f"👤 {_esc(job.experience_level)}")

    if job.salary:
        lines.append(f"💰 {_esc(job.salary)}")

    # Skills extracted from description
    skills = extract_skills(job.description or "")
    if skills:
        lines.append(f"🛠 {' · '.join(skills)}")

    if job.date_posted:
        d = job.date_posted
        lines.append(f"📅 {d.day} {MONTHS_FR[d.month - 1]} {d.year}")

    if job.source:
        lines.append(f"📌 {job.source}")

    lines.append(f"🔗 [Voir l'offre]({job.url})")

    text = "\n".join(lines)

    # Inline action buttons — callback data: "action|job_id"
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Postulée",     "callback_data": f"applied|{job.id}"},
            {"text": "💾 Sauvegarder", "callback_data": f"save|{job.id}"},
            {"text": "❌ Ignorer",      "callback_data": f"ignore|{job.id}"},
        ]]
    }

    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "reply_markup": keyboard,
        },
        timeout=10,
    ).raise_for_status()


def _esc(text: str) -> str:
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
