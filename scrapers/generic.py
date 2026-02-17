import logging
import re
from typing import List
from datetime import datetime
from urllib.parse import urljoin, urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job, is_within_days, parse_relative_time

logger = logging.getLogger(__name__)

# Common job board URL patterns that indicate a listing link
JOB_LINK_PATTERNS = [
    r"/jobs?/",
    r"/positions?/",
    r"/careers?/",
    r"/openings?/",
    r"/listing/",
    r"/apply/",
    r"/job-detail",
    r"/job_detail",
    r"/requisition",
]
JOB_LINK_RE = re.compile("|".join(JOB_LINK_PATTERNS), re.IGNORECASE)

# Patterns to skip (navigation, login, etc.)
SKIP_PATTERNS = re.compile(
    r"(login|signin|sign-up|signup|register|about|contact|privacy|terms|faq|blog|press|#)",
    re.IGNORECASE,
)


class GenericScraper(BaseScraper):
    """
    A best-effort scraper that works with arbitrary job board URLs.

    Accepts a URL (e.g. https://boards.greenhouse.io/stripe) and tries to
    extract job listings by looking for common HTML patterns used by job boards.

    Supports two modes:
    1. Direct URL — scrapes the given page for job links
    2. Search URL — if the site has a search page, appends role as query param
    """

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.base_url = url.rstrip("/")
        parsed = urlparse(self.base_url)
        self.domain = parsed.netloc
        self.source_name = self.domain.replace("www.", "").split(".")[0].title()

    def scrape(self) -> List[Job]:
        jobs = []
        for role in self.roles:
            jobs.extend(self._scrape_role(role))
            self._delay(1.5, 3.0)
        return jobs

    def _scrape_role(self, role: str) -> List[Job]:
        role_jobs = []

        # Try the base URL first (many job boards list all jobs on one page)
        urls_to_try = [self.base_url]

        # Also try appending common search patterns
        query = quote_plus(role)
        urls_to_try.extend([
            f"{self.base_url}?q={query}",
            f"{self.base_url}?query={query}",
            f"{self.base_url}?search={query}",
            f"{self.base_url}?keywords={query}",
        ])

        seen_urls = set()

        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=self._get_headers(), timeout=15)
                if resp.status_code != 200:
                    continue
            except requests.RequestException as e:
                logger.debug(f"[Generic:{self.domain}] Failed to fetch {url}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            page_jobs = self._extract_jobs_from_page(soup, url, role)

            for job in page_jobs:
                if job.url not in seen_urls:
                    seen_urls.add(job.url)
                    role_jobs.append(job)

            if role_jobs:
                break  # Found jobs, no need to try other URL patterns

        logger.info(f"[Generic:{self.domain}] Found {len(role_jobs)} jobs for '{role}'")
        return role_jobs

    def _extract_jobs_from_page(self, soup: BeautifulSoup, page_url: str, role: str) -> List[Job]:
        """Extract job listings from a page using multiple strategies."""
        jobs = []

        # Strategy 1: Look for structured job cards (common patterns)
        jobs = self._try_structured_cards(soup, page_url, role)
        if jobs:
            return jobs

        # Strategy 2: Look for links that match job URL patterns
        jobs = self._try_job_links(soup, page_url, role)
        if jobs:
            return jobs

        # Strategy 3: Look for any list items with links (fallback)
        jobs = self._try_list_items(soup, page_url, role)
        return jobs

    def _try_structured_cards(self, soup: BeautifulSoup, page_url: str, role: str) -> List[Job]:
        """Look for common job card patterns used by ATS platforms."""
        jobs = []

        # Common selectors for job cards across various ATS platforms
        card_selectors = [
            # Greenhouse
            "div.opening", "div.job-post", "section.level-0 div",
            # Lever
            "div.posting", "a.posting-title",
            # Workday
            "li.css-1q2dra3", "div[data-automation-id='jobItem']",
            # Generic patterns
            "div[class*='job-card']", "div[class*='job-listing']",
            "div[class*='job-item']", "div[class*='job-row']",
            "div[class*='position']", "div[class*='opening']",
            "article[class*='job']", "li[class*='job']",
            "tr[class*='job']",
        ]

        for selector in card_selectors:
            cards = soup.select(selector)
            if len(cards) >= 2:  # At least 2 cards to be a real listing
                for card in cards:
                    job = self._parse_card(card, page_url, role)
                    if job:
                        jobs.append(job)
                if jobs:
                    return jobs

        return jobs

    def _try_job_links(self, soup: BeautifulSoup, page_url: str, role: str) -> List[Job]:
        """Find links that look like job postings based on URL patterns."""
        jobs = []
        seen = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(page_url, href)

            if full_url in seen:
                continue
            if SKIP_PATTERNS.search(href):
                continue
            if not JOB_LINK_RE.search(href):
                continue

            text = link.get_text(strip=True)
            if not text or len(text) < 5 or len(text) > 200:
                continue

            seen.add(full_url)
            matched_role = self._match_role(text)

            # Try to find company/location near the link
            parent = link.parent
            company, location, posted, description = self._extract_context(parent)

            if not is_within_days(posted, self.max_age_days):
                continue

            jobs.append(Job(
                title=text,
                company=company,
                location=location or self.location,
                url=full_url,
                source=self.source_name,
                matched_role=matched_role or role,
                posted_date=posted,
                description=description,
            ))

        return jobs

    def _try_list_items(self, soup: BeautifulSoup, page_url: str, role: str) -> List[Job]:
        """Fallback: look for list items or table rows containing links."""
        jobs = []
        seen = set()

        containers = soup.select("ul li, ol li, tbody tr, div[role='listitem']")
        for item in containers:
            link = item.find("a", href=True)
            if not link:
                continue

            href = link["href"]
            full_url = urljoin(page_url, href)
            text = link.get_text(strip=True)

            if full_url in seen or not text or len(text) < 5:
                continue
            if SKIP_PATTERNS.search(href):
                continue

            # Only include if the text looks job-related
            text_lower = text.lower()
            job_keywords = ["intern", "analyst", "engineer", "manager", "developer",
                            "designer", "associate", "coordinator", "specialist",
                            "scientist", "consultant", "architect", "lead", "director"]
            role_keywords = [w.lower() for w in role.split() if len(w) > 3]

            has_job_keyword = any(kw in text_lower for kw in job_keywords)
            has_role_keyword = any(kw in text_lower for kw in role_keywords)

            if not has_job_keyword and not has_role_keyword:
                continue

            seen.add(full_url)
            matched_role = self._match_role(text)
            company, location, posted, description = self._extract_context(item)

            if not is_within_days(posted, self.max_age_days):
                continue

            jobs.append(Job(
                title=text,
                company=company,
                location=location or self.location,
                url=full_url,
                source=self.source_name,
                matched_role=matched_role or role,
                posted_date=posted,
                description=description,
            ))

        return jobs

    def _parse_card(self, card, page_url: str, role: str):
        """Parse a single job card element."""
        link = card.find("a", href=True)
        if not link:
            return None

        title_el = card.find(["h2", "h3", "h4", "h5"]) or link
        title = title_el.get_text(strip=True)
        if not title or len(title) < 3:
            return None

        href = link["href"]
        full_url = urljoin(page_url, href)

        if SKIP_PATTERNS.search(href):
            return None

        matched_role = self._match_role(title)
        company, location, posted, description = self._extract_context(card)

        if not is_within_days(posted, self.max_age_days):
            return None

        return Job(
            title=title,
            company=company,
            location=location or self.location,
            url=full_url,
            source=self.source_name,
            matched_role=matched_role or role,
            posted_date=posted,
            description=description,
        )

    def _extract_context(self, element) -> tuple:
        """Extract company, location, posted date, and description from a parent element."""
        company = ""
        location = ""
        posted = None
        description = ""

        if element is None:
            return company, location, posted, description

        # Company: look for common class patterns
        for cls_pattern in ["company", "employer", "organization", "dept"]:
            el = element.find(class_=lambda c: c and cls_pattern in c.lower() if c else False)
            if el:
                company = el.get_text(strip=True)
                break

        # Location: look for common class patterns
        for cls_pattern in ["location", "loc", "place", "city"]:
            el = element.find(class_=lambda c: c and cls_pattern in c.lower() if c else False)
            if el:
                location = el.get_text(strip=True)
                break

        # If no location found, look for text with state abbreviation pattern
        if not location:
            for text_el in element.find_all(string=True):
                text = text_el.strip()
                if re.search(r",\s*[A-Z]{2}\b", text) and len(text) < 50:
                    location = text
                    break

        # Posted date
        time_el = element.find("time")
        if time_el:
            dt_attr = time_el.get("datetime", "")
            if dt_attr:
                try:
                    posted = datetime.fromisoformat(dt_attr)
                except (ValueError, TypeError):
                    pass
            if not posted:
                posted = parse_relative_time(time_el.get_text(strip=True))

        if not posted:
            for cls_pattern in ["date", "time", "posted", "when"]:
                el = element.find(class_=lambda c: c and cls_pattern in c.lower() if c else False)
                if el:
                    posted = parse_relative_time(el.get_text(strip=True))
                    break

        # Description snippet
        for cls_pattern in ["description", "snippet", "summary", "excerpt"]:
            el = element.find(class_=lambda c: c and cls_pattern in c.lower() if c else False)
            if el:
                description = el.get_text(strip=True)[:300]
                break
        if not description:
            p_el = element.find("p")
            if p_el:
                description = p_el.get_text(strip=True)[:300]

        return company, location, posted, description
