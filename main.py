"""
main.py
=======
Master runner for the Stock Opportunity Bot.

Pipeline:
  1. Validate credentials
  2. Check trading day
  3. Connect Fyers + get market context (GIFT Nifty)
  4. Fetch 229 stocks
  5. Technical analysis
  6. Fundamental check (all candidates — light, fast)
  7. Sector diversification → final picks
  8. News check (final picks only — 2-3 stocks)
  9. Earnings check (final picks only — 2-3 stocks)
  10. Send Telegram report

Optimisation: News + earnings only run on final 2-3 picks,
not all 36 candidates. Saves ~90 seconds per run.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════════════
# VALIDATE CREDENTIALS
# ══════════════════════════════════════════════════════════

def validate_credentials() -> bool:
    required = {
        "FYERS_APP_ID":      os.getenv("FYERS_APP_ID"),
        "FYERS_SECRET_KEY":  os.getenv("FYERS_SECRET_KEY"),
        "FYERS_CLIENT_ID":   os.getenv("FYERS_CLIENT_ID"),
        "FYERS_PIN":         os.getenv("FYERS_PIN"),
        "FYERS_TOTP_SECRET": os.getenv("FYERS_TOTP_SECRET"),
        "TELEGRAM_TOKEN":    os.getenv("TELEGRAM_TOKEN"),
        "TELEGRAM_CHAT_ID":  os.getenv("TELEGRAM_CHAT_ID"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"❌ Missing credentials: {', '.join(missing)}")
        return False
    print("  Credentials: ✅ All present")
    return True


# ══════════════════════════════════════════════════════════
# TRADING DAY CHECK
# ══════════════════════════════════════════════════════════

NSE_HOLIDAYS = {
    2026: [
        "2026-01-26", "2026-02-19", "2026-03-20",
        "2026-04-02", "2026-04-03", "2026-04-14",
        "2026-05-01", "2026-08-15", "2026-08-27",
        "2026-10-02", "2026-10-22", "2026-10-23",
        "2026-11-04", "2026-12-25",
    ],
    2027: [
        "2027-01-26", "2027-03-11", "2027-03-26",
        "2027-04-14", "2027-05-01", "2027-08-15",
        "2027-09-16", "2027-10-02", "2027-10-19",
        "2027-11-10", "2027-12-25",
    ],
}
LAST_KNOWN_HOLIDAY_YEAR = max(NSE_HOLIDAYS.keys())


def is_trading_day() -> bool:
    today   = datetime.now()
    weekday = today.weekday()

    if weekday >= 5:
        print(f"  Market check: Weekend — skipping")
        return False

    if today.year > LAST_KNOWN_HOLIDAY_YEAR:
        print(f"  ⚠️ NSE holiday list missing for {today.year} — "
              f"only {LAST_KNOWN_HOLIDAY_YEAR} loaded. Update NSE_HOLIDAYS in main.py.")

    holidays = NSE_HOLIDAYS.get(today.year, [])
    if today.strftime("%Y-%m-%d") in holidays:
        print("  Market check: NSE Holiday — skipping")
        return False

    print(f"  Market check: Trading day ✅ ({today.strftime('%A, %d %b')})")
    return True


# ══════════════════════════════════════════════════════════
# MAX PICKS
# ══════════════════════════════════════════════════════════

def get_max_picks(market_score: int) -> tuple:
    """Returns (max_picks, caution_label)"""
    if market_score >= 3:    return 5, ""
    elif market_score >= 1:  return 4, ""
    elif market_score >= 0:  return 3, ""
    elif market_score >= -2: return 3, "⚠️ Weak market — consider smaller position sizes"
    elif market_score >= -3: return 2, "🟠 Market under pressure — only highest confidence picks shown"
    else:                    return 1, "🔴 Extreme weakness — only strongest opportunity shown today"


# ══════════════════════════════════════════════════════════
# SECTOR DIVERSIFICATION
# ══════════════════════════════════════════════════════════

def apply_sector_diversification(candidates: list, max_picks: int) -> list:
    final        = []
    sector_count = {}
    for stock in candidates:
        if len(final) >= max_picks:
            break
        sector = stock.get("sector", "Other")
        if sector_count.get(sector, 0) < 2:
            final.append(stock)
            sector_count[sector] = sector_count.get(sector, 0) + 1
    return final


# ══════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_log.json")

def _load_log() -> list:
    """Local file is authoritative if present (faster, no network).
    Otherwise pull from Gist — needed on ephemeral CI containers."""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                return json.load(f)
    except Exception:
        pass

    try:
        from gist_pusher import fetch_run_log
        return fetch_run_log()
    except Exception:
        return []

def _save_log(log: list):
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(log[-60:], f, indent=2)
    except Exception:
        pass

    try:
        from gist_pusher import push_run_log
        push_run_log(log)
    except Exception:
        pass

def log_run(status: str, picks: int, scanned: int, error: str = "",
            open_picks: list = None):
    """Append a run entry. open_picks is a list of {symbol, entry, target,
    stop_loss, date} dicts that resolve_open_picks() will check next run."""
    log = _load_log()
    log.append({
        "date":       datetime.now().strftime("%Y-%m-%d"),
        "time":       datetime.now().strftime("%H:%M:%S"),
        "status":     status,
        "picks":      picks,
        "scanned":    scanned,
        "error":      error,
        "open_picks": open_picks or [],
    })
    _save_log(log)


def resolve_open_picks(fyers) -> dict:
    """Check every open pick from prior runs against current price.
    Records a 'WIN' if high since entry >= target, 'LOSS' if low <= stop,
    or leaves it open. Returns counts for the current week."""
    from fyers_fetcher import get_historical_data

    log = _load_log()
    if not log:
        return {"wins": 0, "losses": 0, "open": 0,
                "all_time_wins": 0, "all_time_losses": 0}

    today  = datetime.now()
    cutoff = today - timedelta(days=7)

    for entry in log:
        for pick in entry.get("open_picks", []):
            if pick.get("outcome"):
                continue

            try:
                entry_dt = datetime.strptime(pick["date"], "%Y-%m-%d")
            except Exception:
                pick["outcome"] = "UNKNOWN"
                continue

            days_held = (today - entry_dt).days
            if days_held <= 0:
                continue

            df = get_historical_data(pick["symbol"],
                                     days=max(days_held + 2, 10),
                                     fyers=fyers)
            if df.empty:
                continue

            since = df[df.index >= entry_dt]
            if since.empty:
                continue

            max_high = float(since["high"].max())
            min_low  = float(since["low"].min())

            if max_high >= pick["target"]:
                pick["outcome"] = "WIN"
            elif min_low <= pick["stop_loss"]:
                pick["outcome"] = "LOSS"
            elif days_held >= 21:
                pick["outcome"] = "EXPIRED"

    _save_log(log)

    week_wins = week_losses = week_open = 0
    all_wins  = all_losses = 0

    for entry in log:
        try:
            entry_dt = datetime.strptime(entry.get("date", ""), "%Y-%m-%d")
        except Exception:
            continue

        in_week = entry_dt >= cutoff
        for pick in entry.get("open_picks", []):
            outcome = pick.get("outcome", "OPEN")
            if outcome == "WIN":
                all_wins += 1
                if in_week: week_wins += 1
            elif outcome == "LOSS":
                all_losses += 1
                if in_week: week_losses += 1
            elif in_week:
                week_open += 1

    return {
        "wins":            week_wins,
        "losses":          week_losses,
        "open":            week_open,
        "all_time_wins":   all_wins,
        "all_time_losses": all_losses,
    }


def get_weekly_performance(fyers=None) -> dict:
    """Resolves any open picks against today's prices, then summarises."""
    stats = resolve_open_picks(fyers) if fyers else {
        "wins": 0, "losses": 0, "open": 0,
        "all_time_wins": 0, "all_time_losses": 0,
    }
    total = stats["all_time_wins"] + stats["all_time_losses"]
    all_time_wr = round(stats["all_time_wins"] / total * 100) if total else 0
    return {
        "wins":              stats["wins"],
        "losses":            stats["losses"],
        "open":              stats["open"],
        "all_time_win_rate": all_time_wr,
    }


