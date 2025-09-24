from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ...modules.analysis.intraday import generate_postmarket_report
from ...modules.analysis.premarket import generate_premarket_briefing
from ...storage.database import get_db_session

router = APIRouter()

# This cache is for demonstration. In production, data should be read from DB.
LATEST_POSTMARKET_CACHE = {}
LATEST_PREMARKET_CACHE = {}

@router.get("/postmarket/{ticker}")
async def get_postmarket_report(ticker: str, db: AsyncSession = Depends(get_db_session)):
    """Retrieves the latest post-market analysis report for a given ticker."""
    try:
        # In production, the scheduler would have already saved the report.
        # We would just fetch it here using a CRUD function.
        report = await crud.get_latest_postmarket_report(db, ticker.upper())
        if not report:
            raise HTTPException(status_code=404, detail="Post-market report not found for this ticker.")
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/premarket/{ticker}")
async def get_premarket_briefing(ticker: str, db: AsyncSession = Depends(get_db_session)):
    """Retrieves the latest pre-market briefing for a given ticker."""
    try:
        # This function generates the report on-the-fly, which is suitable for pre-market.
        briefing = await generate_premarket_briefing(db, ticker.upper())
        return briefing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))