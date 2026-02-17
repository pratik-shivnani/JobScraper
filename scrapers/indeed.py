import logging
from typing import List
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days, parse_relative_time

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    """Scraper for indeed.com — largest US job aggregator."""

    BASE_URL = "https://www.indeed.com"

    def scrape(self) -> List[Job]:
        jobs = []
        for role in self.roles:
            jobs.extend(self._scrape_role(role))
            self._delay(2.0, 4.0)
        return jobs

    def _scrape_role(self, role: str) -> List[Job]:
        role_jobs = []
        query = quote_plus(role)
        url = f"{self.BASE_URL}/jobs?q={query}&l=United+States&fromage=1&sort=date"

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[Indeed] Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        cards = soup.select("div.job_seen_beacon, div.jobsearch-ResultsList div.result")
        if not cards:
            cards = soup.select("div[data-jk], td.resultContent")
        if not cards:
            cards = soup.select("div.slider_container .slider_item")

        for card in cards:
            try:
                title_el = card.find("h2", class_="jobTitle")
                if not title_el:
                    title_el = card.find(["h2", "h3"])
                if not title_el:
                    continue

                title_link = title_el.find("a", href=True)
                if title_link:
                    title = title_link.get_text(strip=True)
                    link = title_link["href"]
                else:
                    title = title_el.get_text(strip=True)
                    link_el = card.find("a", href=True)
                    link = link_el["href"] if link_el else ""

                if not title or not link:
                    continue

                if not link.startswith("http"):
                    link = f"{self.BASE_URL}{link}"

                matched_role = self._match_role(title)

                company = ""
                company_el = card.find("span", {"data-testid": "company-name"})
                if not company_el:
                    company_el = card.find(class_=lambda c: c and "company" in c.lower() if c else False)
                if company_el:
                    company = company_el.get_text(strip=True)

                location = "United States"
                loc_el = card.find("div", {"data-testid": "text-location"})
                if not loc_el:
                    loc_el = card.find(class_=lambda c: c and "location" in c.lower() if c else False)
                if loc_el:
                    location = loc_el.get_text(strip=True)

                description = ""
                desc_el = card.find("div", class_="job-snippet")
                if not desc_el:
                    desc_el = card.find(class_=lambda c: c and "snippet" in c.lower() if c else False)
                if desc_el:
                    description = desc_el.get_text(strip=True)

                posted = None
                date_el = card.find("span", class_="date")
                if not date_el:
                    date_el = card.find(class_=lambda c: c and "date" in c.lower() if c else False)
                if date_el:
                    posted = parse_relative_time(date_el.get_text(strip=True))

                if not is_within_days(posted, self.max_age_days):
                    continue

                role_jobs.append(Job(
                    title=title,
                    company=company,
                    location=location,
                    url=link,
                    source="Indeed",
                    matched_role=matched_role or role,
                    posted_date=posted,
                    description=description,
                ))
            except Exception as e:
                logger.debug(f"[Indeed] Error parsing card: {e}")
                continue

        logger.info(f"[Indeed] Found {len(role_jobs)} jobs for '{role}'")
        return role_jobs
