import logging
from typing import List
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days, parse_relative_time

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn using the public guest jobs API (no auth required)."""

    GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def scrape(self) -> List[Job]:
        jobs = []
        for role in self.roles:
            jobs.extend(self._scrape_role(role))
            self._delay(2.0, 4.0)
        return jobs

    def _scrape_role(self, role: str) -> List[Job]:
        role_jobs = []
        query = quote_plus(role)
        loc_encoded = quote_plus(self.location)
        url = (
            f"{self.GUEST_API}"
            f"?keywords={query}"
            f"&location={loc_encoded}"
            f"&f_TPR=r86400"
            f"&start=0"
        )
        if self.job_type == "internship":
            url += "&f_E=1"  # Entry level / internship
        elif self.job_type == "job":
            url += "&f_E=2,3"  # Associate + Mid-Senior

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[LinkedIn] Failed to fetch: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.find_all("li")

        for item in items:
            try:
                title_el = item.find("h3")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                link_el = item.find("a", href=True)
                if not link_el:
                    continue
                link = link_el["href"]
                if "linkedin.com/jobs/view" not in link:
                    continue

                company_el = item.find("h4")
                company = company_el.get_text(strip=True) if company_el else ""

                location = self.location
                loc_parts = item.find_all(string=True)
                for part in loc_parts:
                    text = part.strip()
                    if "," in text and len(text) < 50 and text != title and text != company:
                        location = text
                        break

                time_el = item.find("time")
                posted = None
                if time_el:
                    time_text = time_el.get_text(strip=True)
                    posted = parse_relative_time(time_text)
                    if not posted and time_el.get("datetime"):
                        try:
                            posted = datetime.fromisoformat(time_el["datetime"])
                        except (ValueError, TypeError):
                            pass

                if not is_within_days(posted, self.max_age_days):
                    continue

                matched_role = self._match_role(title)

                role_jobs.append(Job(
                    title=title,
                    company=company,
                    location=location,
                    url=link,
                    source="LinkedIn",
                    matched_role=matched_role or role,
                    posted_date=posted,
                ))
            except Exception as e:
                logger.debug(f"[LinkedIn] Error parsing item: {e}")
                continue

        logger.info(f"[LinkedIn] Found {len(role_jobs)} jobs for '{role}'")
        return role_jobs
