import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from scrapers.base import Job

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "jobs.db"


class DedupStore:
    """SQLite-backed deduplication store for job URLs."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    source TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def _hash_url(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def filter_new(self, jobs: List[Job]) -> List[Job]:
        """Return only jobs that haven't been seen before, and mark them as seen."""
        new_jobs = []
        with sqlite3.connect(self.db_path) as conn:
            for job in jobs:
                url_hash = self._hash_url(job.url)
                row = conn.execute(
                    "SELECT 1 FROM seen_jobs WHERE url_hash = ?", (url_hash,)
                ).fetchone()
                if row is None:
                    new_jobs.append(job)
                    conn.execute(
                        "INSERT INTO seen_jobs (url_hash, url, title, source) VALUES (?, ?, ?, ?)",
                        (url_hash, job.url, job.title, job.source),
                    )
            conn.commit()

        logger.info(f"Dedup: {len(jobs)} total -> {len(new_jobs)} new jobs")
        return new_jobs

    def purge_old(self, days: int = 30):
        """Remove entries older than `days` to keep the DB small."""
        cutoff = datetime.now() - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            deleted = conn.execute(
                "DELETE FROM seen_jobs WHERE first_seen < ?", (cutoff.isoformat(),)
            ).rowcount
            conn.commit()
        if deleted:
            logger.info(f"Dedup: Purged {deleted} entries older than {days} days")
