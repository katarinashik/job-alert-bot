import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "seen_jobs.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute(
        "CREATE TABLE IF NOT EXISTS seen_jobs (id TEXT PRIMARY KEY, seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    c.commit()
    return c


def is_new(job_id: str) -> bool:
    with _conn() as c:
        row = c.execute("SELECT 1 FROM seen_jobs WHERE id = ?", (job_id,)).fetchone()
        return row is None


def mark_seen(job_id: str) -> None:
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO seen_jobs (id) VALUES (?)", (job_id,))
        c.commit()


def cleanup_old(days: int = 30) -> None:
    with _conn() as c:
        c.execute(
            "DELETE FROM seen_jobs WHERE seen_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        c.commit()
