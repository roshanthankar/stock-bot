"""
telegram_sender.py
==================
Formats analysis results into clean, plain English Telegram messages.

Includes:
- Nifty shown in points (not %) — fixed
- GIFT Nifty gap for today's open estimate
- Market caution label on weak days
- Fundamental summary per pick
- News warnings (danger + caution)
- Earnings date warnings
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# ══════════════════════════════════════════════════════════
# SEND FUNCTION
# ══════════════════════════════════════════════════════════

def send_message(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  Telegram credentials missing — printing to console")
        print(text)
        return False

    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        r = requests.post(url, json=data, timeout=15)
        if r.status_code == 200:
            return True
        if r.status_code == 400 and len(text) > 4000:
            return _send_long_message(text)
        print(f"  Telegram error: {r.status_code} {r.text[:100]}")
        return False
    except Exception as e:
        print(f"  Telegram send error: {e}")
        return False


def _send_long_message(text: str) -> bool:
    parts = []
    while len(text) > 4000:
        split_at = text[:4000].rfind("\n")
        if split_at == -1:
            split_at = 4000
        parts.append(text[:split_at])
        text = text[split_at:]
    parts.append(text)
    return all(send_message(p) for p in parts)


# ══════════════════════════════════════════════════════════
# FORMAT INDIVIDUAL PICK
# ══════════════════════════════════════════════════════════

def format_pick(result: dict, rank: int) -> str:
    symbol     = result["symbol"]
    price      = result["price"]
    target     = result["target"]
    stop_loss  = result["stop_loss"]
    upside     = result["upside_pct"]
    downside   = result["downside_pct"]
    rr         = result["risk_reward"]
    confidence = result["confidence"]
    signal     = result["signal"]
    sig_type   = result["signal_type"]
    emoji      = result.get("emoji", "📊")
    sector     = result.get("sector", "")
    reasons    = result.get("reasons", [])
    warnings   = result.get("warnings", [])
    timing     = result.get("entry_timing", "NEUTRAL")

    # Extra context
    fund_summary     = result.get("fundamental_summary", "")
    news_warnings    = result.get("news_warnings", [])
    news_headlines   = result.get("news_headlines", [])
    has_danger_news  = result.get("has_danger_news", False)
    earnings_warning = result.get("earnings_warning", "")

    timing_line = {
        "IDEAL":   "⏰ _Entry timing: Ideal right now_",
        "WAIT":    "⏳ _Entry timing: Wait for small pullback_",
        "NEUTRAL": "🕐 _Entry timing: Neutral_"
    }.get(timing, "")

    filled         = int(confidence / 10)
    conf_bar       = "█" * filled + "░" * (10 - filled)
    risk_10_shares = round((price - stop_loss) * 10, 2)

    type_desc = {
        "PULLBACK BUY":           "Pulled back from highs — buying opportunity",
        "BREAKOUT BUY":           "Breaking above resistance — momentum building",
        "RECOVERY BUY":           "Recovering from oversold — bounce in progress",
        "CONSOLIDATION BREAKOUT": "Breaking out of tight range — move starting",
        "TECHNICAL BUY":          "Multiple indicators aligned"
    }.get(sig_type, sig_type)

    reasons_text  = "".join(f"  • {r}\n" for r in reasons[:3])
    warnings_text = "".join(f"  ⚠️ {w}\n" for w in warnings[:2])

    msg = (
        f"*#{rank} {symbol}*  |  {sector}\n"
        f"{emoji} _{type_desc}_\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 Signal: *{signal}*\n"
        f"🎯 Confidence: {conf_bar} {confidence}%\n"
        f"\n"
        f"💰 *Buy at:*    ₹{price}\n"
        f"🎯 *Target:*    ₹{target}  _(+{upside}%)_\n"
        f"🛑 *Stop Loss:* ₹{stop_loss}  _(-{downside}%)_\n"
        f"⚖️ *Risk/Reward:* {rr}x\n"
        f"\n"
        f"💸 *Max loss per 10 shares:* ₹{risk_10_shares}\n"
        f"📌 *Suggested:* Never invest more than 5-10% of your capital in one pick\n"
        f"\n"
        f"*Why this stock?*\n"
        f"{reasons_text}"
    )

    if warnings_text:
        msg += f"\n*Technical notes:*\n{warnings_text}"

    if fund_summary:
        msg += f"\n🏢 *Company:* {fund_summary}\n"

    if earnings_warning:
        msg += f"\n{earnings_warning}\n"

    if news_warnings:
        msg += f"\n*Recent news:*\n"
        for w in news_warnings[:2]:
            msg += f"  {w}\n"

    if news_headlines and has_danger_news:
        msg += f"\n*Headlines:*\n"
        for h in news_headlines[:2]:
            msg += f"  _{h}_\n"

    if timing_line:
        msg += f"\n{timing_line}\n"

    msg += f"\n🔗 [View on Screener](https://www.screener.in/company/{symbol}/)\n"
    return msg


# ══════════════════════════════════════════════════════════
# FORMAT DAILY REPORT
# ══════════════════════════════════════════════════════════

def format_daily_report(picks: list, market_context: dict, stocks_scanned: int) -> str:
    today      = datetime.now().strftime("%A, %d %b %Y")
    now        = datetime.now().strftime("%I:%M %p")
    mkt_score  = market_context.get("market_score", 0)
    mkt_desc   = market_context.get("description", "Unknown")
    nifty_chg  = market_context.get("nifty_change", 0)
    gift_gap   = market_context.get("gift_nifty_gap", 0)
    vix        = market_context.get("vix", 0)
    caution    = market_context.get("caution_label", "")
    nifty_icon = "🟢" if nifty_chg > 0 else "🔴"
    gift_icon  = "🟢" if gift_gap > 0 else "🔴"

    # ── Header ────────────────────────────────────────────
    header = (
        f"🤖 *STOCK OPPORTUNITY REPORT*\n"
        f"📅 {today}  |  🕐 {now}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Market:* {mkt_desc}\n"
        f"{nifty_icon} Nifty prev close: {'+' if nifty_chg > 0 else ''}{nifty_chg:.0f} pts\n"
    )

    if gift_gap != 0:
        header += (
            f"{gift_icon} Today's open estimate: "
            f"{'+' if gift_gap > 0 else ''}{gift_gap:.2f}% _(GIFT Nifty)_\n"
        )

    header += f"😨 VIX: {vix:.1f}\n"

    if caution:
        header += f"\n{caution}\n"

    header += f"📊 Scanned: {stocks_scanned} stocks\n"

    # ── No picks ──────────────────────────────────────────
    if not picks:
        return (
            header
            + f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + f"*Today's Picks: None*\n\n"
            + f"{_no_picks_reason(mkt_score)}\n\n"
            + f"💡 *What to do today:*\n"
            + f"  • Hold existing positions\n"
            + f"  • Don't force a trade\n"
            + f"  • Cash is also a position\n\n"
            + f"_Bot will scan again tomorrow_ 🔄"
        )

    # ── Picks ─────────────────────────────────────────────
    picks_section = (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Today's Picks: {len(picks)} "
        f"{'stock' if len(picks)==1 else 'stocks'}*\n\n"
    )

    picks_body = ""
    for i, pick in enumerate(picks, 1):
        picks_body += format_pick(pick, i)
        if i < len(picks):
            picks_body += "\n━━━━━━━━━━━━━━━━\n\n"

    footer = (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ _Opportunity signals only — not guaranteed profits. "
        f"Always set stop loss before buying. "
        f"Check news manually before acting._\n"
        f"_Data: Fyers API (Official NSE)_"
    )

    return header + picks_section + picks_body + footer


def _no_picks_reason(market_score: int) -> str:
    if market_score <= -3:
        return (
            "🔴 *Market is too risky today.*\n"
            "Nifty falling sharply and fear is high.\n"
            "Protecting capital is more important than finding trades."
        )
    elif market_score <= -1:
        return (
            "🟠 *Market is cautious today.*\n"
            "No stocks passed all quality filters.\n"
            "Better opportunities likely in next few days."
        )
    else:
        return (
            "🟡 *No high quality setups found today.*\n"
            "The bot only recommends when confidence is above 60%.\n"
            "Waiting for better setups is the smart move."
        )


# ══════════════════════════════════════════════════════════
# FORMAT FRIDAY REPORT
# ══════════════════════════════════════════════════════════

def format_friday_report(performance: dict) -> str:
    wins        = performance.get("wins", 0)
    losses      = performance.get("losses", 0)
    open_p      = performance.get("open", 0)
    total       = wins + losses + open_p
    win_rate    = round(wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    all_time_wr = performance.get("all_time_win_rate", 0)

    msg = (
        f"📊 *WEEKLY PERFORMANCE REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*This Week:*\n"
        f"Picks sent:       {total}\n"
        f"✅ Hit target:    {wins}\n"
        f"❌ Hit stop loss: {losses}\n"
        f"⏳ Still open:    {open_p}\n"
    )

    if wins + losses > 0:
        msg += f"Win rate:         {win_rate}%\n"

    msg += f"\n*All-Time Record:*\n"
    msg += f"Win rate: {all_time_wr}%\n"
    msg += "\n💪 Always follow the stop losses — that protects your capital.\n"
    msg += "_Full history tracked automatically_ 📋"
    return msg


# ══════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_pick = {
        "symbol":               "HDFCBANK",
        "sector":               "Banking",
        "signal":               "STRONG BUY 🟢",
        "confidence":           78.5,
        "signal_type":          "PULLBACK BUY",
        "emoji":                "📉➡️📈",
        "price":                1650.0,
        "target":               1820.0,
        "stop_loss":            1580.0,
        "upside_pct":           10.3,
        "downside_pct":         4.2,
        "risk_reward":          2.43,
        "entry_timing":         "IDEAL",
        "fundamental_summary":  "Profits growing ✅ | PE 18 — fairly valued",
        "news_warnings":        ["🟡 Caution: 'downgrade' in recent news"],
        "news_headlines":       [],
        "has_danger_news":      False,
        "earnings_warning":     "📅 Results on 28 Mar 2026 (14 days) — consider waiting",
        "has_upcoming_results": True,
        "results_date":         "28 Mar 2026",
        "reasons": [
            "RSI at 48 — healthy momentum zone",
            "Price above all key moving averages",
            "Strong stock pulled back 12% from highs."
        ],
        "warnings": []
    }

    test_market = {
        "market_score":   -1,
        "description":    "CAUTIOUS DAY 🟠",
        "nifty_change":   -488,
        "gift_nifty_gap": 0.15,
        "vix":            18.2,
        "caution_label":  "⚠️ Weak market — consider smaller position sizes"
    }

    report = format_daily_report(
        picks          = [test_pick],
        market_context = test_market,
        stocks_scanned = 229
    )

    print(report)
    print("\nSending to Telegram...")
    send_message(report)