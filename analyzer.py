"""
analyzer.py
===========
Thinks like a smart investor.

Fixes applied:
- Stop loss now chart-based with signal-type specific lookback
- Hard maximum stop loss = 5% (user preference)
- Stocks with support too far away are skipped
"""

import pandas as pd
import numpy as np
from datetime import datetime


# ══════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════

MIN_CANDLES_DAILY  = 50
MIN_CANDLES_WEEKLY = 10
MIN_RR_RATIO       = 2.0
MIN_CONFIDENCE     = 60
MAX_STOP_LOSS_PCT  = 5.0   # Hard maximum — never more than 5% stop loss


# ══════════════════════════════════════════════════════════
# TECHNICAL INDICATORS
# ══════════════════════════════════════════════════════════

def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series):
    ema12  = series.ewm(span=12, adjust=False).mean()
    ema26  = series.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"]  - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["volume"].rolling(period).mean()


def _find_support(df: pd.DataFrame, lookback: int) -> float:
    """
    Find the most recent meaningful support level.
    Looks for swing lows — prices that are lower than neighbours.
    """
    recent = df.tail(lookback)
    best_support = recent["low"].min()

    # Find most recent swing low
    for i in range(len(recent) - 2, 1, -1):
        low_val = recent["low"].iloc[i]
        if (low_val < recent["low"].iloc[i-1] and
            low_val < recent["low"].iloc[i+1]):
            best_support = low_val
            break

    return round(best_support, 2)


def _find_resistance(df: pd.DataFrame, lookback: int) -> float:
    """Find the most recent meaningful resistance level."""
    recent = df.tail(lookback)
    best_resistance = recent["high"].max()

    for i in range(len(recent) - 2, 1, -1):
        high_val = recent["high"].iloc[i]
        if (high_val > recent["high"].iloc[i-1] and
            high_val > recent["high"].iloc[i+1]):
            best_resistance = high_val
            break

    return round(best_resistance, 2)


# ══════════════════════════════════════════════════════════
# STEP 1 — HARD FILTERS
# ══════════════════════════════════════════════════════════

def passes_hard_filters(daily_df: pd.DataFrame, weekly_df: pd.DataFrame) -> tuple:
    """Returns (passes: bool, reason: str)"""

    if daily_df is None or len(daily_df) < MIN_CANDLES_DAILY:
        return False, "Insufficient data"

    close   = daily_df["close"]
    current = close.iloc[-1]

    # Filter: Weekly trend not in clear downtrend
    if weekly_df is not None and len(weekly_df) >= MIN_CANDLES_WEEKLY:
        wc      = weekly_df["close"]
        w_sma10 = wc.rolling(10).mean().iloc[-1]
        w_sma20 = wc.rolling(min(20, len(wc))).mean().iloc[-1]
        if (wc.iloc[-1] < w_sma10 and
            wc.iloc[-1] < w_sma20 and
            wc.iloc[-1] < wc.iloc[-4]):
            return False, "Weekly downtrend"

    # Filter: Not more than 10% below 200 DMA
    if len(close) >= 200:
        dma200 = close.rolling(200).mean().iloc[-1]
        if current < dma200 * 0.90:
            return False, "Too far below 200 DMA"

    # Filter: Not in freefall (>25% drop in a month)
    month_ago = close.iloc[-22] if len(close) >= 22 else close.iloc[0]
    if (current - month_ago) / month_ago * 100 < -25:
        return False, "Falling more than 25% in a month"

    # Filter: Not a penny stock
    if current < 20:
        return False, "Price below ₹20"

    return True, "OK"


# ══════════════════════════════════════════════════════════
# STEP 2 — IDENTIFY THE STORY
# ══════════════════════════════════════════════════════════

