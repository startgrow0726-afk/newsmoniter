import datetime
import math
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from .prices import load_1m, vwap, returns, corr # Keep existing price utilities
from api.storage.pg import get_conn # Added import

# Placeholder for database models - to be replaced with actual imports or defined elsewhere
class CompanyContextScores:
    # Example attributes, replace with actual model fields
    customer_score: int = 0
    supply_score: int = 0
    policy_risk_pct: int = 0
    competition_pct: int = 0
    company_context_score: int = 0 # Added for consistency

class TechLevels:
    # Example attributes, replace with actual model fields
    support: float = 0.0
    resistance: float = 0.0

class Event:
    # Example attributes, replace with actual model fields
    name: str = ""
    type: str = ""
    date: datetime.date = datetime.date.today()

def _load_json_rule(filename: str) -> Dict[str, Any]:
    """Loads a JSON rule file from the config/rules directory."""
    # Adjust path to correctly point to config/rules from api/modules/markets
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "config", "rules")
    file_path = os.path.join(base_path, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Rule file {filename} not found at {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Warning: Error decoding JSON from {filename}")
        return {}

# Load rules once at module load time
RULES_IMPACT_HINT = _load_json_rule("scoring_weights.json").get("IMPACT_HINT", {})
RULES_CATEGORY_WEIGHT = _load_json_rule("scoring_weights.json").get("CATEGORY_WEIGHT", {})
RULES_COMPANY_CORE = _load_json_rule("company_entities.json").get("COMPANY_CORE", {})
RULES_PRODUCTS = _load_json_rule("company_entities.json").get("PRODUCTS", [])
RULES_ECOSYSTEM = _load_json_rule("company_entities.json").get("ECOSYSTEM", [])
RULES_CUSTOMERS_PARTNERS = _load_json_rule("company_entities.json").get("CUSTOMERS_PARTNERS", [])
RULES_COMPETITORS = _load_json_rule("company_entities.json").get("COMPETITORS", [])
RULES_SOURCE_TRUST = _load_json_rule("source_trust.json").get("SOURCE_TRUST", {})

def explain_intraday_move(ticker: str, date: datetime.date, sector_ticker: Optional[str] = None, index_ticker: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes the intraday stock price movement for a given ticker and date.
    It determines the causes of the move, labels investor sentiment, and provides an outlook.

    Args:
        ticker: The stock ticker symbol.
        date: The date for the analysis.
        sector_ticker: Optional ticker for the sector index.
        index_ticker: Optional ticker for the main market index.

    Returns:
        A dictionary containing the detailed analysis.
    """
    # 1. Load necessary data
    ohlcv_1m = _load_ohlcv_1m(ticker, date)
    sector_1m = _load_sector_data_1m(sector_ticker, date) if sector_ticker else []
    index_1m = _load_index_data_1m(index_ticker, date) if index_ticker else []
    news_clusters = _load_news_clusters(ticker, date)
    calendar = _load_event_calendar(date)
    
    if not ohlcv_1m or len(ohlcv_1m) < 2: # Need at least open and close
        return {
          "ticker": ticker, "date": str(date), "move_pct": 0.0,
          "sector_corr": 0.0, "index_corr": 0.0,
          "contributions": {"company": 25, "sector": 25, "macro": 25, "flow": 25}, # Default split
          "sentiment_label": "관망",
          "one_day_view": "시세 데이터 부족으로 분석 제한",
          "short_term_view": "시세 데이터 부족으로 분석 제한",
          "mid_long_view": "시세 데이터 부족으로 분석 제한",
          "evidence": {"provider": "none"}
        }

    # 2. Calculate core metrics
    first_open = ohlcv_1m[0].get('open', ohlcv_1m[0]['close']) # Fallback to close if open not present
    last_close = ohlcv_1m[-1]['close']
    move_pct = (last_close / first_open - 1) * 100
    vwap_val = _calculate_vwap(ohlcv_1m)
    
    r_stk = returns(ohlcv_1m)
    sector_corr = corr(r_stk, returns(sector_1m)) if sector_1m else 0.0
    index_corr = corr(r_stk, returns(index_1m)) if index_1m else 0.0

    # 3. Detect causal factors
    company_heat = _calculate_company_heat(news_clusters)
    sector_heat = _calculate_sector_heat(sector_ticker, date) # Pass sector_ticker
    macro_heat = _calculate_macro_heat(calendar, date)
    
    profit_taking_flag = _detect_profit_taking(ohlcv_1m)
    friday_effect_flag = _is_friday_afternoon(datetime.datetime.fromtimestamp(ohlcv_1m[-1]['timestamp'], tz=datetime.timezone.utc)) # Assuming timestamp is UTC
    
    # 4. Compute contributions
    contributions = _compute_contributions(
        company_heat, sector_heat, macro_heat, sector_corr, index_corr, 
        profit_taking_flag, friday_effect_flag, vwap_val, ohlcv_1m
    )

    # 5. Label investor sentiment
    sentiment_label = _label_investor_sentiment(
        profit_taking_flag, friday_effect_flag, move_pct, 
        _get_volume_trend(ohlcv_1m), company_heat
    )

    # 6. Generate outlook
    context_scores = _get_company_context_scores(ticker)
    tech_levels = _get_technical_levels(ohlcv_1m)
    next_day_events = _get_next_day_events(calendar, date)
    one_day_view, short_term_view, mid_long_view = _make_outlook(
        context_scores, tech_levels, next_day_events
    )

    # 7. Assemble the final report
    return {
        "ticker": ticker,
        "date": str(date),
        "move_pct": round(move_pct, 2),
        "vwap": round(vwap_val, 2),
        "sector_corr": round(sector_corr, 2),
        "index_corr": round(index_corr, 2),
        "contributions": contributions,
        "sentiment_label": sentiment_label,
        "one_day_view": one_day_view,
        "short_term_view": short_term_view,
        "mid_long_view": mid_long_view,
        "evidence": {
            "news_clusters": [c.get('title', '') for c in news_clusters[:3]],
            "technicals": {"vwap": round(vwap_val, 2), "range": f'{min(o.get("low", 0) for o in ohlcv_1m)}-{max(o.get("high", 0) for o in ohlcv_1m)}'},
            "benchmarks": {"sector_corr": round(sector_corr, 2), "index_corr": round(index_corr, 2)}
        },
        "generated_at": datetime.datetime.utcnow().isoformat()
    }

# --- Helper Functions (Implemented) ---

def _load_ohlcv_1m(ticker: str, date: datetime.date) -> List[Dict[str, Any]]:
    """Loads 1-minute OHLCV data for a ticker and date from the database."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT timestamp, open, high, low, close, volume FROM ohlcv_1m WHERE ticker = %s AND date = %s ORDER BY timestamp",
            (ticker, date)
        )
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def _load_sector_data_1m(sector_ticker: str, date: datetime.date) -> List[Dict[str, Any]]:
    """Loads 1-minute data for the ticker's sector index from the database."""
    if not sector_ticker: return []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT timestamp, open, high, low, close, volume FROM ohlcv_1m WHERE ticker = %s AND date = %s ORDER BY timestamp",
            (sector_ticker, date)
        )
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def _load_index_data_1m(index_ticker: str, date: datetime.date) -> List[Dict[str, Any]]:
    """Loads 1-minute data for the main market index from the database."""
    if not index_ticker: return []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT timestamp, open, high, low, close, volume FROM ohlcv_1m WHERE ticker = %s AND date = %s ORDER BY timestamp",
            (index_ticker, date)
        )
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def _load_news_clusters(ticker: str, date: datetime.date) -> List[Dict[str, Any]]:
    """Loads news clusters related to the ticker for the given date from the database."""
    with get_conn() as conn, conn.cursor() as cur:
        # First, get company_id from ticker
        cur.execute("SELECT id FROM companies WHERE %s = ANY(tickers) LIMIT 1", (ticker,))
        company_id = cur.fetchone()
        if not company_id: return []
        company_id = company_id[0]

        cur.execute(
            """SELECT c.title, c.severity, am.importance_pct, c.id as cluster_id
            FROM clusters c
            JOIN cluster_articles ca ON c.id = ca.cluster_id
            JOIN article_entities ae ON ca.article_id = ae.article_id
            JOIN article_meta am ON ca.article_id = am.article_id
            WHERE ae.company_id = %s
            AND c.first_seen::date = %s
            ORDER BY am.importance_pct DESC""",
            (company_id, date)
        )
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def _load_event_calendar(date: datetime.date) -> List[Event]:
    """Loads economic/market events from the calendar (database)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT name, type, date FROM events_calendar WHERE date = %s ORDER BY date",
            (date,)
        )
        cols = [desc[0] for desc in cur.description]
        return [Event(name=row[0], type=row[1], date=row[2]) for row in cur.fetchall()]

# --- Helper Functions (to be implemented) ---

def _calculate_vwap(ohlcv: List[Dict[str, Any]]) -> float:
    """Calculates the Volume-Weighted Average Price."""
    # Use existing vwap from .prices
    return vwap(ohlcv)

def _calculate_correlation(series1: list, series2: list) -> float:
    """Calculates the correlation between two time series."""
    # Use existing corr from .prices
    if not series1 or not series2 or len(series1) != len(series2):
        return 0.0
    return corr(series1, series2)

def _calculate_company_heat(news_clusters: List[Dict[str, Any]]) -> float:
    """Calculates the 'heat' from company-specific news."""
    if not news_clusters:
        return 0.0
    # Example: sum of importance_pct for HIGH/MEDIUM severity news
    return sum(c.get('importance_pct', 0) for c in news_clusters if c.get('severity') in ['HIGH', 'MEDIUM']) / 100.0

def _calculate_sector_heat(sector_ticker: Optional[str], date: datetime.date) -> float:
    """Implement logic to find heat from sector-wide news or events."""
    # TODO: Implement logic to find heat from sector-wide news or events
    return 0.0

def _calculate_macro_heat(calendar: List[Event], date: datetime.date) -> float:
    """Implement logic to find heat from major macro events (e.g., FOMC, CPI)."""
    # TODO: Implement logic to find heat from major macro events (e.g., FOMC, CPI)
    return 0.0

def _detect_profit_taking(ohlcv: List[Dict[str, Any]], prev_runup_window: int = 5) -> bool:
    """Detects signs of profit-taking."""
    # TODO: Implement profit-taking detection logic
    return False

def _is_friday_afternoon(timestamp: datetime.datetime) -> bool:
    """Checks if the timestamp is a Friday afternoon in the local market time."""
    if timestamp.weekday() == 4: # Friday
        return timestamp.hour >= 14 # Example: after 2 PM local time
    return False

def _compute_contributions(
    company_heat: float, sector_heat: float, macro_heat: float, 
    sector_corr: float, index_corr: float,
    profit_taking_flag: bool, friday_effect_flag: bool, 
    vwap_val: float, ohlcv: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Computes the percentage contribution of each factor to the price move."""
    w_company = company_heat * 0.4 # Example weighting
    w_sector = (sector_corr * 0.5 + sector_heat * 0.5) * 0.3
    w_macro = (index_corr * 0.5 + macro_heat * 0.5) * 0.2
    
    w_flow = 0.0
    if profit_taking_flag:
        w_flow += 0.3
    if friday_effect_flag:
        w_flow += 0.2
    
    total_weight = w_company + w_sector + w_macro + w_flow
    if total_weight == 0: 
        return {"company": 25, "sector": 25, "macro": 25, "flow": 25}

    contrib = {
        "company": round(100 * w_company / total_weight),
        "sector": round(100 * w_sector / total_weight),
        "macro": round(100 * w_macro / total_weight),
        "flow": round(100 * w_flow / total_weight)
    }
    current_sum = sum(contrib.values())
    if current_sum != 100:
        contrib["flow"] += (100 - current_sum) 

    return contrib

