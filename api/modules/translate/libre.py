import os, httpx, hashlib, json, time
from functools import lru_cache

BASE = os.getenv("TRANSLATE_BASE_URL","http://localhost:5000")
TIMEOUT = float(os.getenv("TRANSLATE_TIMEOUT","3.0"))

_cache = {}

def _key(text, src, tgt): 
    return hashlib.sha1(f"{src}>{tgt}:{text}".encode()).hexdigest()

def translate(text:str, source='en', target='ko')->str:
    if not text or source==target: return text
    k = _key(text,source,target)
    if k in _cache: return _cache[k]
    try:
        with httpx.Client(timeout=TIMEOUT) as cli:
            r = cli.post(f"{BASE}/translate", json={"q":text, "source":source, "target":target, "format":"text"})
        if r.status_code==200:
            out = r.json().get("translatedText") or text
            _cache[k]=out
            return out
    except Exception:
        pass
    return text
