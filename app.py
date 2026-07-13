"""
app.py

Local live-editing dashboard. Run with `py app.py`, opens at
http://127.0.0.1:5058 (not 5057 - that's the MannaHouse project's port on
this machine, kept separate to avoid any collision).

Two-way sync with the "Elure Maison - Expenses" Google Sheet: every
add/edit/delete writes straight through to the Sheet via sheet_write.py.
A "Sync from Sheet" button pulls in anything hand-edited in the Sheet.
Shopify revenue is fetched live on each Dashboard load (read-only - orders
aren't editable here, only expenses are).
"""

import sqlite3
from datetime import datetime, timezone
from collections import defaultdict
from flask import Flask, request, redirect, url_for, session, Response

from finance_common import (
    normalize_type, type_label, CATEGORIES, build_month_range,
    compute_monthly_forecast, compute_annual_forecast, group_ap_by_due_date,
)
from shopify_revenue import fetch_orders, aggregate_revenue, month_key
from render import shell, dashboard_body, monthly_body, annual_body, ap_body
import sync_sheet
import sheet_write
from init_db import init_db, DB_FILE
from local_config import SHOPIFY_TOKEN

APP_PASSWORD = "Proverbs16:3"
MONTHS_BACK = 13
FORECAST_MONTHS = 6

app = Flask(__name__)
app.secret_key = "elure-maison-finance-local-dev-key"

init_db()

NAV_URLS = {"dashboard": "/", "monthly": "/monthly", "annual": "/annual", "ap": "/ap"}


