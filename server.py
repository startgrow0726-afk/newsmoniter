from fastapi import FastAPI, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
import time, uuid
from sse_starlette.sse import EventSourceResponse
import json, asyncio, time
from datetime import datetime, time as dt_time, timezone
import pytz
from typing import Optional
import os
from datetime import date as dt_date

from storage.pg import get_conn, connect_db, disconnect_db, init_db
from utils.logger import setup_logger, request_id_ctx, get_request_id
from utils.metrics import *
from modules.alerts.bus import bus
from modules.markets.explain import explain_intraday_move
from modules.markets.recap import daily_recap
from modules.personalize.ranker import rank_score
from modules.markets.risk_refresh import refresh_market_risk
from modules.context.rebuilder import rebuild_company_context

log = setup_logger("server")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    log.info("Connecting to database...")
    await connect_db()
    log.info("Database connection established.")

@app.on_event("shutdown")
async def shutdown_event():
    log.info("Disconnecting from database...")
    await disconnect_db()
    log.info("Database connection closed.")

# ----- 구조화 로깅 미들웨어 -----
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # request id 컨텍스트
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request_id_ctx.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            dur = (time.perf_counter() - start) * 1000
            log.info({
                "msg": "http_request",
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status": response.status_code,
                "dur_ms": round(dur,2),
                "rid_hdr": rid
            })
            # 응답 헤더로도 리턴
            response.headers["X-Request-ID"] = rid
            return response
        except Exception as ex:
            dur = (time.perf_counter() - start) * 1000
            log.error({
                "msg": "http_unhandled_exception",
                "err": str(ex),
                "method": request.method,
                "path": request.url.path,
                "dur_ms": round(dur,2)
            })
            return JSONResponse({"error": "internal_error", "rid": rid}, status_code=500)

app.add_middleware(LoggingMiddleware)

# ----- /metrics (Prometheus) -----
metrics_app = make_asgi_app()   # /metrics 전용 서브앱
app.mount("/metrics", metrics_app)

@app.get("/health")
def health():
    return {"ok": True, "rid": get_request_id()}

