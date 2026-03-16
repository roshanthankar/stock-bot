"""
analyzer.py
===========
Thinks like a smart investor.

Improvements applied (based on code review):
1. Pandas anti-pattern fixed — tail().mean() instead of rolling().mean().iloc[-1]
2. ZeroDivisionError fixed — month_ago=0 guard added
3. KeyError protection — "close" column validation added
4. Magic numbers extracted to named constants
5. Type hints tightened — Optional[dict] and tuple for Python 3.9 compatibility
6. Confidence clamped to valid range before scoring
"""

import pandas as pd
import numpy as np
from typing import Optional


# ══════════════════════════════════════════════════════════
# CONSTANTS — All tunable parameters in one place
# ══════════════════════════════════════════════════════════

MIN_CANDLES_DAILY    = 50       # Minimum daily candles needed
MIN_CANDLES_WEEKLY   = 10       # Minimum weekly candles needed
MIN_RR_RATIO         = 2.0      # Minimum reward:risk ratio
MIN_CONFIDENCE       = 60       # Minimum confidence to recommend
MAX_STOP_LOSS_PCT    = 5.0      # Hard maximum stop loss %
MAX_CONFIDENCE       = 95       # Hard cap on confidence score

# Hard filter thresholds
DMA_PERIOD           = 200      # Days for long-term moving average
DMA_MAX_BELOW_PCT    = 0.90     # Max 10% below 200 DMA
FREEFALL_PERIOD      = 22       # Trading days in a month
FREEFALL_MAX_DROP    = -25.0    # Max monthly drop before skipping
MIN_STOCK_PRICE      = 20       # Minimum price (avoid penny stocks)

# Weekly trend
WEEKLY_SMA_SHORT     = 10
WEEKLY_SMA_LONG      = 20

# Volume
VOLUME_SMA_PERIOD    = 20


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


def _volume_sma(df: pd.DataFrame, period: int = VOLUME_SMA_PERIOD) -> pd.Series:
    return df["volume"].rolling(period).mean()


def _find_support(df: pd.DataFrame, lookback: int) -> float:
    """Find most recent meaningful support via swing lows."""
    recent       = df.tail(lookback)
    best_support = recent["low"].min()

    for i in range(len(recent) - 2, 1, -1):
        low_val = recent["low"].iloc[i]
        if (low_val < recent["low"].iloc[i-1] and
            low_val < recent["low"].iloc[i+1]):
            best_support = low_val
            break

    return round(float(best_support), 2)


def _find_resistance(df: pd.DataFrame, lookback: int) -> float:
    """Find most recent meaningful resistance via swing highs."""
    recent          = df.tail(lookback)
    best_resistance = recent["high"].max()

    for i in range(len(recent) - 2, 1, -1):
        high_val = recent["high"].iloc[i]
        if (high_val > recent["high"].iloc[i-1] and
            high_val > recent["high"].iloc[i+1]):
            best_resistance = high_val
            break

    return round(float(best_resistance), 2)


def _has_required_columns(df: pd.DataFrame, cols: list) -> bool:
    """Guard against missing columns from API anomalies."""
    return df is not None and all(c in df.columns for c in cols)


# ══════════════════════════════════════════════════════════
# STEP 1 — HARD FILTERS
# ══════════════════════════════════════════════════════════

