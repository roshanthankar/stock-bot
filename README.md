# 📈 NSE Stock Opportunity Bot

A personal automated stock scanner for NSE India. Runs every weekday at **8:00 AM IST** via GitHub Actions — no servers, no cost, zero manual effort. Scans 229 stocks, applies 5-step smart investor analysis, checks company health and news, then sends a clean Telegram report with picks, exact buy/target/stop prices, and reasoning.

Get more info here: https://roshanthankar.vercel.app/stockbot.html
---

## What You Receive Every Morning

```
🤖 STOCK OPPORTUNITY REPORT
📅 Monday, 16 Mar 2026  |  🕐 08:02 AM
━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: POSITIVE DAY 🟢
🟢 Nifty prev close: +45 pts
😨 VIX: 14.2
📊 Scanned: 229 stocks

━━━━━━━━━━━━━━━━━━━━━━━━━━
Today's Picks: 2 stocks

#1 HDFCBANK  |  Banking
📉➡️📈 Pulled back from highs — buying opportunity
━━━━━━━━━━━━━━━━━━━━
📊 Signal: STRONG BUY 🟢
🎯 Confidence: ████████░░ 78.5%

💰 Buy at:    ₹1,650.75
🎯 Target:    ₹1,821.50  (+10.3%)
🛑 Stop Loss: ₹1,568.20  (-4.9%)
⚖️ Risk/Reward: 2.43x

💸 Max loss per 10 shares: ₹825.50
📌 Never invest more than 5-10% of capital in one pick

Why this stock?
  • RSI at 48 — healthy momentum zone
  • Price above all key moving averages (21 EMA ✅ 50 EMA ✅ 200 EMA ✅)
  • Strong stock pulled back 12.4% from highs. Long term uptrend intact.

🏢 Company: Profits growing consistently ✅ | PE 17 — fairly valued
⏰ Entry timing: Ideal right now

🔗 View on Screener
```

---

## Architecture

```
main.py                     ← Master pipeline — 10 steps
├── fyers_fetcher.py         ← Fyers API login + 229 stock OHLCV fetch
├── analyzer.py              ← 5-step smart investor technical analysis
├── fundamental_checker.py   ← PE ratio + profit trend (Screener.in)
├── news_checker.py          ← Danger/caution flags (Google News RSS)
├── earnings_checker.py      ← Upcoming results warning (NSE calendar)
├── telegram_sender.py       ← Format + send Telegram report
└── stocks_list.py           ← 229 NSE stocks across 28 sectors
```

---

## Pipeline — 10 Steps

```
Step 1   Validate all 7 credentials
Step 2   Check trading day (weekday + NSE holiday list)
Step 3   Auto-login to Fyers API via TOTP
Step 4   Fetch market context — Nifty + India VIX
Step 5   Fetch 229 stocks — daily, weekly, hourly OHLCV
Step 6   5-step technical analysis on every stock
Step 7   Fundamental check — PE + profit trend (all candidates)
Step 8   Sector diversification — max 2 per sector → final picks
Step 9   News + earnings check (final picks only — saves ~90s)
Step 10  Send Telegram report
```

---

## Technical Analysis — 5 Steps in analyzer.py

### Step 1 — Hard Filters
Any failure → stock skipped immediately.

| Filter | Threshold |
|---|---|
| Minimum data | 50 daily candles |
| Weekly trend | Not in clear downtrend (below SMA10, SMA20, and 4 weeks ago) |
| 200 DMA distance | Price must be within 10% of 200-day moving average |
| Monthly freefall | Must not have fallen more than 25% in a month |
| Minimum price | Above ₹20 (no penny stocks) |

### Step 2 — Story Identification
Finds what type of opportunity this is:

| Signal | Condition | SL Lookback |
|---|---|---|
| `PULLBACK BUY` | Strong stock dipped 8–25% from highs, RSI 35–55, above 50 & 200 EMA | 60 days |
| `BREAKOUT BUY` | Breaking 20-day high with 1.3x+ volume, RSI > 50 | 20 days |
| `RECOVERY BUY` | RSI was below 35, now recovering above 35, price rising | 90 days |
| `CONSOLIDATION BREAKOUT` | 20-day range < 12%, breaking out with volume | 30 days |

