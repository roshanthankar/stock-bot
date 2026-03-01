import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_stock_data(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """
    Fetch historical price data for a stock.
    period options: 1mo, 3mo, 6mo, 1y
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty or len(df) < 20:
            return None
            
        df.index = pd.to_datetime(df.index)
        return df
        
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def fetch_stock_info(symbol: str) -> dict:
    """
    Fetch fundamental data like P/E ratio, market cap etc.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "pe_ratio": info.get("trailingPE", None),
            "pb_ratio": info.get("priceToBook", None),
            "market_cap": info.get("marketCap", None),
            "52w_high": info.get("fiftyTwoWeekHigh", None),
            "52w_low": info.get("fiftyTwoWeekLow", None),
            "avg_volume": info.get("averageVolume", None),
            "current_price": info.get("currentPrice", None),
            "dividend_yield": info.get("dividendYield", None),
            "roe": info.get("returnOnEquity", None),
            "debt_to_equity": info.get("debtToEquity", None),
        }
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        return {}

def fetch_batch(symbols: list, delay: float = 0.5) -> dict:
    """
    Fetch data for multiple stocks with a small delay to avoid rate limits.
    Returns dict: { symbol: {"price_data": df, "info": dict} }
    """
    results = {}
    total = len(symbols)
    
    for i, symbol in enumerate(symbols):
        print(f"Fetching {symbol} ({i+1}/{total})...")
        
        price_data = fetch_stock_data(symbol)
        info = fetch_stock_info(symbol)
        
        if price_data is not None:
            results[symbol] = {
                "price_data": price_data,
                "info": info
            }
        
        time.sleep(delay)  # Be polite to the API
    
    print(f"\n✅ Successfully fetched {len(results)}/{total} stocks")
    return results