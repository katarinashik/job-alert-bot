import requests
from dataclasses import dataclass
from typing import Optional


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


def send(token: str, chat_id: str, job: Job) -> None:
    remote_tag = "🌍 Remote" if job.remote else f"📍 {job.location}"
    salary_line = f"\n💰 {job.salary}" if job.salary else ""
    source_tag = f" · {job.source}" if job.source else ""

    text = (
        f"🆕 *{_esc(job.title)}*\n"
        f"🏢 {_esc(job.company)}\n"
        f"{remote_tag}{salary_line}\n"
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
