from urllib.parse import quote_plus

STATIC_FEEDS = [
  # NVIDIA 공식/관련
  "https://investor.nvidia.com/rss/news-releases.xml",
  "https://blogs.nvidia.com/feed/",
  # 톱티어/테크
  "https://www.reuters.com/finance/tech/rss",
  "https://techcrunch.com/feed/",
  "https://www.theverge.com/rss/index.xml",
  # 규제/공정거래
  "https://ec.europa.eu/competition/atom/whatsnew_en.xml",
  "https://www.justice.gov/atr/justice-department-antitrust/rss.xml"
]

def gnews_query(company:str, tickers:list[str]|None=None, locale="US:en") -> str:
    q = [f'"{company}"']
    for t in (tickers or []): q.append(f'"{t}"')
    query = quote_plus(" OR ".join(q))
    return f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid={locale}"
