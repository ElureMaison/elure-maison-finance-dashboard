"""
sync_finance_dashboard.py

CI version - pulls last 13 months of paid Shopify orders + all expense rows
from the "Elure Maison - Expenses" Google Sheet, aggregates both by month,
computes Monthly/Annual P&L forecasts and open Accounts Payable, and writes
finance_data.json. Auth is entirely via environment variables (GitHub
Actions secrets) - no local token files, no interactive login.

Required env vars:
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
  SHOPIFY_TOKEN
  EXPENSE_SHEET_ID (optional override; defaults to the known sheet id)
"""

import os
import json
import re
from datetime import datetime, timezone
from collections import defaultdict
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from finance_common import (
    normalize_type, type_label, build_month_range,
    compute_monthly_forecast, compute_annual_forecast, group_ap_by_due_date,
)
from shopify_revenue import fetch_orders, aggregate_revenue, month_key

EXPENSE_SHEET_ID = os.environ.get("EXPENSE_SHEET_ID", "1Aa_Z6hd854sHRkKhkvFHvDrMAmuR09DtCm-51fjvdug")
MONTHS_BACK = 13  # 12 full months + current partial month
FORECAST_MONTHS = 6


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
    resp = sheets.spreadsheets().values().get(spreadsheetId=EXPENSE_SHEET_ID, range="Expenses!A2:I1000").execute()
    rows = resp.get("values", [])

    expenses = []
    for row in rows:
        if not row or not row[0]:
            continue
        row = row + [""] * (9 - len(row))
        date_str, category, vendor, description, amount_str, payment_method, notes, unpaid_str, due_date = row[:9]
        try:
            date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            continue
        amount_clean = re.sub(r"[^0-9.\-]", "", amount_str or "0") or "0"
        try:
            amount = abs(float(amount_clean))
        except ValueError:
            continue
        unpaid = unpaid_str.strip().upper() == "TRUE"
        category = category.strip() or "Other"
        t = normalize_type(category, unpaid)
        expenses.append({
            "date": date_str.strip(),
            "month": month_key(date),
            "category": category,
            "vendor": vendor.strip(),
            "description": description.strip(),
            "amount": round(amount, 2),
            "payment_method": payment_method.strip(),
            "unpaid": unpaid,
            "due_date": due_date.strip() or None,
            "type": t,
            "type_label": type_label(t),
        })
    return expenses


def main():
    print("Fetching expenses from Google Sheet...")
    expenses = fetch_expenses()
    print(f"  {len(expenses)} expense rows")

    print("Fetching Shopify orders...")
    orders = fetch_orders(token=os.environ["SHOPIFY_TOKEN"], months_back=MONTHS_BACK)
    print(f"  {len(orders)} paid orders")
    revenue_by_month = aggregate_revenue(orders)

    months = build_month_range(MONTHS_BACK)

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

    open_ap = [e for e in expenses if e["unpaid"]]
    total_ap = round(sum(e["amount"] for e in open_ap), 2)
    ap_groups = group_ap_by_due_date(open_ap)

    monthly_forecast = compute_monthly_forecast(series, forecast_months=FORECAST_MONTHS, growth_pct=0.0)
    annual = compute_annual_forecast(series, monthly_forecast)

    recent_expenses = sorted(expenses, key=lambda e: e["date"], reverse=True)[:12]

    snapshot = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "store": "Elure Maison",
        "monthly": series,
        "monthly_forecast": monthly_forecast,
        "annual": annual,
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
        "total_ap": total_ap,
        "ap_groups": ap_groups,
        "orders_scope_ok": len(orders) > 0 or sum(v["orders"] for v in revenue_by_month.values()) > 0,
    }

    with open("finance_data.json", "w") as f:
        json.dump(snapshot, f, indent=2)

    print("Wrote finance_data.json")
    print(f"MTD revenue: ${mtd['revenue']:,.2f}  MTD expenses: ${mtd['expenses']:,.2f}  MTD profit: ${mtd['profit']:,.2f}")
    print(f"Open AP: ${total_ap:,.2f} across {len(open_ap)} items")


if __name__ == "__main__":
    main()
