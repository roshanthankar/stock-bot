"""
earnings_checker.py
===================
Checks if a stock has results coming up soon.
Uses NSE's official corporate actions calendar — free, no API key.

Philosophy (Option B):
- Never blocks a pick — only warns
- Shows exact results date so user can decide
- Results within 3 days = HIGH RISK warning
- Results within 7 days = CAUTION warning

Fix: Cache now works correctly even when NSE is blocked.
     Calendar fetched ONCE per run — not per symbol.
"""

import requests
import time
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.nseindia.com/",
}

# Cache — fetched once per day
_earnings_cache = {}   # { symbol: { date, date_str } }
_cache_date     = None # date string "YYYY-MM-DD"
_cache_loaded   = False


# ══════════════════════════════════════════════════════════
# NSE CALENDAR FETCHER
# ══════════════════════════════════════════════════════════

def _fetch_nse_earnings(days_ahead: int = 10) -> bool:
    """
    Fetch upcoming results from NSE with proper session handling.
    Returns True if successful, False if blocked.

    IMPORTANT: Only fetches once per day.
    Cache check uses date only — not content — so blocked days
    don't keep retrying for every symbol.
    """
    global _earnings_cache, _cache_date, _cache_loaded

    today = datetime.now().strftime("%Y-%m-%d")

    # Already tried today — return immediately regardless of result
    if _cache_date == today:
        return _cache_loaded

    # Mark as tried for today before attempting
    # This ensures we NEVER retry within same run
    _cache_date   = today
    _cache_loaded = False

    try:
        s = requests.Session()
        s.headers.update(HEADERS)

        # NSE requires visiting homepage first to get cookies
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        s.get("https://www.nseindia.com/market-data/upcoming-result", timeout=10)
        time.sleep(0.5)

        date_from = datetime.now().strftime("%d-%m-%Y")
        date_to   = (datetime.now() + timedelta(days=days_ahead)).strftime("%d-%m-%Y")

        url = (
            f"https://www.nseindia.com/api/corporates-corporateActions"
            f"?index=equities&from_date={date_from}&to_date={date_to}"
        )

        r = s.get(url, timeout=10)

        # Empty or blocked response
        if r.status_code != 200 or not r.text.strip() or r.text.strip() == "[]":
            print("  Earnings calendar: unavailable (NSE blocked) — skipping earnings check")
            return False

        data = r.json()
        if not isinstance(data, list):
            print("  Earnings calendar: unexpected response format")
            return False

        count = 0
        for item in data:
            purpose = item.get("purpose", "").lower()
            symbol  = item.get("symbol", "").upper()
            ex_date = item.get("exDate", "") or item.get("date", "")

            if not symbol or not ex_date:
                continue

            if any(kw in purpose for kw in ["results", "quarterly", "financial"]):
                try:
                    result_dt = datetime.strptime(ex_date, "%d-%b-%Y")
                    _earnings_cache[symbol] = {
                        "symbol":   symbol,
                        "date":     result_dt,
                        "date_str": result_dt.strftime("%d %b %Y")
                    }
                    count += 1
                except Exception:
                    continue

        _cache_loaded = True
        print(f"  Earnings calendar: {count} upcoming results loaded ✅")
        return True

    except Exception as e:
        print(f"  Earnings calendar unavailable: {e}")
        return False


# ══════════════════════════════════════════════════════════
# EARNINGS CHECK PER STOCK
# ══════════════════════════════════════════════════════════

def check_earnings(symbol: str) -> dict:
    """
    Check if a stock has upcoming results.
    Uses cached calendar data — no API call per symbol.

    Returns dict with warning (never blocks — Option B).
    """
    result = {
        "has_upcoming_results": False,
        "days_to_results":      None,
        "results_date":         None,
        "warning":              "",
        "earnings_ok":          True
    }

    # Check cache — if symbol is in it, we have data
    item = _earnings_cache.get(symbol)
    if not item:
        return result

    today     = datetime.now()
    days_away = (item["date"] - today).days

    result["has_upcoming_results"] = True
    result["days_to_results"]      = days_away
    result["results_date"]         = item["date_str"]

    if days_away <= 0:
        result["warning"] = f"📋 Results TODAY — extremely high risk entry"
    elif days_away <= 3:
        result["warning"] = (
            f"⚠️ Results on {item['date_str']} ({days_away} days) — "
            f"HIGH RISK: stock can gap sharply on results"
        )
    elif days_away <= 7:
        result["warning"] = (
            f"📅 Results on {item['date_str']} ({days_away} days) — "
            f"consider waiting until after results"
        )

    return result


# ══════════════════════════════════════════════════════════
# BATCH CHECK
# ══════════════════════════════════════════════════════════

def check_earnings_batch(symbols: list) -> dict:
    """
    Check earnings for a list of symbols.

    Key fix: Fetches NSE calendar ONCE at the start.
    All subsequent per-symbol checks use cached data — instant.
    No repeated API calls or error messages.
    """
    results = {}
    if not symbols:
        return results

    print(f"  Checking earnings calendar for {len(symbols)} candidates...")

    # Fetch calendar once — all symbols checked against this
    _fetch_nse_earnings(days_ahead=10)

    # Check each symbol against cache — no API calls here
    for symbol in symbols:
        results[symbol] = check_earnings(symbol)

    upcoming = sum(1 for r in results.values() if r["has_upcoming_results"])
    if upcoming > 0:
        print(f"  Earnings: {upcoming} stocks have upcoming results ⚠️")

    return results


# ══════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_symbols = ["HDFCBANK", "INFY", "RELIANCE", "TCS", "SBIN"]
    print("Testing earnings checker...")

    results = check_earnings_batch(test_symbols)

    for sym, r in results.items():
        print(f"\n{sym}:")
        if r["has_upcoming_results"]:
            print(f"  Date:    {r['results_date']}")
            print(f"  Days:    {r['days_to_results']}")
            print(f"  Warning: {r['warning']}")
        else:
            print(f"  No upcoming results in next 10 days")