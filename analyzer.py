import pandas as pd
import numpy as np
import ta  # technical analysis library

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to the price dataframe."""
    
    # --- TREND INDICATORS ---
    # Moving Averages
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['EMA_9'] = ta.trend.ema_indicator(df['Close'], window=9)
    df['EMA_21'] = ta.trend.ema_indicator(df['Close'], window=21)
    
    # MACD (Moving Average Convergence Divergence)
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()
    
    # --- MOMENTUM INDICATORS ---
    # RSI (Relative Strength Index) - measures if overbought/oversold
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # Stochastic Oscillator
    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
    df['Stoch_K'] = stoch.stoch()
    df['Stoch_D'] = stoch.stoch_signal()
    
    # --- VOLATILITY INDICATORS ---
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['Close'], window=20)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    df['BB_mid'] = bb.bollinger_mavg()
    df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_mid']
    
    # ATR (Average True Range) - measures volatility
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
    
    # --- VOLUME INDICATORS ---
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_ratio'] = df['Volume'] / df['Volume_SMA_20']
    
    return df

def score_stock(df: pd.DataFrame, info: dict) -> dict:
    """
    Score a stock from 0-100 across 9 factors.
    Returns score and reasoning.
    """
    
    if df is None or len(df) < 50:
        return None
    
    df = calculate_technical_indicators(df)
    latest = df.iloc[-1]  # Most recent data point
    prev = df.iloc[-2]    # Previous day
    
    scores = {}
    signals = []
    
    # ============================================================
    # FACTOR 1: RSI Signal (0-15 points)
    # RSI < 30 = oversold = potential BUY
    # RSI > 70 = overbought = potential SELL
    # ============================================================
    rsi = latest['RSI']
    if rsi < 30:
        scores['rsi'] = 15
        signals.append(f"RSI {rsi:.1f} — Oversold (strong buy zone)")
    elif rsi < 40:
        scores['rsi'] = 12
        signals.append(f"RSI {rsi:.1f} — Approaching oversold")
    elif rsi < 50:
        scores['rsi'] = 8
        signals.append(f"RSI {rsi:.1f} — Neutral-bearish")
    elif rsi < 60:
        scores['rsi'] = 6
        signals.append(f"RSI {rsi:.1f} — Neutral-bullish")
    elif rsi < 70:
        scores['rsi'] = 4
        signals.append(f"RSI {rsi:.1f} — Approaching overbought")
    else:
        scores['rsi'] = 0
        signals.append(f"RSI {rsi:.1f} — Overbought (caution)")
    
    # ============================================================
    # FACTOR 2: MACD Signal (0-15 points)
    # MACD crossing above signal = BUY
    # ============================================================
    macd_cross_up = (latest['MACD'] > latest['MACD_signal']) and (prev['MACD'] <= prev['MACD_signal'])
    macd_positive = latest['MACD'] > latest['MACD_signal']
    macd_hist_rising = latest['MACD_hist'] > prev['MACD_hist']
    
    if macd_cross_up:
        scores['macd'] = 15
        signals.append("MACD crossed above signal — Bullish crossover!")
    elif macd_positive and macd_hist_rising:
        scores['macd'] = 10
        signals.append("MACD above signal and rising — Bullish momentum")
    elif macd_positive:
        scores['macd'] = 6
        signals.append("MACD above signal — Mildly bullish")
    else:
        scores['macd'] = 2
        signals.append("MACD below signal — Bearish")
    
    # ============================================================
    # FACTOR 3: Moving Average Trend (0-15 points)
    # Price above SMA20 > SMA50 = strong uptrend
    # ============================================================
    price = latest['Close']
    sma20 = latest['SMA_20']
    sma50 = latest['SMA_50']
    
    if price > sma20 > sma50:
        scores['trend'] = 15
        signals.append("Price > SMA20 > SMA50 — Strong uptrend")
    elif price > sma20:
        scores['trend'] = 10
        signals.append("Price above SMA20 — Short-term uptrend")
    elif price > sma50:
        scores['trend'] = 5
        signals.append("Price above SMA50 — Medium-term support")
    else:
        scores['trend'] = 0
        signals.append("Price below both MAs — Downtrend")
    
    # ============================================================
    # FACTOR 4: Bollinger Band Position (0-10 points)
    # Price near lower band = potential bounce (BUY)
    # ============================================================
    bb_position = (price - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower'])
    
    if bb_position < 0.1:
        scores['bollinger'] = 10
        signals.append("Price at lower Bollinger Band — Potential bounce")
    elif bb_position < 0.3:
        scores['bollinger'] = 7
        signals.append("Price in lower Bollinger zone — Attractive entry")
    elif bb_position < 0.6:
        scores['bollinger'] = 5
        signals.append("Price in mid Bollinger zone — Neutral")
    elif bb_position < 0.85:
        scores['bollinger'] = 2
        signals.append("Price in upper Bollinger zone — Stretched")
    else:
        scores['bollinger'] = 0
        signals.append("Price at upper Bollinger Band — Overbought risk")
    
    # ============================================================
    # FACTOR 5: Volume Analysis (0-15 points)
    # High volume on up days = conviction
    # ============================================================
    vol_ratio = latest['Volume_ratio']
    price_up = price > prev['Close']
    
    if vol_ratio > 2.0 and price_up:
        scores['volume'] = 15
        signals.append(f"Volume {vol_ratio:.1f}x above average on up move — Strong conviction!")
    elif vol_ratio > 1.5 and price_up:
        scores['volume'] = 10
        signals.append(f"Volume {vol_ratio:.1f}x above average — Good buying interest")
    elif vol_ratio > 1.0:
        scores['volume'] = 6
        signals.append(f"Volume slightly above average")
    else:
        scores['volume'] = 3
        signals.append(f"Volume below average — Low conviction")
    
    # ============================================================
    # FACTOR 6: 52-Week Position (0-10 points)
    # Near 52-week low but turning = opportunity
    # ============================================================
    high_52w = info.get('52w_high')
    low_52w = info.get('52w_low')
    
    if high_52w and low_52w and high_52w > low_52w:
        position_52w = (price - low_52w) / (high_52w - low_52w)
        
        if position_52w < 0.2:
            scores['52w'] = 9
            signals.append(f"Near 52W Low — Deep value zone ({position_52w*100:.0f}% of range)")
        elif position_52w < 0.4:
            scores['52w'] = 7
            signals.append(f"In lower half of 52W range — Value zone")
        elif position_52w < 0.7:
            scores['52w'] = 5
            signals.append(f"Mid 52W range — Neutral")
        elif position_52w < 0.9:
            scores['52w'] = 3
            signals.append(f"Near 52W highs — Less upside")
        else:
            scores['52w'] = 1
            signals.append(f"At 52W High — Momentum play but risky")
    else:
        scores['52w'] = 4  # neutral if no data
    
    # ============================================================
    # FACTOR 7: Momentum (3-day price change) (0-10 points)
    # ============================================================
    if len(df) >= 4:
        momentum_3d = (price - df.iloc[-4]['Close']) / df.iloc[-4]['Close'] * 100
        
        if 1 < momentum_3d < 5:
            scores['momentum'] = 10
            signals.append(f"3-day momentum +{momentum_3d:.1f}% — Healthy upside")
        elif momentum_3d > 5:
            scores['momentum'] = 5
            signals.append(f"3-day momentum +{momentum_3d:.1f}% — Strong but watch for pullback")
        elif -1 < momentum_3d < 1:
            scores['momentum'] = 6
            signals.append(f"3-day flat — Consolidating")
        elif -3 < momentum_3d < -1:
            scores['momentum'] = 4
            signals.append(f"3-day momentum {momentum_3d:.1f}% — Mild weakness")
        else:
            scores['momentum'] = 2
            signals.append(f"3-day momentum {momentum_3d:.1f}% — Weak")
    else:
        scores['momentum'] = 5
    
    # ============================================================
    # FACTOR 8: Stochastic (0-5 points)
    # ============================================================
    stoch_k = latest['Stoch_K']
    stoch_d = latest['Stoch_D']
    
    if stoch_k < 20 and stoch_k > stoch_d:
        scores['stoch'] = 5
        signals.append(f"Stochastic {stoch_k:.0f} — Oversold with upward cross")
    elif stoch_k < 30:
        scores['stoch'] = 3
        signals.append(f"Stochastic {stoch_k:.0f} — Oversold zone")
    elif stoch_k > 80:
        scores['stoch'] = 1
        signals.append(f"Stochastic {stoch_k:.0f} — Overbought zone")
    else:
        scores['stoch'] = 2
        signals.append(f"Stochastic {stoch_k:.0f} — Neutral")
    
    # ============================================================
    # FACTOR 9: P/E Ratio - Fundamental (0-5 points)
    # ============================================================
    pe = info.get('pe_ratio')
    
    if pe and pe > 0:
        if pe < 15:
            scores['pe'] = 5
            signals.append(f"P/E {pe:.1f} — Undervalued")
        elif pe < 25:
            scores['pe'] = 4
            signals.append(f"P/E {pe:.1f} — Fairly valued")
        elif pe < 40:
            scores['pe'] = 2
            signals.append(f"P/E {pe:.1f} — Moderately expensive")
        else:
            scores['pe'] = 0
            signals.append(f"P/E {pe:.1f} — Expensive")
    else:
        scores['pe'] = 2  # neutral if no data
    
    # --- CALCULATE TOTAL SCORE ---
    total_score = sum(scores.values())
    max_possible = 100
    confidence = (total_score / max_possible) * 100
    
    # --- DETERMINE SIGNAL TYPE ---
    if confidence >= 65:
        signal_type = "STRONG BUY 🟢"
    elif confidence >= 55:
        signal_type = "BUY 🟩"
    elif confidence >= 45:
        signal_type = "HOLD/WATCH 🟡"
    elif confidence >= 35:
        signal_type = "WEAK 🟠"
    else:
        signal_type = "AVOID 🔴"
    
    # --- CALCULATE TARGET & STOP LOSS ---
    atr = latest['ATR']
    
    if confidence >= 55:  # BUY signal
        target_price = price + (atr * 3)    # 3x ATR above
        stop_loss = price - (atr * 1.5)     # 1.5x ATR below
        risk_reward = (target_price - price) / (price - stop_loss)
    else:
        target_price = price * 1.05         # 5% target
        stop_loss = price * 0.95            # 5% stop
        risk_reward = 1.0
    
    return {
        "symbol": None,  # Will be filled by caller
        "price": round(price, 2),
        "signal": signal_type,
        "confidence": round(confidence, 1),
        "total_score": total_score,
        "target": round(target_price, 2),
        "stop_loss": round(stop_loss, 2),
        "risk_reward": round(risk_reward, 2),
        "signals": signals,
        "scores": scores
    }