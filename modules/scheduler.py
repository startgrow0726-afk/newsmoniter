from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

# Import the functions to be scheduled
from .pipeline.orchestrator import run_news_pipeline
from .data_sources.finra import fetch_finra_short_volume
from ..storage.database import AsyncSessionFactory
from ..storage import crud
import pandas as pd

async def run_finra_job():
    """Fetches FINRA short volume data and saves it to the database."""
    print(f"[{datetime.now()}] Running FINRA short volume job...")
    # FINRA data is for the previous trading day (T-1)
    trade_date = datetime.now() - timedelta(days=1)
    df = await fetch_finra_short_volume(trade_date)
    
    if df is not None and not df.empty:
        df['short_volume_ratio'] = df['ShortVolume'] / df['TotalVolume']
        # Rename columns to match DB model
        df.rename(columns={
            'Date': 'date', 'Symbol': 'ticker', 
            'ShortVolume': 'short_volume', 'TotalVolume': 'total_volume'
        }, inplace=True)

        records = df[['date', 'ticker', 'short_volume', 'total_volume', 'short_volume_ratio']].to_dict(orient='records')
        
        db: AsyncSession = AsyncSessionFactory()
        try:
            # In a real scenario, this should be an efficient bulk upsert.
            for record in records:
                await crud.save_short_interest_record(db, record) # A new CRUD function is needed
            await db.commit()
            print(f"Successfully saved {len(records)} FINRA records.")
        except Exception as e:
            print(f"[ERROR] Failed to save FINRA data: {e}")
            await db.rollback()
        finally:
            await db.close()


# from .analysis.intraday import run_intraday_analysis_for_all_markets
# from .analysis.recap import run_morning_recap_for_all_users

scheduler = AsyncIOScheduler(timezone="UTC")

def setup_jobs():
    """Sets up and schedules all recurring jobs."""
    pipeline_interval = int(os.getenv("PIPELINE_INTERVAL_MINUTES", "10"))

    # 1. News Pipeline (runs continuously)
    scheduler.add_job(
        # run_news_pipeline, # Placeholder for the actual function
        lambda: print("Running news pipeline..."), # Dummy function for now
        'interval',
        minutes=pipeline_interval,
        id='news_pipeline_job',
        replace_existing=True
    )

    # 2. Post-Market Analysis (runs once per day after market close)
    # This job will be dynamically scheduled based on market data.
    # For now, we add a placeholder job that runs once a day.
    scheduler.add_job(
        # run_intraday_analysis_for_all_markets, # Placeholder
        lambda: generate_postmarket_report("NVDA", datetime.now()), # Placeholder
        CronTrigger(hour=22, minute=30, day_of_week='mon-fri'), # Example: 22:30 UTC for NYSE close
        id='post_market_analysis_job',
        replace_existing=True
    )

    # 3. Pre-Market Insight (runs once per day in the morning KST)
    scheduler.add_job(
        # run_morning_recap_for_all_users, # Placeholder
        lambda: generate_premarket_briefing("NVDA"), # Placeholder
        CronTrigger(hour=22, minute=30, day_of_week='mon-fri', timezone='Asia/Seoul'), # 07:30 KST = 22:30 UTC of previous day
        id='pre_market_recap_job',
        replace_existing=True
    )

    print("All jobs have been scheduled.")
    print(scheduler.get_jobs())
)
