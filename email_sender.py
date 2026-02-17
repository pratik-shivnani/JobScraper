import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict
from datetime import datetime
from typing import List

from scrapers.base import Job

logger = logging.getLogger(__name__)


def _build_html(jobs: List[Job]) -> str:
    """Build an HTML email body with jobs grouped by matching role keyword."""
    grouped = defaultdict(list)
    for job in jobs:
        grouped[job.source].append(job)

    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 8px 0 0; opacity: 0.9; font-size: 14px; }}
            .stats {{ display: flex; gap: 20px; padding: 20px 30px; background: #f8f9fa; border-bottom: 1px solid #eee; }}
            .stat {{ text-align: center; }}
            .stat-num {{ font-size: 28px; font-weight: bold; color: #667eea; }}
            .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            .source-section {{ padding: 20px 30px; }}
            .source-title {{ font-size: 16px; font-weight: 600; color: #333; margin: 20px 0 12px; padding-bottom: 8px; border-bottom: 2px solid #667eea; }}
            .job-card {{ padding: 12px 16px; margin: 8px 0; background: #f8f9fa; border-radius: 8px; border-left: 3px solid #667eea; }}
            .job-title {{ font-size: 15px; font-weight: 600; color: #333; }}
            .job-title a {{ color: #667eea; text-decoration: none; }}
            .job-title a:hover {{ text-decoration: underline; }}
            .job-meta {{ font-size: 13px; color: #666; margin-top: 4px; }}
            .footer {{ padding: 20px 30px; background: #f8f9fa; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 Job Scraper Alert</h1>
                <p>{now}</p>
            </div>
            <div class="stats">
                <div class="stat">
                    <div class="stat-num">{len(jobs)}</div>
                    <div class="stat-label">New Jobs</div>
                </div>
                <div class="stat">
                    <div class="stat-num">{len(grouped)}</div>
                    <div class="stat-label">Sources</div>
                </div>
            </div>
    """

    for source, source_jobs in sorted(grouped.items()):
        html += f'<div class="source-section">'
        html += f'<div class="source-title">📌 {source} ({len(source_jobs)} jobs)</div>'
        for job in source_jobs:
            company_str = f" at {job.company}" if job.company else ""
            location_str = f" · {job.location}" if job.location else ""
            html += f"""
                <div class="job-card">
                    <div class="job-title"><a href="{job.url}" target="_blank">{job.title}</a></div>
                    <div class="job-meta">{company_str}{location_str}</div>
                </div>
            """
        html += "</div>"

    html += """
            <div class="footer">
                Sent by JobScraper · Unsubscribe by stopping the script
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email(
    jobs: List[Job],
    gmail_address: str,
    gmail_app_password: str,
    recipient_email: str,
):
    """Send an HTML email with the job listings."""
    if not jobs:
        logger.info("No new jobs to send — skipping email.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔍 {len(jobs)} New Internship Listings Found"
    msg["From"] = gmail_address
    msg["To"] = recipient_email

    plain_text = f"Found {len(jobs)} new internship listings:\n\n"
    for job in jobs:
        plain_text += f"- {job.title}"
        if job.company:
            plain_text += f" at {job.company}"
        plain_text += f"\n  {job.url}\n  Source: {job.source}\n\n"

    html_body = _build_html(jobs)

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, recipient_email, msg.as_string())
        logger.info(f"Email sent to {recipient_email} with {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
