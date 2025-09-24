from .entity_matcher import match_companies
from .categorizer import detect_category
from .event_extractor import extract_event
from .summarizer import two_line_summary, keywords
from .scoring import sentiment_score, accuracy_pct, importance_pct, impact_level, positivity_pct
from .topics import tag_topics
import re
from storage.pg import get_conn

IMPACT_HINT_MAP = {
  0.30: ["ban","recall","data breach","antitrust probe","guidance cut","downgrade","plant halt","export ban"],
  0.20: ["merger","acquisition","IPO","major partnership","export control","sanction"],
  0.15: ["lawsuit","investigation","shipment delay","supply shortage","production issue"]
}

def _impact_hint(ev:str|None)->float:
    if not ev: return 0.0
    for w,keys in IMPACT_HINT_MAP.items():
        if ev in keys: return float(w)
    return 0.0

def extract_links(text:str)->list[str]:
    urls = re.findall(r'https?://[^\s)"]+', text)
    allow_domains = ("sec.gov","ec.europa.eu","justice.gov","reuters.com","bloomberg.com","ft.com","wsj.com","nvidia.com","investor.nvidia.com")
    out=[]
    for u in urls:
        for d in allow_domains:
            if d in u:
                out.append(u)
                break
    return list(dict.fromkeys(out))[:5]

def _persist_links(article_id:int, links:list[str]):
    if not links: return
    with get_conn() as conn, conn.cursor() as cur:
        for u in links:
            cur.execute("""
            INSERT INTO article_links(article_id, link_type, url)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
            """,(article_id, "related", u))

def enrich_article(row:dict)->dict:
    # row: {id,title,body,lang,source_domain,published_at}
    txt = f"{row['title']}. {row['body']}"
    companies = match_companies(row['title'], row['body'])
    category = detect_category(txt)
    ev = extract_event(txt)
    sent = sentiment_score(txt)
    pos_pct = positivity_pct(sent)
    hint = _impact_hint(ev)
    top_conf = companies[0].confidence if companies else 0.0
    acc = accuracy_pct(row['source_domain'])
    imp = importance_pct(category, sent, row['published_at'], top_conf, hint)
    impact = impact_level(imp, hint)
    topics = tag_topics(txt)
    ko_short = two_line_summary(row['title'], row['body'], row.get('lang','en'))
    kw = keywords(row['body'])
    links = extract_links(txt)
    return {
        "companies":[c.__dict__ for c in companies],
        "category": category,
        "topic_tags": topics,
        "related_event": ev,
        "sentiment": sent,
        "positivity_pct": pos_pct,
        "accuracy_pct": acc,
        "importance_pct": imp,
        "impact_level": impact,
        "severity": "HIGH" if (imp>=80 or hint>=0.25) else ("MEDIUM" if imp>=60 else "LOW"),
        "ko_short": ko_short,
        "keyword_summary": kw,
        "related_links": links
    }