import httpx
import feedparser
import asyncio
from typing import List, Optional, Dict

REQUEST_TIMEOUT = 8

async def fetch_single_feed(url: str, client: httpx.AsyncClient) -> Optional[Dict]:
    """Asynchronously fetches a single RSS feed."""
    try:
        headers = {
            'User-Agent': 'NewsMonitor/3.0 (https://github.com/your-repo)'
        }
        response = await client.get(url, headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
        
        # feedparser is sync, but we can run it in a thread pool if it becomes a bottleneck
        feed_data = feedparser.parse(response.content)
        if feed_data.bozo:
            print(f"[Warning] Malformed feed from {url}: {feed_data.bozo_exception}")

        return feed_data
    except httpx.HTTPStatusError as e:
        print(f"[Error] HTTP error for {url}: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"[Error] Failed to fetch RSS feed {url}: {e}")
        return None

async def fetch_all_feeds(urls: List[str]) -> List[Dict]:
    """Fetches all RSS feeds concurrently."""
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_feed(url, client) for url in urls]
        results = await asyncio.gather(*tasks)
        return [res for res in results if res is not None]
