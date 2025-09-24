import asyncio
import hashlib
from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from .fetcher import fetch_all_feeds
from .enricher import (
    strip_html,
    compute_scores,
    match_companies
)
from ...storage import crud
from ...storage.database import AsyncSessionFactory

async def run_news_pipeline():
    """The main pipeline function to be called by the scheduler."""
    print(f"[{datetime.now()}] Running news pipeline...")
    db: AsyncSession = AsyncSessionFactory()
    try:
        # 1. Prepare source list
        # For now, using a static list. Will be replaced by dynamic list from DB.
        fixed_feeds = ["http://feeds.arstechnica.com/arstechnica/index/", "https://techcrunch.com/feed/"]
        watchlist_companies = await crud.get_all_watchlist_companies(db)
        dynamic_feeds = [f"https://news.google.com/rss/search?q={c.name}&hl=en-US&gl=US&ceid=US:en" for c in watchlist_companies]
        all_feed_urls = list(set(fixed_feeds + dynamic_feeds))

        # 2. Fetch all feeds
        feed_results = await fetch_all_feeds(all_feed_urls)
        
        processed_count = 0
        for feed in feed_results:
            for entry in feed.entries:
                url = entry.get('link')
                if not url or len(url) > 1024: continue

                # 3. Check for duplicates
                if await crud.get_article_by_url(db, url):
                    continue

                # 4. Enrich data
                title = entry.get("title", "")
                body_raw = entry.get("summary", "") or entry.get("description", "")
                body = strip_html(body_raw)
                full_text = f"{title}. {body}"

                pub_time_parsed = entry.get("published_parsed")
                published_at = datetime(*pub_time_parsed[:6], tzinfo=timezone.utc) if pub_time_parsed else datetime.now(timezone.utc)

                scores = compute_scores(title, sentiment_score(full_text), published_at, full_text)
                companies = match_companies(title, body)

                # 5. Store in DB
                article_data = {
                    'url': url,
                    'url_hash': int(hashlib.md5(url.encode()).hexdigest(), 16) % (10**12),
                    'source_domain': url.split('/')[2],
                    'title': title,
                    'body': body,
                    'published_at': published_at,
                }
                await crud.create_article_and_meta(db, article_data, scores, companies)
                processed_count += 1
        
        await db.commit()
        print(f"Pipeline finished. Processed {processed_count} new articles.")

    except Exception as e:
        print(f"[ERROR] An error occurred in the pipeline: {e}")
        await db.rollback()
    finally:
        await db.close()