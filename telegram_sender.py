import os
import asyncio
from telegram import Bot
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_message_async(text: str):
    """Send a message via Telegram."""
    bot = Bot(token=TOKEN)
    # Telegram has a 4096 char limit per message
    if len(text) > 4000:
        # Split into chunks
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=chunk,
                parse_mode='Markdown'
            )
            await asyncio.sleep(0.5)
    else:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode='Markdown'
        )

def send_message(text: str):
    """Synchronous wrapper."""
    asyncio.run(send_message_async(text))

def format_recommendation(result: dict, rank: int) -> str:
    """Format a stock recommendation for Telegram."""
    
    symbol_clean = result['symbol'].replace('.NS', '')
    
    msg = f"""
{'='*35}
🏆 PICK #{rank}: *{symbol_clean}*
{'='*35}
📊 Signal: *{result['signal']}*
💯 Confidence: *{result['confidence']}%*

💰 Current Price: ₹{result['price']}
🎯 Target Price:  ₹{result['target']}
🛑 Stop Loss:    ₹{result['stop_loss']}
⚖️ Risk:Reward:  1:{result['risk_reward']:.1f}

📈 *Why this stock?*
"""
    
    # Add top 4 signal reasons
    for signal in result['signals'][:4]:
        msg += f"• {signal}\n"
    
    return msg

def format_full_report(recommendations: list, scanned_count: int) -> str:
    """Format the complete daily report."""
    
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    
    header = f"""
🤖 *AI STOCK PICKS — {now}*
📡 Scanned: {scanned_count} NSE stocks
🎯 High-Confidence Picks: {len(recommendations)}
"""
    
    if not recommendations:
        return header + "\n⚠️ No high-confidence picks today. Market conditions unfavorable. Stay in cash."
    
    body = ""
    for i, rec in enumerate(recommendations[:5], 1):  # Max 5 picks
        body += format_recommendation(rec, i)
    
    footer = """
━━━━━━━━━━━━━━━━━━━━
⚠️ *DISCLAIMER*
This is algorithmic analysis, NOT financial advice. Always do your own research. Never invest more than you can afford to lose.
━━━━━━━━━━━━━━━━━━━━
"""
    
    return header + body + footer