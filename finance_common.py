"""
finance_common.py

Shared accounting logic used by both the local Flask app (app.py, live
editing) and the static site generator (sync_finance_dashboard.py +
generate_dashboard.py, GitHub Actions auto-refresh). Mirrors the pattern
used in the MannaHouse project's dashboard_common.py - one place for
transaction-type classification and P&L math so both surfaces can't
silently drift apart.

Expense categorization mirrors MannaHouse's simplified entry: the user only
ever picks "Expense" (revenue is Shopify-only, not manually entered here),
plus an "Unpaid" checkbox. The granular accounting type is auto-detected:
  - unpaid=True                          -> accounts_payable
  - category contains a COGS/production hint -> cogs
  - otherwise                            -> operating_expense
"Other expense" exists as a type but nothing currently auto-classifies into
it - reserved for manual override if ever needed.
"""

from datetime import datetime, date
from collections import defaultdict

EXPENSE_TYPES = ["cogs", "operating_expense", "other_expense", "accounts_payable"]
TYPE_LABELS = {
    "cogs": "COGS",
    "operating_expense": "Operating Expense",
    "other_expense": "Other Expense",
    "accounts_payable": "Accounts Payable",
}

COGS_HINTS = ("cogs", "production", "sourcing", "sampling", "packaging")

CATEGORIES = [
    "COGS / Production",
    "Shipping",
    "Advertising",
    "Software / Apps",
    "Website",
    "Payroll / Contractors",
    "Packaging",
    "Fees (Shopify, payment processing)",
    "Sourcing / Sampling",
    "Other",
]

DEFAULT_PAYMENT_METHODS = [
    "Visa ...6539",
]


def normalize_type(category, unpaid):
    if unpaid:
        return "accounts_payable"
    cat_lower = (category or "").lower()
    if any(hint in cat_lower for hint in COGS_HINTS):
        return "cogs"
    return "operating_expense"


def type_label(t):
    return TYPE_LABELS.get(t, t)


def month_key(dt):
    return dt.strftime("%Y-%m")


def build_month_range(months_back, anchor=None):
    anchor = anchor or datetime.now()
    months = []
    y, m = anchor.year, anchor.month
    for i in range(months_back - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        months.append(f"{yy:04d}-{mm:02d}")
    return months


def compute_monthly_forecast(actuals, forecast_months=6, growth_pct=0.0):
    """
    actuals: list of {"month": "YYYY-MM", "revenue": x, "expenses": y} sorted ascending.
    Forecast = trailing-3-actual-month average, compounded by growth_pct/month.
    Returns list of forecast rows in the same shape, months continuing after actuals.
    """
    if not actuals:
        return []
    trail = actuals[-3:] if len(actuals) >= 3 else actuals
    avg_rev = sum(a["revenue"] for a in trail) / len(trail)
    avg_exp = sum(a["expenses"] for a in trail) / len(trail)

    last_month = actuals[-1]["month"]
    y, m = int(last_month[:4]), int(last_month[5:7])

    rows = []
    rev, exp = avg_rev, avg_exp
    for i in range(1, forecast_months + 1):
        rev *= (1 + growth_pct / 100)
        exp *= (1 + growth_pct / 100)
        m += 1
        if m > 12:
            m = 1
            y += 1
        rows.append({
            "month": f"{y:04d}-{m:02d}",
            "revenue": round(rev, 2),
            "expenses": round(exp, 2),
            "profit": round(rev - exp, 2),
            "actual": False,
        })
    return rows


def compute_annual_forecast(monthly_actuals, monthly_forecast):
    """
    monthly_actuals + monthly_forecast: combined list of {"month","revenue","expenses"}.
    Groups by year; current year (if it has both actual + forecast months) is
    labeled "Actual + Projected".
    """
    this_year = datetime.now().year
    combined = defaultdict(lambda: {"revenue": 0.0, "expenses": 0.0, "actual_months": 0, "forecast_months": 0})
    all_rows = [(r, True) for r in monthly_actuals] + [(r, False) for r in monthly_forecast]
    for r, is_actual in all_rows:
        y = int(r["month"][:4])
        combined[y]["revenue"] += r["revenue"]
        combined[y]["expenses"] += r["expenses"]
        if is_actual:
            combined[y]["actual_months"] += 1
        else:
            combined[y]["forecast_months"] += 1

    years = []
    for y in sorted(combined.keys()):
        c = combined[y]
        if c["forecast_months"] == 0:
            label = "Actual"
        elif c["actual_months"] == 0:
            label = "Projected"
        else:
            label = "Actual + Projected"
        years.append({
            "year": y,
            "label": label,
            "revenue": round(c["revenue"], 2),
            "expenses": round(c["expenses"], 2),
            "profit": round(c["revenue"] - c["expenses"], 2),
        })
    return years


def group_ap_by_due_date(open_ap):
    """open_ap: list of expense dicts with due_date, amount, category, description, vendor."""
    groups = defaultdict(list)
    for item in open_ap:
        key = item.get("due_date") or ""
        groups[key].append(item)

    today = date.today().isoformat()
    result = []
    for due_date in sorted(groups.keys(), key=lambda d: (d == "", d)):
        items = groups[due_date]
        total = sum(i["amount"] for i in items)
        result.append({
            "due_date": due_date or None,
            "overdue": bool(due_date) and due_date < today,
            "total": round(total, 2),
            "count": len(items),
            "items": items,
        })
    return result
