import os
import sys
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import settings
import storage
import notifier
from filter import is_relevant, is_valid_location, is_valid_experience, score
from telegram_commands import process_commands, load_state, save_state

PARIS = ZoneInfo("Europe/Paris")

MONTHS_FR = ["jan", "fév", "mar", "avr", "mai", "juin",
             "juil", "août", "sep", "oct", "nov", "déc"]


def _update_daily_stats(state: dict, sent: int, irrelevant: int,
                        overqualified: int, wrong_location: int) -> None:
    today = datetime.now(PARIS).strftime("%Y-%m-%d")
    if state.get("daily_stats", {}).get("date") != today:
        state["daily_stats"] = {
            "date": today,
            "sent": 0,
            "irrelevant": 0,
            "overqualified": 0,
            "wrong_location": 0,
            "summary_sent": False,
        }
    ds = state["daily_stats"]
    ds["sent"] += sent
    ds["irrelevant"] += irrelevant
    ds["overqualified"] += overqualified
    ds["wrong_location"] += wrong_location


def _maybe_send_daily_summary(state: dict, token: str, chat_id: str) -> None:
    now = datetime.now(PARIS)
    ds = state.get("daily_stats", {})
    if now.hour < 20 or ds.get("summary_sent"):
        return

    date_str = ds.get("date", now.strftime("%Y-%m-%d"))
    sent = ds.get("sent", 0)
    irrelevant = ds.get("irrelevant", 0)
    overqualified = ds.get("overqualified", 0)
    wrong_location = ds.get("wrong_location", 0)
    total = sent + irrelevant + overqualified + wrong_location

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = f"{d.day} {MONTHS_FR[d.month - 1]} {d.year}"
    except Exception:
        date_label = date_str

    text = (
        f"📊 <b>Résumé du {date_label}</b>\n\n"
        f"✅ Alertes envoyées: <b>{sent}</b>\n"
        f"🔍 Vues au total: <b>{total}</b>\n\n"
        f"Filtrées:\n"
        f"  • Non pertinentes: {irrelevant}\n"
        f"  • Trop expérimenté: {overqualified}\n"
        f"  • Mauvaise localisation: {wrong_location}"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        ).raise_for_status()
        ds["summary_sent"] = True
        print("[summary] Daily report sent.")
    except Exception as e:
        print(f"[summary] Failed to send daily report: {e}")


def run() -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    ft_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID", "")
    ft_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET", "")

    try:
        import config
        token = token or config.TELEGRAM_TOKEN
        chat_id = chat_id or config.TELEGRAM_CHAT_ID
        ft_id = ft_id or config.FRANCE_TRAVAIL_CLIENT_ID
        ft_secret = ft_secret or config.FRANCE_TRAVAIL_CLIENT_SECRET
    except ImportError:
        pass

    if not token:
        print("ERROR: TELEGRAM_TOKEN not set")
        sys.exit(1)
    if not chat_id:
        print("ERROR: TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    should_run = process_commands(token, chat_id)
    if not should_run:
        print("Bot is paused. Send /resume in Telegram to restart.")
        return

    storage.cleanup_old(days=30)

    sources = [
        france_travail.fetch(ft_id, ft_secret,
            settings.SEARCH_KEYWORDS, settings.OFFICE_LOCATIONS, settings.MAX_JOB_AGE_HOURS),
        jobspy_scraper.fetch(
            settings.SEARCH_KEYWORDS, settings.OFFICE_LOCATIONS, settings.MAX_JOB_AGE_HOURS),
        welcome_jungle.fetch(
            settings.SEARCH_KEYWORDS, settings.OFFICE_LOCATIONS, settings.MAX_JOB_AGE_HOURS),
        apec.fetch(
            settings.SEARCH_KEYWORDS, settings.OFFICE_LOCATIONS, settings.MAX_JOB_AGE_HOURS),
    ]

    candidates: list[tuple[int, notifier.Job]] = []
    skipped_relevance = 0
    skipped_location = 0
    skipped_experience = 0

    for source in sources:
        for job in source:
            if not is_relevant(job.title, job.company):
                skipped_relevance += 1
                print(f"[filter:relevance] {job.title} @ {job.company}")
                continue
            if not is_valid_experience(job):
                skipped_experience += 1
                print(f"[filter:experience] {job.title} ({job.experience_level})")
                continue
            if not is_valid_location(job):
                skipped_location += 1
                print(f"[filter:location] {job.title} — {job.location} (not remote, not MTP/LYN)")
                continue
            if not storage.is_new(job.id, job.title, job.company):
                continue
            candidates.append((score(job.title), job))

    candidates.sort(key=lambda x: x[0], reverse=True)

    sent = 0
    for job_score, job in candidates:
        try:
            notifier.send(token, chat_id, job)
            storage.mark_seen(job.id, job.title, job.company)
            sent += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"[notify] failed for {job.id}: {e}")

    print(
        f"Done. Sent {sent} alert(s). "
        f"Filtered: {skipped_relevance} irrelevant, "
        f"{skipped_experience} overqualified, "
        f"{skipped_location} wrong location."
    )

    # Update daily stats and send evening summary if it's time
    state = load_state()
    _update_daily_stats(state, sent, skipped_relevance, skipped_experience, skipped_location)
    _maybe_send_daily_summary(state, token, chat_id)
    save_state(state)


if __name__ == "__main__":
    run()