def passes_hard_filters(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame
) -> tuple:
    """
    Hard filters — if any fails, stock is skipped entirely.
    Returns (passes, reason).
    """

    # Column validation — protects against API returning bad data
    if not _has_required_columns(daily_df, ["close", "high", "low", "volume"]):
        return False, "Missing required columns"

    if len(daily_df) < MIN_CANDLES_DAILY:
        return False, "Insufficient data"

    close   = daily_df["close"]
    current = float(close.iloc[-1])

    # Filter: Weekly trend not in clear downtrend
    if (_has_required_columns(weekly_df, ["close"]) and
            len(weekly_df) >= MIN_CANDLES_WEEKLY):
        wc      = weekly_df["close"]
        # Fix: tail().mean() is more efficient than rolling().mean().iloc[-1]
        w_sma10 = float(wc.tail(WEEKLY_SMA_SHORT).mean())
        w_sma20 = float(wc.tail(min(WEEKLY_SMA_LONG, len(wc))).mean())
        if (float(wc.iloc[-1]) < w_sma10 and
            float(wc.iloc[-1]) < w_sma20 and
            float(wc.iloc[-1]) < float(wc.iloc[-4])):
            return False, "Weekly downtrend"

    # Filter: Not more than 10% below 200 DMA
    if len(close) >= DMA_PERIOD:
        # Fix: tail().mean() instead of rolling().mean().iloc[-1]
        dma200 = float(close.tail(DMA_PERIOD).mean())
        if current < dma200 * DMA_MAX_BELOW_PCT:
            return False, "Too far below 200 DMA"

    # Filter: Not in freefall
    if len(close) >= FREEFALL_PERIOD:
        month_ago = float(close.iloc[-FREEFALL_PERIOD])
    else:
        month_ago = float(close.iloc[0])

    # Fix: ZeroDivisionError guard — month_ago can be 0 on bad API data
    if month_ago and month_ago != 0:
        monthly_change = (current - month_ago) / month_ago * 100
        if monthly_change < FREEFALL_MAX_DROP:
            return False, "Falling more than 25% in a month"

    # Filter: Not a penny stock
    if current < MIN_STOCK_PRICE:
        return False, f"Price below ₹{MIN_STOCK_PRICE}"

    return True, "OK"


# ══════════════════════════════════════════════════════════
# STEP 2 — IDENTIFY THE STORY
# ══════════════════════════════════════════════════════════