@app.post("/subscribe_email")
async def subscribe_email(email: str = Body(..., embed=True)):
    email_file_path = os.path.join(os.path.dirname(__file__), "subscribed_emails.txt")
    with open(email_file_path, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {email}\n")
    return {"message": "Email subscribed successfully!"}

# --- 공통 유틸 ---
def in_quiet_hours(user_prefs: dict, now_utc: datetime, tz_name: str = 'Asia/Seoul') -> bool:
    # quiet_hours_start/end: 'HH:MM'
    start = user_prefs.get('quiet_hours_start','23:00')
    end   = user_prefs.get('quiet_hours_end','07:00')
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone('Asia/Seoul')
    now_local = now_utc.astimezone(tz)
    s_h, s_m = map(int, start.split(":"))
    e_h, e_m = map(int, end.split(":"))
    start_t = dt_time(s_h, s_m)
    end_t   = dt_time(e_h, e_m)
    cur_t = now_local.time()
    if start_t <= end_t:
        # 같은 날
        return start_t <= cur_t < end_t
    else:
        # 자정을 걸치는 범위
        return cur_t >= start_t or cur_t < end_t

def sev_rank(s: str) -> int:
    return {"LOW":0,"MEDIUM":1,"HIGH":2}.get((s or "LOW").upper(),0)

@app.get("/me/feed")
async def me_feed(limit:int=20, min_importance:int=55, severity:str|None=None, user_id:int=1):
    # 1) 후보 가져오기
    async with get_conn() as conn:
        q = """
        SELECT a.id, a.title, a.canonical_url, a.source_domain, a.published_at,
               m.category, m.topic_tags, m.related_event, m.importance_pct, m.accuracy_pct,
               m.impact_level, m.severity, COALESCE(ca.cluster_id,'') as cluster_id,
               ARRAY(SELECT al.url FROM article_links al WHERE al.article_id=a.id AND al.link_type='related' LIMIT 5) AS evidence
        FROM articles a
        JOIN article_meta m ON m.article_id=a.id
        LEFT JOIN cluster_articles ca ON ca.article_id=a.id
        WHERE m.importance_pct >= $1
        """
        params=[min_importance]
        if severity:
            q+=" AND m.severity=$2"; params.append(severity.upper())
        q+=" ORDER BY a.published_at DESC LIMIT $3"
        params.append(limit*3)  # 후보 넉넉히
        
        items = await conn.fetch(q, *params)
        items = [dict(row) for row in items]

        # 2) 유저 선호/행동
        row = await conn.fetchrow("SELECT COALESCE(topic_weights,'{}'), COALESCE(company_weights,'{}'), COALESCE(source_weights,'{}') FROM user_prefs WHERE user_id=$1",(user_id,))
        prefs={"topic_weights": row[0] if row else {}, "company_weights": row[1] if row else {}, "source_weights": row[2] if row else {}}

        beh = await conn.fetch("SELECT article_id, clicked, saved, delivered_at FROM deliveries WHERE user_id=$1 ORDER BY delivered_at DESC LIMIT 200",(user_id,))
        beh = [dict(row) for row in beh]

        seen_records = await conn.fetch("SELECT DISTINCT cluster_id FROM deliveries WHERE user_id=$1 AND seen=true", (user_id,))
        seen = {r['cluster_id'] for r in seen_records if r['cluster_id']}

    # 3) 랭킹 점수
    for it in items:
        it["score"] = rank_score(it, prefs, beh, seen)

    items.sort(key=lambda x:(x["score"], x["importance_pct"], x["published_at"]), reverse=True)
    return {"items": items[:limit]}

@app.get("/me/alerts/stream")
async def alerts_stream(user_id:int=1):
    async def gen():
        while True:
            try:
                item = await asyncio.wait_for(bus.queue.get(), timeout=20)
            except asyncio.TimeoutError:
                yield {"event":"ping","data":json.dumps({"ts":int(time.time())})}
                continue

            # --- 필터링: Quiet Hours, 최소 중요도/카테고리/Severity ---
            async with get_conn() as conn:
                r = await conn.fetchrow("""SELECT quiet_hours_start, quiet_hours_end, alert_min_importance, alert_categories, alert_severity_min,
                                      alert_gex_enabled, alert_gex_zero_band, alert_maxpain_enabled, alert_maxpain_gap_pct
                               FROM user_prefs WHERE user_id=$1""",(user_id,))
                prefs = {
                    "quiet_hours_start": r[0] if r else "23:00",
                    "quiet_hours_end":   r[1] if r else "07:00",
                    "alert_min_importance": r[2] if r else 70,
                    "alert_categories": r[3] if r else ["regulation","financials","supply_chain","corporate_action"],
                    "alert_severity_min": (r[4] if r else "LOW").upper(),
                    "alert_gex_enabled": bool(r[5]) if r else False,
                    "alert_gex_zero_band": float(r[6]) if r and r[6] is not None else 0.01,
                    "alert_maxpain_enabled": bool(r[7]) if r else False,
                    "alert_maxpain_gap_pct": float(r[8]) if r and r[8] is not None else 3.0
                }

            now_utc = datetime.now(timezone.utc)
            is_quiet = in_quiet_hours(prefs, now_utc, 'Asia/Seoul')

            imp_ok = (item.get("importance_pct",0) >= prefs["alert_min_importance"])
            cat_ok = item.get('category') in prefs['alert_categories'] if item.get('category') else True
            sev_ok = (sev_rank(item.get("severity","LOW")) >= sev_rank(prefs["alert_severity_min"]))

            gex_ok = True
            mp_ok  = True
            try:
                if prefs["alert_gex_enabled"]:
                    async with get_conn() as conn:
                        rr = await conn.fetchrow("""SELECT under_price, curve FROM option_gex_curve
                                       WHERE ticker=$1 ORDER BY updated_at DESC LIMIT 1""",
                                    (item.get("ticker","NVDA"),))  # 알림 payload에 ticker를 포함해 주세요
                    if rr:
                        spot = float(rr[0]) if rr[0] else None
                        curve = rr[1] or []
                        band = prefs["alert_gex_zero_band"]
                        lo, hi = (spot*(1.0-band), spot*(1.0+band)) if spot else (None, None)
                        sub = [x for x in curve if spot and lo <= float(x["strike"]) <= hi]
                        if sub:
                            signs = { "pos": any(x["gex"]>0 for x in sub),
                                      "neg": any(x["gex"]<0 for x in sub) }
                            gex_ok = (signs["pos"] and signs["neg"])  # 밴드 안에서 부호가 혼재 → 0 교차대 근접
                if prefs["alert_maxpain_enabled"]:
                    async with get_conn() as conn:
                        rr = await conn.fetchrow("""SELECT under_price, max_pain FROM option_gex_curve
                                       WHERE ticker=$1 ORDER BY updated_at DESC LIMIT 1""",
                                    (item.get("ticker","NVDA"),))
                    if rr and rr[0] and rr[1]:
                        spot, mp = float(rr[0]), float(rr[1])
                        gap_pct = abs(spot - mp) / max(1e-9, spot) * 100.0
                        mp_ok = (gap_pct >= prefs["alert_maxpain_gap_pct"])
            except Exception:
                gex_ok, mp_ok = True, True

            if is_quiet and item.get("severity","LOW") != "HIGH":
                continue
            if not (imp_ok and cat_ok and sev_ok and gex_ok and mp_ok):
                continue

            yield {"event":"alert",
                   "id": f"{item.get('cluster_id','')}-{int(time.time())}",
                   "data": json.dumps(item)}

    return EventSourceResponse(gen())

@app.get("/me/intraday_explain")
def intraday_explain(ticker:str, date:str, sector_ticker:str|None=None, index_ticker:str|None=None):
    return explain_intraday_move(ticker, date, sector_ticker, index_ticker)

@app.get("/me/recap")
def recap(ticker:str, date:str):
    return daily_recap(ticker, date)

def _read_json(path:str) -> Optional[dict]:
    try:
        if os.path.exists(path):
            with open(path,"r",encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None

def _read_csv_first(path:str) -> Optional[dict]:
    try:
        if os.path.exists(path):
            with open(path,"r",encoding="utf-8") as f:
                rd = csv.DictReader(f)
                for r in rd:
                    return r
    except Exception:
        return None
    return None

async def get_market_risk(ticker:str) -> dict:
    # 1) DB 캐시 우선
    async with get_conn() as conn:
        row = await conn.fetchrow("SELECT gamma_exposure, max_pain, put_call_ratio, short_float_pct, days_to_cover, updated_at FROM market_risk_cache WHERE ticker=$1",(ticker.upper(),))
        if row:
            return {
                "ticker": ticker.upper(),
                "gamma_exposure": float(row[0]) if row[0] is not None else None,
                "max_pain": float(row[1]) if row[1] is not None else None,
                "put_call_ratio": float(row[2]) if row[2] is not None else None,
                "short_float_pct": float(row[3]) if row[3] is not None else None,
                "days_to_cover": float(row[4]) if row[4] is not None else None,
                "source": "cache",
                "updated_at": row[5].isoformat() if row[5] else None
            }
    # 2) 로컬 파일 폴백
    base = "data"
    j = _read_json(os.path.join(base, f"options/{ticker.upper()}_risk.json")) or {}
    c = _read_csv_first(os.path.join(base, f"shorts/{ticker.upper()}_short.csv")) or {}
    risk = {
        "ticker": ticker.upper(),
        "gamma_exposure": j.get("gamma_exposure"),
        "max_pain": j.get("max_pain"),
        "put_call_ratio": j.get("put_call_ratio"),
        "short_float_pct": float(c.get("short_float_pct")) if c.get("short_float_pct") else None,
        "days_to_cover": float(c.get("days_to_cover")) if c.get("days_to_cover") else None,
        "source": "local"
    }
    return risk

@app.get("/market/risk")
async def market_risk(ticker:str):
    return await get_market_risk(ticker)

def _norm(x, low=0, high=100):
    try:
        v=float(x)
        v=max(low,min(high,v))
        return int(round(v))
    except Exception:
        return None

@app.get("/company/context")
async def company_context(company:str):
    # DB 우선, 없으면 로컬 파일 data/company_context.json에서 찾기
    async with get_conn() as conn:
        row = await conn.fetchrow("""SELECT customer_score, supply_score, policy_risk_pct, competition_pct,
                              customers, suppliers, policies, competitors, updated_at
                       FROM company_context WHERE lower(company_name)=lower($1)""",(company,))
    if row:
        data = {
            "company": company,
            "scores": {
                "customers": _norm(row[0]),
                "supply": _norm(row[1]),
                "policy_inverse": _norm(100 - (row[2] or 0)),
                "competition_inverse": _norm(100 - (row[3] or 0))
            },
            "lists": {
                "customers": row[4] or [],
                "suppliers": row[5] or [],
                "policies": row[6] or [],
                "competitors": row[7] or []
            },
            "source": "db"
        }
        return data

    # 로컬 파일 폴백
    js = _read_json("data/company_context.json") or {}
    rec = js.get(company) or js.get(company.upper()) or js.get(company.capitalize())
    if rec:
        return {
            "company": company,
            "scores": {
                "customers": _norm(rec.get("customer_score",70)),
                "supply": _norm(rec.get("supply_score",60)),
                "policy_inverse": _norm(100 - rec.get("policy_risk_pct",30)),
                "competition_inverse": _norm(100 - rec.get("competition_pct",40))
            },
            "lists": {
                "customers": rec.get("customers",[]),
                "suppliers": rec.get("suppliers",[]),
                "policies": rec.get("policies",[]),
                "competitors": rec.get("competitors",[])
            },
            "source": "local"
        }
    # 기본값
    return {
        "company": company,
        "scores": {"customers":60,"supply":60,"policy_inverse":70,"competition_inverse":65},
        "lists": {"customers":[],"suppliers":[],"policies":[],"competitors":[]},
        "source": "default"
    }

@app.get("/me/settings/alerts")
async def get_alert_settings(user_id:int=1):
    async with get_conn() as conn:
        r = await conn.fetchrow("""SELECT quiet_hours_start, quiet_hours_end, alert_min_importance,
                              alert_categories, alert_severity_min,
                              alert_gex_enabled, alert_gex_zero_band,
                              alert_maxpain_enabled, alert_maxpain_gap_pct
                       FROM user_prefs WHERE user_id=$1""",(user_id,))
        if not r:
            return {
              "quiet_hours":{"start":"23:00","end":"07:00"},
              "min_importance":70,"categories":["regulation","financials","supply_chain","corporate_action"],
              "severity_min":"LOW",
              "gex":{"enabled":False,"zero_band_pct":1.0},
              "maxpain":{"enabled":False,"gap_pct":3.0}
            }
        return {
          "quiet_hours":{"start":r[0], "end":r[1]},
          "min_importance": r[2],
          "categories": r[3],
          "severity_min": r[4],
          "gex":{"enabled": bool(r[5]), "zero_band_pct": float(r[6])*100 if r[6] and float(r[6])<1.0 else (float(r[6]) if r[6] else 1.0)},
          "maxpain":{"enabled": bool(r[7]), "gap_pct": float(r[8]) if r[8] else 3.0}
        }

@app.post("/me/settings/alerts")
async def set_alert_settings(user_id:int=1, payload: dict = Body(...)):
    qh = payload.get("quiet_hours",{})
    start = qh.get("start","23:00"); end = qh.get("end","07:00")
    min_imp = int(payload.get("min_importance",70))
    cats = payload.get("categories",["regulation","financials","supply_chain","corporate_action"])
    sev  = payload.get("severity_min","LOW").upper()
    gex  = payload.get("gex",{})
    mp   = payload.get("maxpain",{})

    # 프론트는 % 단위로 보냄 → 서버 저장은 소수(예: 1% → 0.01)
    gex_enabled = bool(gex.get("enabled", False))
    gex_band = float(gex.get("zero_band_pct", 1.0))
    if gex_band > 1.0: gex_band /= 100.0

    mp_enabled = bool(mp.get("enabled", False))
    mp_gap_pct = float(mp.get("gap_pct", 3.0))

    async with get_conn() as conn:
        await conn.execute("""
        INSERT INTO user_prefs(user_id, quiet_hours_start, quiet_hours_end, alert_min_importance,
                               alert_categories, alert_severity_min,
                               alert_gex_enabled, alert_gex_zero_band, alert_maxpain_enabled, alert_maxpain_gap_pct)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        ON CONFLICT (user_id) DO UPDATE SET
          quiet_hours_start=EXCLUDED.quiet_hours_start,
          quiet_hours_end=EXCLUDED.quiet_hours_end,
          alert_min_importance=EXCLUDED.alert_min_importance,
          alert_categories=EXCLUDED.alert_categories,
          alert_severity_min=EXCLUDED.alert_severity_min,
          alert_gex_enabled=EXCLUDED.alert_gex_enabled,
          alert_gex_zero_band=EXCLUDED.alert_gex_zero_band,
          alert_maxpain_enabled=EXCLUDED.alert_maxpain_enabled,
          alert_maxpain_gap_pct=EXCLUDED.alert_maxpain_gap_pct
        """,user_id, start, end, min_imp, cats, sev,
             gex_enabled, gex_band, mp_enabled, mp_gap_pct)
    return {"ok": True}

@app.post("/admin/market/risk/refresh")
def admin_risk_refresh(ticker:str, expiry:str|None=None, date:str|None=None):
    return refresh_market_risk(ticker, expiry, date)

@app.post("/admin/context/rebuild")
async def admin_ctx_rebuild(company:str):
    return await rebuild_company_context(company)

@app.get("/market/gex_curve")
async def gex_curve(ticker:str, as_of:str|None=None, expiry:str|None=None):
    # 최신 스냅샷(또는 요청 as_of/expiry)을 반환
    async with get_conn() as conn:
        if as_of and expiry:
            r = await conn.fetchrow("""SELECT under_price, max_pain, curve, updated_at
                           FROM option_gex_curve
                           WHERE ticker=$1 AND as_of=$2 AND expiry=$3""",
                        ticker.upper(), dt_date.fromisoformat(as_of), dt_date.fromisoformat(expiry))
        elif as_of:
            r = await conn.fetchrow("""SELECT under_price, max_pain, curve, updated_at
                           FROM option_gex_curve
                           WHERE ticker=$1 AND as_of=$2
                           ORDER BY updated_at DESC LIMIT 1""",
                        ticker.upper(), dt_date.fromisoformat(as_of))
        else:
            r = await conn.fetchrow("""SELECT under_price, max_pain, curve, updated_at
                           FROM option_gex_curve
                           WHERE ticker=$1
                           ORDER BY updated_at DESC LIMIT 1""",
                        ticker.upper())
    if not r:
        return {"ticker": ticker.upper(), "curve": [], "spot": None, "max_pain": None, "updated_at": None}
    return {
        "ticker": ticker.upper(),
        "curve": r[2],
        "spot": float(r[0]) if r[0] is not None else None,
        "max_pain": float(r[1]) if r[1] is not None else None,
        "updated_at": r[3].isoformat() if r[3] else None
    }

@app.get("/debug-static")
def debug_static_path():
    import os
    web_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
    dashboard_path = os.path.join(web_dir_path, "dashboard.html")
    index_path = os.path.join(web_dir_path, "index.html")
    return {
        "note": "This is a debug endpoint. It shows the paths the server is using for static files.",
        "cwd": os.getcwd(),
        "server_file_path": __file__,
        "calculated_web_dir": web_dir_path,
        "web_dir_exists": os.path.isdir(web_dir_path),
        "calculated_dashboard_path": dashboard_path,
        "dashboard_exists": os.path.isfile(dashboard_path),
        "calculated_index_path": index_path,
        "index_exists": os.path.isfile(index_path),
    }

web_dir_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "web"))
app.mount("/", StaticFiles(directory=web_dir_path, html=True), name="web")
