"""fx_convert.py - historical currency conversion via the free Frankfurter API
(ECB rates, no API key required). Used to convert a PHP-denominated expense
to its USD equivalent as of the actual transaction date, since the dashboard's
math is USD throughout.
"""

import requests

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/{date}"


def get_historical_rate(date_str, base="PHP", target="USD"):
    """Returns the rate such that amount_in_base * rate = amount_in_target."""
    resp = requests.get(FRANKFURTER_URL.format(date=date_str), params={"from": base, "to": target}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["rates"][target]


def convert_to_usd(amount, currency, date_str):
    """Returns (usd_amount, rate_used). currency='USD' is a no-op (rate=1.0)."""
    if currency == "USD":
        return round(amount, 2), 1.0
    rate = get_historical_rate(date_str, base=currency, target="USD")
    return round(amount * rate, 2), rate
