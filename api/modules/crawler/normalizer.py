import re, datetime as dt
from trafilatura import extract as trafilatura_extract
from langdetect import detect
from utils.metrics import normalizer_fallback_total
from utils.logger import setup_logger

log = setup_logger("normalizer")

def _clean(text:str)->str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t

def extract_main_text(url:str, summary_raw:str, domain:str|None=None)->str:
    try:
        txt = trafilatura_extract(url, include_comments=False, include_tables=False) or ""
        if len(txt.strip()) < 120:
            normalizer_fallback_total.labels(domain=domain or "unknown").inc()
            return _clean(summary_raw)
        return _clean(txt)
    except Exception as ex:
        normalizer_fallback_total.labels(domain=domain or "unknown").inc()
        log.warning({"msg":"normalize_fallback","url":url,"err":str(ex)})
        return _clean(summary_raw)

def detect_language(title:str, body:str)->str:
    sample = (title + ". " + body)[:5000]
    try:
        return detect(sample)
    except:
        return "en"

def parse_pub(published)->dt.datetime:
    if hasattr(published, "tm_year"):
        return dt.datetime(published.tm_year, published.tm_mon, published.tm_mday,
                           published.tm_hour, published.tm_min, published.tm_sec, tzinfo=dt.timezone.utc)
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
