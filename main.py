#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

from collections import defaultdict
from scrapers.base import Job
from scrapers.internlist import InternListScraper
from scrapers.wayup import WayUpScraper
from scrapers.simplyhired import SimplyHiredScraper
from scrapers.indeed import IndeedScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.glassdoor import GlassdoorScraper
from dedup import DedupStore
from email_sender import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("JobScraper")

SCRAPER_MAP = {
    "internlist": InternListScraper,
    "wayup": WayUpScraper,
    "simplyhired": SimplyHiredScraper,
    "indeed": IndeedScraper,
    "linkedin": LinkedInScraper,
    "glassdoor": GlassdoorScraper,
}


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def save_to_file(jobs, output_dir: Path, roles: list):
    """Save job results to JSON + HTML report, grouped by role."""
    from html_report import build_html_grouped

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_path = output_dir / f"jobs_{timestamp}.json"
    html_path = output_dir / f"jobs_{timestamp}.html"

    data = [
        {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "matched_role": job.matched_role,
            "posted_date": job.posted_date.isoformat() if job.posted_date else None,
            "description": job.description,
        }
        for job in jobs
    ]

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    html_content = build_html_grouped(data, roles)
    with open(html_path, "w") as f:
        f.write(html_content)

    logger.info(f"JSON saved to {json_path}")
    logger.info(f"Report saved to {html_path}")

    if not jobs:
        print("\nNo new jobs found.")
        return

    by_role = defaultdict(list)
    unmatched = []
    for job in jobs:
        if job.matched_role:
            by_role[job.matched_role].append(job)
        else:
            unmatched.append(job)

    print(f"\n{'='*60}")
    print(f"  Found {len(jobs)} new internship listings")
    print(f"  Report: {html_path}")
    print(f"  JSON:   {json_path}")
    print(f"{'='*60}")

    for role in roles:
        role_jobs = by_role.get(role, [])
        if not role_jobs:
            continue
        print(f"\n  [{role}] ({len(role_jobs)} jobs)")
        for job in role_jobs:
            company = f" @ {job.company}" if job.company else ""
            print(f"    - {job.title}{company}")
            print(f"      {job.url}")

    if unmatched:
        print(f"\n  [Other] ({len(unmatched)} jobs)")
        for job in unmatched:
            company = f" @ {job.company}" if job.company else ""
            print(f"    - {job.title}{company}")
            print(f"      {job.url}")

    print(f"\n{'='*60}\n")


def run_scrape(no_email: bool = False):
    """Run all configured scrapers, deduplicate, and optionally send email or save to file."""
    load_dotenv()

    config = load_config()
    roles = config.get("roles", [])
    location = config.get("location", "United States")
    enabled_scrapers = config.get("scrapers", [])

    max_age_days = config.get("max_age_days", 1)

    logger.info(f"Starting scrape for {len(roles)} roles across {len(enabled_scrapers)} sources")
    logger.info(f"Roles: {roles}")
    logger.info(f"Sources: {enabled_scrapers}")
    logger.info(f"Max age: {max_age_days} day(s)")

    all_jobs = []
    for scraper_name in enabled_scrapers:
        scraper_cls = SCRAPER_MAP.get(scraper_name)
        if not scraper_cls:
            logger.warning(f"Unknown scraper: {scraper_name}")
            continue

        scraper = scraper_cls(roles=roles, location=location, max_age_days=max_age_days)
        jobs = scraper.safe_scrape()
        all_jobs.extend(jobs)

    logger.info(f"Total jobs scraped: {len(all_jobs)}")

    dedup = DedupStore()
    new_jobs = dedup.filter_new(all_jobs)
    dedup.purge_old(days=30)

    logger.info(f"New jobs after dedup: {len(new_jobs)}")

    output_dir = Path(__file__).parent / "output"
    save_to_file(new_jobs, output_dir, roles)

    if not no_email:
        gmail_address = os.getenv("GMAIL_ADDRESS")
        gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
        recipient_email = os.getenv("RECIPIENT_EMAIL")

        if not all([gmail_address, gmail_app_password, recipient_email]):
            logger.warning(
                "Email not configured. Set GMAIL_ADDRESS, GMAIL_APP_PASSWORD, "
                "and RECIPIENT_EMAIL in .env — or use --no-email"
            )
        else:
            send_email(
                jobs=new_jobs,
                gmail_address=gmail_address,
                gmail_app_password=gmail_app_password,
                recipient_email=recipient_email,
            )

    logger.info("Scrape cycle complete.")


def main():
    parser = argparse.ArgumentParser(description="Job Scraper — periodic internship finder")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run a single scrape immediately and exit",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Skip sending email — only save results to output/ folder",
    )
    args = parser.parse_args()

    if args.now:
        logger.info("Running one-shot scrape...")
        run_scrape(no_email=args.no_email)
        return

    config = load_config()
    schedule_hours = config.get("schedule_hours", 4)

    logger.info(f"Starting scheduler — will run every {schedule_hours} hours")
    if args.no_email:
        logger.info("Email disabled — results will be saved to output/ folder")
    logger.info("Press Ctrl+C to stop")

    run_scrape(no_email=args.no_email)

    scheduler = BlockingScheduler()
    scheduler.add_job(run_scrape, "interval", hours=schedule_hours, kwargs={"no_email": args.no_email})

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
