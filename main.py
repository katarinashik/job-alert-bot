import os
import sys
import time
import config
import storage
import notifier
from sources import france_travail, jobspy_scraper, welcome_jungle


def run() -> None:
    token = os.environ.get("TELEGRAM_TOKEN", config.TELEGRAM_TOKEN)
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", config.TELEGRAM_CHAT_ID)
    ft_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID", config.FRANCE_TRAVAIL_CLIENT_ID)
    ft_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET", config.FRANCE_TRAVAIL_CLIENT_SECRET)

    if not chat_id or chat_id == "YOUR_CHAT_ID":
        print("ERROR: set TELEGRAM_CHAT_ID")
        sys.exit(1)

    storage.cleanup_old(days=30)

    sources = [
        france_travail.fetch(
            ft_id, ft_secret,
            config.SEARCH_KEYWORDS,
            config.OFFICE_LOCATIONS,
            config.MAX_JOB_AGE_HOURS,
        ),
        jobspy_scraper.fetch(
            config.SEARCH_KEYWORDS,
            config.OFFICE_LOCATIONS,
            config.MAX_JOB_AGE_HOURS,
        ),
        welcome_jungle.fetch(
            config.SEARCH_KEYWORDS,
            config.OFFICE_LOCATIONS,
            config.MAX_JOB_AGE_HOURS,
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
                time.sleep(0.5)  # respect Telegram rate limit
            except Exception as e:
                print(f"[notify] failed for {job.id}: {e}")

    print(f"Done. Sent {sent} new job alert(s).")


if __name__ == "__main__":
    run()
