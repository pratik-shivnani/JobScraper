import logging
from typing import List, Dict
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days

logger = logging.getLogger(__name__)

ROLE_TO_PAGE: Dict[str, str] = {
    "Product Management Intern": "/pm-intern-list",
    "Technical Program Management Intern": "/pm-intern-list",
    "Technical Project Management Intern": "/pm-intern-list",
    "Data Analyst Intern": "/da-intern-list",
    "Business Analyst Intern": "/da-intern-list",
}


class InternListScraper(BaseScraper):
    """Scraper for intern-list.com using their dedicated category pages."""

    BASE_URL = "https://www.intern-list.com"

    def scrape(self) -> List[Job]:
        jobs = []
        scraped_pages = set()
        for role in self.roles:
            page_path = ROLE_TO_PAGE.get(role, "")
            if not page_path or page_path in scraped_pages:
                continue
            scraped_pages.add(page_path)
            jobs.extend(self._scrape_page(page_path))
            self._delay()
        return jobs

    def _scrape_page(self, page_path: str) -> List[Job]:
        page_jobs = []
        url = f"{self.BASE_URL}{page_path}"

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[InternList] Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.select("ul > li")

        for item in items:
            try:
                links = item.find_all("a", href=True)
                if not links:
                    continue

                main_link = None
                for a in links:
                    href = a.get("href", "")
                    if page_path.lstrip("/").split("/")[0] in href and href != "#":
                        main_link = a
                        break
                if not main_link:
                    continue

                href = main_link["href"]
                if not href.startswith("http"):
                    href = f"{self.BASE_URL}{href}"

                paragraphs = item.find_all("p")
                if len(paragraphs) < 2:
                    continue

                title = paragraphs[0].get_text(strip=True)
                date_str = paragraphs[1].get_text(strip=True)
                company = paragraphs[2].get_text(strip=True) if len(paragraphs) >= 3 else ""

                if not title or title == company:
                    continue

                posted_date = None
                try:
                    posted_date = datetime.strptime(date_str, "%B %d, %Y")
                except (ValueError, TypeError):
                    pass

                if not is_within_days(posted_date, self.max_age_days):
                    continue

                matched_role = self._match_role(title)

                page_jobs.append(Job(
                    title=title,
                    company=company,
                    location=self.location,
                    url=href,
                    source="intern-list.com",
                    matched_role=matched_role,
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[InternList] Error parsing item: {e}")
                continue

        logger.info(f"[InternList] Found {len(page_jobs)} jobs from {page_path}")
        return page_jobs
