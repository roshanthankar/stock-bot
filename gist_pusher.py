"""
gist_pusher.py
==============
Pushes the daily stock picks JSON to a GitHub Gist.
The iOS widget fetches from this Gist's raw URL.

Setup (one-time):
  1. Go to github.com/settings/tokens → Generate new token (classic)
     → Select "gist" scope only → Copy token
  2. Go to gist.github.com → Create new public Gist
     → Filename: stock_picks.json → Content: {} → Create
     → Copy the Gist ID from the URL
  3. Add to your .env:
       GITHUB_TOKEN=your_personal_access_token
       GIST_ID=your_gist_id
  4. Add same secrets to GitHub Actions repo secrets

Called from main.py after successful report send.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GH_TOKEN", "")
GIST_ID      = os.getenv("GIST_ID", "")
GIST_FILE    = "stock_picks.json"
LOG_FILE     = "run_log.json"


def _gist_headers() -> dict:
    return {
        "Authorization":        f"Bearer {GITHUB_TOKEN}",
        "Accept":                "application/vnd.github+json",
        "X-GitHub-Api-Version":  "2022-11-28",
    }


def fetch_run_log() -> list:
    """Pull the latest run_log.json from the Gist so weekly stats survive
    ephemeral GitHub Actions containers. Returns [] on any failure."""
    if not GITHUB_TOKEN or not GIST_ID:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers=_gist_headers(),
            timeout=10
        )
        if r.status_code != 200:
            return []
        files   = r.json().get("files", {})
        content = files.get(LOG_FILE, {}).get("content", "")
        return json.loads(content) if content else []
    except Exception:
        return []


def push_run_log(log: list) -> bool:
    """Push the run_log.json back to the Gist alongside stock_picks.json."""
    if not GITHUB_TOKEN or not GIST_ID:
        return False
    try:
        r = requests.patch(
            f"https://api.github.com/gists/{GIST_ID}",
            headers=_gist_headers(),
            json={
                "files": {
                    LOG_FILE: {
                        "content": json.dumps(log[-60:], indent=2)
                    }
                }
            },
            timeout=15
        )
        return r.status_code == 200
    except Exception:
        return False


def push_to_gist(picks: list, market_context: dict) -> bool:
    """
    Format picks into widget-friendly JSON and push to GitHub Gist.

    JSON structure the iOS widget expects:
    {
        "updated":      "16 Mar 2026, 08:02 AM",
        "market":       "POSITIVE DAY",
        "market_score": 2,
        "picks": [
            {
                "symbol":       "HDFCBANK",
                "sector":       "Banking",
                "signal":       "STRONG BUY",
                "confidence":   78.5,
                "signal_type":  "PULLBACK BUY",
                "price":        1650.75,
                "target":       1821.50,
                "stop_loss":    1568.20,
                "upside_pct":   10.3,
                "downside_pct": 4.9,
                "risk_reward":  2.43,
                "reason":       "Strong stock pulled back 12.4% from highs."
            }
        ]
    }
    """
    if not GITHUB_TOKEN or not GIST_ID:
        print("  Gist push skipped — GITHUB_TOKEN or GIST_ID missing")
        return False

    try:
        now          = datetime.now()
        market_label = (market_context.get("description", "Unknown")
                        .replace("🟢", "").replace("🔴", "")
                        .replace("🟡", "").replace("🟠", "")
                        .strip())

        # Build picks array — only include fields the widget needs
        widget_picks = []
        for pick in picks:
            # Use first reason as the "why invest" line
            reasons = pick.get("reasons", [])
            reason  = reasons[0] if reasons else pick.get("signal_type", "")

            widget_picks.append({
                "symbol":       pick["symbol"],
                "sector":       pick.get("sector", ""),
                "signal":       pick.get("signal", ""),
                "confidence":   round(float(pick.get("confidence", 0)), 1),
                "signal_type":  pick.get("signal_type", ""),
                "price":        round(float(pick.get("price", 0)), 2),
                "target":       round(float(pick.get("target", 0)), 2),
                "stop_loss":    round(float(pick.get("stop_loss", 0)), 2),
                "upside_pct":   round(float(pick.get("upside_pct", 0)), 1),
                "downside_pct": round(float(pick.get("downside_pct", 0)), 1),
                "risk_reward":  round(float(pick.get("risk_reward", 0)), 2),
                "reason":       reason,
            })

        payload = {
            "updated":      now.strftime("%d %b %Y, %I:%M %p"),
            "market":       market_label,
            "market_score": int(market_context.get("market_score", 0)),
            "picks":        widget_picks,
        }

        # Update Gist via GitHub API
        response = requests.patch(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept":        "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "files": {
                    GIST_FILE: {
                        "content": json.dumps(payload, indent=2, ensure_ascii=False)
                    }
                }
            },
            timeout=15
        )

        if response.status_code == 200:
            gist_url = response.json().get("html_url", "")
            print(f"  Widget data pushed to Gist ✅")
            print(f"  Raw URL: https://gist.githubusercontent.com/{_get_username()}/{GIST_ID}/raw/{GIST_FILE}")
            return True
        else:
            print(f"  Gist push failed: {response.status_code} {response.text[:100]}")
            return False

    except Exception as e:
        print(f"  Gist push error: {e}")
        return False


def _get_username() -> str:
    """Fetch GitHub username from token."""
    try:
        r = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
            timeout=5
        )
        return r.json().get("login", "YOUR_USERNAME")
    except Exception:
        return "YOUR_USERNAME"


def push_no_picks(market_context: dict) -> bool:
    """Push empty picks state — widget shows 'No picks today'."""
    return push_to_gist([], market_context)


# ══════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_picks = [
        {
            "symbol":       "HDFCBANK",
            "sector":       "Banking",
            "signal":       "STRONG BUY 🟢",
            "confidence":   78.5,
            "signal_type":  "PULLBACK BUY",
            "price":        1650.75,
            "target":       1821.50,
            "stop_loss":    1568.20,
            "upside_pct":   10.3,
            "downside_pct": 4.9,
            "risk_reward":  2.43,
            "reasons":      ["Strong stock pulled back 12.4% from highs. Long term uptrend intact."],
        }
    ]

    test_market = {
        "description":  "POSITIVE DAY 🟢",
        "market_score": 2,
        "nifty_change": 45,
        "vix":          14.2,
    }

    result = push_to_gist(test_picks, test_market)
    print(f"Push result: {result}")