def identify_signal_type(daily_df: pd.DataFrame) -> dict:
    """Identifies which type of opportunity this is."""
    close  = daily_df["close"]
    volume = daily_df["volume"]
    high   = daily_df["high"]
    low    = daily_df["low"]

    current = float(close.iloc[-1])
    vol_sma = float(_volume_sma(daily_df).iloc[-1])
    vol_now = float(volume.iloc[-3:].mean())
    ema21   = float(_ema(close, 21).iloc[-1])
    ema50   = float(_ema(close, 50).iloc[-1])
    ema200  = float(_ema(close, 200).iloc[-1]) if len(close) >= 200 else ema50
    rsi_val = float(_rsi(close).iloc[-1])

    year_high = float(high.tail(252).max()) if len(high) >= 252 else float(high.max())
    year_low  = float(low.tail(252).min())  if len(low)  >= 252 else float(low.min())

    # Guard against year_high = 0
    from_high = ((current - year_high) / year_high * 100) if year_high != 0 else 0

    # PULLBACK BUY
    if (current > ema200 and current > ema50 and
            -25 < from_high < -8 and 35 < rsi_val < 55):
        return {
            "signal_type": "PULLBACK BUY",
            "story":       f"Strong stock pulled back {abs(from_high):.1f}% from highs. Long term uptrend intact. Good entry at discount.",
            "strength":    3 if from_high > -15 else 2,
            "emoji":       "📉➡️📈",
            "sl_lookback": 60
        }

    # BREAKOUT BUY
    recent_high = float(high.tail(20).max())
    vol_ratio   = (vol_now / vol_sma) if vol_sma != 0 else 1

    if (current >= recent_high * 0.99 and
            vol_ratio > 1.3 and
            rsi_val > 50 and current > ema21):
        return {
            "signal_type": "BREAKOUT BUY",
            "story":       f"Breaking above recent resistance with {vol_ratio:.1f}x normal volume. Momentum is strong.",
            "strength":    3 if from_high > -5 else 2,
            "emoji":       "🚀",
            "sl_lookback": 20
        }

    # RECOVERY BUY
    rsi_5d_ago = float(_rsi(close).iloc[-5]) if len(close) >= 5 else rsi_val
    if (35 < rsi_val < 55 and rsi_5d_ago < 35 and
            float(close.iloc[-5]) != 0 and
            current > float(close.iloc[-5]) and
            current > ema200):
        return {
            "signal_type": "RECOVERY BUY",
            "story":       f"Stock was oversold (RSI hit {rsi_5d_ago:.0f}) and is now recovering. Momentum turning positive.",
            "strength":    2,
            "emoji":       "🔄",
            "sl_lookback": 90
        }

    # CONSOLIDATION BREAKOUT
    high_20   = float(high.tail(20).max())
    low_20    = float(low.tail(20).min())
    range_pct = ((high_20 - low_20) / low_20 * 100) if low_20 != 0 else 0

    if (range_pct < 12 and current >= high_20 * 0.98 and vol_now > vol_sma):
        return {
            "signal_type": "CONSOLIDATION BREAKOUT",
            "story":       f"Stock consolidated in a tight {range_pct:.1f}% range and is now breaking out.",
            "strength":    2,
            "emoji":       "💥",
            "sl_lookback": 30
        }

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
    current = float(close.iloc[-1])
    score   = 0
    reasons = []
    warnings= []

    # ── RSI (0-20 pts) ────────────────────────────────────
    rsi     = _rsi(close)
    rsi_now = float(rsi.iloc[-1])
    rsi_prev= float(rsi.iloc[-3])

    if 40 <= rsi_now <= 60:
        score += 20
        reasons.append(f"RSI at {rsi_now:.0f} — healthy momentum zone")
    elif 30 <= rsi_now < 40:
        score += 15
        reasons.append(f"RSI recovering from oversold ({rsi_now:.0f})" if rsi_now > rsi_prev
                       else f"RSI at {rsi_now:.0f} — near oversold")
    elif 60 < rsi_now <= 70:
        score += 12
        reasons.append(f"RSI at {rsi_now:.0f} — strong momentum")
    elif rsi_now > 70:
        score += 5
        warnings.append(f"RSI at {rsi_now:.0f} — overbought, risky entry")
    elif rsi_now < 30:
        score += 8
        reasons.append(f"RSI bouncing from oversold ({rsi_now:.0f})" if rsi_now > rsi_prev
                       else f"RSI at {rsi_now:.0f} — deeply oversold")

    # ── MACD (0-20 pts) ───────────────────────────────────
    _, _, hist = _macd(close)
    hist_now   = float(hist.iloc[-1])
    hist_prev  = float(hist.iloc[-2])

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

    # ── Moving Averages (0-20 pts) ────────────────────────
    ema21  = float(_ema(close, 21).iloc[-1])
    ema50  = float(_ema(close, 50).iloc[-1])
    # Fix: tail().mean() for 200 DMA
    ema200 = float(close.tail(DMA_PERIOD).mean()) if len(close) >= DMA_PERIOD else ema50

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

    # ── Volume (0-15 pts) ─────────────────────────────────
    vol_sma   = float(_volume_sma(daily_df).iloc[-1])
    vol_5d    = float(volume.tail(5).mean())
    vol_ratio = (vol_5d / vol_sma) if vol_sma != 0 else 1

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

    # ── 52 Week Position (0-15 pts) ───────────────────────
    year_high  = float(high.tail(252).max()) if len(high) >= 252 else float(high.max())
    year_low   = float(low.tail(252).min())  if len(low)  >= 252 else float(low.min())
    year_range = year_high - year_low
    position   = ((current - year_low) / year_range * 100) if year_range != 0 else 50
    from_high  = ((current - year_high) / year_high * 100) if year_high != 0 else 0

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

    # ── Trend Consistency (0-10 pts) ──────────────────────
    if len(close) >= 20:
        h10 = float(high.tail(10).max())
        h20 = float(high.tail(20).head(10).max())
        l10 = float(low.tail(10).min())
        l20 = float(low.tail(20).head(10).min())

        if h10 > h20 and l10 > l20:
            score += 10
            reasons.append("Making higher highs and higher lows — healthy uptrend")
        elif h10 > h20 or l10 > l20:
            score += 5

    return {
        "score":    min(100, max(0, score)),   # Clamp 0-100
        "reasons":  reasons,
        "warnings": warnings,
        "rsi":      round(rsi_now, 1),
        "above_200":current > ema200,
        "vol_ratio":round(vol_ratio, 2)
    }


# ══════════════════════════════════════════════════════════
# STEP 4 — RISK/REWARD
# ══════════════════════════════════════════════════════════

