from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...storage.database import get_db_session
from ...modules.pipeline.orchestrator import process_and_store_feeds
from ...storage import crud

router = APIRouter()

# Dummy RSS list for now
RSS_FEEDS = [
    "http://feeds.arstechnica.com/arstechnica/index/",
    "https://techcrunch.com/feed/",
    "http://www.theverge.com/rss/index.xml",
]

@router.post("/trigger_pipeline")
async def trigger_pipeline(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):
    """Triggers the news processing pipeline in the background."""
    background_tasks.add_task(process_and_store_feeds, db, RSS_FEEDS)
    return {"message": "News processing pipeline triggered in the background."}

@router.get("/")
async def get_feed_from_db(db: AsyncSession = Depends(get_db_session), skip: int = 0, limit: int = 20):
    """Retrieves the processed news feed from the database."""
    # This is a placeholder. A real implementation would join tables and sort.
    articles = await db.execute(crud.Article.__table__.select().offset(skip).limit(limit))
    return articles.mappings().all()