def identify_signal_type(daily_df: pd.DataFrame) -> dict:
    """Identifies which type of opportunity this is."""
    close   = daily_df["close"]
    volume  = daily_df["volume"]
    high    = daily_df["high"]
    low     = daily_df["low"]

    current  = close.iloc[-1]
    vol_sma  = _volume_sma(daily_df).iloc[-1]
    vol_now  = volume.iloc[-3:].mean()
    ema21    = _ema(close, 21).iloc[-1]
    ema50    = _ema(close, 50).iloc[-1]
    ema200   = _ema(close, 200).iloc[-1] if len(close) >= 200 else ema50
    rsi_val  = _rsi(close).iloc[-1]

    year_high = high.tail(252).max() if len(high) >= 252 else high.max()
    year_low  = low.tail(252).min()  if len(low)  >= 252 else low.min()
    from_high = (current - year_high) / year_high * 100

    # PULLBACK BUY
    if (current > ema200 and current > ema50 and
        -25 < from_high < -8 and 35 < rsi_val < 55):
        strength = 3 if from_high > -15 else 2
        return {
            "signal_type":   "PULLBACK BUY",
            "story":         f"Strong stock pulled back {abs(from_high):.1f}% from highs. Long term uptrend intact. Good entry at discount.",
            "strength":      strength,
            "emoji":         "📉➡️📈",
            "sl_lookback":   60   # Use 60-day support for pullbacks
        }

    # BREAKOUT BUY
    recent_high = high.tail(20).max()
    if (current >= recent_high * 0.99 and
        vol_now > vol_sma * 1.3 and
        rsi_val > 50 and current > ema21):
        return {
            "signal_type":   "BREAKOUT BUY",
            "story":         f"Breaking above recent resistance with {(vol_now/vol_sma):.1f}x normal volume. Momentum is strong.",
            "strength":      3 if from_high > -5 else 2,
            "emoji":         "🚀",
            "sl_lookback":   20   # Use 20-day support for breakouts
        }

    # RECOVERY BUY
    rsi_5d_ago = _rsi(close).iloc[-5] if len(close) >= 5 else rsi_val
    if (35 < rsi_val < 55 and rsi_5d_ago < 35 and
        current > close.iloc[-5] and current > ema200):
        return {
            "signal_type":   "RECOVERY BUY",
            "story":         f"Stock was oversold (RSI hit {rsi_5d_ago:.0f}) and is now recovering. Momentum turning positive.",
            "strength":      2,
            "emoji":         "🔄",
            "sl_lookback":   90   # Use 90-day support for recoveries
        }

    # CONSOLIDATION BREAKOUT
    high_20  = high.tail(20).max()
    low_20   = low.tail(20).min()
    range_pct= (high_20 - low_20) / low_20 * 100
    if (range_pct < 12 and current >= high_20 * 0.98 and vol_now > vol_sma):
        return {
            "signal_type":   "CONSOLIDATION BREAKOUT",
            "story":         f"Stock consolidated in a tight {range_pct:.1f}% range and is now breaking out.",
            "strength":      2,
            "emoji":         "💥",
            "sl_lookback":   30
        }

    # DEFAULT
    return {
        "signal_type": "TECHNICAL BUY",
        "story":       "Multiple technical indicators aligned positively.",
        "strength":    1,
        "emoji":       "📊",
        "sl_lookback": 20
    }


# ══════════════════════════════════════════════════════════
# STEP 3 — TECHNICAL SCORING
# ══════════════════════════════════════════════════════════

