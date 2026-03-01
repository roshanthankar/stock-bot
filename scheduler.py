from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from main import run_analysis
from telegram_sender import send_message

def start_scheduler():
    """Start the daily scheduler."""
    
    scheduler = BlockingScheduler()
    IST = pytz.timezone('Asia/Kolkata')
    
    # Run every weekday (Mon-Fri) at 8:00 AM IST
    scheduler.add_job(
        func=run_analysis,
        trigger=CronTrigger(
            day_of_week='mon-fri',  # Only weekdays
            hour=8,
            minute=0,
            timezone=IST
        ),
        id='daily_stock_scan',
        name='Daily NSE Stock Analysis',
        replace_existing=True
    )
    
    print("⏰ Scheduler started!")
    print("📅 Will run Mon-Fri at 8:00 AM IST")
    print("Press Ctrl+C to stop\n")
    
    send_message("✅ Stock Bot started! I'll send picks every weekday at 8 AM IST 🚀")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Scheduler stopped.")
        scheduler.shutdown()

if __name__ == "__main__":
    start_scheduler()