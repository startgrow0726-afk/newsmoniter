from prometheus_client import Counter, Histogram, Gauge

# Fetcher
fetch_requests_total = Counter(
    "fetch_requests_total", "Number of RSS fetch requests", ["domain", "status"]
)
fetch_latency_seconds = Histogram(
    "fetch_latency_seconds", "Latency of RSS fetch requests", ["domain"]
)

# Pipeline/Articles
articles_ingested_total = Counter(
    "articles_ingested_total", "Number of articles inserted", ["domain"]
)
normalizer_fallback_total = Counter(
    "normalizer_fallback_total", "Times we had to fallback to summary_raw", ["domain"]
)
feed_errors_total = Counter(
    "feed_errors_total", "Errors while ingesting a feed", ["stage"]
)

# Scheduler
scheduler_runs_total = Counter(
    "scheduler_runs_total", "Number of scheduler runs", ["job"]
)
scheduler_running_gauge = Gauge(
    "scheduler_running", "1 if scheduler loop is healthy", ["job"]
)