def calculate_risk_reward(daily_df: pd.DataFrame, sl_lookback: int = 20) -> dict:
    """Chart-based stop loss with 5% hard maximum."""
    close   = daily_df["close"]
    current = float(close.iloc[-1])
    atr     = float(_atr(daily_df).iloc[-1])

    lookback  = min(sl_lookback, len(daily_df) - 1)
    support   = _find_support(daily_df, lookback)
    stop_loss = round(support * 0.99, 2)

    max_stop  = round(current * (1 - MAX_STOP_LOSS_PCT / 100), 2)
    if stop_loss < max_stop:
        stop_loss = max_stop

    if stop_loss >= current:
        stop_loss = round(current * 0.95, 2)

    resistance = _find_resistance(daily_df, lookback)
    if resistance <= current * 1.04:
        resistance = round(current + (3.0 * atr), 2)

    target = resistance
    risk   = current - stop_loss

    # Ensure minimum 2:1 R/R
    min_target = round(current + (MIN_RR_RATIO * risk), 2)
    if target < min_target:
        target = min_target

    reward   = target - current
    rr       = round(reward / risk, 2) if risk > 0 else 0
    upside   = round((target - current) / current * 100, 1) if current != 0 else 0
    downside = round((current - stop_loss) / current * 100, 1) if current != 0 else 0

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
    if not _has_required_columns(hourly_df, ["close", "volume"]) or len(hourly_df) < 5:
        return {"timing": "NEUTRAL", "note": "No hourly data", "bonus": 0}

    close  = hourly_df["close"]
    volume = hourly_df["volume"]

    current        = float(close.iloc[-1])
    vol_avg        = float(volume.mean())
    vol_now        = float(volume.iloc[-1])
    rsi_hourly     = float(_rsi(close).iloc[-1]) if len(close) >= 14 else 50
    h_ema9         = float(_ema(close, min(9, len(close))).iloc[-1])
    _, _, hist     = _macd(close)
    hourly_macd_up = (float(hist.iloc[-1]) > float(hist.iloc[-2])) if len(hist) >= 2 else True

    if (current > h_ema9 and hourly_macd_up and
            30 < rsi_hourly < 70 and
            vol_avg != 0 and vol_now >= vol_avg * 0.8):
        return {"timing": "IDEAL",   "note": "Good entry — hourly trend up, momentum positive", "bonus": 5}
    elif rsi_hourly > 75:
        return {"timing": "WAIT",    "note": "Overbought on hourly — wait for small pullback",   "bonus": -5}
    elif current < h_ema9 and not hourly_macd_up:
        return {"timing": "WAIT",    "note": "Hourly trend down — wait for stabilisation",       "bonus": -3}
    else:
        return {"timing": "NEUTRAL", "note": "Entry timing is neutral",                          "bonus": 0}


# ══════════════════════════════════════════════════════════
# MASTER FUNCTION
# ══════════════════════════════════════════════════════════

def analyse_stock(symbol: str, data: dict) -> Optional[dict]:
    from stocks_list import get_sector

    daily_df  = data.get("price_data")
    weekly_df = data.get("weekly_data")
    hourly_df = data.get("hourly_data")

    passes, reason = passes_hard_filters(daily_df, weekly_df)
    if not passes:
        return None

    signal_info = identify_signal_type(daily_df)
    if signal_info["strength"] < 1:
        return None

    tech        = score_technicals(daily_df)
    sl_lookback = signal_info.get("sl_lookback", 20)
    rr_info     = calculate_risk_reward(daily_df, sl_lookback=sl_lookback)

    if not rr_info["is_valid"]:
        return None

    timing = check_entry_timing(hourly_df)

    story_bonus  = {3: 10, 2: 5, 1: 0}.get(signal_info["strength"], 0)
    timing_bonus = timing["bonus"]
    rr_bonus     = 8 if rr_info["risk_reward"] >= 3.0 else (5 if rr_info["risk_reward"] >= 2.5 else 2)

    # Clamp confidence to valid range
    raw_confidence = tech["score"] + story_bonus + timing_bonus + rr_bonus
    confidence     = max(0, min(MAX_CONFIDENCE, raw_confidence))

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
# ANALYSE ALL
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
            print(f"  Price:     ₹{r['price']:.2f}")
            print(f"  Target:    ₹{r['target']:.2f} (+{r['upside_pct']:.1f}%)")
            print(f"  Stop Loss: ₹{r['stop_loss']:.2f} (-{r['downside_pct']:.1f}%)")
            print(f"  R/R:       {r['risk_reward']:.2f}x")
            for reason in r["reasons"]:
                print(f"  • {reason}")