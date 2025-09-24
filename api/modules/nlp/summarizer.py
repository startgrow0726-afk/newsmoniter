import re
from modules.translate.libre import translate

def split_sentences(t:str)->list[str]:
    t = re.sub(r"\s+"," ",t).strip()
    s = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9가-힣])", t)
    return [x.strip() for x in s if len(x.strip())>0]

FIN_KWS = set("earnings revenue guidance probe investigation recall ban acquisition merger ipo benchmark lawsuit breach downgrade upgrade".split())

def two_line_summary(title:str, body:str, lang:str)->str:
    sents = split_sentences(f"{title}. {body}")[:12]
    if not sents: return title[:180]
    scored=[]
    for s in sents:
        L = len(s)
        len_score = 1/(1+abs(L-120)/60)
        kw = sum(1 for w in FIN_KWS if w.lower() in s.lower())
        score = len_score*0.6 + (kw>0)*0.4
        scored.append((score,s))
    top = [x[1] for x in sorted(scored, reverse=True)[:2]]
    out = " ".join(top)[:360]
    if lang=="en": out = translate(out, source="en", target="ko")
    return out

def keywords(body:str, k:int=5)->list[str]:
    words = re.findall(r"[A-Za-z가-힣0-9]{3,}", body.lower())
    stop = set("the and for with this that from have will into over under been being are was were their they them you your our its has had not but his her can may might would should because while about into onto within without upon among amongs between across".split())
    freq={}
    for w in words:
        if w in stop: continue
        freq[w]=freq.get(w,0)+1
    return [w for w,_ in sorted(freq.items(), key=lambda kv:kv[1], reverse=True)[:k]]