def _label_investor_sentiment(
    profit_taking_flag: bool, friday_effect_flag: bool, move_pct: float, 
    volume_trend: str, company_heat: float
) -> str:
    """Labels the dominant investor sentiment."""
    if profit_taking_flag:
        return '수익실현'
    elif friday_effect_flag and move_pct < 0: 
        return '금요일 위험회피'
    elif move_pct > 0 and volume_trend == 'increasing' and company_heat > 0.5:
        return '확신'
    elif move_pct < 0 and volume_trend == 'increasing' and company_heat < 0.2:
        return '공포'
    return "관망"

def _get_company_context_scores(ticker: str) -> Optional[CompanyContextScores]:
    """Load scores from the company_context table."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT customer_score, supply_score, policy_risk_pct, competition_pct, company_context_score FROM company_context WHERE company_id = (SELECT id FROM companies WHERE %s = ANY(tickers) LIMIT 1)",
            (ticker,)
        )
        row = cur.fetchone()
        if row:
            scores = CompanyContextScores()
            scores.customer_score = row[0]
            scores.supply_score = row[1]
            scores.policy_risk_pct = row[2]
            scores.competition_pct = row[3]
            scores.company_context_score = row[4]
            return scores
    return CompanyContextScores() # Return default if not found

def _get_technical_levels(ohlcv: List[Dict[str, Any]]) -> TechLevels:
    """Calculates key support/resistance levels."""
    # TODO: Implement logic to calculate support/resistance levels
    return TechLevels()

def _get_next_day_events(calendar: List[Event], date: datetime.date) -> List[Event]:
    """Filters calendar for next day's events."""
    # TODO: Implement logic to filter events for the next day
    return []

def _make_outlook(
    context_scores: CompanyContextScores, 
    tech_levels: TechLevels, 
    next_day_events: List[Event]
) -> Tuple[str, str, str]:
    """Generates 1-day, short-term, and mid-long-term outlooks."""
    one_day = "Stable movement expected."
    short_term = "Monitor for upcoming catalysts."
    mid_long_term = "Fundamentals remain a key driver."

    if context_scores.policy_risk_pct > 70:
        mid_long_term = "정책 리스크가 커져 변동성 장기화 가능성. 주요 마일스톤 확인 전까지 보수적 접근."
    
    return one_day, short_term, mid_long_term

def _get_volume_trend(ohlcv: List[Dict[str, Any]]) -> str:
    """Analyze volume trend (e.g., increasing, decreasing, average)."""
    # TODO: Implement volume trend analysis
    return "average"