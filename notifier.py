import requests
from dataclasses import dataclass, field
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


def send(token: str, chat_id: str, job: Job) -> None:
    remote_tag = "🌍 Remote" if job.remote else f"📍 {job.location}"
    salary_line = f"\n💰 {job.salary}" if job.salary else ""
    source_tag = f" · {job.source}" if job.source else ""
    date_line = f"\n📅 {job.date_posted.strftime('%d %b %Y')}" if job.date_posted else ""

    text = (
        f"🆕 *{_esc(job.title)}*\n"
        f"🏢 {_esc(job.company)}\n"
        f"{remote_tag}{salary_line}{date_line}\n"
        f"🔗 [Voir l'offre →]({job.url})"
        f"\n_{source_tag}_"
    )

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
