import os
from apscheduler.schedulers.background import BackgroundScheduler
from storage import dao as DAO
from .rate_limit import DomainRateLimiter
from .fetcher import Fetcher
from .pipeline import ingest_one_feed
from .sources import STATIC_FEEDS, gnews_query
from utils.metrics import scheduler_runs_total, scheduler_running_gauge
from utils.logger import setup_logger

log = setup_logger("scheduler")

def _seed_initial_feeds():
    for u in STATIC_FEEDS:
        DAO.upsert_feed(u, None, None)
    DAO.upsert_feed(gnews_query("NVIDIA", ["NVDA"]))

def start_jobs():
    rl = DomainRateLimiter(
        max_rps=float(os.getenv("MAX_RPS_DOMAIN","0.8")),
        max_concurrent=int(os.getenv("MAX_CONCURRENT_DOMAIN","2"))
    )
    fetcher = Fetcher(rl, DAO)

    def fetch_round_robin():
        job = "fetch_round_robin"
        scheduler_running_gauge.labels(job=job).set(1)
        scheduler_runs_total.labels(job=job).inc()
        rows = DAO.list_active_feeds(limit=20)
        for r in rows:
            try:
                ingest_one_feed(r, fetcher, DAO)
            except Exception as ex:
                log.error({"msg":"ingest_feed_error","feed_id":r.get("id"),"url":r.get("url"),"err":str(ex)})
        scheduler_running_gauge.labels(job=job).set(0)

    _seed_initial_feeds()
    sched = BackgroundScheduler(timezone=os.getenv("TZ","Asia/Seoul"))
    sched.add_job(fetch_round_robin, 'interval', seconds=int(os.getenv("FEED_INTERVAL_SEC","120")))
    sched.start()
    log.info({"msg":"scheduler_started","interval_sec":int(os.getenv('FEED_INTERVAL_SEC','120'))})
    return sched
