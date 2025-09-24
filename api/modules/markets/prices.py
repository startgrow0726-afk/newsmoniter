import os, csv, math, datetime as dt
from .providers import fetch_intraday

def _parse_ts(s:str)->dt.datetime:
    try:
        if isinstance(s,(int,float)) or (isinstance(s,str) and s.isdigit()):
            return dt.datetime.utcfromtimestamp(int(s)).replace(tzinfo=dt.timezone.utc)
        return dt.datetime.fromisoformat(s.replace("Z","")).replace(tzinfo=dt.timezone.utc)
    except Exception:
        return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

def load_csv_1m(ticker:str, date:str, base:str="data/ohlcv")->list[dict]:
    p = os.path.join(base, f"{ticker.upper()}_{date}.csv")
    if not os.path.exists(p): return []
    out=[]
    with open(p,"r",newline="",encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out.append({
                "ts": _parse_ts(r["ts"]),
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
                "volume": float(r["volume"])
            })
    return out

def load_1m(ticker:str, date:str|None=None)->list[dict]:
    # 1) 로컬 CSV 우선  2) 외부 API 폴백
    if date:
        csv_rows = load_csv_1m(ticker, date)
        if csv_rows: return csv_rows
    api_rows = fetch_intraday(ticker, date)
    out=[]
    for r in api_rows:
        out.append({
            "ts": _parse_ts(r["ts"]),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
            "volume": float(r["volume"])
        })
    return out

def vwap(series:list[dict])->float|None:
    num=0.0; den=0.0
    for r in series:
        price = (r["high"]+r["low"]+r["close"])/3.0
        vol = r["volume"]
        num += price*vol; den += vol
    return round(num/den, 4) if den>0 else None

def returns(series:list[dict])->list[float]:
    out=[]
    for i in range(1,len(series)):
        p0 = series[i-1]["close"]; p1 = series[i]["close"]
        if p0>0: out.append((p1/p0)-1.0)
    return out

def corr(a:list[float], b:list[float])->float|None:
    n=min(len(a), len(b))
    if n<3: return None
    a=a[-n:]; b=b[-n:]
    ma=sum(a)/n; mb=sum(b)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    va=sum((x-ma)**2 for x in a); vb=sum((y-mb)**2 for y in b)
    if va==0 or vb==0: return 0.0
    return round(cov/math.sqrt(va*vb), 3)
