import os, time, httpx

PROVIDER = os.getenv("PRICE_PROVIDER", "alphavantage").lower()
AV_KEY  = os.getenv("ALPHAVANTAGE_KEY", "")
POLY_KEY= os.getenv("POLYGON_KEY", "")
IEX_KEY = os.getenv("IEX_KEY", "")

HTTP_TIMEOUT = float(os.getenv("PRICE_HTTP_TIMEOUT","8"))

def _get(url, params=None, headers=None):
    with httpx.Client(timeout=HTTP_TIMEOUT) as cli:
        r = cli.get(url, params=params or {}, headers=headers or {})
        r.raise_for_status()
        return r.json()

def fetch_intraday_alphavantage(ticker:str, interval="1min", output_size="compact"):
    # API 제한: 분당 5회/일 500회. 과호출 주의.
    url="https://www.alphavantage.co/query"
    js = _get(url, {"function":"TIME_SERIES_INTRADAY","symbol":ticker,
                    "interval":interval,"outputsize":output_size,"apikey":AV_KEY})
    key = next((k for k in js.keys() if "Time Series" in k), None)
    if not key: return []
    out=[]
    for ts, row in sorted(js[key].items()):
        out.append({
            "ts": ts,  # ISO 문자열
            "open": float(row["1. open"]),
            "high": float(row["2. high"]),
            "low":  float(row["3. low"]),
            "close":float(row["4. close"]),
            "volume": float(row["5. volume"])
        })
    return out

def fetch_intraday_polygon(ticker:str, date:str, timespan="minute"):
    # /v2/aggs/ticker/NVDA/range/1/minute/2025-09-19/2025-09-19
    base="https://api.polygon.io/v2/aggs/ticker/{}/range/1/{}/{}/{}"
    url=base.format(ticker.upper(), timespan, date, date)
    js = _get(url, {"apiKey": POLY_KEY})
    out=[]
    for r in js.get("results", []):
        out.append({
            "ts": int(r["t"]/1000),
            "open": r["o"], "high": r["h"], "low": r["l"],
            "close": r["c"], "volume": r["v"]
        })
    return out

def fetch_intraday_iex(ticker:str, range_="1d"):
    url=f"https://cloud.iexapis.com/stable/stock/{ticker}/intraday-prices"
    js=_get(url, {"token": IEX_KEY, "chartIEXOnly": "true"})
    out=[]
    for r in js:
        if not r.get("marketClose"): # 일부 레코드가 비어있음
            continue
        ts=f"{r['date']} {r['minute']}:00"
        out.append({
            "ts": ts,
            "open": r.get("open") or r.get("close") or 0.0,
            "high": r.get("high") or 0.0, "low": r.get("low") or 0.0,
            "close": r.get("close") or 0.0,
            "volume": r.get("volume") or 0.0
        })
    return out

def fetch_intraday(ticker:str, date_iso:str|None=None)->list[dict]:
    if os.getenv("TEST_MODE") == "true":
        print("TEST_MODE: Using mock intraday data")
        return [
            {'ts': '2025-09-20 09:30:00', 'open': 125.0, 'high': 126.0, 'low': 124.0, 'close': 125.5, 'volume': 1000000},
            {'ts': '2025-09-20 10:00:00', 'open': 125.5, 'high': 127.0, 'low': 125.0, 'close': 126.5, 'volume': 800000},
            {'ts': '2025-09-20 10:30:00', 'open': 126.5, 'high': 126.8, 'low': 125.5, 'close': 126.0, 'volume': 700000},
        ]

    if PROVIDER=="polygon" and POLY_KEY and date_iso:
        return fetch_intraday_polygon(ticker, date_iso)
    if PROVIDER=="iex" and IEX_KEY:
        return fetch_intraday_iex(ticker)
    # 기본: Alpha Vantage
    return fetch_intraday_alphavantage(ticker)