### Step 3 — Technical Scoring (0–100)

| Factor | Points |
|---|---|
| RSI position and direction | 0–20 |
| MACD histogram direction | 0–20 |
| Price vs 21/50/200 EMA | 0–20 |
| Volume vs 20-day average | 0–15 |
| 52-week range position | 0–15 |
| Higher highs + higher lows | 0–10 |

Minimum to proceed: **60 points**

### Step 4 — Risk/Reward
- Stop loss at nearest chart support (lookback from Step 2)
- Hard cap: **maximum 5% below current price**
- Target at nearest chart resistance, minimum 2x the stop distance
- If R/R < 2.0 → stock skipped

### Step 5 — Entry Timing (hourly chart)
- `IDEAL` → hourly trend up, MACD positive, RSI healthy → +5 confidence
- `WAIT` → overbought or hourly downtrend → -3 to -5 confidence
- `NEUTRAL` → no strong signal

**Final confidence = technical score + story bonus + timing bonus + R/R bonus**
Clamped to 0–95%. Minimum 60% to appear in report.

---

## Market Conditions

| Market Score | Label | Max Picks | Notes |
|---|---|---|---|
| ≥ +4 | Bull Run 🟢 | 5 | Normal |
| +2 to +3 | Positive Day 🟢 | 4 | Normal |
| 0 to +1 | Neutral Day 🟡 | 3 | Normal |
| -1 to -2 | Weak Day 🔴 | 3 | Caution warning added |
| -3 | Very Weak 🔴 | 2 | Caution warning added |
| ≤ -4 | Avoid Today 🔴🔴 | 1 | Strong warning |

Score calculated from: Nifty previous close direction + India VIX level.

---

## Fundamental Check — fundamental_checker.py

Runs on all technical candidates via Screener.in (free, no API key):

- **PE Ratio** → attractive (< 15) / fair (15–30) / premium (30–60) / expensive (> 60)
- **Quarterly Profit Trend** → Growing / Stable / Declining / Loss-Making
- **Filter** → stocks with 3+ consecutive loss quarters are removed entirely

---

## News Check — news_checker.py

Google News RSS — no API key needed. Checks top 20 headlines per stock.

**Danger keywords** (🔴 serious warning):
`fraud, scam, CBI, ED raid, SEBI ban, SEBI order, insider trading, bankruptcy, insolvency, debt default, delisted, CEO quits, MD resigns, auditor resigns, accounting fraud`

**Caution keywords** (🟡 informational):
`downgrade, sell rating, target cut, net loss, quarterly loss, earnings miss, revenue miss, SEBI notice, SEBI probe, income tax notice, penalty imposed, fine imposed, order cancelled`

Bot never blocks picks — only adds warnings so you decide.

---

## Earnings Check — earnings_checker.py

Fetches NSE corporate calendar once per run, checks all final picks:

| Days to Results | Warning Shown |
|---|---|
| Today | `📋 Results TODAY — extremely high risk entry` |
| 1–3 days | `⚠️ HIGH RISK: stock can gap sharply on results` |
| 4–7 days | `📅 Consider waiting until after results` |

---

## Stock Universe — stocks_list.py

229 stocks across 28 sectors:

| Sector | Count | Key Stocks |
|---|---|---|
| Banking | 20 | HDFCBANK, ICICIBANK, SBIN, KOTAKBANK |
| Finance | 15 | BAJFINANCE, SHRIRAMFIN, CHOLAFIN |
| IT | 18 | TCS, INFY, HCLTECH, WIPRO, LTIM |
| Pharma | 15 | SUNPHARMA, DRREDDY, CIPLA, DIVISLAB |
| FMCG | 18 | HINDUNILVR, ITC, NESTLEIND, BRITANNIA |
| Auto | 10 | MARUTI, BAJAJ-AUTO, TATAMOTORS, EICHERMOT |
| Metals | 11 | TATASTEEL, JSWSTEEL, HINDALCO, VEDL |
| Defence | 9 | BEL, HAL, GRSE, COCHINSHIP |
| Power | 10 | NTPC, TATAPOWER, ADANIGREEN, POWERGRID |
| Real Estate | 11 | DLF, GODREJPROP, PRESTIGE, LODHA |
| + 18 more | ... | Infrastructure, Chemicals, Retail, Tech Platforms... |

