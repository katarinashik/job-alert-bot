import requests
from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str        # city / region
    url: str
    salary: Optional[str] = None
    source: str = ""
    remote: bool = False
    date_posted: Optional[date] = None
    experience_level: Optional[str] = None  # e.g. "Entry level", "Mid-Senior"


def send(token: str, chat_id: str, job: Job) -> None:
    lines = [f"🆕 *{_esc(job.title)}*", f"🏢 {_esc(job.company)}"]

    # always show city, then remote badge if applicable
    if job.location:
        lines.append(f"📍 {_esc(job.location)}")
    if job.remote:
        lines.append("🌍 Remote / Télétravail")

    if job.salary:
        lines.append(f"💰 {_esc(job.salary)}")
    if job.date_posted:
        lines.append(f"📅 {job.date_posted.strftime('%d %b %Y')}")

    source_tag = f"_{job.source}_" if job.source else ""
    lines.append(f"🔗 [Voir l'offre →]({job.url})  {source_tag}")

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
