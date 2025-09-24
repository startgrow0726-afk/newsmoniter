import os, feedparser, httpx, urllib.parse, time
from .backoff import sleep_with_backoff
from utils.logger import setup_logger
from utils.metrics import fetch_requests_total, fetch_latency_seconds

UA = os.getenv("SEC_USER_AGENT","NewsMonitor/1.0")
log = setup_logger("fetcher")

class Fetcher:
    def __init__(self, rate_limiter, dao):
        self.r = rate_limiter
        self.dao = dao
        self.timeout = int(os.getenv("REQUEST_TIMEOUT","8"))

    def _headers(self, feed_row):
        h = {"User-Agent": UA}
        if feed_row.get("etag"): h["If-None-Match"] = feed_row["etag"]
        if feed_row.get("last_modified"): h["If-Modified-Since"] = feed_row["last_modified"]
        return h

    def _expand_gnews(self, link:str)->str:
        try:
            u = urllib.parse.urlparse(link)
            if "news.google.com" not in u.netloc: return link
            q = urllib.parse.parse_qs(u.query)
            return q.get("url",[link])[0]
        except:
            return link

    def _canonical(self, url:str)->str:
        u = urllib.parse.urlparse(url)
        qs = [(k,v) for k,v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(qs, doseq=True)))

    def fetch_feed(self, feed_row:dict)->dict:
        url = feed_row["url"]
        domain = urllib.parse.urlparse(url).netloc
        self.r.acquire(domain)
        t0 = time.perf_counter()
        try:
            for attempt in range(3):
                try:
                    resp = httpx.get(url, headers=self._headers(feed_row), timeout=self.timeout)
                    status = resp.status_code
                    fetch_requests_total.labels(domain=domain, status=str(status)).inc()
                    fetch_latency_seconds.labels(domain=domain).observe(time.perf_counter()-t0)

                    if status == 304:
                        log.info({"msg":"feed_not_modified","url":url,"domain":domain})
                        return {"status":"not_modified","entries":[], "etag":resp.headers.get("ETag"),
                                "last_modified":resp.headers.get("Last-Modified")}
                    if status != 200:
                        log.warning({"msg":"feed_bad_status","url":url,"status":status,"attempt":attempt+1})
                        sleep_with_backoff(attempt); continue

                    parsed = feedparser.parse(resp.content)
                    items = []
                    for e in parsed.entries[:100]:
                        link = e.get("link") or ""
                        link = self._expand_gnews(link)
                        link = self._canonical(link)
                        items.append({
                            "title": (e.get("title") or "").strip(),
                            "link": link,
                            "summary_raw": (e.get("summary") or e.get("description") or "").strip(),
                            "published": e.get("published_parsed") or e.get("updated_parsed") or None,
                            "source_domain": urllib.parse.urlparse(link).netloc
                        })
                    log.info({"msg":"feed_ok","url":url,"count":len(items)})
                    return {"status":"ok","entries":items,"etag":resp.headers.get("ETag"),
                            "last_modified":resp.headers.get("Last-Modified")}
                except Exception as ex:
                    log.warning({"msg":"feed_exception","url":url,"err":str(ex),"attempt":attempt+1})
                    sleep_with_backoff(attempt)
            log.error({"msg":"feed_error","url":url})
            return {"status":"error","entries":[]}
        finally:
            self.r.release(domain)
