"""sync_sheet.py - pulls the Expenses sheet into finances.db (full replace)."""

import re
import sqlite3
from googleapiclient.discovery import build
from google_auth import get_creds
from finance_common import normalize_type

SHEET_ID = "1Aa_Z6hd854sHRkKhkvFHvDrMAmuR09DtCm-51fjvdug"
DB_FILE = "finances.db"


def parse_amount(raw):
    clean = re.sub(r"[^0-9.\-]", "", raw or "0") or "0"
    try:
        return abs(float(clean))
    except ValueError:
        return 0.0


def sync():
    creds = get_creds()
    sheets = build("sheets", "v4", credentials=creds)
    resp = sheets.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="Expenses!A2:I1000").execute()
    rows = resp.get("values", [])

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM transactions")

    count = 0
    for i, row in enumerate(rows, start=2):
        if not row or not row[0]:
            continue
        row = row + [""] * (9 - len(row))
        date_, category, vendor, description, amount_str, payment_method, notes, unpaid_str, due_date = row[:9]
        if not date_.strip():
            continue
        amount = parse_amount(amount_str)
        unpaid = 1 if unpaid_str.strip().upper() == "TRUE" else 0
        t = normalize_type(category, unpaid)
        c.execute("""
            INSERT INTO transactions (date, category, vendor, description, amount, payment_method, notes, unpaid, due_date, type, sheet_row)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_.strip(), category.strip() or "Other", vendor.strip(), description.strip(), amount,
              payment_method.strip(), notes.strip(), unpaid, due_date.strip() or None, t, i))
        count += 1

    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    n = sync()
    print(f"Synced {n} rows from Sheet into {DB_FILE}")
