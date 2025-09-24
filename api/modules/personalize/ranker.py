from math import exp
from datetime import datetime, timezone, timedelta

def decay(days:float, half_life=14.0)->float:
    return 0.5 ** (days/half_life)

def interest_match(item_topics:list[str], item_company:str|None, prefs:dict)->float:
    tw = prefs.get("topic_weights",{})
    cw = prefs.get("company_weights",{})
    sw = prefs.get("source_weights",{})
    t_score = sum(tw.get(t,0) for t in item_topics)/max(1,len(item_topics) or 1)
    c_score = cw.get(item_company or "", 0)
    s_score = 0  # 필요 시 도메인 반영
    return (t_score + c_score + s_score)/2.0  # -1..+1 → 평균

def behavior_boost(deliveries:list[dict])->float:
    # 최근 clicked/saved에 가중
    boost=0.0
    now=datetime.now(timezone.utc)
    for d in deliveries:
        if d.get("clicked") or d.get("saved"):
            dt_days = (now - d["delivered_at"]).total_seconds()/86400.0
            boost += 1.0*decay(dt_days)
    return min(1.0, boost)

def freshness(published_at)->float:
    hours = (datetime.now(timezone.utc)-published_at).total_seconds()/3600.0
    if hours<=12: return 1.0
    if hours<=48: return 0.3
    return 0.0

def rank_score(item, prefs, behavior, seen_cluster_ids:set)->int:
    base=item["importance_pct"]/100.0
    im = interest_match(item.get("topic_tags",[]), item.get("company_name"), prefs) # -1..+1
    bh = behavior_boost(behavior)  # 0..1
    dup = 1.0 if item.get("cluster_id") in seen_cluster_ids else 0.0
    fr = freshness(item["published_at"])  # 0..1
    score = 0.55*base + 0.20*max(-1.0, min(1.0, im))/2 + 0.10*(item.get("source_trust",0.7))
    score += 0.10*bh + 0.10*fr - 0.15*dup
    return int(round(score*100))
