"""
generate_dashboard.py

Reads finance_data.json + dashboard_template.html, embeds the data and the
gate password hash, and writes the final page (defaults to docs/index.html
for GitHub Pages).

Password comes from the GATE_PASSWORD env var. Falls back to a default
only for local testing - CI always sets it from a secret.
"""

import hashlib
import json
import os
import sys

TEMPLATE = "dashboard_template.html"
DATA_FILE = "finance_data.json"


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "docs/index.html"
    password = os.environ.get("GATE_PASSWORD", "elure2026")

    with open(DATA_FILE) as f:
        data = json.load(f)
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()

    gate_hash = hashlib.sha256(password.encode()).hexdigest()

    html = template.replace("__DATA_JSON__", json.dumps(data))
    html = html.replace("__GATE_HASH__", gate_hash)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
