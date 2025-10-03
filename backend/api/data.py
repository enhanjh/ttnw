from fastapi import APIRouter, HTTPException
from typing import List
from beanie import PydanticObjectId
from ..data_collector import get_stock_data
from ..portfolio_calculator import get_portfolio_returns

router = APIRouter(
    prefix="/api",
    tags=["data"],
)

@router.get("/data/stock/{symbol}")
async def get_stock_historical_data(symbol: str, start_date: str, end_date: str = None):
    data = get_stock_data(symbol, start_date, end_date)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {symbol}")
    return data.to_dict(orient="records")

@router.get("/portfolio_returns/{portfolio_id}")
async def get_portfolio_returns_endpoint(
    portfolio_id: PydanticObjectId,
    start_date: str,
    end_date: str,
):
    results = await get_portfolio_returns(portfolio_id, start_date, end_date)
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results