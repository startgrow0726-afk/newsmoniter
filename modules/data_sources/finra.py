import httpx
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

async def fetch_finra_short_volume(date: datetime) -> Optional[pd.DataFrame]:
    """Fetches and parses daily short sale volume data from FINRA for a given date."""
    # FINRA publishes data for T-1. We fetch for the provided date.
    date_str = date.strftime("%Y%m%d")
    # Example URL: https://cdn.finra.org/equity/regsho/daily/CNMSshvol20231228.txt
    # We need to find the correct market suffix (CNMS, FNYX, etc.)
    # For this example, we'll just try one.
    url = f"https://cdn.finra.org/equity/regsho/daily/FNYXshvol{date_str}.txt"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            response.raise_for_status()

        # The file is pipe-delimited text
        # Column names: Date|Symbol|ShortVolume|TotalVolume|Market
        data = response.text
        df = pd.read_csv(StringIO(data), sep='|')
        df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d')
        return df

    except httpx.HTTPStatusError as e:
        print(f"[FINRA] Data not available for {date_str} at {url}. Status: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"[FINRA] Failed to fetch or parse FINRA data: {e}")
        return None
