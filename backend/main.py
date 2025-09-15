from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from . import models, schemas, hantoo_auth
from .database import SessionLocal, engine, get_db
from .data_collector import get_stock_data, get_historical_data
from .portfolio_calculator import get_portfolio_returns
from .backtesting_engine import BacktestingEngine, buy_and_hold_strategy # Import BacktestingEngine and example strategy
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine) # Ensure tables are created on startup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to Portfolio Manager API!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

class AuthRequest(BaseModel):
    appkey: str
    appsecret: str

@app.post("/auth/token")
async def get_auth_token(request: AuthRequest):
    try:
        result = hantoo_auth.auth(appkey=request.appkey, appsecret=request.appsecret)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolios/", response_model=schemas.Portfolio)
def create_portfolio(portfolio: schemas.PortfolioCreate, db: Session = Depends(get_db)):
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.name == portfolio.name).first()
    if db_portfolio:
        raise HTTPException(status_code=400, detail="Portfolio with this name already exists")
    db_portfolio = models.Portfolio(**portfolio.dict())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@app.get("/portfolios/", response_model=List[schemas.Portfolio])
def read_portfolios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    portfolios = db.query(models.Portfolio).offset(skip).limit(limit).all()
    return portfolios

@app.get("/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
def read_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@app.put("/portfolios/{portfolio_id}", response_model=schemas.Portfolio)
def update_portfolio(portfolio_id: int, portfolio: schemas.PortfolioCreate, db: Session = Depends(get_db)):
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db_portfolio.name = portfolio.name
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@app.delete("/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if db_portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(db_portfolio)
    db.commit()
    return {"message": "Portfolio deleted successfully"}

# --- Asset Endpoints ---

@app.post("/assets/", response_model=schemas.Asset)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == asset.portfolio_id).first()
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Check for existing asset with the same symbol in the same portfolio
    db_asset = db.query(models.Asset).filter(
        models.Asset.symbol == asset.symbol,
        models.Asset.portfolio_id == asset.portfolio_id
    ).first()
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists in this portfolio")

    # Handle cash assets specifically
    if asset.symbol.lower() == "cash_krw":
        asset.name = "Korean Won Cash"
        asset.asset_type = "cash"
    elif asset.symbol.lower() == "cash_usd":
        asset.name = "US Dollar Cash"
        asset.asset_type = "cash"

    db_asset = models.Asset(**asset.dict())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@app.get("/assets/", response_model=List[schemas.Asset])
def read_assets(portfolio_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Asset)
    if portfolio_id:
        query = query.filter(models.Asset.portfolio_id == portfolio_id)
    assets = query.offset(skip).limit(limit).all()
    return assets

@app.get("/assets/{asset_id}", response_model=schemas.Asset)
def read_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@app.put("/assets/{asset_id}", response_model=schemas.Asset)
def update_asset(asset_id: int, asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    db_asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == asset.portfolio_id).first()
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Check if the new symbol already exists in the same portfolio for another asset
    existing_asset_with_symbol = db.query(models.Asset).filter(
        models.Asset.symbol == asset.symbol,
        models.Asset.portfolio_id == asset.portfolio_id,
        models.Asset.id != asset_id
    ).first()
    if existing_asset_with_symbol:
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists in this portfolio")

    for key, value in asset.dict().items():
        setattr(db_asset, key, value)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    db_asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(db_asset)
    db.commit()
    return {"message": "Asset deleted successfully"}

# --- Transaction Endpoints ---

@app.post("/transactions/", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # Handle cash asset creation if it doesn't exist
    if isinstance(transaction.asset_id, str) and transaction.asset_id.startswith("cash_"):
        symbol = transaction.asset_id.lower()
        asset_name = "Korean Won Cash" if symbol == "cash_krw" else "US Dollar Cash"
        asset_type = "cash"

        db_asset = db.query(models.Asset).filter(
            models.Asset.symbol == symbol,
            models.Asset.portfolio_id == transaction.portfolio_id
        ).first()

        if not db_asset:
            # Create the cash asset if it doesn't exist
            new_asset = models.Asset(
                symbol=symbol,
                name=asset_name,
                asset_type=asset_type,
                portfolio_id=transaction.portfolio_id
            )
            db.add(new_asset)
            db.commit()
            db.refresh(new_asset)
            transaction.asset_id = new_asset.id
            db_asset = new_asset # Fix: Update db_asset to the newly created asset
        else:
            transaction.asset_id = db_asset.id
    else:
        db_asset = db.query(models.Asset).filter(models.Asset.id == transaction.asset_id).first()
        if not db_asset:
            raise HTTPException(status_code=404, detail="Asset not found")

    # Validate transaction type
    if db_asset.asset_type == "cash":
        allowed_types = ["deposit", "withdrawal", "dividend"]
        if transaction.transaction_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Cash transactions must be one of: { ', '.join(allowed_types) }"
            )
        transaction.price = 1.0
    else:  # Non-cash assets
        allowed_types = ["buy", "sell"]
        if transaction.transaction_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Non-cash transactions must be one of: { ', '.join(allowed_types) }"
            )

    # Create the primary transaction
    db_transaction = models.Transaction(**transaction.dict())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # --- Automatic Cash Transaction Logic (for non-cash assets) ---
    if db_asset.asset_type.startswith("stock_"):
        cash_symbol = ""
        if db_asset.asset_type.startswith("stock_kr"):
            cash_symbol = "cash_krw"
        elif db_asset.asset_type.startswith("stock_us"):
            cash_symbol = "cash_usd"

        if cash_symbol:
            # Find or create the corresponding cash asset
            cash_asset = db.query(models.Asset).filter(
                models.Asset.symbol == cash_symbol,
                models.Asset.portfolio_id == transaction.portfolio_id
            ).first()

            if not cash_asset:
                cash_asset_name = "Korean Won Cash" if cash_symbol == "cash_krw" else "US Dollar Cash"
                new_cash_asset = models.Asset(
                    symbol=cash_symbol, name=cash_asset_name, asset_type="cash",
                    portfolio_id=transaction.portfolio_id
                )
                db.add(new_cash_asset)
                db.commit()
                db.refresh(new_cash_asset)
                cash_asset = new_cash_asset

            # Determine cash flow based on transaction type
            cash_amount = 0
            cash_transaction_type = ""

            if transaction.transaction_type == "buy":
                cash_amount = (transaction.quantity * transaction.price) + (transaction.fee or 0)
                cash_transaction_type = "withdrawal"
            elif transaction.transaction_type == "sell":
                cash_amount = (transaction.quantity * transaction.price) - (transaction.fee or 0) - (transaction.tax or 0)
                cash_transaction_type = "deposit"

            # Create the corresponding cash transaction if applicable
            if cash_amount != 0 and cash_transaction_type:
                cash_transaction = models.Transaction(
                    asset_id=cash_asset.id,
                    portfolio_id=transaction.portfolio_id,
                    transaction_type=cash_transaction_type,
                    quantity=cash_amount,
                    price=1.0,
                    transaction_date=transaction.transaction_date,
                    fee=0,  # Fee/tax only applies to the primary transaction
                    tax=0
                )
                db.add(cash_transaction)
                db.commit()
                db.refresh(cash_transaction)

    return db_transaction

