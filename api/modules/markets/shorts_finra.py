import os, httpx, csv, io

FINRA_BASE = os.getenv("FINRA_BASE","https://cdn.finra.org")
IEX_KEY = os.getenv("IEX_KEY","")
HTTP_TIMEOUT = float(os.getenv("PRICE_HTTP_TIMEOUT","8"))

def finra_daily_short_volume(ticker: str)->dict|None:
    """
    FINRA는 일별 short volume 파일을 공개. 포맷: CSV (Symbol, ShortVolume, TotalVolume, ShortExemptVolume, ...).
    실제 파일 경로는 일자별/거래소별로 다름. 여기선 통합 요약 API 프록시를 사용했다고 가정하거나,
    사내 파이프라인에서 최신 날짜 CSV를 합산해 둔 엔드포인트를 사용.
    간편화를 위해 통합 요약 프록시가 있다고 가정하고 예시를 제공합니다.
    """
    # 예시: /equity/shortsale/2025/2025-09-19/SHRT20250919.csv 와 같은 원본을 모두 합산해서 사내 캐시에 넣는 것을 권장.
    # 여기선 단순 스텁. 실구현에서는 날짜를 받아 최신 파일들을 병합하세요.
    return None  # 외부 파일 파싱은 환경 의존. 내부 캐시 사용 권장.

def iex_short_stats(ticker: str)->dict|None:
    if os.getenv("TEST_MODE") == "true":
        print("TEST_MODE: Using mock short stats data")
        return {"short_float_pct": 5.5, "days_to_cover": 2.1}
    if not IEX_KEY: return None
    try:
        import httpx
        url = f"https://cloud.iexapis.com/stable/stock/{ticker}/stats/shortInterest"
        with httpx.Client(timeout=HTTP_TIMEOUT) as cli:
            js = cli.get(url, params={"token": IEX_KEY}).json()
            # js: {"shortInterest":..., "shortRatio":..., "float":...}
            return {
                "short_float_pct": round(100.0 * float(js.get("shortInterest",0)) / max(1.0, float(js.get("float",0))), 2) if js.get("float") else None,
                "days_to_cover": float(js.get("shortRatio")) if js.get("shortRatio") is not None else None
            }
    except Exception:
        return None
