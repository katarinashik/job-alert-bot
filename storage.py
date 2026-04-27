import sqlite3
import re
import os

DB_PATH = os.environ.get("DB_PATH", "seen_jobs.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute(
        "CREATE TABLE IF NOT EXISTS seen_jobs "
        "(id TEXT PRIMARY KEY, seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS seen_fingerprints "
        "(fp TEXT PRIMARY KEY, seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    # Stores info about every job sent to Telegram (for button callbacks)
    c.execute(
        "CREATE TABLE IF NOT EXISTS sent_jobs "
        "(job_id TEXT PRIMARY KEY, title TEXT, company TEXT, url TEXT, "
        " sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    # Stores user actions: 'applied' or 'saved'
    c.execute(
        "CREATE TABLE IF NOT EXISTS job_actions "
        "(job_id TEXT PRIMARY KEY, action TEXT, "
        " actioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.commit()
    return c


def is_new(job_id: str, title: str, company: str) -> bool:
    fp = _fingerprint(title, company)
    with _conn() as c:
        if c.execute("SELECT 1 FROM seen_jobs WHERE id = ?", (job_id,)).fetchone():
            return False
        if c.execute("SELECT 1 FROM seen_fingerprints WHERE fp = ?", (fp,)).fetchone():
            return False
    return True


def mark_seen(job_id: str, title: str, company: str) -> None:
    fp = _fingerprint(title, company)
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO seen_jobs (id) VALUES (?)", (job_id,))
        c.execute("INSERT OR IGNORE INTO seen_fingerprints (fp) VALUES (?)", (fp,))
        c.commit()


def store_sent_job(job_id: str, title: str, company: str, url: str) -> None:
    """Remember every job sent to Telegram so button callbacks can look it up."""
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO sent_jobs (job_id, title, company, url) VALUES (?, ?, ?, ?)",
            (job_id, title, company, url),
        )
        c.commit()


def mark_job_action(job_id: str, action: str) -> tuple | None:
    """
    Record a user action ('applied' or 'saved') on a job.
    Returns (title, company, url) if the job was found, else None.
    """
    with _conn() as c:
        row = c.execute(
            "SELECT title, company, url FROM sent_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row:
            c.execute(
                "INSERT OR REPLACE INTO job_actions (job_id, action) VALUES (?, ?)",
                (job_id, action),
            )
            c.commit()
        return row


def remove_job_action(job_id: str) -> None:
    """Remove a saved/applied action (e.g. user unsaves a job)."""
    with _conn() as c:
        c.execute("DELETE FROM job_actions WHERE job_id = ?", (job_id,))
        c.commit()


def get_job_actions(action: str) -> list:
    """
    Return list of (job_id, title, company, url, actioned_at)
    for the given action ('applied' or 'saved'), newest first.
    """
    with _conn() as c:
        return c.execute(
            """SELECT ja.job_id, sj.title, sj.company, sj.url, ja.actioned_at
               FROM job_actions ja
               JOIN sent_jobs sj ON ja.job_id = sj.job_id
               WHERE ja.action = ?
               ORDER BY ja.actioned_at DESC""",
            (action,),
        ).fetchall()


def cleanup_old(days: int = 30) -> None:
    with _conn() as c:
        c.execute(
            "DELETE FROM seen_jobs WHERE seen_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        c.execute(
            "DELETE FROM seen_fingerprints WHERE seen_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        c.execute(
            "DELETE FROM sent_jobs WHERE sent_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        c.execute(
            """DELETE FROM job_actions WHERE job_id NOT IN
               (SELECT job_id FROM sent_jobs)""",
        )
        c.commit()


def _fingerprint(title: str, company: str) -> str:
    return _norm(title) + "|" + _norm(company)


def _norm(text: str) -> str:
    t = text.lower()
    # remove gender markers common in French job titles
    t = re.sub(r"\b(h/f|f/h|h/f/x|f/h/x|m/f|f/m)\b", "", t)
    # remove company legal forms
    t = re.sub(r"\b(sas|sarl|sa|sasu|snc|sci|eurl|gmbh|inc|ltd|llc|s\.a\.)\b", "", t)
    # remove punctuation and extra spaces
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t
