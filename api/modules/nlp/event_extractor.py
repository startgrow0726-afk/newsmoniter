import json, os, re
RULES_PATH = os.path.join(os.path.dirname(__file__), "../../data/rules/category_event_rules.json")
def extract_event(text:str)->str|None:
    with open(RULES_PATH,"r",encoding="utf-8") as f:
        ev = json.load(f)["EVENT_REGEX"]
    for label, pats in ev.items():
        for p in pats:
            if re.search(p, text, flags=re.I): return label
    return None
