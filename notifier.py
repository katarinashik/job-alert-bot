import requests
from dataclasses import dataclass
from typing import Optional
from datetime import date


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


# map LinkedIn job_level values to short French labels
LEVEL_LABELS = {
    "entry level": "Débutant / Junior",
    "associate": "Junior / 1-3 ans",
    "mid-senior level": "Intermédiaire / 2-5 ans",
    "director": None,
    "executive": None,
}


def send(token: str, chat_id: str, job: Job) -> None:
    lines = [f"*{_esc(job.title)}*", f"🏢 {_esc(job.company)}"]

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

    if job.date_posted:
        lines.append(f"📅 {job.date_posted.strftime('%d %b %Y')}")

    if job.source:
        lines.append(f"📌 {job.source}")

    lines.append(f"🔗 [Voir l'offre]({job.url})")

    text = "\n".join(lines)

    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=10,
    ).raise_for_status()


def _esc(text: str) -> str:
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
