"""Generate a self-contained HTML report from job listings, grouped by role."""

import json
import html as html_mod
from collections import defaultdict
from datetime import datetime
from typing import List


def _esc(text: str) -> str:
    return html_mod.escape(text or "")


def build_html(jobs: list, roles: list) -> str:
    """Build a self-contained HTML report.

    `jobs` is a list of dicts with keys:
        title, company, location, url, source, matched_role, posted_date, description
    """
    now_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    sources = sorted(set(j.get("source", "") for j in jobs if j.get("source")))
    companies = sorted(set(j.get("company", "") for j in jobs if j.get("company")))

    by_role = defaultdict(list)
    unmatched = []
    for job in jobs:
        r = job.get("matched_role", "")
        if r:
            by_role[r].append(job)
        else:
            unmatched.append(job)

    all_roles_with_jobs = [r for r in roles if by_role.get(r)]
    if unmatched:
        all_roles_with_jobs.append("Other")

    jobs_json = json.dumps(jobs)

    rows_html = ""
    idx = 0
    for role in roles:
        for job in by_role.get(role, []):
            idx += 1
            rows_html += _build_row(idx, job, role)
    for job in unmatched:
        idx += 1
        rows_html += _build_row(idx, job, "Other")

    role_options = ""
    for r in all_roles_with_jobs:
        count = len(by_role.get(r, [])) if r != "Other" else len(unmatched)
        role_options += f'<option value="{_esc(r)}">{_esc(r)} ({count})</option>\n'

    source_options = ""
    for s in sources:
        source_options += f'<option value="{_esc(s)}">{_esc(s)}</option>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Internship Listings - {datetime.now().strftime("%b %d, %Y")}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a2e; padding: 24px; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 4px; color: #1a1a2e; }}
  .subtitle {{ color: #666; margin-bottom: 20px; font-size: 0.95rem; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat {{ background: #fff; border-radius: 10px; padding: 14px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 100px; }}
  .stat-num {{ font-size: 1.5rem; font-weight: 700; color: #4361ee; }}
  .stat-label {{ font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
  .filters {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }}
  .filters input, .filters select {{ padding: 10px 14px; border: 1px solid #ddd; border-radius: 10px; font-size: 0.9rem; outline: none; transition: border-color 0.2s; background: #fff; }}
  .filters input:focus, .filters select:focus {{ border-color: #4361ee; }}
  .filters input {{ flex: 1; min-width: 200px; }}
  .filters select {{ min-width: 160px; }}
  .filters label {{ font-size: 0.8rem; color: #666; font-weight: 500; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .role-section {{ margin-bottom: 28px; }}
  .role-header {{ font-size: 1.15rem; font-weight: 700; color: #1a1a2e; padding: 12px 0 8px; border-bottom: 2px solid #4361ee; margin-bottom: 0; display: flex; align-items: center; gap: 10px; }}
  .role-count {{ background: #4361ee; color: #fff; font-size: 0.75rem; padding: 2px 10px; border-radius: 20px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 4px; }}
  thead {{ background: #4361ee; color: #fff; }}
  th {{ padding: 12px 14px; text-align: left; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer; user-select: none; white-space: nowrap; }}
  th:hover {{ background: #3a56d4; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 0.88rem; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8f9ff; }}
  tr.hidden {{ display: none; }}
  a {{ color: #4361ee; text-decoration: none; font-weight: 500; }}
  a:hover {{ text-decoration: underline; }}
  .company {{ color: #555; font-weight: 500; }}
  .location {{ color: #888; white-space: nowrap; }}
  .source {{ display: inline-block; background: #eef0ff; color: #4361ee; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 500; }}
  .date {{ color: #888; white-space: nowrap; font-size: 0.82rem; }}
  .num {{ color: #bbb; font-size: 0.8rem; text-align: center; }}
  .desc {{ color: #777; font-size: 0.82rem; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .no-results {{ text-align: center; padding: 40px; color: #999; font-size: 1rem; }}
  .time-badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; margin-left: 6px; }}
  .time-today {{ background: #e8f5e9; color: #2e7d32; }}
  .time-yesterday {{ background: #fff3e0; color: #e65100; }}
  .time-older {{ background: #f5f5f5; color: #999; }}
  @media (max-width: 768px) {{
    th, td {{ padding: 8px 6px; font-size: 0.8rem; }}
    h1 {{ font-size: 1.4rem; }}
    .filters {{ flex-direction: column; }}
    .desc {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Internship Listings</h1>
  <p class="subtitle">Generated on {_esc(now_str)}</p>
  <div class="stats">
    <div class="stat"><div class="stat-num" id="stat-total">{len(jobs)}</div><div class="stat-label">Total Jobs</div></div>
    <div class="stat"><div class="stat-num">{len(sources)}</div><div class="stat-label">Sources</div></div>
    <div class="stat"><div class="stat-num">{len(companies)}</div><div class="stat-label">Companies</div></div>
    <div class="stat"><div class="stat-num" id="stat-visible">{len(jobs)}</div><div class="stat-label">Showing</div></div>
  </div>
  <div class="filters">
    <div class="filter-group" style="flex:1;min-width:200px;">
      <label>Search</label>
      <input type="text" id="search" placeholder="Search by title, company, location..." oninput="applyFilters()">
    </div>
    <div class="filter-group">
      <label>Role</label>
      <select id="roleFilter" onchange="applyFilters()">
        <option value="">All Roles</option>
        {role_options}
      </select>
    </div>
    <div class="filter-group">
      <label>Source</label>
      <select id="sourceFilter" onchange="applyFilters()">
        <option value="">All Sources</option>
        {source_options}
      </select>
    </div>
    <div class="filter-group">
      <label>Posted</label>
      <select id="timeFilter" onchange="applyFilters()">
        <option value="">Any Time</option>
        <option value="6">Last 6 hours</option>
        <option value="12">Last 12 hours</option>
        <option value="24" selected>Last 24 hours</option>
        <option value="48">Last 2 days</option>
        <option value="168">Last 7 days</option>
      </select>
    </div>
  </div>

  <div id="content">
    {rows_html}
  </div>
  <div class="no-results" id="noResults" style="display:none;">No jobs match your filters.</div>
</div>
<script>
const JOBS = {jobs_json};

function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase();
  const role = document.getElementById('roleFilter').value;
  const source = document.getElementById('sourceFilter').value;
  const hours = parseInt(document.getElementById('timeFilter').value) || 0;
  const now = Date.now();
  const rows = document.querySelectorAll('tr[data-role]');
  let visible = 0;

  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    const rRole = row.getAttribute('data-role');
    const rSource = row.getAttribute('data-source');
    const rDate = row.getAttribute('data-date');

    let show = true;
    if (q && !text.includes(q)) show = false;
    if (role && rRole !== role) show = false;
    if (source && rSource !== source) show = false;
    if (hours && rDate) {{
      const posted = new Date(rDate).getTime();
      if (now - posted > hours * 3600000) show = false;
    }}

    row.style.display = show ? '' : 'none';
    if (show) visible++;
  }});

  // Show/hide role sections based on visible rows
  document.querySelectorAll('.role-section').forEach(section => {{
    const visibleRows = section.querySelectorAll('tr[data-role]:not([style*="display: none"])');
    section.style.display = visibleRows.length > 0 ? '' : 'none';
    const countEl = section.querySelector('.role-count');
    if (countEl) countEl.textContent = visibleRows.length;
  }});

  document.getElementById('stat-visible').textContent = visible;
  document.getElementById('noResults').style.display = visible === 0 ? '' : 'none';
}}

// Run on load
applyFilters();
</script>
</body>
</html>"""


def _build_row(idx: int, job: dict, role: str) -> str:
    title = _esc(job.get("title", ""))
    company = _esc(job.get("company", "")) or "—"
    location = _esc(job.get("location", "")) or "—"
    source = _esc(job.get("source", ""))
    url = _esc(job.get("url", ""))
    desc = _esc((job.get("description", "") or "")[:200])
    posted = job.get("posted_date", "")
    date_display = ""
    time_class = "time-older"
    if posted:
        try:
            dt = datetime.fromisoformat(posted) if isinstance(posted, str) else posted
            date_display = dt.strftime("%b %d, %I:%M %p")
            hours_ago = (datetime.now() - dt).total_seconds() / 3600
            if hours_ago < 24:
                time_class = "time-today"
            elif hours_ago < 48:
                time_class = "time-yesterday"
        except (ValueError, TypeError):
            date_display = str(posted)[:16]

    posted_attr = posted if isinstance(posted, str) else (posted.isoformat() if posted else "")

    return (
        f'<tr data-role="{_esc(role)}" data-source="{source}" data-date="{_esc(posted_attr)}">'
        f'<td class="num">{idx}</td>'
        f'<td><a href="{url}" target="_blank" rel="noopener">{title}</a></td>'
        f'<td class="company">{company}</td>'
        f'<td class="location">{location}</td>'
        f'<td><span class="date {time_class}">{date_display}</span></td>'
        f'<td><span class="source">{source}</span></td>'
        f'<td class="desc" title="{desc}">{desc}</td>'
        f'</tr>\n'
    )


def build_html_grouped(jobs: list, roles: list) -> str:
    """Build HTML with jobs grouped under role section headers."""
    now_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    sources = sorted(set(j.get("source", "") for j in jobs if j.get("source")))
    companies = sorted(set(j.get("company", "") for j in jobs if j.get("company")))

    by_role = defaultdict(list)
    unmatched = []
    for job in jobs:
        r = job.get("matched_role", "")
        if r:
            by_role[r].append(job)
        else:
            unmatched.append(job)

    all_roles_with_jobs = [r for r in roles if by_role.get(r)]
    if unmatched:
        all_roles_with_jobs.append("Other")

    jobs_json = json.dumps(jobs)

    sections_html = ""
    idx = 0
    for role in roles:
        role_jobs = by_role.get(role, [])
        if not role_jobs:
            continue
        sections_html += f'<div class="role-section" data-section-role="{_esc(role)}">\n'
        sections_html += f'<div class="role-header">{_esc(role)} <span class="role-count">{len(role_jobs)}</span></div>\n'
        sections_html += '<table><thead><tr><th>#</th><th>Title</th><th>Company</th><th>Location</th><th>Posted</th><th>Source</th><th>Description</th></tr></thead><tbody>\n'
        for job in role_jobs:
            idx += 1
            sections_html += _build_row(idx, job, role)
        sections_html += '</tbody></table></div>\n'

    if unmatched:
        sections_html += f'<div class="role-section" data-section-role="Other">\n'
        sections_html += f'<div class="role-header">Other Matches <span class="role-count">{len(unmatched)}</span></div>\n'
        sections_html += '<table><thead><tr><th>#</th><th>Title</th><th>Company</th><th>Location</th><th>Posted</th><th>Source</th><th>Description</th></tr></thead><tbody>\n'
        for job in unmatched:
            idx += 1
            sections_html += _build_row(idx, job, "Other")
        sections_html += '</tbody></table></div>\n'

    role_options = ""
    for r in all_roles_with_jobs:
        count = len(by_role.get(r, [])) if r != "Other" else len(unmatched)
        role_options += f'<option value="{_esc(r)}">{_esc(r)} ({count})</option>\n'

    source_options = ""
    for s in sources:
        source_options += f'<option value="{_esc(s)}">{_esc(s)}</option>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Internship Listings - {datetime.now().strftime("%b %d, %Y")}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a2e; padding: 24px; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 4px; color: #1a1a2e; }}
  .subtitle {{ color: #666; margin-bottom: 20px; font-size: 0.95rem; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat {{ background: #fff; border-radius: 10px; padding: 14px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 100px; }}
  .stat-num {{ font-size: 1.5rem; font-weight: 700; color: #4361ee; }}
  .stat-label {{ font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
  .filters {{ display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; align-items: flex-end; }}
  .filters input, .filters select {{ padding: 10px 14px; border: 1px solid #ddd; border-radius: 10px; font-size: 0.9rem; outline: none; transition: border-color 0.2s; background: #fff; }}
  .filters input:focus, .filters select:focus {{ border-color: #4361ee; }}
  .filters input {{ flex: 1; min-width: 200px; }}
  .filters select {{ min-width: 160px; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .filter-group label {{ font-size: 0.8rem; color: #666; font-weight: 500; }}
  .role-section {{ margin-bottom: 28px; }}
  .role-header {{ font-size: 1.15rem; font-weight: 700; color: #1a1a2e; padding: 12px 0 8px; border-bottom: 2px solid #4361ee; margin-bottom: 0; display: flex; align-items: center; gap: 10px; }}
  .role-count {{ background: #4361ee; color: #fff; font-size: 0.75rem; padding: 2px 10px; border-radius: 20px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  thead {{ background: #4361ee; color: #fff; }}
  th {{ padding: 12px 14px; text-align: left; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 0.88rem; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8f9ff; }}
  a {{ color: #4361ee; text-decoration: none; font-weight: 500; }}
  a:hover {{ text-decoration: underline; }}
  .company {{ color: #555; font-weight: 500; }}
  .location {{ color: #888; white-space: nowrap; }}
  .source {{ display: inline-block; background: #eef0ff; color: #4361ee; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 500; }}
  .date {{ color: #888; white-space: nowrap; font-size: 0.82rem; }}
  .num {{ color: #bbb; font-size: 0.8rem; text-align: center; }}
  .desc {{ color: #777; font-size: 0.82rem; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .no-results {{ text-align: center; padding: 40px; color: #999; font-size: 1rem; }}
  .time-today {{ color: #2e7d32; }}
  .time-yesterday {{ color: #e65100; }}
  .time-older {{ color: #999; }}
  @media (max-width: 768px) {{
    th, td {{ padding: 8px 6px; font-size: 0.8rem; }}
    h1 {{ font-size: 1.4rem; }}
    .filters {{ flex-direction: column; }}
    .desc {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Internship Listings</h1>
  <p class="subtitle">Generated on {_esc(now_str)}</p>
  <div class="stats">
    <div class="stat"><div class="stat-num">{len(jobs)}</div><div class="stat-label">Total Jobs</div></div>
    <div class="stat"><div class="stat-num">{len(sources)}</div><div class="stat-label">Sources</div></div>
    <div class="stat"><div class="stat-num">{len(companies)}</div><div class="stat-label">Companies</div></div>
    <div class="stat"><div class="stat-num" id="stat-visible">{len(jobs)}</div><div class="stat-label">Showing</div></div>
  </div>
  <div class="filters">
    <div class="filter-group" style="flex:1;min-width:200px;">
      <label>Search</label>
      <input type="text" id="search" placeholder="Search by title, company, location..." oninput="applyFilters()">
    </div>
    <div class="filter-group">
      <label>Role</label>
      <select id="roleFilter" onchange="applyFilters()">
        <option value="">All Roles</option>
        {role_options}
      </select>
    </div>
    <div class="filter-group">
      <label>Source</label>
      <select id="sourceFilter" onchange="applyFilters()">
        <option value="">All Sources</option>
        {source_options}
      </select>
    </div>
    <div class="filter-group">
      <label>Posted</label>
      <select id="timeFilter" onchange="applyFilters()">
        <option value="">Any Time</option>
        <option value="6">Last 6 hours</option>
        <option value="12">Last 12 hours</option>
        <option value="24">Last 24 hours</option>
        <option value="48">Last 2 days</option>
        <option value="168">Last 7 days</option>
        <option value="720">Last 30 days</option>
      </select>
    </div>
  </div>

  <div id="content">
    {sections_html}
  </div>
  <div class="no-results" id="noResults" style="display:none;">No jobs match your filters.</div>
</div>
<script>
function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase();
  const role = document.getElementById('roleFilter').value;
  const source = document.getElementById('sourceFilter').value;
  const hours = parseInt(document.getElementById('timeFilter').value) || 0;
  const now = Date.now();
  const rows = document.querySelectorAll('tr[data-role]');
  let visible = 0;

  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    const rRole = row.getAttribute('data-role');
    const rSource = row.getAttribute('data-source');
    const rDate = row.getAttribute('data-date');

    let show = true;
    if (q && !text.includes(q)) show = false;
    if (role && rRole !== role) show = false;
    if (source && rSource !== source) show = false;
    if (hours && rDate) {{
      const posted = new Date(rDate).getTime();
      if (now - posted > hours * 3600000) show = false;
    }}

    row.style.display = show ? '' : 'none';
    if (show) visible++;
  }});

  document.querySelectorAll('.role-section').forEach(section => {{
    const trs = section.querySelectorAll('tr[data-role]');
    let sectionVisible = 0;
    trs.forEach(tr => {{ if (tr.style.display !== 'none') sectionVisible++; }});
    section.style.display = sectionVisible > 0 ? '' : 'none';
    const countEl = section.querySelector('.role-count');
    if (countEl) countEl.textContent = sectionVisible;
  }});

  document.getElementById('stat-visible').textContent = visible;
  document.getElementById('noResults').style.display = visible === 0 ? '' : 'none';
}}
</script>
</body>
</html>"""
