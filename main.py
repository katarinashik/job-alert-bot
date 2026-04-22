import os
import sys
import time
import settings
import storage
import notifier
from sources import france_travail, jobspy_scraper, welcome_jungle


def run() -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    ft_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID", "")
    ft_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET", "")

    # fallback to local config.py if it exists (for local testing)
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

    storage.cleanup_old(days=30)

    sources = [
        france_travail.fetch(
            ft_id, ft_secret,
            settings.SEARCH_KEYWORDS,
            settings.OFFICE_LOCATIONS,
            settings.MAX_JOB_AGE_HOURS,
        ),
        jobspy_scraper.fetch(
            settings.SEARCH_KEYWORDS,
            settings.OFFICE_LOCATIONS,
            settings.MAX_JOB_AGE_HOURS,
        ),
        welcome_jungle.fetch(
            settings.SEARCH_KEYWORDS,
            settings.OFFICE_LOCATIONS,
            settings.MAX_JOB_AGE_HOURS,
        ),
    ]

    sent = 0
    for source in sources:
        for job in source:
            if not storage.is_new(job.id):
                continue
            try:
                notifier.send(token, chat_id, job)
                storage.mark_seen(job.id)
                sent += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"[notify] failed for {job.id}: {e}")

    print(f"Done. Sent {sent} new job alert(s).")


if __name__ == "__main__":
    run()
