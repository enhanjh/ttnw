from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from beanie import PydanticObjectId
from .. import models, schemas, portfolio_calculator, data_collector
import pandas as pd
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/portfolios",
    tags=["portfolios"],
)

@router.post("/", response_model=schemas.Portfolio)
async def create_portfolio(portfolio: schemas.PortfolioCreate):
    db_portfolio_with_name = await models.Portfolio.find_one(models.Portfolio.name == portfolio.name)
    if db_portfolio_with_name:
        raise HTTPException(status_code=400, detail="Portfolio with this name already exists")

    portfolio_data = portfolio.dict()
    strategy_id = portfolio_data.pop("strategy_id", None)
    
    # Ensure allowed_telegram_ids is a list
    if portfolio_data.get("allowed_telegram_ids") is None:
        portfolio_data["allowed_telegram_ids"] = []

    db_portfolio = models.Portfolio(**portfolio_data)

    if strategy_id:
        strategy = await models.Strategy.get(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy with id {strategy_id} not found")
        db_portfolio.strategy = strategy

    await db_portfolio.insert()

    # Fetch the link to return the full object
    await db_portfolio.fetch_link(models.Portfolio.strategy)
    
    return schemas.Portfolio.model_validate(db_portfolio)

@router.get("/", response_model=List[schemas.Portfolio])
async def read_portfolios(skip: int = 0, limit: int = 100):
    portfolios_from_db = await models.Portfolio.find_all(fetch_links=True).skip(skip).limit(limit).to_list()
    return [schemas.Portfolio.model_validate(p) for p in portfolios_from_db]

@router.get("/{portfolio_id}", response_model=schemas.Portfolio)
async def read_portfolio(portfolio_id: PydanticObjectId):
    portfolio = await models.Portfolio.get(portfolio_id, fetch_links=True)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return schemas.Portfolio.model_validate(portfolio)

@router.get("/{portfolio_id}/holdings")
async def read_portfolio_holdings(portfolio_id: PydanticObjectId):
    """
    Calculates and returns the current holdings for a portfolio, including
    quantity, average buy price, current market price (approx), value, and return %.
    """
    portfolio = await models.Portfolio.get(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    transactions = await models.Transaction.find(models.Transaction.portfolio_id == portfolio_id).to_list()
    
    # Calculate holdings (Qty, Avg Price)
    holdings_data = portfolio_calculator.calculate_current_holdings(transactions)
    
    if not holdings_data:
        return []

    asset_ids = list(holdings_data.keys())
    assets = await models.Asset.find({"_id": {"$in": asset_ids}}).to_list()
    asset_map = {a.id: a for a in assets}

    result = []
    
    # Pre-fetch current prices to optimize
    # We'll fetch data for the last 5 days to ensure we get a recent close price
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    for asset_id, data in holdings_data.items():
        asset = asset_map.get(asset_id)
        if not asset:
            continue
            
        symbol = asset.symbol
        quantity = data['quantity']
        avg_price = data['average_price']
        
        # Fetch current price (Simplified: getting latest close from yfinance)
        # In a real system, this might come from a Redis cache or real-time provider
        current_price = 0.0
        try:
            # Check asset type to decide how to fetch price if needed
            # For now, using get_stock_data which wraps yfinance
            df = data_collector.get_stock_data(symbol, start_date, end_date)
            if not df.empty:
                current_price = float(df['Close'].iloc[-1])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
        
        # Fallback if price fetch failed or returned 0, use avg_price to avoid division errors (or keep 0)
        # current_price = current_price if current_price > 0 else avg_price 

        current_value = quantity * current_price
        invested_amount = quantity * avg_price
        
        return_pct = 0.0
        if invested_amount > 0:
            return_pct = ((current_value - invested_amount) / invested_amount) * 100
            
        result.append({
            "asset_id": str(asset_id),
            "symbol": symbol,
            "name": asset.name,
            "quantity": quantity,
            "average_price": avg_price,
            "current_price": current_price,
            "current_value": current_value,
            "return_percentage": return_pct
        })
        
    return result

@router.put("/{portfolio_id}", response_model=schemas.Portfolio)
async def update_portfolio(portfolio_id: PydanticObjectId, portfolio_update: schemas.PortfolioCreate):
    db_portfolio = await models.Portfolio.get(portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    update_data = portfolio_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        if key == "strategy_id":
            if value:
                strategy = await models.Strategy.get(value)
                if not strategy:
                    raise HTTPException(status_code=404, detail=f"Strategy with id {value} not found")
                db_portfolio.strategy = strategy
            else:
                db_portfolio.strategy = None
        else:
            setattr(db_portfolio, key, value)

    await db_portfolio.save()

    # Fetch the link to return the full object
    await db_portfolio.fetch_link(models.Portfolio.strategy)

    return schemas.Portfolio.model_validate(db_portfolio)

@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: PydanticObjectId):
    db_portfolio = await models.Portfolio.get(portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Also need to consider if there are linked transactions, etc.
    # For now, we just delete the portfolio itself.
    # Add more logic here if cascading deletes are needed.
    
    await db_portfolio.delete()
    return {"message": "Portfolio deleted successfully"}