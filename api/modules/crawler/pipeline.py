import datetime as dt
from .fetcher import Fetcher
from .normalizer import extract_main_text, detect_language, parse_pub
from .dedupe import url_hash
from utils.metrics import articles_ingested_total, feed_errors_total
from utils.logger import setup_logger
from modules.nlp.pipe import enrich_article, _persist_links
from storage.pg import get_conn
from modules.cluster.clusterer import assign_cluster
from modules.alerts.bus import bus

log = setup_logger("pipeline")

def ingest_one_feed(feed_row:dict, fetcher:Fetcher, dao):
    res = fetcher.fetch_feed(feed_row)
    if res.get("etag") or res.get("last_modified"):
        dao.mark_feed_headers(feed_row["id"], res.get("etag"), res.get("last_modified"))
    if res["status"] != "ok":
        feed_errors_total.labels(stage="fetch").inc()
        return 0

    inserted = 0
    for e in res["entries"]:
        try:
            can = e["link"]
            body = extract_main_text(can, e["summary_raw"], e["source_domain"])
            lang = detect_language(e["title"], body)
            pub = parse_pub(e["published"])
            row = {
                "url": e["link"],
                "canonical_url": can,
                "url_hash": url_hash(can),
                "source_domain": e["source_domain"],
                "source_id": feed_row.get("source_id"),
                "title": e["title"],
                "body": body,
                "lang": lang,
                "published_at": pub
            }
            article_id = dao.insert_article(row)
            if article_id:
                inserted += 1
                articles_ingested_total.labels(domain=e["source_domain"]).inc()
                # ----- NLP -----
                meta = enrich_article({
                    "id": article_id, "title": row["title"], "body": row["body"], "lang": row["lang"],
                    "source_domain": row["source_domain"], "published_at": row["published_at"]
                })
                _persist_meta(article_id, meta)
                _persist_links(article_id, meta.get("related_links",[]))
                # ----- 클러스터 할당 -----
                cluster_id, csev = assign_cluster(article_id, row["title"], meta["ko_short"] or row["body"][:160],
                                                  severity=meta["severity"])
                # ----- 알림 트리거 -----
                if (meta["severity"] == "HIGH" or csev == "HIGH") and bus.should_send(cluster_id):
                    payload = {
                        "cluster_id": cluster_id,
                        "severity": "HIGH",
                        "title": row["title"],
                        "company": (meta["companies"][0]["name"] if meta.get("companies") else None),
                        "importance_pct": meta["importance_pct"],
                        "accuracy_pct": meta["accuracy_pct"],
                        "evidence": [],
                        "published_at": row["published_at"].isoformat(),
                        "category": meta["category"], 
                        "ticker": (meta["companies"][0]["ticker"] if meta.get("companies") and meta["companies"][0].get("ticker") else None)
                    }
                    try:
                        import asyncio
                        # 백그라운드에서 publish
                        asyncio.get_running_loop().create_task(bus.publish(payload))
                    except RuntimeError:
                        # 이벤트 루프 없으면 동기 대기용 루프 생성
                        asyncio.run(bus.publish(payload))

        except Exception as ex:
            feed_errors_total.labels(stage="normalize_or_insert").inc()
            log.error({"msg":"ingest_entry_error","url":e.get('link'),"err":str(ex)})
    if inserted:
        log.info({"msg":"ingest_feed_done","feed_id":feed_row["id"],"count":inserted})
    return inserted

def _persist_meta(article_id:int, meta:dict):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO article_meta(article_id, category, topic_tags, related_event, sentiment, positivity_pct, accuracy_pct, importance_pct, impact_level, severity)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (article_id) DO UPDATE SET
          category=EXCLUDED.category, topic_tags=EXCLUDED.topic_tags, related_event=EXCLUDED.related_event,
          sentiment=EXCLUDED.sentiment, positivity_pct=EXCLUDED.positivity_pct, accuracy_pct=EXCLUDED.accuracy_pct,
          importance_pct=EXCLUDED.importance_pct, impact_level=EXCLUDED.impact_level, severity=EXCLUDED.severity
        """,(
          article_id, meta["category"], meta["topic_tags"], meta["related_event"], meta["sentiment"],
          meta["positivity_pct"], meta["accuracy_pct"], meta["importance_pct"], meta["impact_level"], meta["severity"]
        ))
