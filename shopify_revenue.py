"""shopify_revenue.py - fetch + aggregate paid Shopify orders. Shared by the
CI sync script and the local Flask app."""

import os
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SHOPIFY_STORE = "elure-maison.myshopify.com"
SHOPIFY_API_VERSION = "2024-01"


def month_key(dt):
    return dt.strftime("%Y-%m")


def fetch_orders(token=None, months_back=13):
    token = token or os.environ.get("SHOPIFY_TOKEN")
    if not token:
        raise RuntimeError("Shopify token not provided - set SHOPIFY_TOKEN or pass token= explicitly")
    since = (datetime.now(timezone.utc) - timedelta(days=months_back * 31)).strftime("%Y-%m-%dT00:00:00Z")
    orders = []
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/orders.json"
    params = {
        "status": "any",
        "financial_status": "paid",
        "created_at_min": since,
        "limit": 250,
        "fields": "id,created_at,total_price,current_total_price,total_discounts,subtotal_price,total_tax,cancelled_at,refunds",
    }
    headers = {"X-Shopify-Access-Token": token}

    while url:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 403:
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
        params = None

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