@app.before_request
def require_login():
    if request.path in ("/login", "/static") or request.path.startswith("/static/"):
        return
    if not session.get("authenticated"):
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        error = "Incorrect password."
    from render import VERSE
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Elure Maison — Finance</title>
    <style>
    body {{ font-family: system-ui, sans-serif; background:#0d0d0d; color:#fff; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
    form {{ display:flex; flex-direction:column; gap:12px; width:260px; }}
    input {{ padding:10px 12px; border-radius:8px; border:1px solid #444; background:#1a1a19; color:#fff; font-size:14px; }}
    button {{ padding:10px 12px; border-radius:8px; border:none; background:#2a78d6; color:#fff; font-size:14px; cursor:pointer; }}
    .err {{ color:#e66767; font-size:12.5px; }}
    .verse {{ font-size:12px; font-style:italic; color:#aaa; text-align:center; }}
    </style></head><body>
    <form method="POST">
    <div style="font-size:15px; font-weight:600; text-align:center;">Elure Maison — Finance</div>
    <input type="password" name="password" placeholder="Password" autofocus>
    <button type="submit">Log in</button>
    <div class="err">{error}</div>
    <div class="verse">{VERSE}</div>
    </form></body></html>"""


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_payment_methods():
    conn = db()
    rows = conn.execute("SELECT name FROM payment_methods ORDER BY sort_order").fetchall()
    conn.close()
    return [r["name"] for r in rows]


def register_payment_method(name):
    if not name:
        return
    conn = db()
    row = conn.execute("SELECT MAX(sort_order) AS m FROM payment_methods").fetchone()
    next_order = (row["m"] or 0) + 1
    conn.execute("INSERT OR IGNORE INTO payment_methods (name, sort_order) VALUES (?, ?)", (name, next_order))
    conn.commit()
    conn.close()


def build_finance_data(include_shopify=True):
    conn = db()
    txns = [dict(r) for r in conn.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()]
    conn.close()

    for t in txns:
        t["unpaid"] = bool(t["unpaid"])
        t["type_label"] = type_label(t["type"])

    revenue_by_month = {}
    if include_shopify:
        orders = fetch_orders(token=SHOPIFY_TOKEN)
        revenue_by_month = aggregate_revenue(orders)

    months = build_month_range(MONTHS_BACK)
    expenses_by_month = defaultdict(float)
    category_totals_current_month = defaultdict(float)
    current_month = months[-1]
    for t in txns:
        m = t["date"][:7]
        expenses_by_month[m] += t["amount"]
        if m == current_month:
            category_totals_current_month[t["category"]] += t["amount"]

    series = []
    for m in months:
        rev = revenue_by_month.get(m, {"gross": 0.0, "refunds": 0.0, "orders": 0})
        net_revenue = rev["gross"] - rev["refunds"]
        exp = expenses_by_month.get(m, 0.0)
        series.append({
            "month": m, "revenue": round(net_revenue, 2), "orders": rev["orders"],
            "expenses": round(exp, 2), "profit": round(net_revenue - exp, 2),
        })

    mtd = series[-1]
    ytd_months = [s for s in series if s["month"].startswith(str(datetime.now().year))]
    ytd_revenue = sum(s["revenue"] for s in ytd_months)
    ytd_expenses = sum(s["expenses"] for s in ytd_months)

    open_ap = [t for t in txns if t["unpaid"]]
    total_ap = round(sum(t["amount"] for t in open_ap), 2)
    ap_groups = group_ap_by_due_date(open_ap)

    monthly_forecast = compute_monthly_forecast(series, forecast_months=FORECAST_MONTHS, growth_pct=0.0)
    annual = compute_annual_forecast(series, monthly_forecast)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_display": datetime.now().strftime("%b %d, %Y %H:%M"),
        "monthly": series,
        "monthly_forecast": monthly_forecast,
        "annual": annual,
        "mtd": mtd,
        "ytd": {"revenue": round(ytd_revenue, 2), "expenses": round(ytd_expenses, 2), "profit": round(ytd_revenue - ytd_expenses, 2)},
        "current_month_expense_breakdown": [
            {"category": k, "amount": round(v, 2)} for k, v in sorted(category_totals_current_month.items(), key=lambda x: -x[1])
        ],
        "recent_expenses": txns[:20],
        "total_ap": total_ap,
        "ap_groups": ap_groups,
    }


def page(title, active_tab, body_html, data):
    return shell(title, active_tab, NAV_URLS, body_html, data, gate_hash=None)


@app.route("/")
def dashboard():
    data = build_finance_data()
    pm_options = "".join(f'<option value="{p}"></option>' for p in get_payment_methods())
    body = dashboard_body(data, editable=True).replace("{PAYMENT_METHOD_OPTIONS}", pm_options)
    body = f'<div style="margin-bottom:12px;"><a href="/sync" class="fd-btn">Sync from Sheet</a> <form method="POST" action="/logout" style="display:inline;"><button class="fd-btn" type="submit">Log out</button></form></div>' + body
    return page("Elure Maison — Finance Dashboard", "dashboard", body, data)


@app.route("/monthly")
def monthly():
    data = build_finance_data()
    return page("Elure Maison — Monthly P&L", "monthly", monthly_body(data), data)


@app.route("/annual")
def annual():
    data = build_finance_data()
    return page("Elure Maison — Annual P&L", "annual", annual_body(data), data)


@app.route("/ap")
def ap():
    data = build_finance_data(include_shopify=False)
    return page("Elure Maison — Accounts Payable", "ap", ap_body(data, editable=True), data)


@app.route("/sync")
def sync_route():
    n = sync_sheet.sync()
    return redirect(url_for("dashboard"))


def parse_form():
    f = request.form
    category = f.get("category", "Other")
    unpaid = f.get("unpaid") == "1"
    payment_method = f.get("payment_method", "").strip()
    new_pm = f.get("new_payment_method", "").strip()
    if new_pm:
        payment_method = new_pm
        register_payment_method(new_pm)
    return {
        "date": f.get("date", ""),
        "category": category,
        "vendor": f.get("vendor", ""),
        "description": f.get("description", ""),
        "amount": float(f.get("amount") or 0),
        "payment_method": payment_method,
        "notes": f.get("notes", ""),
        "unpaid": unpaid,
        "due_date": f.get("due_date") or None,
        "type": normalize_type(category, unpaid),
    }


@app.route("/add", methods=["POST"])
def add():
    txn = parse_form()
    sheet_row = sheet_write.append_row(txn)
    conn = db()
    conn.execute("""
        INSERT INTO transactions (date, category, vendor, description, amount, payment_method, notes, unpaid, due_date, type, sheet_row)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (txn["date"], txn["category"], txn["vendor"], txn["description"], txn["amount"],
          txn["payment_method"], txn["notes"], int(txn["unpaid"]), txn["due_date"], txn["type"], sheet_row))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/edit/<int:txn_id>", methods=["GET", "POST"])
def edit(txn_id):
    conn = db()
    existing = conn.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)).fetchone()
    if not existing:
        conn.close()
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        txn = parse_form()
        sheet_write.update_row(existing["sheet_row"], txn)
        conn.execute("""
            UPDATE transactions SET date=?, category=?, vendor=?, description=?, amount=?, payment_method=?, notes=?, unpaid=?, due_date=?, type=?
            WHERE id=?
        """, (txn["date"], txn["category"], txn["vendor"], txn["description"], txn["amount"],
              txn["payment_method"], txn["notes"], int(txn["unpaid"]), txn["due_date"], txn["type"], txn_id))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    conn.close()
    cats_options = "".join(f'<option value="{c}" {"selected" if c == existing["category"] else ""}>{c}</option>' for c in CATEGORIES)
    unpaid_checked = "checked" if existing["unpaid"] else ""
    due_display = "flex" if existing["unpaid"] else "none"
    body = f"""
    <div class="fd-card">
      <div class="fd-card-head"><h2 class="fd-card-title">Edit expense</h2></div>
      <form method="POST" class="fd-form-row" style="align-items:end;">
        <label>Date <input type="date" name="date" value="{existing['date']}" required></label>
        <label>Category <select name="category">{cats_options}</select></label>
        <label>Vendor <input type="text" name="vendor" value="{existing['vendor'] or ''}"></label>
        <label>Description <input type="text" name="description" value="{existing['description'] or ''}"></label>
        <label>Amount <input type="number" step="0.01" name="amount" value="{existing['amount']}" required></label>
        <label>Payment method <input type="text" name="payment_method" value="{existing['payment_method'] or ''}"></label>
        <label style="flex-direction:row; align-items:center; gap:6px;"><input type="checkbox" name="unpaid" value="1" {unpaid_checked} onchange="document.getElementById('due-date-field').style.display=this.checked?'flex':'none'" style="width:auto;"> Unpaid</label>
        <label id="due-date-field" style="display:{due_display};">Due date <input type="date" name="due_date" value="{existing['due_date'] or ''}"></label>
        <button type="submit" class="fd-btn">Save</button>
        <a href="/" class="fd-btn" style="background:var(--text-muted);">Cancel</a>
      </form>
    </div>
    """
    data = build_finance_data(include_shopify=False)
    return page("Edit expense", "dashboard", body, data)


@app.route("/delete/<int:txn_id>", methods=["POST"])
def delete(txn_id):
    conn = db()
    existing = conn.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)).fetchone()
    if existing:
        sheet_write.clear_row(existing["sheet_row"])
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/mark_paid/<int:txn_id>", methods=["POST"])
def mark_paid(txn_id):
    conn = db()
    existing = conn.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)).fetchone()
    if existing:
        t = normalize_type(existing["category"], False)
        txn = {
            "date": existing["date"], "category": existing["category"], "vendor": existing["vendor"],
            "description": existing["description"], "amount": existing["amount"],
            "payment_method": existing["payment_method"], "notes": existing["notes"],
            "unpaid": False, "due_date": None, "type": t,
        }
        sheet_write.update_row(existing["sheet_row"], txn)
        conn.execute("UPDATE transactions SET unpaid=0, due_date=NULL, type=? WHERE id=?", (t, txn_id))
        conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


if __name__ == "__main__":
    print("Elure Maison Finance — http://127.0.0.1:5058")
    app.run(debug=True, port=5058)
