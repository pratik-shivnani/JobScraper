# JobScraper 🔍

An automated internship aggregator that scrapes 6 US job boards, classifies listings by target role, deduplicates results, and publishes a filterable HTML report via GitHub Pages.

**Live Report:** [pratik-shivnani.github.io/JobScraper](https://pratik-shivnani.github.io/JobScraper/)

## Features

- **Multi-source scraping** — Aggregates listings from 6 job boards using requests, BeautifulSoup, and Playwright
- **Role matching** — Fuzzy keyword matching classifies jobs into target internship categories
- **Time filtering** — Configurable `max_age_days` surfaces only recently posted positions
- **Deduplication** — SQLite-backed URL tracking prevents duplicate listings across runs
- **Interactive HTML reports** — Self-contained HTML with client-side search, role, source, and time filters
- **Automated deployment** — GitHub Actions runs the scraper every 6 hours and publishes to GitHub Pages
- **Email notifications** — Optional Gmail SMTP alerts for new listings

## Target Roles

- Product Management Intern
- Technical Program Management Intern
- Technical Project Management Intern
- Data Analyst Intern
- Business Analyst Intern

## Sources

| Site | Coverage |
|------|----------|
| LinkedIn | Public job listings via guest API |
| SimplyHired | US-focused job search |
| Indeed | Largest US job aggregator |
| Glassdoor | US jobs with company reviews |
| WayUp | Big brand US student internships |
| intern-list.com | Curated US intern listings |

## Setup

### 1. Clone and install

```bash
git clone https://github.com/pratik-shivnani/JobScraper.git
cd JobScraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure (optional)

Edit `config.yaml` to change:
- **roles** — job titles to search for
- **max_age_days** — only include jobs posted within N days (default: 1)
- **schedule_hours** — how often to run (default: 4 hours)
- **scrapers** — which sources to enable/disable

### 3. Set up email notifications (optional)

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=abcd-efgh-ijkl-mnop
RECIPIENT_EMAIL=recipient@example.com
```

## Usage

### Run once (generates JSON + HTML report)

```bash
python main.py --now --no-email
```

### Run on a schedule (every 4 hours by default)

```bash
python main.py
```

### Combine all historical results into one report

```bash
python combine_reports.py
```

### Automated via GitHub Actions

The scraper runs automatically every 6 hours via GitHub Actions and publishes the latest report to GitHub Pages. You can also trigger it manually from the **Actions** tab.

## How It Works

1. **Scrape** — Each enabled scraper searches its site for the configured roles
2. **Match** — Jobs are classified into target roles via fuzzy keyword matching
3. **Filter** — Only jobs posted within `max_age_days` are included
4. **Deduplicate** — SQLite database tracks seen job URLs to avoid duplicates
5. **Report** — Self-contained HTML report generated with interactive filters
6. **Publish** — GitHub Actions deploys the report to GitHub Pages
7. **Notify** — Optional email with new listings (if configured)

## Tech Stack

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
| CI/CD | GitHub Actions + GitHub Pages |

## Project Structure

```
JobScraper/
├── main.py              # Entry point — scheduler + CLI
├── config.yaml          # Roles, sources, schedule config
├── html_report.py       # HTML report generator with embedded CSS/JS
├── combine_reports.py   # Merge all JSON results into one HTML report
├── requirements.txt     # Python dependencies
├── .env                 # Gmail credentials (not committed)
├── .github/
│   └── workflows/
│       └── scrape.yml   # GitHub Actions: scrape + deploy to Pages
├── scrapers/
│   ├── base.py          # Job dataclass + abstract scraper
│   ├── internlist.py    # intern-list.com
│   ├── wayup.py         # wayup.com
│   ├── simplyhired.py   # simplyhired.com
│   ├── indeed.py        # indeed.com
│   ├── linkedin.py      # linkedin.com (guest API)
│   └── glassdoor.py     # glassdoor.com
├── dedup.py             # SQLite deduplication
├── email_sender.py      # Gmail SMTP sender
└── output/              # Generated JSON + HTML reports (gitignored)
```

## Notes

- **Rate limiting**: Scrapers use random delays and User-Agent rotation to reduce blocking risk
- **Fragility**: Web scrapers can break when sites change their HTML structure. If a scraper stops finding results, it may need selector updates.
- **LinkedIn/Glassdoor**: These sites have anti-bot measures. The scrapers work with public endpoints but may get rate-limited.
- **Email**: Only sends if new (unseen) jobs are found. No spam.
