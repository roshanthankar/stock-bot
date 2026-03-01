import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from stocks_list import ALL_STOCKS
from data_fetcher import fetch_batch
from analyzer import score_stock
from telegram_sender import send_message, format_full_report

def run_analysis():
    """Main function — runs the full scan and sends recommendations."""
    
    print(f"\n{'='*50}")
    print(f"🚀 Starting Stock Analysis — {datetime.now()}")
    print(f"{'='*50}")
    
    # Step 1: Send a "starting" message
    send_message(f"⏳ Starting scan of {len(ALL_STOCKS)} NSE stocks... Will send results shortly!")
    
    # Step 2: Fetch all stock data
    print(f"\n📡 Fetching data for {len(ALL_STOCKS)} stocks...")
    stock_data = fetch_batch(ALL_STOCKS, delay=0.3)
    
    # Step 3: Analyze each stock
    print(f"\n🔍 Analyzing {len(stock_data)} stocks...")
    results = []
    
    for symbol, data in stock_data.items():
        try:
            result = score_stock(data['price_data'], data['info'])
            if result:
                result['symbol'] = symbol
                results.append(result)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            continue
    
    # Step 4: Sort by confidence score (highest first)
    results.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Step 5: Filter only high-confidence BUY signals (60%+)
    top_picks = [r for r in results if r['confidence'] >= 60 and 'BUY' in r['signal']]
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Total analyzed: {len(results)}")
    print(f"🎯 High-confidence picks: {len(top_picks)}")
    
    # Step 6: Format and send the report
    report = format_full_report(top_picks[:5], len(results))
    send_message(report)
    
    print(f"\n✉️ Report sent to Telegram!")
    
    # Also print top picks to console
    print(f"\n--- TOP PICKS ---")
    for pick in top_picks[:5]:
        print(f"{pick['symbol']}: {pick['signal']} | {pick['confidence']}% | ₹{pick['price']}")
    
    return top_picks

if __name__ == "__main__":
    run_analysis()