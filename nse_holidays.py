"""
nse_holidays.py
===============
Live NSE trading-holiday lookup.

Replaces the previously hardcoded NSE_HOLIDAYS dict in main.py — that list
got stale (missed Bakri Eid 2026) and the bot fired on a holiday. This
module fetches NSE's official holiday-master endpoint, caches it, and
falls back to a baked-in list if the network is unreachable.
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Optional

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          ".nse_holidays.json")
CACHE_TTL_DAYS  = 7
NSE_HOME        = "https://www.nseindia.com"
NSE_HOLIDAY_URL = "https://www.nseindia.com/api/holiday-master?type=trading"

# Used only if NSE is unreachable AND there is no usable cache. Keep this
# in sync with the official NSE calendar; it is a safety net, not the
# source of truth.
FALLBACK_HOLIDAYS = {
    2026: [
        "2026-01-26", "2026-02-19", "2026-03-20",
        "2026-04-02", "2026-04-03", "2026-04-14",
        "2026-05-01", "2026-05-27", "2026-05-28",
        "2026-08-15", "2026-08-27", "2026-10-02",
        "2026-10-22", "2026-10-23", "2026-11-04",
        "2026-12-25",
    ],
    2027: [
        "2027-01-26", "2027-03-11", "2027-03-26",
        "2027-04-14", "2027-05-01", "2027-08-15",
        "2027-09-16", "2027-10-02", "2027-10-19",
        "2027-11-10", "2027-12-25",
    ],
}


def _load_cache() -> Optional[List[str]]:
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        with open(CACHE_FILE) as f:
            data = json.load(f)
        fetched = datetime.strptime(data["fetched"], "%Y-%m-%d")
        if (datetime.now() - fetched).days > CACHE_TTL_DAYS:
            return None
        return data["holidays"]
    except Exception:
        return None


def _save_cache(holidays: List[str]) -> None:
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({
                "fetched":  datetime.now().strftime("%Y-%m-%d"),
                "holidays": holidays,
            }, f, indent=2)
    except Exception:
        pass


def _fetch_from_nse() -> List[str]:
    """Hit NSE's holiday-master endpoint. Returns YYYY-MM-DD strings.

    NSE blocks bare requests — you have to visit the home page first to
    pick up the cookies their CDN sets, then reuse the session."""
    session = requests.Session()
    headers = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.nseindia.com/",
    }
    session.get(NSE_HOME, headers=headers, timeout=10)
    resp = session.get(NSE_HOLIDAY_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    # Response shape: { "CM": [ { "tradingDate": "27-May-2026", ... }, ... ], ... }
    cm = payload.get("CM", [])
    out = []
    for entry in cm:
        raw = entry.get("tradingDate", "")
        try:
            out.append(datetime.strptime(raw, "%d-%b-%Y").strftime("%Y-%m-%d"))
        except Exception:
            continue
    return sorted(set(out))


def get_holidays() -> List[str]:
    """Return list of NSE trading holidays as YYYY-MM-DD strings.

    Tries cache → NSE live → hardcoded fallback (current year only). If
    the live fetch returns empty, we treat it as a failure and fall back
    rather than caching an empty list."""
    cached = _load_cache()
    if cached is not None:
        return cached

    try:
        holidays = _fetch_from_nse()
        if holidays:
            _save_cache(holidays)
            return holidays
        print("  ⚠️ NSE holiday API returned empty — using fallback list")
    except Exception as e:
        print(f"  ⚠️ NSE holiday fetch failed ({e}) — using fallback list")

    current_year = datetime.now().year
    fallback     = FALLBACK_HOLIDAYS.get(current_year, [])
    if not fallback:
        # Both live fetch and fallback failed. Without this warning the bot
        # would silently trade on every real holiday until someone notices.
        max_known = max(FALLBACK_HOLIDAYS.keys()) if FALLBACK_HOLIDAYS else current_year
        print(f"  🚨 CRITICAL: no holiday data for {current_year} "
              f"(fallback ends at {max_known}). Bot may fire on holidays — "
              f"update FALLBACK_HOLIDAYS in nse_holidays.py.")
    return fallback


def is_holiday(date: Optional[datetime] = None) -> bool:
    if date is None:
        date = datetime.now()
    return date.strftime("%Y-%m-%d") in get_holidays()
