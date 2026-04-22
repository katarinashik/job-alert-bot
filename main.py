import os
import sys
import time
import settings
import storage
import notifier
from filter import is_relevant, score
from telegram_commands import process_commands
from sources import france_travail, jobspy_scraper, welcome_jungle, apec


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

    # check for /pause /resume /status before doing anything
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

    # collect, filter, score
    candidates: list[tuple[int, notifier.Job]] = []
    skipped = 0

    for source in sources:
        for job in source:
            if not is_relevant(job.title, job.company):
                skipped += 1
                print(f"[filter] skipped: {job.title} @ {job.company}")
                continue
            if not storage.is_new(job.id, job.title, job.company):
                continue
            candidates.append((score(job.title), job))

    # send highest-scored first
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

    print(f"Done. Sent {sent} alert(s), filtered {skipped} irrelevant.")


if __name__ == "__main__":
    run()