---

## Data Sources

| Data | Source | Cost |
|---|---|---|
| Stock OHLCV (daily/weekly/hourly) | Fyers API | Free |
| Live market quotes | Fyers API | Free |
| Fundamental ratios | Screener.in HTML | Free |
| News sentiment | Google News RSS | Free |
| Earnings calendar | NSE India API | Free |

**Total running cost: ₹0/month**

---

## Schedule

Runs via GitHub Actions — no server needed:

```yaml
on:
  schedule:
    - cron: '30 2 * * 1-5'   # 8:00 AM IST = 2:30 AM UTC, weekdays only
  workflow_dispatch:           # Manual trigger available anytime
```

| Day | Time | What runs |
|---|---|---|
| Monday–Friday | 8:00 AM IST | Full scan + Telegram report |
| Friday | 8:00 AM IST | Also sends weekly performance summary |

---

## Setup

### Prerequisites
- Python 3.9+
- Fyers trading account (free at fyers.in)
- Telegram bot
- GitHub account (free Actions minutes sufficient)

### 1. Clone and install

```bash
git clone https://github.com/roshanthankar/stock-bot
cd stock-bot
python -m venv venv
venv/bin/pip install fyers-apiv3 pyotp requests pandas numpy python-dotenv ta
```

### 2. Create .env

```
FYERS_APP_ID=your_app_id
FYERS_SECRET_KEY=your_secret_key
FYERS_CLIENT_ID=your_client_id
FYERS_PIN=your_4_digit_pin
FYERS_TOTP_SECRET=your_totp_secret_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 3. Fyers API setup
1. Open free account at [fyers.in](https://fyers.in)
2. Go to [myapi.fyers.in](https://myapi.fyers.in) → Create App → copy App ID and Secret
3. Enable TOTP at myaccount.fyers.in → Security → 2FA
4. Scan QR code with any authenticator app → copy the secret key

### 4. Telegram setup
1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token
2. Message [@userinfobot](https://t.me/userinfobot) → copy your Chat ID

### 5. GitHub Secrets
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → add all 7:
```
FYERS_APP_ID  FYERS_SECRET_KEY  FYERS_CLIENT_ID
FYERS_PIN  FYERS_TOTP_SECRET  TELEGRAM_TOKEN  TELEGRAM_CHAT_ID
```

### 6. Test locally

```bash
venv/bin/python main.py --test
```

`--test` flag skips the trading day check so you can run any day.

---

## Limitations

- **LTIM and TATAMOTORS** occasionally hit Fyers rate limits and get skipped
- **NSE earnings API** is sometimes blocked — earnings check may silently fail
- **Screener.in parsing** can break if they change their HTML structure
- **Confidence scores** are not backtested — treat as directional signals only
- **GitHub Actions** free tier may trigger 5–15 minutes late
- **No performance tracker** yet — wins/losses not auto-recorded

---

## Roadmap

- [ ] Performance tracker — auto-record and track pick outcomes
- [ ] Backtest — validate scoring weights against historical data
- [ ] Position sizing — suggest capital allocation per pick
- [ ] Volatility-adjusted stop losses — ATR-based instead of fixed 5%
- [ ] Weekly MF/ETF Monday report

---

## Disclaimer

This bot provides technical analysis signals for informational purposes only. It does not guarantee profit and is not financial advice. Always:

- Set your stop loss before buying
- Never invest more than 5–10% of capital in a single pick
- Check news manually before acting on any recommendation
- Past signals do not guarantee future performance

---

*Data sourced from Fyers API — Official NSE feed. Built for personal use.*
