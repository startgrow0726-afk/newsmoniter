from .options_orats import OratsClient, compute_gex, compute_max_pain, compute_put_call_ratio
from .shorts_finra import finra_daily_short_volume, iex_short_stats
from api.storage.pg import get_conn
from datetime import datetime, timezone
from .options_orats import build_gex_curve, nearest_zero_cross
from datetime import date as dt_date
import json

def refresh_market_risk(ticker:str, expiry:str|None=None, date:str|None=None)->dict:
    """옵션체인(ORATS)에서 GEX/MaxPain/PCR, 공매도(IEX/FINRA) 합쳐서 market_risk_cache 업데이트"""
    # 옵션
    gex=None; max_pain=None; pcr=None
    try:
        cli = OratsClient()
        chain = cli.option_chain(ticker, expiry=expiry, date=date)
        rows = chain.get("rows") or chain  # 공급사 응답 포맷에 따라 조정
        gex = compute_gex(rows)
        max_pain = compute_max_pain(rows)
        pcr = compute_put_call_ratio(rows)
    except Exception:
        pass

    # 공매도
    short_float=None; dtc=None
    stats = iex_short_stats(ticker) or {}
    short_float = stats.get("short_float_pct")
    dtc = stats.get("days_to_cover")

    # FINRA 일별 숏볼륨은 부가 정보로 활용 가능 (여기선 누락 가능)
    # sv = finra_daily_short_volume(ticker)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO market_risk_cache(ticker, gamma_exposure, max_pain, put_call_ratio, short_float_pct, days_to_cover, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s, now())
        ON CONFLICT (ticker) DO UPDATE SET
          gamma_exposure=EXCLUDED.gamma_exposure,
          max_pain=EXCLUDED.max_pain,
          put_call_ratio=EXCLUDED.put_call_ratio,
          short_float_pct=EXCLUDED.short_float_pct,
          days_to_cover=EXCLUDED.days_to_cover,
          updated_at=now()
        """, (ticker.upper(), gex, max_pain, pcr, short_float, dtc))
    
    try:
        refresh_gex_curve(ticker, expiry=expiry, date=date)
    except Exception:
        pass

    return {
        "ticker": ticker.upper(),
        "gamma_exposure": gex,
        "max_pain": max_pain,
        "put_call_ratio": pcr,
        "short_float_pct": short_float,
        "days_to_cover": dtc,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

def refresh_gex_curve(ticker:str, expiry:str|None=None, date:str|None=None)->dict:
    cli = OratsClient()
    chain = cli.option_chain(ticker, expiry=expiry, date=date)
    rows  = chain.get("rows") or chain
    curve = build_gex_curve(rows)
    # spot, max_pain 재활용
    try:
        spot = float(rows[0].get("underPrice", rows[0].get("under", 0)) or 0.0)
    except Exception:
        spot = None
    mp = compute_max_pain(rows)
    nz = nearest_zero_cross(curve, spot) if spot else None

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO option_gex_curve(ticker, as_of, expiry, under_price, max_pain, curve, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s, now())
        ON CONFLICT (ticker, as_of, COALESCE(expiry, '1970-01-01')) DO UPDATE SET
          under_price=EXCLUDED.under_price,
          max_pain=EXCLUDED.max_pain,
          curve=EXCLUDED.curve,
          updated_at=now()
        """, (ticker.upper(),
              (dt_date.fromisoformat(date) if date else dt_date.today()),
              (dt_date.fromisoformat(expiry) if expiry else None),
              spot, mp, json.dumps(curve)))
    return {"ticker": ticker.upper(), "spot": spot, "max_pain": mp, "zero_cross": nz, "count": len(curve)}