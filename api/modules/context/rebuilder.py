from api.storage.pg import get_conn
from datetime import datetime, timedelta, timezone
import re

POS_POLICIES = ["subsidy","approval","license","incentive"]
NEG_POLICIES = ["ban","probe","investigation","lawsuit","sanction","export control"]
SUPPLY_WORDS = ["HBM","CoWoS","capacity","lead time","shortage","production","recall"]
CUSTOMER_PHRASES = ["powered by","using","based on","adopted","partnered with","instance"]
COMPETITORS = ["AMD","Intel","TPU","Gaudi","MI300","MI325","MI350","Google TPU"]

def _norm(x: float, lo=0.0, hi=1.0)->float:
    if x is None: return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo))) if hi>lo else 0.0

def _score_company_context(company_name:str, since_days:int=30)->dict:
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        SELECT a.title, a.body, a.source_domain, a.published_at, COALESCE(m.topic_tags,'{}'), COALESCE(m.category,'general')
        FROM articles a
        JOIN article_meta m ON m.article_id=a.id
        JOIN article_entities e ON e.article_id=a.id
        WHERE e.company_id = (SELECT id FROM companies WHERE lower(name)=lower(%s))
          AND a.published_at >= %s
        """,(company_name, since))
        rows = cur.fetchall()

    # 시그널
    customer_hits=0; supply_hits=0; policy_pos=0; policy_neg=0; comp_hits=0
    customers=set(); suppliers=set(); policies=set(); competitors=set()

    for title, body, domain, ts, tags, cat in rows:
        txt = f"{title or ''}. {body or ''}"
        lo = txt.lower()

        # 고객(문구) 추출
        for ph in CUSTOMER_PHRASES:
            if ph in lo: customer_hits += 1

        # 공급/생산
        if any(w.lower() in lo for w in SUPPLY_WORDS): supply_hits += 1

        # 정책
        if any(w in lo for w in POS_POLICIES): policy_pos += 1
        if any(w in lo for w in NEG_POLICIES):
            policy_neg += 1
            policies.add(" ".join([w for w in NEG_POLICIES if w in lo]) or "policy risk")

        # 경쟁
        for c in COMPETITORS:
            if re.search(rf"\b{re.escape(c.lower())}\b", lo):
                comp_hits += 1
                competitors.add(c)

        # 간단 고객/공급사 문자열 추출(대문자 토큰)
        caps = set(re.findall(r"\b[A-Z][A-Za-z0-9&\-]{2,}\b", txt))
        # 지나치게 일반적인 단어 제거
        blacklist={"The","And","For","With","From","News","Report","Update","Market","Company"}
        caps = {x for x in caps if x not in blacklist}
        # 고객 후보
        for k in list(caps):
            if "Inc" in k or "LLC" in k or k in ("AWS","Azure","GCP","Meta","Tesla","Dell","HPE","Microsoft","Google","Amazon"):
                customers.add(k)

        # 공급 후보
        for k in list(caps):
            if k in ("TSMC","ASML","Micron","Samsung","SK","Foxconn","Quanta"):
                suppliers.add(k)

    # 점수화 (0~100)
    customer_score   = round(100 * _norm(customer_hits, 0, 25))
    supply_score     = round(100 * _norm(supply_hits,   0, 25))
    # 정책 리스크는 '부정-긍정'의 함수 (높을수록 리스크 ↑)
    policy_risk_pct  = round(100 * _norm(policy_neg - 0.3*policy_pos, 0, 15))
    competition_pct  = round(100 * _norm(comp_hits, 0, 20))

    # Calculate overall company_context_score
    overall_context_score = max(0, min(100, round(
        0.40 * customer_score + 
        0.30 * (100 - policy_risk_pct) + 
        0.20 * (100 - competition_pct) + 
        0.10 * supply_score
    )))

    return {
        "customer_score": customer_score,
        "supply_score": supply_score,
        "policy_risk_pct": policy_risk_pct,
        "competition_pct": competition_pct,
        "company_context_score": overall_context_score, # Include new score
        "customers": sorted(list(customers))[:12],
        "suppliers": sorted(list(suppliers))[:12],
        "policies": sorted(list(policies))[:12],
        "competitors": sorted(list(competitors))[:12]
    }

def rebuild_company_context(company_name:str)->dict:
    sc = _score_company_context(company_name, since_days=30)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO company_context(company_name, customer_score, supply_score, policy_risk_pct, competition_pct, company_context_score, customers, suppliers, policies, competitors, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
        ON CONFLICT (company_name) DO UPDATE SET
          customer_score=EXCLUDED.customer_score,
          supply_score=EXCLUDED.supply_score,
          policy_risk_pct=EXCLUDED.policy_risk_pct,
          competition_pct=EXCLUDED.competition_pct,
          company_context_score=EXCLUDED.company_context_score, -- Update new score
          customers=EXCLUDED.customers,
          suppliers=EXCLUDED.suppliers,
          policies=EXCLUDED.policies,
          competitors=EXCLUDED.competitors,
          updated_at=now()
        """,(company_name, sc["customer_score"], sc["supply_score"], sc["policy_risk_pct"], sc["competition_pct"], sc["company_context_score"],
             sc["customers"], sc["suppliers"], sc["policies"], sc["competitors"]))
    sc["company_name"]=company_name
    return sc
