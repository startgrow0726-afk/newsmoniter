import re
import math
from typing import List, Dict, Any
from datetime import datetime, timezone

from ..config import (
    CATEGORY_WEIGHT, IMPACT_HINT, ENTITY_MAP, REGEX_PATTERNS
)

TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')

def strip_html(text: str) -> str:
    if not text:
        return ""
    clean_text = TAG_RE.sub("", text)
    return WHITESPACE_RE.sub(" ", clean_text).strip()

def summarize_en(text: str, max_sentences: int = 2) -> str:
    if not text:
        return ""
    text = WHITESPACE_RE.sub(" ", text.strip())
    if len(text) < 100:
        return text[:280]
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    sentences = [s.strip() for s in sentences if 20 <= len(s) <= 300]
    if not sentences:
        return text[:280]
    return " ".join(sentences[:max_sentences])

def detect_category(text: str) -> str:
    text_lower = text.lower()
    category_scores: Dict[str, int] = {cat: 0 for cat in CATEGORY_WEIGHT.keys()}

    for category, pattern in REGEX_PATTERNS.get('CATEGORY_REGEX', {}).items():
        if category in category_scores:
            category_scores[category] = len(re.findall(pattern, text_lower, re.I))

    if any(score > 0 for score in category_scores.values()):
        return max(category_scores, key=category_scores.get)
    return "general"

def classify_severity(text: str) -> str:
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in IMPACT_HINT.get("0.30", [])):
        return "HIGH"
    if any(keyword in text_lower for keyword in IMPACT_HINT.get("0.20", [])):
        return "MEDIUM"
    if any(keyword in text_lower for keyword in IMPACT_HINT.get("0.15", [])):
        return "MEDIUM"
    return "LOW"

def sentiment_score(text: str) -> float:
    text_lower = text.lower()
    pos_words = ['growth', 'profit', 'beat', 'strong', 'success', 'upgrade', 'surpass', 'outperform']
    neg_words = ['loss', 'decline', 'miss', 'weak', 'failure', 'downgrade', 'risk', 'concern', 'plunge']
    score = sum(text_lower.count(word) for word in pos_words)
    score -= sum(text_lower.count(word) for word in neg_words)
    return math.tanh(score / 5) # Normalize to -1 to 1, less sensitive

def compute_scores(category: str, sentiment: float, published_at: datetime, text: str) -> Dict[str, Any]:
    hours_ago = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600
    recency_weight = math.exp(-hours_ago / 48.0)

    impact_hint_score = 0
    for score_val, keywords in IMPACT_HINT.items():
        if any(keyword in text.lower() for keyword in keywords):
            impact_hint_score = max(impact_hint_score, float(score_val))

    base_score = 40
    category_bonus = CATEGORY_WEIGHT.get(category, 0.4) * 25
    sentiment_bonus = abs(sentiment) * 15
    recency_bonus = recency_weight * 10
    impact_bonus = impact_hint_score * 30

    importance_pct = max(0, min(100, int(base_score + category_bonus + sentiment_bonus + recency_bonus + impact_bonus)))
    positivity_pct = int((sentiment + 1) * 50)

    return {
        "importance_pct": importance_pct,
        "positivity_pct": positivity_pct,
        "sentiment": sentiment,
        "category": category,
        "severity": classify_severity(text)
    }

def match_companies(title: str, body: str) -> List[Dict]:
    results = []
    full_text = f"{title} {body}".lower()
    
    for name, data in ENTITY_MAP.items():
        score = 0
        matched_term = ""
        
        # Ticker matching
        for ticker in data.get('tickers', []):
            if re.search(rf'\b{ticker.lower()}\b', full_text):
                score += 6
                if not matched_term: matched_term = ticker

        # Alias matching
        for alias in data.get('aliases', []):
            if alias.lower() in full_text:
                score += 3
                if alias.lower() in title.lower(): score += 2
                if not matched_term: matched_term = alias
        
        if score > 0:
            # Context and negative keywords can refine the score here
            confidence = min(1.0, score / 10.0)
            if confidence > 0.5:
                results.append({"name": name, "confidence": confidence, "matched": matched_term})

    return sorted(results, key=lambda x: x["confidence"], reverse=True)