import logging
from typing import List
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days, parse_relative_time

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    """Scraper for glassdoor.com — US job listings with company reviews."""

    BASE_URL = "https://www.glassdoor.com"

    def scrape(self) -> List[Job]:
        jobs = []
        for role in self.roles:
            jobs.extend(self._scrape_role(role))
            self._delay(2.0, 5.0)
        return jobs

    def _scrape_role(self, role: str) -> List[Job]:
        role_jobs = []
        query = quote_plus(role)
        url = f"{self.BASE_URL}/Job/jobs.htm?sc.keyword={query}&locT=N&locId=1&fromAge=1"

        try:
            headers = self._get_headers()
            headers["Referer"] = "https://www.glassdoor.com/"
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[Glassdoor] Failed to fetch: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        cards = soup.select("li.react-job-listing, div[data-test='jobListing']")
        if not cards:
            cards = soup.select("ul.job-list li, div.jobCard")
        if not cards:
            cards = soup.select("li[data-jobid], li[data-id]")

        for card in cards:
            try:
                title_el = card.find("a", {"data-test": "job-link"})
                if not title_el:
                    title_el = card.find(["h2", "h3", "a"])
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link = title_el.get("href", "") if title_el.name == "a" else ""
                if not link:
                    link_el = card.find("a", href=True)
                    link = link_el["href"] if link_el else ""

                if not title or not link:
                    continue

                if not link.startswith("http"):
                    link = f"{self.BASE_URL}{link}"

                matched_role = self._match_role(title)

                company = ""
                company_el = card.find(class_=lambda c: c and "employer" in c.lower() if c else False)
                if not company_el:
                    company_el = card.find("div", {"data-test": "emp-name"})
                if company_el:
                    company = company_el.get_text(strip=True)

                location = "United States"
                loc_el = card.find(class_=lambda c: c and "location" in c.lower() if c else False)
                if not loc_el:
                    loc_el = card.find("span", {"data-test": "emp-location"})
                if loc_el:
                    location = loc_el.get_text(strip=True)

                description = ""
                desc_el = card.find(class_=lambda c: c and ("description" in c.lower() or "snippet" in c.lower()) if c else False)
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
                    source="Glassdoor",
                    matched_role=matched_role or role,
                    posted_date=posted,
                    description=description,
                ))
            except Exception as e:
                logger.debug(f"[Glassdoor] Error parsing card: {e}")
                continue

        logger.info(f"[Glassdoor] Found {len(role_jobs)} jobs for '{role}'")
        return role_jobs
