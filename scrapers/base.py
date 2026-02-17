import logging
import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    matched_role: str = ""
    posted_date: Optional[datetime] = None
    description: str = ""

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if not isinstance(other, Job):
            return False
        return self.url == other.url


def is_within_days(posted_date: Optional[datetime], days: int = 1) -> bool:
    """Check if a posted date is within the last N days."""
    if posted_date is None:
        return True
    cutoff = datetime.now() - timedelta(days=days)
    return posted_date >= cutoff


def parse_relative_time(text: str) -> Optional[datetime]:
    """Parse relative time strings like '5 hours ago', '1 day ago', '24 minutes ago'."""
    text = text.lower().strip()
    now = datetime.now()
    try:
        if "minute" in text:
            mins = int("".join(c for c in text.split("minute")[0] if c.isdigit()) or "0")
            return now - timedelta(minutes=mins)
        elif "hour" in text:
            hours = int("".join(c for c in text.split("hour")[0] if c.isdigit()) or "0")
            return now - timedelta(hours=hours)
        elif "day" in text:
            days = int("".join(c for c in text.split("day")[0] if c.isdigit()) or "0")
            return now - timedelta(days=days)
        elif "just now" in text or "moment" in text:
            return now
    except (ValueError, IndexError):
        pass
    return None


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    def __init__(self, roles: List[str], location: str = "United States", max_age_days: int = 1, job_type: str = "internship"):
        self.roles = roles
        self.location = location
        self.max_age_days = max_age_days
        self.job_type = job_type  # "internship", "job", or "all"
        self._ua = UserAgent()

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def _get_headers(self) -> dict:
        return {
            "User-Agent": self._ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    def _delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def _match_role(self, title: str) -> str:
        """Return the best matching role for a job title, or empty string if no match."""
        title_lower = title.lower()
        for role in self.roles:
            keywords = [w.lower() for w in role.split() if len(w) > 3]
            if all(kw in title_lower for kw in keywords):
                return role
            if sum(1 for kw in keywords if kw in title_lower) >= max(len(keywords) - 1, 1):
                return role
        return ""

    @abstractmethod
    def scrape(self) -> List[Job]:
        """Scrape job listings and return a list of Job objects."""
        pass

    def safe_scrape(self) -> List[Job]:
        """Wrapper around scrape() with error handling."""
        try:
            logger.info(f"[{self.name}] Starting scrape...")
            jobs = self.scrape()
            logger.info(f"[{self.name}] Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.error(f"[{self.name}] Scrape failed: {e}", exc_info=True)
            return []
