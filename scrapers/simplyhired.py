import logging
from typing import List
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days, parse_relative_time

logger = logging.getLogger(__name__)


class SimplyHiredScraper(BaseScraper):
    """Scraper for simplyhired.com — US-focused job search."""

    BASE_URL = "https://www.simplyhired.com"

    def scrape(self) -> List[Job]:
        jobs = []
        for role in self.roles:
            jobs.extend(self._scrape_role(role))
            self._delay()
        return jobs

    def _scrape_role(self, role: str) -> List[Job]:
        role_jobs = []
        query = quote_plus(role)
        loc_encoded = quote_plus(self.location)
        type_param = f"&t={self.job_type}" if self.job_type != "all" else ""
        url = f"{self.BASE_URL}/search?q={query}&l={loc_encoded}{type_param}&fdb=1"

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[SimplyHired] Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        cards = soup.select("article[data-jobkey], div.SerpJob, li.SerpJob-jobCard")
        if not cards:
            cards = soup.select("div[data-testid='searchSerpJob'], div.jobposting")
        if not cards:
            cards = soup.select("li[data-jobkey], div[data-job-id]")

        for card in cards:
            try:
                title_el = card.find(["h2", "h3", "h4", "a"], class_=lambda c: c and "title" in c.lower() if c else False)
                if not title_el:
                    title_el = card.find(["h2", "h3", "h4"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)

                link_el = card.find("a", href=True)
                link = link_el["href"] if link_el else ""
                if not link:
                    continue
                if not link.startswith("http"):
                    link = f"{self.BASE_URL}{link}"

                matched_role = self._match_role(title)

                company = ""
                company_el = card.find(class_=lambda c: c and "company" in c.lower() if c else False)
                if not company_el:
                    company_el = card.find("span", {"data-testid": "companyName"})
                if company_el:
                    company = company_el.get_text(strip=True)

                location = self.location
                loc_el = card.find(class_=lambda c: c and "location" in c.lower() if c else False)
                if not loc_el:
                    loc_el = card.find("span", {"data-testid": "searchSerpJobLocation"})
                if loc_el:
                    location = loc_el.get_text(strip=True)

                description = ""
                desc_el = card.find(class_=lambda c: c and ("snippet" in c.lower() or "description" in c.lower()) if c else False)
                if not desc_el:
                    desc_el = card.find("p")
                if desc_el:
                    description = desc_el.get_text(strip=True)

                posted = None
                date_el = card.find(class_=lambda c: c and "date" in c.lower() if c else False)
                if not date_el:
                    date_el = card.find("time")
                if date_el:
                    posted = parse_relative_time(date_el.get_text(strip=True))

                if not is_within_days(posted, self.max_age_days):
                    continue

                role_jobs.append(Job(
                    title=title,
                    company=company,
                    location=location,
                    url=link,
                    source="SimplyHired",
                    matched_role=matched_role or role,
                    posted_date=posted,
                    description=description,
                ))
            except Exception as e:
                logger.debug(f"[SimplyHired] Error parsing card: {e}")
                continue

        logger.info(f"[SimplyHired] Found {len(role_jobs)} jobs for '{role}'")
        return role_jobs
