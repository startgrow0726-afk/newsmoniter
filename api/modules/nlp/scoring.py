import json, os, math, urllib.parse

TRUST_PATH = os.path.join(os.path.dirname(__file__), "../../data/rules/source_trust.json")

def _trust(domain:str)->float:
    with open(TRUST_PATH,"r",encoding="utf-8") as f: T=json.load(f)
    return T.get(domain, T.get("unknown",0.6))

def sentiment_score(text:str)->float:
    pos = sum(text.lower().count(x) for x in ["soar","record","beat","strong","robust","optim"])
    neg = sum(text.lower().count(x) for x in ["plunge","miss","weak","ban","probe","risk","cut","downgrade"])
    if pos+neg==0: return 0.0
    return max(-1.0, min(1.0, (pos-neg)/(pos+neg)))

def accuracy_pct(domain:str, multisource:int=1, official:bool=False, metrics_cons:int=0)->int:
    base = int(100*_trust(domain))
    base += min(10, 3*max(0, multisource-1))
    base += 5 if official else 0
    base += max(-5, min(5, metrics_cons))
    return max(50, min(100, base))

_CAT_WEIGHT = {"financials":1.0,"corporate_action":0.95,"regulation":0.90,"supply_chain":0.80,"product":0.65,"competition":0.55,"general":0.40}

def importance_pct(category:str, sentiment:float, published_at, top_conf:float, impact_hint:float)->int:
    from datetime import datetime, timezone
    hours_ago = max(0.0, (datetime.now(timezone.utc)-published_at).total_seconds()/3600.0)
    recency = math.exp(-hours_ago/48)
    raw = 55*_CAT_WEIGHT.get(category,0.4) + 20*recency + 15*impact_hint + 10*abs(sentiment) + 10*top_conf
    return int(max(0, min(100, round(raw))))

def impact_level(importance:int, impact_hint:float)->str:
    if importance>=80 or impact_hint>=0.25: return "큼"
    if importance>=50: return "보통"
    return "작음"

def positivity_pct(sentiment:float)->int:
    return int(round((sentiment+1)*50))
