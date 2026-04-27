import os
import sys
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import settings
import storage
import notifier
from filter import is_relevant, is_valid_location, is_valid_experience, is_valid_description, extract_exp_from_description, score
from telegram_commands import process_commands, load_state, save_state
from sources import france_travail, jobspy_scraper, welcome_jungle, apec

PARIS = ZoneInfo("Europe/Paris")

MONTHS_FR = ["jan", "fév", "mar", "avr", "mai", "juin",
             "juil", "août", "sep", "oct", "nov", "déc"]


# ── Digest mode ─────────────────────────────────────────────────────────────

def _should_send_digest(state: dict, period: str) -> bool:
    """True if it's time to send the morning (9h) or evening (18h) digest."""
    now = datetime.now(PARIS)
    today = now.strftime("%Y-%m-%d")
    threshold = 9 if period == "morning" else 18
    return now.hour >= threshold and state.get(f"digest_{period}_sent") != today


def _send_digest(token: str, chat_id: str, state: dict, period: str) -> None:
    rows = storage.get_pending_jobs()
    today = datetime.now(PARIS).strftime("%Y-%m-%d")
    state[f"digest_{period}_sent"] = today

    if not rows:
        return  # nothing queued — silently mark as sent

    label = "🌅 Digest du matin" if period == "morning" else "🌆 Digest du soir"
    n = len(rows)
    plural = "s" if n > 1 else ""
    lines = [f"*{label}* — {n} nouvelle{plural} offre{plural}\n"]

    for _, title, company, url, remote, job_score in rows:
        stars = notifier._stars(job_score)
        remote_icon = " 🌍" if remote else ""
        # Escape for Markdown
        t = title.replace("*", "").replace("[", "").replace("]", "")
        c = company.replace("*", "").replace("[", "").replace("]", "")
        lines.append(f"{stars}[{t} @ {c}]({url}){remote_icon}")

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "\n".join(lines),
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        ).raise_for_status()
        storage.clear_pending_jobs()
        print(f"[digest] {period} digest sent ({n} jobs).")
    except Exception as e:
        print(f"[digest] failed to send {period} digest: {e}")


# ── Weekly report ────────────────────────────────────────────────────────────

def _update_weekly_stats(state: dict, sent: int) -> None:
    now = datetime.now(PARIS)
    week_key = now.strftime("%G-W%V")  # ISO week
    if state.get("weekly_stats", {}).get("week") != week_key:
        state["weekly_stats"] = {"week": week_key, "jobs_sent": 0, "report_sent": False}
    state["weekly_stats"]["jobs_sent"] = state["weekly_stats"].get("jobs_sent", 0) + sent


def _maybe_send_weekly_report(state: dict, token: str, chat_id: str) -> None:
    now = datetime.now(PARIS)
    ws = state.get("weekly_stats", {})
    # Sunday = weekday 6, send at first run on or after 18:00
    if now.weekday() != 6 or now.hour < 18 or ws.get("report_sent"):
        return

    jobs_sent = ws.get("jobs_sent", 0)
    week_key = ws.get("week", now.strftime("%G-W%V"))

    applied_rows = storage.get_job_actions("applied")
    saved_rows = storage.get_job_actions("saved")
    cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    applied_week = sum(1 for r in applied_rows if r[4] and r[4][:10] >= cutoff)
    saved_week = sum(1 for r in saved_rows if r[4] and r[4][:10] >= cutoff)

    top = storage.get_top_companies(days=7)
    companies_text = ""
    if top:
        companies_text = "\n\n🏢 <b>Entreprises fréquentes:</b>\n"
        companies_text += "\n".join(f"  {i+1}. {c} ({n})" for i, (c, n) in enumerate(top))

    text = (
        f"📈 <b>Rapport de la semaine {week_key}</b>\n\n"
        f"🔔 Offres envoyées: <b>{jobs_sent}</b>\n"
        f"✅ Candidatures: <b>{applied_week}</b>\n"
        f"💾 Sauvegardées: <b>{saved_week}</b>"
        f"{companies_text}"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        ).raise_for_status()
        ws["report_sent"] = True
        print("[weekly] Weekly report sent.")
    except Exception as e:
        print(f"[weekly] Failed to send weekly report: {e}")


# ── Daily stats ──────────────────────────────────────────────────────────────

