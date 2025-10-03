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
    db_portfolio = await models.Portfolio.find_one(models.Portfolio.name == portfolio.name)
    if db_portfolio:
        raise HTTPException(status_code=400, detail="Portfolio with this name already exists")
    db_portfolio = models.Portfolio(**portfolio.dict())
    await db_portfolio.insert()
    return schemas.Portfolio.model_validate(db_portfolio)

@router.get("/", response_model=List[schemas.Portfolio])
async def read_portfolios(skip: int = 0, limit: int = 100):
    portfolios_from_db = await models.Portfolio.find_all().skip(skip).limit(limit).to_list()
    serialized_portfolios = [schemas.Portfolio.model_validate(p) for p in portfolios_from_db]
    return serialized_portfolios

@router.get("/{portfolio_id}", response_model=schemas.Portfolio)
async def read_portfolio(portfolio_id: PydanticObjectId):
    portfolio = await models.Portfolio.get(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return schemas.Portfolio.model_validate(portfolio)

@router.put("/{portfolio_id}", response_model=schemas.Portfolio)
async def update_portfolio(portfolio_id: PydanticObjectId, portfolio: schemas.PortfolioCreate):
    db_portfolio = await models.Portfolio.get(portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db_portfolio.name = portfolio.name
    await db_portfolio.save()
    return schemas.Portfolio.model_validate(db_portfolio)

@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: PydanticObjectId):
    db_portfolio = await models.Portfolio.get(portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    await db_portfolio.delete()
    return {"message": "Portfolio deleted successfully"}