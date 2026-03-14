"""
news_checker.py
===============
Checks recent news for each candidate stock.
Uses Google News RSS feed — free, no API key needed.

Fix: Date window extended to 30 days.
Headlines from January were being filtered out by 7-day cutoff.
Real bad news can be 2-3 weeks old and still matter.

Philosophy (Option B):
- Never blocks a pick — only adds warnings
- User sees the news and makes their own decision
"""

import requests
import time
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET


# ══════════════════════════════════════════════════════════
# KEYWORDS
# ══════════════════════════════════════════════════════════

DANGER_KEYWORDS = [
    "fraud", "scam", "cbi", "enforcement directorate", "ed raid",
    "sebi ban", "sebi order", "sebi action", "insider trading",
    "money laundering", "arrested", "chargesheet",
    "bankruptcy", "insolvency", "debt default", "loan default",
    "npa", "delisted", "delisting", "trading suspended",
    "ceo quits", "ceo resigns", "md quits", "md resigns",
    "chairman steps down", "auditor resigns", "auditor quits",
    "accounting fraud", "account irregularities", "restatement",
]

CAUTION_KEYWORDS = [
    # Only meaningful analyst actions
    "downgrade", "sell rating", "target cut", "target reduced",
    "rating cut", "underperform",
    # Only significant result problems
    "net loss", "quarterly loss", "loss widens",
    "earnings miss", "revenue miss",
    # Regulatory
    "sebi notice", "sebi probe", "income tax notice",
    "gst notice", "penalty imposed", "fine imposed",
    # Serious business events only
    "order cancelled", "contract lost",
    "promoter sells entire", "promoter offloads entire",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _fetch_google_news(symbol: str) -> list:
    """
    Fetch recent news via Google News RSS.
    No date filter — top 20 headlines regardless of age.
    Bad news (fraud, CEO exit) stays relevant for months.
    """
    url = (
        f"https://news.google.com/rss/search"
        f"?q={symbol}+NSE+India&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return []

        root  = ET.fromstring(r.content)
        items = root.findall(".//item")
        news  = []

        for item in items[:20]:
            title = item.findtext("title", "")
            date  = item.findtext("pubDate", "")[:16]
            if title:
                news.append({
                    "title": title.lower(),
                    "raw":   title,
                    "date":  date
                })

        return news

    except Exception:
        return []


def check_news(symbol: str) -> dict:
    """Check recent news. Never blocks — Option B."""
    result = {
        "has_danger_news":  False,
        "has_caution_news": False,
        "warnings":         [],
        "headlines":        [],
        "news_ok":          True
    }

    news_items = _fetch_google_news(symbol)
    if not news_items:
        return result

    seen = set()

    for item in news_items:
        title = item["title"]
        raw   = item["raw"]

        for kw in DANGER_KEYWORDS:
            if kw in title and kw not in seen:
                result["has_danger_news"] = True
                seen.add(kw)
                result["warnings"].append(f"🔴 Serious: '{kw}' in recent news")
                h = f"🔴 {raw[:80]}"
                if h not in result["headlines"]:
                    result["headlines"].append(h)
                break

        for kw in CAUTION_KEYWORDS:
            if kw in title and kw not in seen:
                result["has_caution_news"] = True
                seen.add(kw)
                result["warnings"].append(f"🟡 Note: '{kw}' — check before buying")
                h = f"🟡 {raw[:80]}"
                if h not in result["headlines"]:
                    result["headlines"].append(h)
                break

    result["warnings"]  = list(dict.fromkeys(result["warnings"]))[:2]
    result["headlines"] = list(dict.fromkeys(result["headlines"]))[:2]
    return result


def check_news_batch(symbols: list, delay: float = 0.5) -> dict:
    results = {}
    if not symbols:
        return results

    print(f"  Checking news for {len(symbols)} candidates...")

    for symbol in symbols:
        results[symbol] = check_news(symbol)
        time.sleep(delay)

    danger  = sum(1 for r in results.values() if r["has_danger_news"])
    caution = sum(1 for r in results.values() if r["has_caution_news"])

    if danger > 0 or caution > 0:
        print(f"  News: {danger} danger ⚠️, {caution} caution 🟡")
    else:
        print(f"  News: No flags ✅")

    return results


if __name__ == "__main__":
    for sym in ["HDFCBANK", "PAYTM", "ADANIGREEN"]:
        print(f"\n{sym}:")
        r = check_news(sym)
        print(f"  Danger:   {r['has_danger_news']}")
        print(f"  Caution:  {r['has_caution_news']}")
        if r["warnings"]:
            for w in r["warnings"]:
                print(f"  {w}")
        if r["headlines"]:
            for h in r["headlines"]:
                print(f"  {h}")
        time.sleep(0.5)