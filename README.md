# JobScraper 🔍

A Python-based job scraper that periodically scrapes US job boards for internship listings, deduplicates results, and sends a summary email via Gmail SMTP.

## Target Roles

- Product Management Intern
- Technical Program Management Intern
- Technical Project Management Intern
- Data Analyst Intern
- Business Analyst Intern

## Sources

| Site | Coverage |
|------|----------|
| intern-list.com | Curated US intern listings |
| WayUp | Big brand US student internships |
| SimplyHired | US-focused job search |
| Indeed | Largest US job aggregator |
| LinkedIn | Public job listings (no auth) |
| Glassdoor | US jobs with company reviews |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication if not already enabled
3. Go to **App Passwords** (search for it in account settings)
4. Generate a new app password for "Mail"
5. Copy the 16-character password

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=abcd-efgh-ijkl-mnop
RECIPIENT_EMAIL=recipient@example.com
```

### 4. Customize roles and schedule (optional)

Edit `config.yaml` to change:
- **roles** — job titles to search for
- **schedule_hours** — how often to run (default: 4 hours)
- **lookback_hours** — only include recent jobs (default: 6 hours)
- **scrapers** — which sources to enable/disable

## Usage

### Run once (one-shot)

```bash
python main.py --now
```

### Run on a schedule (every 4 hours by default)

```bash
python main.py
```

### Run in the background

```bash
# Using nohup
nohup python main.py > scraper.log 2>&1 &

# Using macOS launchd — create a plist in ~/Library/LaunchAgents/
```

## How It Works

1. **Scrape** — Each enabled scraper searches its site for the configured roles
2. **Deduplicate** — SQLite database tracks seen job URLs to avoid duplicates
3. **Email** — New jobs are sent as a formatted HTML email grouped by source
4. **Repeat** — APScheduler triggers the cycle every N hours

## Project Structure

```
JobScraper/
├── main.py              # Entry point — scheduler + CLI
├── config.yaml          # Roles, sources, schedule config
├── .env                 # Gmail credentials (not committed)
├── requirements.txt     # Python dependencies
├── scrapers/
│   ├── base.py          # Job dataclass + abstract scraper
│   ├── internlist.py    # intern-list.com
│   ├── wayup.py         # wayup.com
│   ├── simplyhired.py   # simplyhired.com
│   ├── indeed.py        # indeed.com
│   ├── linkedin.py      # linkedin.com (public)
│   └── glassdoor.py     # glassdoor.com
├── dedup.py             # SQLite deduplication
├── email_sender.py      # Gmail SMTP sender
└── jobs.db              # Auto-created at runtime
```

## Notes

- **Rate limiting**: Scrapers use random delays and User-Agent rotation to reduce blocking risk
- **Fragility**: Web scrapers can break when sites change their HTML structure. If a scraper stops finding results, it may need selector updates.
- **LinkedIn/Glassdoor**: These sites have anti-bot measures. The scrapers work with public endpoints but may get rate-limited.
- **Email**: Only sends if new (unseen) jobs are found. No spam.