@app.get("/transactions/", response_model=List[schemas.Transaction])
def read_transactions(portfolio_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Transaction)
    if portfolio_id:
        query = query.filter(models.Transaction.portfolio_id == portfolio_id)
    transactions = query.offset(skip).limit(limit).all()
    return transactions

@app.get("/transactions/{transaction_id}", response_model=schemas.Transaction)
def read_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@app.put("/transactions/{transaction_id}", response_model=schemas.Transaction)
def update_transaction(transaction_id: int, transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db_asset = db.query(models.Asset).filter(models.Asset.id == transaction.asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db_portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == transaction.portfolio_id).first()
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    update_data = transaction.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(db_transaction)
    db.commit()
    return {"message": "Transaction deleted successfully"}

# --- Data Collection Endpoint (Example) ---

@app.get("/data/stock/{symbol}")
async def get_stock_historical_data(symbol: str, start_date: str, end_date: str = None):
    data = get_stock_data(symbol, start_date, end_date)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {symbol}")
    return data.to_dict(orient="records")

# --- Portfolio Returns Endpoint ---

@app.get("/portfolio_returns/{portfolio_id}")
async def get_portfolio_returns_endpoint(
    portfolio_id: int,
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    results = get_portfolio_returns(db, portfolio_id, start_date, end_date)
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results

# --- Backtesting Endpoint ---

@app.post("/backtest/buy_and_hold")
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
