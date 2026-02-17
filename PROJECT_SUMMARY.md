# Job Scraper — Automated Internship Aggregator

## Resume Summary

**Job Scraper — Automated Internship Aggregator**

- Built a Python-based web scraping pipeline that aggregates internship listings from 6 sources (LinkedIn, SimplyHired, Indeed, Glassdoor, WayUp, intern-list.com) using requests, BeautifulSoup, and Playwright for browser-automated scraping
- Engineered intelligent role-matching logic to classify scraped jobs into target internship categories (Product Management, TPM, Data Analyst, Business Analyst) using fuzzy keyword matching against job titles
- Implemented configurable time-based filtering (max_age_days) with relative date parsing to surface only recently posted positions, reducing noise from stale listings
- Designed a SQLite-backed deduplication system to prevent duplicate job alerts across scheduled scraping cycles
- Generated self-contained HTML reports with client-side filtering (search, role, source, posted time) and live counters, grouped by internship role for quick review
- Built a JSON-based data pipeline with a combine utility to merge historical scrape results into a single deduplicated report
- Automated periodic execution via APScheduler with optional Gmail SMTP email notifications for new listings
- Tech stack: Python, Playwright, BeautifulSoup4, SQLite, APScheduler, YAML config, HTML/CSS/JS

---

## Product Requirements Document (PRD)

### 1. Overview

**Product Name:** Job Scraper — Automated Internship Aggregator

**Purpose:** Automate the discovery and aggregation of US-based internship listings across multiple job boards, classify them by target role, filter by recency, deduplicate across runs, and deliver a consolidated, filterable HTML report.

**Target User:** Students and early-career professionals actively searching for internships in Product Management, Technical Program Management, Technical Project Management, Data Analytics, and Business Analysis.

---

### 2. Problem Statement

Manually searching multiple job boards daily for relevant internship postings is time-consuming and error-prone. Listings appear and disappear quickly, and tracking which jobs have already been reviewed across multiple sources is difficult. There is no single aggregated view that groups listings by target role with recency filtering.

---

### 3. Goals & Success Metrics

| Goal | Metric |
|------|--------|
| Reduce manual search time | < 1 min to review all new listings vs. 30+ min across 6 sites |
| Comprehensive coverage | Scrape 6+ job sources per cycle |
| Freshness | Only surface jobs posted within configurable time window (default: 1 day) |
| Zero duplicates | SQLite dedup ensures no repeated listings across runs |
| Actionable output | Single HTML report with filters, clickable links, and role grouping |

---

### 4. User Stories

1. **As a student**, I want to run a single command and get all relevant internship listings from multiple job boards, so I don't have to visit each site individually.
2. **As a job seeker**, I want listings grouped by my target roles, so I can focus on the most relevant opportunities first.
3. **As a busy applicant**, I want to filter by time posted, so I only see fresh listings I haven't reviewed yet.
4. **As a repeat user**, I want deduplication across runs, so I'm not re-reading the same jobs.
5. **As a mobile user**, I want a responsive HTML report I can open in any browser.

---

### 5. Features

#### 5.1 Multi-Source Scraping
- **Sources:** LinkedIn (guest API), SimplyHired, Indeed, Glassdoor, WayUp, intern-list.com
- **Configurable:** Enable/disable sources via `config.yaml`
- **Resilient:** Each scraper has error handling; one failure doesn't block others

#### 5.2 Role Matching
- Configurable list of target roles in `config.yaml`
- Fuzzy keyword matching against job titles
- Each job tagged with `matched_role` for grouping

#### 5.3 Time Filtering
- `max_age_days` config parameter (default: 1)
- Parses relative time strings ("2 hours ago", "1 day ago") and absolute dates
- Jobs outside the window are excluded from results

#### 5.4 Deduplication
- SQLite database (`jobs.db`) stores URL hashes
- Jobs seen in previous runs are filtered out
- Auto-purge entries older than 30 days

#### 5.5 HTML Report Generation
- Self-contained single HTML file (no external dependencies)
- Grouped by internship role with section headers and counts
- **Client-side filters:**
  - Text search (title, company, location)
  - Role dropdown
  - Source dropdown
  - Time posted (6h / 12h / 24h / 2d / 7d / 30d)
- Live "Showing X" counter
- Responsive design for mobile/desktop

#### 5.6 JSON Data Pipeline
- Each run saves raw JSON alongside HTML
- `combine_reports.py` merges all historical JSONs into one deduplicated HTML
- Enables longitudinal analysis of job market trends

#### 5.7 Scheduling & Notifications
- APScheduler for periodic execution (configurable interval)
- Optional Gmail SMTP notifications for new listings
- `--now --no-email` flags for one-shot file-only mode

---

### 6. Architecture

```
config.yaml          → Roles, sources, schedule, max_age_days
     ↓
main.py              → Orchestrator: loads config, runs scrapers, dedup, output
     ↓
scrapers/            → One module per source (base.py, linkedin.py, simplyhired.py, ...)
     ↓
dedup.py             → SQLite-backed URL deduplication
     ↓
html_report.py       → HTML report generator with embedded CSS/JS
     ↓
output/              → Timestamped JSON + HTML files
     ↓
combine_reports.py   → Merge all JSONs → single combined HTML
     ↓
email_sender.py      → Optional Gmail SMTP notifications
```

---

### 7. Configuration

**`config.yaml`:**
```yaml
roles:
  - Product Management Intern
  - Technical Program Management Intern
  - Technical Project Management Intern
  - Data Analyst Intern
  - Business Analyst Intern
location: United States
schedule_hours: 4
max_age_days: 1
scrapers:
  - linkedin
  - simplyhired
  - indeed
  - glassdoor
  - wayup
  - internlist
```

---

### 8. Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.x |
| HTTP scraping | requests, BeautifulSoup4 |
| Browser automation | Playwright |
| Database | SQLite |
| Scheduling | APScheduler |
| Config | YAML |
| Email | smtplib (Gmail SMTP) |
| Report | Self-contained HTML/CSS/JS |

---

### 9. Future Enhancements

- **Salary/compensation extraction** from job descriptions
- **Application tracking** — mark jobs as applied/saved within the report
- **Slack/Discord webhook** notifications alongside email
- **Cloud deployment** (AWS Lambda / GitHub Actions) for serverless scheduled runs
- **NLP-based relevance scoring** to rank listings by fit
- **Browser extension** to auto-fill applications from report links
