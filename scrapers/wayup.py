import logging
from typing import List
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days, parse_relative_time

logger = logging.getLogger(__name__)


class WayUpScraper(BaseScraper):
    """Scraper for wayup.com — US student internships at big brands."""

    BASE_URL = "https://www.wayup.com"

    def scrape(self) -> List[Job]:
        jobs = []
        for role in self.roles:
            jobs.extend(self._scrape_role(role))
            self._delay()
        return jobs

    def _scrape_role(self, role: str) -> List[Job]:
        role_jobs = []
        query = quote_plus(role)
        path = "internships" if self.job_type == "internship" else "jobs"
        url = f"{self.BASE_URL}/s/{path}/?q={query}"

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[WayUp] Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        cards = soup.select("div[class*='job'], div[class*='listing'], article, div[class*='card']")
        if not cards:
            cards = soup.select("a[href*='/listing/']")

        for card in cards:
            try:
                if card.name == "a":
                    title = card.get_text(strip=True)
                    link = card.get("href", "")
                else:
                    title_el = card.find(["h2", "h3", "h4"])
                    if not title_el:
                        link_el = card.find("a", href=True)
                        if link_el and "/listing/" in link_el.get("href", ""):
                            title = link_el.get_text(strip=True)
                            link = link_el["href"]
                        else:
                            continue
                    else:
                        title = title_el.get_text(strip=True)
                        link_el = card.find("a", href=True)
                        link = link_el["href"] if link_el else ""

                if not title or not link:
                    continue

                if not link.startswith("http"):
                    link = f"{self.BASE_URL}{link}" if link.startswith("/") else f"{self.BASE_URL}/{link}"

                if "/s/internships/" in link and "/listing/" not in link:
                    continue

                matched_role = self._match_role(title)

                company = ""
                company_el = card.find(class_=lambda c: c and "company" in c.lower() if c else False)
                if company_el:
                    company = company_el.get_text(strip=True)

                location = self.location
                loc_el = card.find(class_=lambda c: c and "location" in c.lower() if c else False)
                if loc_el:
                    location = loc_el.get_text(strip=True)

                description = ""
                desc_el = card.find(class_=lambda c: c and ("description" in c.lower() or "snippet" in c.lower()) if c else False)
                if not desc_el:
                    desc_el = card.find("p")
                if desc_el:
                    description = desc_el.get_text(strip=True)

                role_jobs.append(Job(
                    title=title,
                    company=company,
                    location=location,
                    url=link,
                    source="WayUp",
                    matched_role=matched_role or role,
                    posted_date=datetime.now(),
                    description=description,
                ))
            except Exception as e:
                logger.debug(f"[WayUp] Error parsing card: {e}")
                continue

        logger.info(f"[WayUp] Found {len(role_jobs)} jobs for '{role}'")
        return role_jobs
