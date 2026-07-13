"""
sync_finance_dashboard.py

CI version - pulls last 13 months of paid Shopify orders + all expense rows
from the "Elure Maison - Expenses" Google Sheet, aggregates both by month,
and writes finance_data.json. Auth is entirely via environment variables
(GitHub Actions secrets) - no local token files, no interactive login.

Required env vars:
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
  SHOPIFY_TOKEN
  EXPENSE_SHEET_ID (optional override; defaults to the known sheet id)
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

EXPENSE_SHEET_ID = os.environ.get("EXPENSE_SHEET_ID", "1Aa_Z6hd854sHRkKhkvFHvDrMAmuR09DtCm-51fjvdug")

SHOPIFY_STORE = "elure-maison.myshopify.com"
SHOPIFY_TOKEN = os.environ["SHOPIFY_TOKEN"]
SHOPIFY_API_VERSION = "2024-01"

MONTHS_BACK = 13  # 12 full months + current partial month


def month_key(dt):
    return dt.strftime("%Y-%m")


def get_sheets_creds():
    creds = Credentials(
        None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    creds.refresh(Request())
    return creds


def fetch_expenses():
    creds = get_sheets_creds()
    sheets = build("sheets", "v4", credentials=creds)
    resp = sheets.spreadsheets().values().get(spreadsheetId=EXPENSE_SHEET_ID, range="Expenses!A2:G1000").execute()
    rows = resp.get("values", [])

    expenses = []
    for row in rows:
        if not row or not row[0]:
            continue
        row = row + [""] * (7 - len(row))
        date_str, category, vendor, description, amount_str, payment_method, notes = row[:7]
        try:
            date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            continue
        amount_clean = re.sub(r"[^0-9.\-]", "", amount_str or "0") or "0"
        try:
            amount = abs(float(amount_clean))
        except ValueError:
            continue
        expenses.append({
            "date": date_str.strip(),
            "month": month_key(date),
            "category": category.strip() or "Other",
            "vendor": vendor.strip(),
            "description": description.strip(),
            "amount": round(amount, 2),
        })
    return expenses


def fetch_orders():
    since = (datetime.now(timezone.utc) - timedelta(days=MONTHS_BACK * 31)).strftime("%Y-%m-%dT00:00:00Z")
    orders = []
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/orders.json"
    params = {
        "status": "any",
        "financial_status": "paid",
        "created_at_min": since,
        "limit": 250,
        "fields": "id,created_at,total_price,current_total_price,total_discounts,subtotal_price,total_tax,cancelled_at,refunds",
    }
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}

    while url:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 403:
            print("Shopify orders access denied (missing read_orders scope) - revenue will be zero.")
            return []
        resp.raise_for_status()
        data = resp.json()
        orders.extend(data.get("orders", []))

        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        url = next_url
        params = None  # pagination URL already includes params

    return orders


def aggregate_revenue(orders):
    monthly = defaultdict(lambda: {"gross": 0.0, "refunds": 0.0, "orders": 0})
    for o in orders:
        if o.get("cancelled_at"):
            continue
        created = datetime.strptime(o["created_at"][:10], "%Y-%m-%d")
        m = month_key(created)
        monthly[m]["gross"] += float(o.get("current_total_price") or o.get("total_price") or 0)
        monthly[m]["orders"] += 1
        for refund in o.get("refunds", []):
            for line in refund.get("transactions", []):
                if line.get("kind") == "refund":
                    monthly[m]["refunds"] += float(line.get("amount") or 0)
    return monthly


def build_month_range():
    today = datetime.now(timezone.utc)
    months = []
    y, m = today.year, today.month
    for i in range(MONTHS_BACK - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        months.append(f"{yy:04d}-{mm:02d}")
    return months


def main():
    print("Fetching expenses from Google Sheet...")
    expenses = fetch_expenses()
    print(f"  {len(expenses)} expense rows")

    print("Fetching Shopify orders...")
    orders = fetch_orders()
    print(f"  {len(orders)} paid orders")
    revenue_by_month = aggregate_revenue(orders)

    months = build_month_range()

    expenses_by_month = defaultdict(float)
    category_totals_current_month = defaultdict(float)
    current_month = months[-1]
    for e in expenses:
        expenses_by_month[e["month"]] += e["amount"]
        if e["month"] == current_month:
            category_totals_current_month[e["category"]] += e["amount"]

    series = []
    for m in months:
        rev = revenue_by_month.get(m, {"gross": 0.0, "refunds": 0.0, "orders": 0})
        net_revenue = rev["gross"] - rev["refunds"]
        exp = expenses_by_month.get(m, 0.0)
        series.append({
            "month": m,
            "revenue": round(net_revenue, 2),
            "orders": rev["orders"],
            "expenses": round(exp, 2),
            "profit": round(net_revenue - exp, 2),
        })

    mtd = series[-1]
    ytd_months = [s for s in series if s["month"].startswith(str(datetime.now().year))]
    ytd_revenue = sum(s["revenue"] for s in ytd_months)
    ytd_expenses = sum(s["expenses"] for s in ytd_months)

    recent_expenses = sorted(expenses, key=lambda e: e["date"], reverse=True)[:12]

    snapshot = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "store": "Elure Maison",
        "monthly": series,
        "mtd": mtd,
        "ytd": {
            "revenue": round(ytd_revenue, 2),
            "expenses": round(ytd_expenses, 2),
            "profit": round(ytd_revenue - ytd_expenses, 2),
        },
        "current_month_expense_breakdown": [
            {"category": k, "amount": round(v, 2)} for k, v in sorted(category_totals_current_month.items(), key=lambda x: -x[1])
        ],
        "recent_expenses": recent_expenses,
        "orders_scope_ok": len(orders) > 0 or sum(v["orders"] for v in revenue_by_month.values()) > 0,
    }

    with open("finance_data.json", "w") as f:
        json.dump(snapshot, f, indent=2)

    print("Wrote finance_data.json")
    print(f"MTD revenue: ${mtd['revenue']:,.2f}  MTD expenses: ${mtd['expenses']:,.2f}  MTD profit: ${mtd['profit']:,.2f}")


if __name__ == "__main__":
    main()
