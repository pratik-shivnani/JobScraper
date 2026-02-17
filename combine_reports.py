#!/usr/bin/env python3
"""Combine all JSON job files in output/ into a single HTML report."""

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

from html_report import build_html_grouped


def main():
    output_dir = Path(__file__).parent / "output"
    config_path = Path(__file__).parent / "config.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)
    roles = config.get("roles", [])

    json_files = sorted(output_dir.glob("jobs_*.json"))
    if not json_files:
        print("No JSON files found in output/")
        sys.exit(1)

    all_jobs = []
    seen_urls = set()
    for jf in json_files:
        with open(jf) as f:
            data = json.load(f)
        for job in data:
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_jobs.append(job)

    print(f"Combined {len(all_jobs)} unique jobs from {len(json_files)} files")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    html_path = output_dir / f"combined_{timestamp}.html"

    html_content = build_html_grouped(all_jobs, roles)
    with open(html_path, "w") as f:
        f.write(html_content)

    print(f"Report saved to {html_path}")


if __name__ == "__main__":
    main()
