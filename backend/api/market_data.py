import os
from fastapi import APIRouter, HTTPException, Query
from datetime import date
from ..data_collector import get_fred_yield_curve # Import the new function

router = APIRouter(
    prefix="/api/market_data",
    tags=["market_data"],
)

@router.get("/us_yield_curve")
async def fetch_us_yield_curve(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format")
):
    """
    Fetches the U.S. Treasury yield curve rates from FRED for a given date range.
    """
    fred_api_key = os.getenv("FRED_API_KEY")
    if not fred_api_key:
        raise HTTPException(
            status_code=500,
            detail="FRED_API_KEY environment variable not set on the server."
        )

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date.")
        
    try:
        yield_curve_df = get_fred_yield_curve(
            api_key=fred_api_key,
            start_date=start_date.strftime('%Y-%m-%d'), 
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if yield_curve_df.empty:
            return {}
            
        # orient='index' creates a dict like {"date": {"col1": val1, ...}}
        # The index is a DatetimeIndex, convert to string for JSON
        yield_curve_df.index = yield_curve_df.index.strftime('%Y-%m-%d')
        return yield_curve_df.to_dict(orient='index')
        
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in fetch_us_yield_curve endpoint: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while fetching yield curve data.")