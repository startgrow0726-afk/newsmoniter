from api.modules.crawler.scheduler import start_jobs
from api.utils.logger import setup_logger
from api.modules.markets.risk_refresh import refresh_market_risk, refresh_gex_curve
from api.modules.context.rebuilder import rebuild_company_context
from api.modules.markets.explain import explain_intraday_move
from api.modules.markets.recap import daily_recap
from api.storage.pg import get_conn
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Added import
import os
from datetime import datetime, time as dt_time, timezone, date as dt_date, timedelta
import pytz

log = setup_logger("worker")

CTX_REFRESH_MIN = int(os.getenv("CTX_REFRESH_MIN","120"))
RISK_REFRESH_MIN = int(os.getenv("RISK_REFRESH_MIN","60"))

async def scheduled_refresh_context():
    # watchlist의 기업을 순회하며 갱신
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT c.name FROM user_watchlist uw JOIN companies c ON c.id=uw.company_id")
        names=[r[0] for r in cur.fetchall()]
    for nm in names or []:
        try:
            rebuild_company_context(nm)
        except Exception as e:
            print("context rebuild error", nm, e)

async def scheduled_refresh_risk():
    # watchlist의 티커를 순회
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT unnest(c.tickers) FROM user_watchlist uw JOIN companies c ON c.id=uw.company_id")
        ticks=[r[0] for r in cur.fetchall()]
    for t in ticks or []:
        try:
            refresh_market_risk(t)
        except Exception as e:
            print("risk refresh error", t, e)

async def scheduled_refresh_gex_curve():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT unnest(c.tickers) FROM user_watchlist uw JOIN companies c ON c.id=uw.company_id")
        ticks=[r[0] for r in cur.fetchall()]
    for t in ticks or []:
        try:
            refresh_gex_curve(t)
        except Exception as e:
            print("gex curve refresh error", t, e)

async def scheduled_intraday_explain():
    # 시장 마감 후 실행 (예: 미국 시장 마감 후)
    # 워치리스트의 티커를 순회하며 전일 데이터에 대해 explain_intraday_move 호출
    today = dt_date.today()
    yesterday = today - timedelta(days=1) # Adjust for weekends/holidays
    
    # TODO: Determine market close time and run after that
    # For now, assume it runs after market close for US stocks
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT unnest(c.tickers) FROM user_watchlist uw JOIN companies c ON c.id=uw.company_id")
        tickers = [r[0] for r in cur.fetchall()]
    
    for t in tickers or []:
        try:
            # Assuming explain_intraday_move can handle datetime.date
            explain_intraday_move(t, yesterday) # Pass yesterday's date
            log.info(f"Intraday explain generated for {t} on {yesterday}")
        except Exception as e:
            log.error(f"Intraday explain error for {t} on {yesterday}: {e}")

async def scheduled_daily_recap():
    # 매 영업일 아침 07:30 KST 실행
    today = dt_date.today()
    yesterday = today - timedelta(days=1) # Adjust for weekends/holidays
    
    # TODO: Ensure this runs only on weekdays and handles holidays
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT unnest(c.tickers) FROM user_watchlist uw JOIN companies c ON c.id=uw.company_id")
        tickers = [r[0] for r in cur.fetchall()]
    
    for t in tickers or []:
        try:
            # Assuming daily_recap can handle datetime.date
            daily_recap(t, yesterday) # Pass yesterday's date
            log.info(f"Daily recap generated for {t} on {yesterday}")
        except Exception as e:
            log.error(f"Daily recap error for {t} on {yesterday}: {e}")

def scheduler_start(loop):
    sch = AsyncIOScheduler(event_loop=loop, timezone="UTC")
    sch.add_job(scheduled_refresh_context, "interval", minutes=CTX_REFRESH_MIN, id="ctx_rebuild")
    sch.add_job(scheduled_refresh_risk, "interval", minutes=RISK_REFRESH_MIN, id="risk_refresh")
    sch.add_job(scheduled_refresh_gex_curve, "interval", minutes=max(30, int(os.getenv("RISK_REFRESH_MIN","60"))), id="gex_curve_refresh")
    
    # New jobs
    # Intraday explain: Run after US market close (e.g., 21:00 UTC for 16:00 ET)
    sch.add_job(scheduled_intraday_explain, "cron", hour=21, minute=0, day_of_week="mon-fri", id="intraday_explain")
    # Daily recap: Run every weekday morning at 07:30 KST (07:30 KST = 22:30 UTC previous day)
    sch.add_job(scheduled_daily_recap, "cron", hour=22, minute=30, day_of_week="sun-thu", id="daily_recap", timezone="UTC") # KST 07:30 is UTC 22:30 of previous day
    
    sch.start()
    print("scheduler_started: ctx=%sm, risk=%sm" % (CTX_REFRESH_MIN, RISK_REFRESH_MIN))

if __name__ == "__main__":
    log.info({"msg":"worker_boot"})
    start_jobs()
    # If running as main, we need an event loop
    import asyncio
    loop = asyncio.get_event_loop()
    scheduler_start(loop)
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass