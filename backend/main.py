from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from beanie import PydanticObjectId
from mangum import Mangum
from dotenv import load_dotenv

load_dotenv()

from . import models, schemas, hantoo_auth
from .database import init_db, close_db
from .data_collector import get_stock_data, get_historical_data
from .portfolio_calculator import get_portfolio_returns
from .backtesting_engine import BacktestingEngine, buy_and_hold_strategy
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ttnw-api")

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.on_event("shutdown")
async def on_shutdown():
    close_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

class AuthRequest(BaseModel):
    appkey: str
    appsecret: str

@app.post("/api/auth/token")
async def get_auth_token(request: AuthRequest):
    try:
        result = hantoo_auth.auth(appkey=request.appkey, appsecret=request.appsecret)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolios/", response_model=schemas.Portfolio)
async def create_portfolio(portfolio: schemas.PortfolioCreate):
    db_portfolio = await models.Portfolio.find_one(models.Portfolio.name == portfolio.name)
    if db_portfolio:
        raise HTTPException(status_code=400, detail="Portfolio with this name already exists")
    db_portfolio = models.Portfolio(**portfolio.dict())
    await db_portfolio.insert()
    return schemas.Portfolio.model_validate(db_portfolio)

@app.get("/api/portfolios/", response_model=List[schemas.Portfolio])
async def read_portfolios(skip: int = 0, limit: int = 100):
    portfolios_from_db = await models.Portfolio.find_all().skip(skip).limit(limit).to_list()
    serialized_portfolios = [schemas.Portfolio.model_validate(p) for p in portfolios_from_db]
    return serialized_portfolios

@app.get("/api/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
async def read_portfolio(portfolio_id: PydanticObjectId):
    portfolio = await models.Portfolio.get(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return schemas.Portfolio.model_validate(portfolio)

@app.put("/api/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
async def update_portfolio(portfolio_id: PydanticObjectId, portfolio: schemas.PortfolioCreate):
    db_portfolio = await models.Portfolio.get(portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db_portfolio.name = portfolio.name
    await db_portfolio.save()
    return schemas.Portfolio.model_validate(db_portfolio)

@app.delete("/api/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: PydanticObjectId):
    db_portfolio = await models.Portfolio.get(portfolio_id)
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    await db_portfolio.delete()
    return {"message": "Portfolio deleted successfully"}

# --- Asset Endpoints ---

@app.post("/api/assets/", response_model=schemas.Asset)
async def create_asset(asset: schemas.AssetCreate):
    db_portfolio = await models.Portfolio.get(asset.portfolio_id)
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    db_asset = await models.Asset.find_one(
        models.Asset.symbol == asset.symbol,
        models.Asset.portfolio.id == asset.portfolio_id
    )
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists in this portfolio")

    if asset.symbol.lower() == "cash_krw":
        asset.name = "Korean Won Cash"
        asset.asset_type = "cash"
    elif asset.symbol.lower() == "cash_usd":
        asset.name = "US Dollar Cash"
        asset.asset_type = "cash"

    db_asset = models.Asset(**asset.dict())
    await db_asset.insert()
    return schemas.Asset.model_validate(db_asset)

@app.get("/api/assets/", response_model=List[schemas.Asset])
async def read_assets(portfolio_id: Optional[PydanticObjectId] = None, skip: int = 0, limit: int = 100):
    query = models.Asset.find_all()
    if portfolio_id:
        query = query.find(models.Asset.portfolio.id == portfolio_id)
    assets_from_db = await query.skip(skip).limit(limit).to_list()
    serialized_assets = []
    for a in assets_from_db:
        asset_dict = a.model_dump()
        asset_dict['portfolio_id'] = a.portfolio.id
        serialized_assets.append(schemas.Asset.model_validate(asset_dict))
    return serialized_assets

@app.get("/api/assets/{asset_id}", response_model=schemas.Asset)
async def read_asset(asset_id: PydanticObjectId):
    asset = await models.Asset.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return schemas.Asset.model_validate(asset)

@app.put("/api/assets/{asset_id}", response_model=schemas.Asset)
async def update_asset(asset_id: PydanticObjectId, asset: schemas.AssetCreate):
    db_asset = await models.Asset.get(asset_id)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    db_portfolio = await models.Portfolio.get(asset.portfolio_id)
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    existing_asset_with_symbol = await models.Asset.find_one(
        models.Asset.symbol == asset.symbol,
        models.Asset.portfolio.id == asset.portfolio_id,
        models.Asset.id != asset_id
    )
    if existing_asset_with_symbol:
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists in this portfolio")

    update_data = asset.dict()
    for key, value in update_data.items():
        setattr(db_asset, key, value)
    await db_asset.save()
    return schemas.Asset.model_validate(db_asset)

@app.delete("/api/assets/{asset_id}")
async def delete_asset(asset_id: PydanticObjectId):
    db_asset = await models.Asset.get(asset_id)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db_asset.delete()
    return {"message": "Asset deleted successfully"}

# --- Transaction Endpoints ---

@app.post("/api/transactions/", response_model=schemas.Transaction)
async def create_transaction(transaction: schemas.TransactionCreate):
    db_asset = await models.Asset.get(transaction.asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db_transaction = models.Transaction(**transaction.dict())
    await db_transaction.insert()

    # Automatic cash transaction logic can be added here if needed

    return schemas.Transaction.model_validate(db_transaction)

@app.get("/api/transactions/", response_model=List[schemas.Transaction])
async def read_transactions(portfolio_id: Optional[PydanticObjectId] = None, skip: int = 0, limit: int = 100):
    if portfolio_id:
        query = models.Transaction.find(models.Transaction.portfolio.id == portfolio_id)
    else:
        query = models.Transaction.find_all()
    transactions_from_db = await query.skip(skip).limit(limit).to_list()
    serialized_transactions = []
    for t in transactions_from_db:
        transaction_dict = t.model_dump()
        transaction_dict['asset_id'] = t.asset.id
        transaction_dict['portfolio_id'] = t.portfolio.id
        serialized_transactions.append(schemas.Transaction.model_validate(transaction_dict))
    return serialized_transactions

@app.get("/api/transactions/{transaction_id}", response_model=schemas.Transaction)
async def read_transaction(transaction_id: PydanticObjectId):
    transaction = await models.Transaction.get(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return schemas.Transaction.model_validate(transaction)

@app.put("/api/transactions/{transaction_id}", response_model=schemas.Transaction)
async def update_transaction(transaction_id: PydanticObjectId, transaction: schemas.TransactionCreate):
    db_transaction = await models.Transaction.get(transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    update_data = transaction.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    await db_transaction.save()
    return schemas.Transaction.model_validate(db_transaction)

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: PydanticObjectId):
    db_transaction = await models.Transaction.get(transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db_transaction.delete()
    return {"message": "Transaction deleted successfully"}

# --- Data Collection Endpoint (Example) ---

@app.get("/api/data/stock/{symbol}")
async def get_stock_historical_data(symbol: str, start_date: str, end_date: str = None):
    data = get_stock_data(symbol, start_date, end_date)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {symbol}")
    return data.to_dict(orient="records")

# --- Portfolio Returns Endpoint ---

@app.get("/api/portfolio_returns/{portfolio_id}")
async def get_portfolio_returns_endpoint(
    portfolio_id: PydanticObjectId,
    start_date: str,
    end_date: str,
):
    results = await get_portfolio_returns(portfolio_id, start_date, end_date)
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results

# --- Backtesting Endpoint ---

@app.post("/api/backtest/buy_and_hold")
async def run_buy_and_hold_backtest(
    symbols: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0
):
    engine = BacktestingEngine(initial_capital=initial_capital)
    results = engine.run_backtest(
        strategy=buy_and_hold_strategy,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results

handler = Mangum(app)