# ══════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════

def run():
    start_time = time.time()
    today      = datetime.now()
    weekday    = today.weekday()
    test_mode  = "--test" in sys.argv

    print("\n" + "="*50)
    print(f"Stock Bot — {today.strftime('%d %b %Y, %I:%M %p')}")
    print(f"Mode: {'TEST' if test_mode else 'LIVE'}")
    print("="*50)

    if not validate_credentials():
        return

    if not test_mode and not is_trading_day():
        print("  Not a trading day — exiting")
        return

    from fyers_fetcher       import get_fyers_client, fetch_batch, get_market_context
    from analyzer            import analyse_all
    from stocks_list         import ALL_STOCKS
    from telegram_sender     import send_message, format_daily_report, format_friday_report
    from fundamental_checker import check_batch as fundamental_check
    from news_checker        import check_news_batch
    from earnings_checker    import check_earnings_batch

    # ── Connect to Fyers ──────────────────────────────────
    print("\n  Connecting to Fyers...")
    fyers = get_fyers_client()
    if fyers is None:
        print("  ❌ Could not connect to Fyers")
        log_run("FAILED", 0, 0, "Fyers connection failed")
        return

    # ── Market context ────────────────────────────────────
    print("\n  Getting market context...")
    market = get_market_context(fyers=fyers)
    print(f"  Market: {market['description']} | "
          f"Nifty: {market['nifty_change']:+.0f} pts | "
          f"GIFT gap: {market['gift_nifty_gap']:+.2f}% | "
          f"VIX: {market['vix']:.1f}")

    # ── Friday report ─────────────────────────────────────
    if weekday == 4:
        print("\n  Sending Friday performance report...")
        send_message(format_friday_report(get_weekly_performance(fyers)))

    # ── Fetch stock data ──────────────────────────────────
    print(f"\n  Fetching {len(ALL_STOCKS)} stocks...")
    stock_data = fetch_batch(ALL_STOCKS, delay=0.2, max_workers=4)

    if not stock_data:
        send_message("🚨 *Stock Bot Alert*\n❌ No data fetched — Fyers API may be down.")
        log_run("FAILED", 0, 0, "No data fetched")
        return

    # ── Technical analysis ────────────────────────────────
    print(f"\n  Running technical analysis...")
    all_results = analyse_all(stock_data)

    # ── Fundamental check (all candidates) ───────────────
    # Fast — Screener.in light check, only on technical candidates
    if all_results:
        candidate_symbols = [r["symbol"] for r in all_results]
        fundamentals      = fundamental_check(candidate_symbols)

        filtered = []
        for r in all_results:
            fund = fundamentals.get(r["symbol"], {})
            if fund.get("fundamental_ok", True):
                r["fundamental_summary"] = fund.get("summary", "")
                r["pe_ratio"]            = fund.get("pe_ratio")
                filtered.append(r)
            else:
                print(f"  ❌ {r['symbol']}: Removed — {fund.get('summary', 'loss making')}")
        all_results = filtered

    # ── Sector diversification → final picks ─────────────
    max_picks, caution_label = get_max_picks(market["market_score"])
    final_picks = apply_sector_diversification(all_results, max_picks)

    if caution_label:
        market["caution_label"] = caution_label

    # ── News check (final picks only — 2-3 stocks) ───────
    # Moved here deliberately — saves 90s vs checking all 36 candidates
    if final_picks:
        pick_symbols = [r["symbol"] for r in final_picks]
        news_results = check_news_batch(pick_symbols)

        for r in final_picks:
            news = news_results.get(r["symbol"], {})
            r["news_warnings"]  = news.get("warnings", [])
            r["news_headlines"] = news.get("headlines", [])
            r["has_danger_news"]= news.get("has_danger_news", False)

    # ── Earnings check (final picks only — 2-3 stocks) ───
    if final_picks:
        pick_symbols     = [r["symbol"] for r in final_picks]
        earnings_results = check_earnings_batch(pick_symbols)

        for r in final_picks:
            earn = earnings_results.get(r["symbol"], {})
            r["earnings_warning"]     = earn.get("warning", "")
            r["has_upcoming_results"] = earn.get("has_upcoming_results", False)
            r["results_date"]         = earn.get("results_date", "")

    elapsed = round(time.time() - start_time, 1)
    print(f"\n  Final picks: {len(final_picks)} | "
          f"Scanned: {len(stock_data)} | "
          f"Time: {elapsed}s")

    # ── Send report ───────────────────────────────────────
    print("\n  Sending Telegram report...")
    report = format_daily_report(
        picks          = final_picks,
        market_context = market,
        stocks_scanned = len(stock_data)
    )
    sent = send_message(report)

    if sent:
        print("  ✅ Report sent successfully")
        open_picks = [
            {
                "symbol":    p["symbol"],
                "entry":     p["price"],
                "target":    p["target"],
                "stop_loss": p["stop_loss"],
                "date":      today.strftime("%Y-%m-%d"),
            }
            for p in final_picks
        ]
        log_run("SUCCESS", len(final_picks), len(stock_data),
                open_picks=open_picks)

        # Push to iOS widget
        from gist_pusher import push_to_gist, push_no_picks
        if final_picks:
            push_to_gist(final_picks, market)
        else:
            push_no_picks(market)

    else:
        print("  ❌ Failed to send report")
        log_run("FAILED", 0, len(stock_data), "Telegram send failed")

    print(f"\n{'='*50}")
    print(f"DONE — {len(final_picks)} picks sent in {elapsed}s")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()