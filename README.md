# NSE Stock Opportunity Bot — Archived

This project is no longer running. The Fyers API data layer (`fyers_fetcher.py`) and the orchestration script (`main.py`) have been removed, and the GitHub Actions workflows are disabled. The remaining modules are preserved for reference and reuse.

## What it was

A personal automated stock scanner for NSE India that ran every weekday at 8:00 AM IST via GitHub Actions. It scanned 229 stocks, applied a 5-step technical analysis with fundamental and news filters, then sent a Telegram report with buy/target/stop prices.

More context: https://roshanthankar.vercel.app/stockbot.html

## What's still here

| File | Purpose |
|---|---|
| `analyzer.py` | 5-step technical analysis — hard filters, story identification, scoring, R/R, entry timing |
| `fundamental_checker.py` | PE ratio + profit trend scraper (Screener.in) |
| `news_checker.py` | Danger/caution keyword flags from Google News RSS |
| `earnings_checker.py` | Upcoming results warning (NSE corporate calendar) |
| `telegram_sender.py` | Telegram report formatting + sending |
| `stocks_list.py` | 229 NSE stocks across 28 sectors |
| `nse_holidays.py` | NSE holiday calendar check |
| `gist_pusher.py` | iOS widget gist updater |

Each is independent and can be wired into a new pipeline with any OHLCV data source.

## Technical Analysis — `analyzer.py`

### Step 1 — Hard Filters

| Filter | Threshold |
|---|---|
| Minimum data | 50 daily candles |
| Weekly trend | Not in clear downtrend (below SMA10, SMA20, and 4 weeks ago) |
| 200 DMA distance | Price must be within 10% of 200-day moving average |
| Monthly freefall | Must not have fallen more than 25% in a month |
| Minimum price | Above ₹20 (no penny stocks) |

### Step 2 — Story Identification

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

Final confidence = technical score + story bonus + timing bonus + R/R bonus. Clamped to 0–95%.

## Disclaimer

This bot provided technical analysis signals for informational purposes only. It did not guarantee profit and is not financial advice. Past signals do not guarantee future performance.
