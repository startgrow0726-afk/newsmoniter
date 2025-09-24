import os, httpx, math, time
from statistics import mean

ORATS_BASE = os.getenv("ORATS_BASE","https://api.orats.io")
ORATS_KEY  = os.getenv("ORATS_API_KEY","")
HTTP_TIMEOUT = float(os.getenv("PRICE_HTTP_TIMEOUT","8"))

class OratsClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ORATS_KEY

    def _get(self, path: str, params: dict):
        if not self.api_key:
            raise RuntimeError("ORATS_API_KEY missing")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=HTTP_TIMEOUT) as cli:
            r = cli.get(f"{ORATS_BASE}{path}", params=params, headers=headers)
            r.raise_for_status()
            return r.json()

    def option_chain(self, ticker: str, expiry: str | None = None, date: str | None = None):
        if os.getenv("TEST_MODE") == "true":
            print("TEST_MODE: Using mock option chain data")
            return { "rows": [
                {"strike": 120, "type": "C", "gamma": 0.05, "openInterest": 100, "underPrice": 125},
                {"strike": 125, "type": "C", "gamma": 0.08, "openInterest": 200, "underPrice": 125},
                {"strike": 130, "type": "C", "gamma": 0.06, "openInterest": 150, "underPrice": 125},
                {"strike": 120, "type": "P", "gamma": 0.04, "openInterest": 120, "underPrice": 125},
                {"strike": 125, "type": "P", "gamma": 0.07, "openInterest": 180, "underPrice": 125},
                {"strike": 130, "type": "P", "gamma": 0.05, "openInterest": 130, "underPrice": 125},
            ]}

        """
        ticker: 'NVDA'
        expiry: '2025-10-17' (선택)
        date:   '2025-09-19' (선택)
        """
        params = {"ticker": ticker.upper()}
        if expiry: params["expiry"] = expiry
        if date: params["date"] = date
        return self._get("/options/chain", params)

def compute_max_pain(chain_rows: list[dict]) -> float | None:
    """가장 누적 손실(콜·풋 OI * 거리)이 최소인 행사가 (Max Pain) 추정"""
    # 기대값 단순화: sum_over_strikes( abs(K - S)*OI_total_at_K )
    if not chain_rows: return None
    strikes = sorted(set(float(r["strike"]) for r in chain_rows))
    # 현물 S는 체인의 미드에서 유추(더 정확히는 외부 가격 사용)
    mids = []
    for r in chain_rows:
        bid = float(r.get("mid", r.get("mark", 0)) or 0)
        if bid>0: mids.append(bid)
    S = None
    try:
        S = float(chain_rows[0].get("underPrice") or chain_rows[0].get("under", 0)) or None
    except Exception:
        S = None

    best_k, best_loss = None, float("inf")
    # OI 합계 사전
    agg = {}
    for r in chain_rows:
        k = float(r["strike"]); t = r["type"].upper()  # 'C' or 'P'
        oi = float(r.get("openInterest", 0))
        if math.isnan(oi): oi = 0
        agg.setdefault(k, {"C":0, "P":0})
        agg[k][t] += oi

    for k in strikes:
        tot_oi = agg.get(k, {"C":0,"P":0})
        # 페이아웃 근사: 콜은 S>K면 (S-K)*OI, 풋은 K>S면 (K-S)*OI
        # S가 None이면 단순히 OI 총량 최소인 행사가를 proxy로 사용
        if S is None:
            loss = tot_oi["C"] + tot_oi["P"]
        else:
            loss = abs(S - k) * (tot_oi["C"] + tot_oi["P"])
        if loss < best_loss:
            best_loss = loss; best_k = k
    return best_k

def compute_gex(chain_rows: list[dict]) -> float | None:
    """
    감마 익스포저(GEX) 근사: Σ( gamma * price^2 * OI * contract_multiplier * sign )
    call은 +, put은 - 부호(시장 전반 감마 민감도)로 흔히 근사. 세부식은 공급사 정의에 맞게 조정.
    """
    if not chain_rows: return None
    gex = 0.0
    for r in chain_rows:
        gamma = float(r.get("gamma", 0) or 0)
        S = float(r.get("underPrice", r.get("under", 0)) or 0)
        oi = float(r.get("openInterest", 0) or 0)
        mult = 100.0  # 미국 주식 옵션
        sign = +1.0 if str(r.get("type","C")).upper().startswith("C") else -1.0
        gex += gamma * (S**2) * oi * mult * sign
    return round(gex, 2)

def compute_put_call_ratio(chain_rows: list[dict]) -> float | None:
    if not chain_rows: return None
    p = sum(float(r.get("openInterest",0) or 0) for r in chain_rows if str(r.get("type","P")).upper().startswith("P"))
    c = sum(float(r.get("openInterest",0) or 0) for r in chain_rows if str(r.get("type","C")).upper().startswith("C"))
    if (p+c) == 0: return None
    return round(p / max(1.0, c), 3)

def build_gex_curve(chain_rows: list[dict]) -> list[dict]:
    """
    rows: ORATS 체인 행들. 각 행은 최소한 {type(C/P), strike, gamma, underPrice} 포함
    return: [{"strike": K, "gex": gex_at_K}, ...] (콜 +, 풋 -의 합산)
    """
    if not chain_rows: return []
    agg = {}
    S = None
    for r in chain_rows:
        try:
            k = float(r["strike"])
            gamma = float(r.get("gamma", 0) or 0.0)
            S = S or float(r.get("underPrice", r.get("under", 0)) or 0.0)
            oi = float(r.get("openInterest", 0) or 0.0)
            mult = 100.0
            sign = +1.0 if str(r.get("type","C")).upper().startswith("C") else -1.0
            val = gamma * (S**2) * oi * mult * sign
            agg[k] = agg.get(k, 0.0) + val
        except Exception:
            continue
    curve = [{"strike": float(k), "gex": round(v, 2)} for k, v in agg.items()]
    curve.sort(key=lambda x: x["strike"])
    return curve

def nearest_zero_cross(curve: list[dict], spot: float) -> float | None:
    """
    스팟(현물)에 가장 가까운 구간에서 GEX 부호가 바뀌는(0 근처 통과) strike를 추정
    리턴: 추정 스트라이크(없으면 None)
    """
    if not curve or spot is None: return None
    # 인접한 두 점의 부호가 다르면 선형 보간으로 0 통과점 근사
    best = None; best_dist = 1e18
    for i in range(1, len(curve)):
        x0, y0 = curve[i-1]["strike"], curve[i-1]["gex"]
        x1, y1 = curve[i]["strike"], curve[i]["gex"]
        if y0 == 0: z = x0
        elif (y0 > 0 and y1 < 0) or (y0 < 0 and y1 > 0):
            # 선형 근사: y = y0 + (y1-y0)*t, y=0 -> t = -y0/(y1-y0)
            t = -y0/((y1 - y0) or 1e-9)
            z = x0 + (x1 - x0) * max(0.0, min(1.0, t))
        else:
            z = None
        if z is not None:
            d = abs(z - spot)
            if d < best_dist:
                best_dist = d; best = z
    return best