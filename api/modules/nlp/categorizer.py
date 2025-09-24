import json, os, re

RULES_PATH = os.path.join(os.path.dirname(__file__), "../../data/rules/category_event_rules.json")
_ORDER = ["regulation","financials","corporate_action","supply_chain","product","competition","general"]

def _rules():
    with open(RULES_PATH,"r",encoding="utf-8") as f: return json.load(f)

def detect_category(text:str)->str:
    R=_rules()["CATEGORY_REGEX"]; scores={k:0 for k in R}
    for cat, pats in R.items():
        for p in pats:
            hits = len(re.findall(p, text, flags=re.I))
            scores[cat]+=hits*(3 if cat in ("financials","regulation","corporate_action") else 2)
    best = max(scores.items(), key=lambda kv:(kv[1], -_ORDER.index(kv[0]) if kv[0] in _ORDER else 99))[0]
    return best if scores[best]>0 else "general"
