from fastapi import APIRouter, HTTPException
from typing import List
from beanie import PydanticObjectId
from .. import models, schemas

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