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
