import json, os, re
from dataclasses import dataclass

RULES_PATH = os.path.join(os.path.dirname(__file__), "../../data/rules/company_nvidia.json")

@dataclass
class Match:
    name:str; confidence:float; matched:str

def load_company_rules()->dict:
    with open(RULES_PATH,"r",encoding="utf-8") as f:
        return json.load(f)["COMPANY_CORE"]

def match_companies(title:str, body:str, rules=None)->list[Match]:
    if rules is None: rules = load_company_rules()
    txt = f"{title}\n{body}".lower()
    out=[]
    for name,meta in rules.items():
        score=0.0; alias_hits=0
        for t in meta.get("tickers",[]):
            if re.search(rf"\b{re.escape(t.lower())}\b", txt): score+=6
        for a in meta.get("aliases",[]):
            if re.search(rf"\b{re.escape(a.lower())}\b", txt):
                alias_hits+=1; score+=3
                if re.search(rf"\b{re.escape(a.lower())}\b", title.lower()): score+=2
        ctx = sum(1 for c in meta.get("context",[]) if re.search(rf"\b{re.escape(c.lower())}\b", txt))
        score += min(2, 0.3*ctx)
        neg = sum(1 for n in meta.get("negative",[]) if re.search(rf"\b{re.escape(n.lower())}\b", txt))
        score -= 1.5*neg
        ok = (alias_hits>=1) or (score>=6) or (alias_hits>=2) or (alias_hits>=1 and ctx>=2)
        if ok:
            conf = max(0.05, min(1.0, score/10))
            out.append(Match(name=name, confidence=round(conf,2), matched=name))
    out.sort(key=lambda m:m.confidence, reverse=True)
    return out