def score_technicals(daily_df: pd.DataFrame) -> dict:
    close   = daily_df["close"]
    volume  = daily_df["volume"]
    high    = daily_df["high"]
    low     = daily_df["low"]
    current = close.iloc[-1]
    score   = 0
    reasons = []
    warnings= []

    # RSI (0-20 pts)
    rsi     = _rsi(close)
    rsi_now = rsi.iloc[-1]
    rsi_prev= rsi.iloc[-3]

    if 40 <= rsi_now <= 60:
        score += 20
        reasons.append(f"RSI at {rsi_now:.0f} — healthy momentum zone")
    elif 30 <= rsi_now < 40:
        score += 15
        reasons.append(f"RSI recovering from oversold ({rsi_now:.0f})" if rsi_now > rsi_prev else f"RSI at {rsi_now:.0f} — near oversold")
    elif 60 < rsi_now <= 70:
        score += 12
        reasons.append(f"RSI at {rsi_now:.0f} — strong momentum")
    elif rsi_now > 70:
        score += 5
        warnings.append(f"RSI at {rsi_now:.0f} — overbought, risky entry")
    elif rsi_now < 30:
        score += 8
        reasons.append(f"RSI bouncing from oversold ({rsi_now:.0f})" if rsi_now > rsi_prev else f"RSI at {rsi_now:.0f} — deeply oversold")

    # MACD (0-20 pts)
    _, _, hist = _macd(close)
    hist_now  = hist.iloc[-1]
    hist_prev = hist.iloc[-2]

    if hist_now > 0 and hist_now > hist_prev:
        score += 20
        reasons.append("MACD histogram rising — buying momentum increasing")
    elif hist_now > 0:
        score += 12
        reasons.append("MACD positive but momentum slowing")
    elif hist_now < 0 and hist_now > hist_prev:
        score += 15
        reasons.append("MACD turning up — momentum reversing")
    else:
        score += 3
        warnings.append("MACD negative — bearish momentum")

    # Moving Averages (0-20 pts)
    ema21  = _ema(close, 21).iloc[-1]
    ema50  = _ema(close, 50).iloc[-1]
    ema200 = _ema(close, 200).iloc[-1] if len(close) >= 200 else ema50

    ma_score = 0
    ma_notes = []
    if current > ema21:  ma_score += 5;  ma_notes.append("21 EMA ✅")
    if current > ema50:  ma_score += 7;  ma_notes.append("50 EMA ✅")
    if current > ema200: ma_score += 8;  ma_notes.append("200 EMA ✅")

    score += ma_score
    if ma_score >= 15:
        reasons.append(f"Price above all key moving averages ({', '.join(ma_notes)})")
    elif ma_score >= 10:
        reasons.append(f"Price above {', '.join(ma_notes)}")
    elif ma_score < 5:
        warnings.append("Price below key moving averages")

    # Volume (0-15 pts)
    vol_sma   = _volume_sma(daily_df).iloc[-1]
    vol_ratio = volume.tail(5).mean() / vol_sma if vol_sma > 0 else 1

    if vol_ratio >= 1.5:
        score += 15
        reasons.append(f"Volume {vol_ratio:.1f}x above average — strong buyer interest")
    elif vol_ratio >= 1.2:
        score += 10
        reasons.append(f"Volume {vol_ratio:.1f}x above average — good buying activity")
    elif vol_ratio >= 0.8:
        score += 6
    else:
        score += 2
        warnings.append("Volume below average — weak conviction")

    # 52 Week Position (0-15 pts)
    year_high = high.tail(252).max() if len(high) >= 252 else high.max()
    year_low  = low.tail(252).min()  if len(low)  >= 252 else low.min()
    year_range= year_high - year_low
    position  = (current - year_low) / year_range * 100 if year_range > 0 else 50
    from_high = (current - year_high) / year_high * 100

    if 30 <= position <= 70:
        score += 15
        reasons.append("Price in middle of 52-week range — not overextended")
    elif position > 70:
        score += 8
        if from_high < -5:
            reasons.append(f"Near 52-week highs — strong stock, {from_high:.1f}% from top")
        else:
            warnings.append("Very close to 52-week high — limited upside near term")
    elif position < 30:
        score += 10
        reasons.append("Near 52-week lows — potential reversal zone")

    # Trend Consistency (0-10 pts)
    if len(close) >= 20:
        h10 = high.tail(10).max()
        h20 = high.tail(20).head(10).max()
        l10 = low.tail(10).min()
        l20 = low.tail(20).head(10).min()

        if h10 > h20 and l10 > l20:
            score += 10
            reasons.append("Making higher highs and higher lows — healthy uptrend")
        elif h10 > h20 or l10 > l20:
            score += 5

    return {
        "score":    min(100, score),
        "reasons":  reasons,
        "warnings": warnings,
        "rsi":      round(rsi_now, 1),
        "above_200":current > ema200,
        "vol_ratio":round(vol_ratio, 2)
    }


# ══════════════════════════════════════════════════════════
# STEP 4 — RISK/REWARD (Chart-based + 5% max stop loss)
# ══════════════════════════════════════════════════════════

