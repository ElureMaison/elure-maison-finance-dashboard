"""
generate_dashboard.py

Reads finance_data.json and renders the 4-page static site (Dashboard,
Monthly P&L, Annual P&L, Accounts Payable) into docs/ for GitHub Pages.
Read-only (no add/edit/delete forms) - that lives in the local Flask app.

Password comes from the GATE_PASSWORD env var.
"""

import hashlib
import json
import os
from datetime import datetime

from render import shell, dashboard_body, monthly_body, annual_body, ap_body

DATA_FILE = "finance_data.json"
OUT_DIR = "docs"

PAGES = [
    ("dashboard", "Elure Maison — Finance Dashboard", "index.html", dashboard_body),
    ("monthly", "Elure Maison — Monthly P&L", "monthly.html", monthly_body),
    ("annual", "Elure Maison — Annual P&L", "annual.html", annual_body),
    ("ap", "Elure Maison — Accounts Payable", "ap.html", ap_body),
]

NAV_URLS = {"dashboard": "index.html", "monthly": "monthly.html", "annual": "annual.html", "ap": "ap.html"}


def main():
    password = os.environ.get("GATE_PASSWORD", "elure2026")
    gate_hash = hashlib.sha256(password.encode()).hexdigest()

    with open(DATA_FILE) as f:
        data = json.load(f)

    gen_dt = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
    data["generated_at_display"] = gen_dt.strftime("%b %d, %Y %H:%M UTC")

    os.makedirs(OUT_DIR, exist_ok=True)

    for key, title, filename, body_fn in PAGES:
        body_html = body_fn(data)
        html = shell(title, key, NAV_URLS, body_html, data, gate_hash=gate_hash)
        with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Wrote {OUT_DIR}/{filename}")


if __name__ == "__main__":
    main()