def _update_daily_stats(state: dict, sent: int, irrelevant: int,
                        overqualified: int, wrong_location: int,
                        spam: int = 0) -> None:
    today = datetime.now(PARIS).strftime("%Y-%m-%d")
    if state.get("daily_stats", {}).get("date") != today:
        state["daily_stats"] = {
            "date": today,
            "sent": 0,
            "irrelevant": 0,
            "overqualified": 0,
            "wrong_location": 0,
            "spam": 0,
            "summary_sent": False,
        }
    ds = state["daily_stats"]
    ds["sent"] += sent
    ds["irrelevant"] += irrelevant
    ds["overqualified"] += overqualified
    ds["wrong_location"] += wrong_location
    ds["spam"] = ds.get("spam", 0) + spam


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
    spam = ds.get("spam", 0)
    total = sent + irrelevant + overqualified + wrong_location + spam

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = f"{d.day} {MONTHS_FR[d.month - 1]} {d.year}"
    except Exception:
        date_label = date_str

    spam_line = f"  • Spam / doublon: {spam}\n" if spam else ""
    text = (
        f"📊 <b>Résumé du {date_label}</b>\n\n"
        f"✅ Alertes envoyées: <b>{sent}</b>\n"
        f"🔍 Vues au total: <b>{total}</b>\n\n"
        f"Filtrées:\n"
        f"  • Non pertinentes: {irrelevant}\n"
        f"  • Trop expérimenté: {overqualified}\n"
        f"  • Mauvaise localisation: {wrong_location}\n"
        f"{spam_line}"
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
    skipped_spam = 0
    seen_desc_hashes: set[str] = set()

    for source in sources:
        for job in source:
            if not is_relevant(job.title, job.company):
                skipped_relevance += 1
                print(f"[filter:relevance] {job.title} @ {job.company}")
                continue
            # Enrich experience_level from description text if not already set by the source
            if job.experience_level is None and job.description:
                _, label = extract_exp_from_description(job.description)
                if label:
                    job.experience_level = label
            if not is_valid_experience(job):
                skipped_experience += 1
                print(f"[filter:experience] {job.title} ({job.experience_level})")
                continue
            if not is_valid_location(job):
                skipped_location += 1
                print(f"[filter:location] {job.title} — {job.location} (not remote, not MTP/LYN)")
                continue
            if not is_valid_description(job, seen_desc_hashes):
                skipped_spam += 1
                print(f"[filter:spam] {job.title} @ {job.company} (short/duplicate description)")
                continue
            if not storage.is_new(job.id, job.title, job.company):
                continue
            candidates.append((score(job.title), job))

    candidates.sort(key=lambda x: x[0], reverse=True)

    state = load_state()
    digest_mode = state.get("digest_mode", False)
    sent = 0

    if digest_mode:
        # Queue jobs for next digest window instead of sending immediately
        for job_score, job in candidates:
            storage.add_pending_job(job.id, job.title, job.company, job.url,
                                    job.remote, job_score)
            storage.mark_seen(job.id, job.title, job.company)
            storage.store_sent_job(job.id, job.title, job.company, job.url)
            sent += 1
        if candidates:
            print(f"[digest] Queued {sent} job(s) for next digest.")
        # Send digest if it's time (morning or evening)
        for period in ("morning", "evening"):
            if _should_send_digest(state, period):
                _send_digest(token, chat_id, state, period)
    else:
        # Real-time mode: send each job immediately
        for job_score, job in candidates:
            try:
                notifier.send(token, chat_id, job, job_score)
                storage.mark_seen(job.id, job.title, job.company)
                storage.store_sent_job(job.id, job.title, job.company, job.url)
                sent += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"[notify] failed for {job.id}: {e}")

    print(
        f"Done. Sent {sent} alert(s). "
        f"Filtered: {skipped_relevance} irrelevant, "
        f"{skipped_experience} overqualified, "
        f"{skipped_location} wrong location, "
        f"{skipped_spam} spam/duplicate."
    )

    # Update stats and send reports if it's time
    _update_daily_stats(state, sent, skipped_relevance, skipped_experience,
                        skipped_location, skipped_spam)
    _update_weekly_stats(state, sent)
    _maybe_send_daily_summary(state, token, chat_id)
    _maybe_send_weekly_report(state, token, chat_id)
    save_state(state)


if __name__ == "__main__":
    run()