def calculate_risk_reward(daily_df: pd.DataFrame, sl_lookback: int = 20) -> dict:
    """
    Smart investor always defines risk before reward.

    Stop loss:
    - Chart-based support level using signal-type specific lookback
    - Hard maximum: 5% below current price (user preference)
    - If chart support is more than 5% away → skip this stock

    Target:
    - Chart resistance level
    - Minimum 2x the stop loss distance
    """
    close   = daily_df["close"]
    high    = daily_df["high"]
    low     = daily_df["low"]
    current = close.iloc[-1]
    atr     = _atr(daily_df).iloc[-1]

    # ── Support level (Stop Loss) ─────────────────────────
    lookback  = min(sl_lookback, len(daily_df) - 1)
    support   = _find_support(daily_df, lookback)

    # Buffer below support
    stop_loss = round(support * 0.99, 2)

    # ── Apply 5% hard maximum ─────────────────────────────
    max_stop  = round(current * (1 - MAX_STOP_LOSS_PCT / 100), 2)

    if stop_loss < max_stop:
        # Chart support is too far — use 5% maximum
        stop_loss = max_stop

    # Safety check — stop must be below current price
    if stop_loss >= current:
        stop_loss = round(current * 0.95, 2)

    # ── Resistance level (Target) ─────────────────────────
    resistance = _find_resistance(daily_df, lookback)

    # If resistance is too close or below current price
    if resistance <= current * 1.04:
        # Use ATR-based target (3x ATR)
        resistance = round(current + (3.0 * atr), 2)

    target = resistance

    # Minimum target must be at least 2x the stop loss distance
    risk   = current - stop_loss
    min_target = round(current + (MIN_RR_RATIO * risk), 2)
    if target < min_target:
        target = min_target

    # ── Calculate final R/R ───────────────────────────────
    reward   = target - current
    risk     = current - stop_loss
    rr       = round(reward / risk, 2) if risk > 0 else 0
    upside   = round((target - current) / current * 100, 1)
    downside = round((current - stop_loss) / current * 100, 1)

    return {
        "current_price": round(current, 2),
        "stop_loss":     stop_loss,
        "target":        round(target, 2),
        "risk_reward":   rr,
        "upside_pct":    upside,
        "downside_pct":  downside,
        "is_valid":      rr >= MIN_RR_RATIO and stop_loss < current < target
    }


# ══════════════════════════════════════════════════════════
# STEP 5 — ENTRY TIMING
# ══════════════════════════════════════════════════════════

def check_entry_timing(hourly_df: pd.DataFrame) -> dict:
    if hourly_df is None or len(hourly_df) < 5:
        return {"timing": "NEUTRAL", "note": "No hourly data", "bonus": 0}

    close  = hourly_df["close"]
    volume = hourly_df["volume"]

    current       = close.iloc[-1]
    vol_avg       = volume.mean()
    vol_now       = volume.iloc[-1]
    rsi_hourly    = _rsi(close).iloc[-1] if len(close) >= 14 else 50
    h_ema9        = _ema(close, min(9, len(close))).iloc[-1]
    _, _, hist    = _macd(close)
    hourly_macd_up= hist.iloc[-1] > hist.iloc[-2] if len(hist) >= 2 else True

    if (current > h_ema9 and hourly_macd_up and
        30 < rsi_hourly < 70 and vol_now >= vol_avg * 0.8):
        return {"timing": "IDEAL", "note": "Good entry — hourly trend up, momentum positive", "bonus": 5}
    elif rsi_hourly > 75:
        return {"timing": "WAIT", "note": "Overbought on hourly — wait for small pullback", "bonus": -5}
    elif current < h_ema9 and not hourly_macd_up:
        return {"timing": "WAIT", "note": "Hourly trend down — wait for stabilisation", "bonus": -3}
    else:
        return {"timing": "NEUTRAL", "note": "Entry timing is neutral", "bonus": 0}


# ══════════════════════════════════════════════════════════
# MASTER FUNCTION — Analyse one stock
# ══════════════════════════════════════════════════════════

def analyse_stock(symbol: str, data: dict) -> dict:
    from stocks_list import get_sector

    daily_df  = data.get("price_data")
    weekly_df = data.get("weekly_data")
    hourly_df = data.get("hourly_data")

    # Step 1: Hard filters
    passes, reason = passes_hard_filters(daily_df, weekly_df)
    if not passes:
        return None

    # Step 2: Story
    signal_info = identify_signal_type(daily_df)
    if signal_info["strength"] < 1:
        return None

    # Step 3: Technical scoring
    tech = score_technicals(daily_df)

    # Step 4: Risk/Reward with signal-type lookback
    sl_lookback = signal_info.get("sl_lookback", 20)
    rr_info     = calculate_risk_reward(daily_df, sl_lookback=sl_lookback)

    if not rr_info["is_valid"]:
        return None

    # Step 5: Entry timing
    timing = check_entry_timing(hourly_df)

    # ── Final Confidence ──────────────────────────────────
    story_bonus  = {3: 10, 2: 5, 1: 0}.get(signal_info["strength"], 0)
    timing_bonus = timing["bonus"]
    rr_bonus     = 8 if rr_info["risk_reward"] >= 3.0 else (5 if rr_info["risk_reward"] >= 2.5 else 2)
    confidence   = min(95, tech["score"] + story_bonus + timing_bonus + rr_bonus)

    if confidence < MIN_CONFIDENCE:
        return None

    if confidence >= 75:   signal = "STRONG BUY 🟢"
    elif confidence >= 65: signal = "BUY 🟩"
    else:                  signal = "WATCH 🟡"

    top_reasons = (tech["reasons"][:2] + [signal_info["story"]])[:3]

    return {
        "symbol":       symbol,
        "sector":       get_sector(symbol),
        "signal":       signal,
        "confidence":   round(confidence, 1),
        "signal_type":  signal_info["signal_type"],
        "emoji":        signal_info.get("emoji", "📊"),
        "price":        rr_info["current_price"],
        "target":       rr_info["target"],
        "stop_loss":    rr_info["stop_loss"],
        "upside_pct":   rr_info["upside_pct"],
        "downside_pct": rr_info["downside_pct"],
        "risk_reward":  rr_info["risk_reward"],
        "entry_timing": timing["timing"],
        "entry_note":   timing["note"],
        "reasons":      top_reasons,
        "warnings":     tech["warnings"][:2],
        "rsi":          tech["rsi"],
        "above_200dma": tech["above_200"],
        "vol_ratio":    tech["vol_ratio"],
    }


# ══════════════════════════════════════════════════════════
# ANALYSE ALL STOCKS
# ══════════════════════════════════════════════════════════

def analyse_all(stock_data: dict) -> list:
    results = []
    total   = len(stock_data)
    print(f"  Analysing {total} stocks...")

    for symbol, data in stock_data.items():
        try:
            result = analyse_stock(symbol, data)
            if result:
                result["symbol"] = symbol
                results.append(result)
        except Exception:
            continue

    results.sort(key=lambda x: x["confidence"], reverse=True)
    print(f"  Found {len(results)} candidates from {total} stocks")
    return results


# ══════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    from fyers_fetcher import fetch_batch, get_fyers_client
    from stocks_list import ALL_STOCKS

    client = get_fyers_client()
    if client:
        data    = fetch_batch(ALL_STOCKS[:20])
        results = analyse_all(data)

        print(f"\n{'='*50}")
        print(f"Results: {len(results)} candidates")
        print(f"{'='*50}")
        for r in results:
            print(f"\n{r['symbol']} — {r['signal']} ({r['confidence']}%)")
            print(f"  Type:      {r['signal_type']} {r['emoji']}")
            print(f"  Price:     ₹{r['price']}")
            print(f"  Target:    ₹{r['target']} (+{r['upside_pct']}%)")
            print(f"  Stop Loss: ₹{r['stop_loss']} (-{r['downside_pct']}%)")
            print(f"  R/R:       {r['risk_reward']}x")
            for reason in r['reasons']:
                print(f"  • {reason}")