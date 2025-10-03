from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict

from . import schemas

class Portfolio(Document):
    name: str = Field(..., max_length=50)
    manager: Optional[str] = Field(None, max_length=50)
    environment: str = Field("live", max_length=50) # 'live' or 'backtest'
    status: str = Field("active", max_length=50) # 'active' or 'inactive'
    broker_provider: Optional[str] = Field(None, max_length=50) # e.g., 'hantoo_vps', 'hantoo_prod'
    broker_account_no: Optional[str] = Field(None, max_length=50)
    allowed_telegram_ids: Optional[List[int]] = Field(default_factory=list)
    strategy: Optional[Link['Strategy']] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "portfolios"

class Asset(Document):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    asset_type: str = Field(..., max_length=50)
    minimum_tradable_quantity: Optional[float] = Field(1.0, description="Minimum tradable quantity for this asset")

    class Settings:
        name = "assets"

class Transaction(Document):
    asset_id: PydanticObjectId
    portfolio_id: PydanticObjectId
    transaction_type: str
    quantity: float
    price: float
    fee: float = 0.0
    tax: float = 0.0
    transaction_date: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "transactions"


class VirtualTransaction(Document):
    asset_id: PydanticObjectId
    portfolio_id: PydanticObjectId # This will be the virtual portfolio ID
    backtest_result_id: PydanticObjectId # Link to the BacktestResult
    transaction_type: str
    quantity: float
    price: float
    fee: float = 0.0
    tax: float = 0.0
    transaction_date: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "virtual_transactions" # Separate collection for virtual transactions

class US_Symbol(Document):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "us_symbols"

class KOSPI_Symbol(Document):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "kospi_symbols"

class KOSDAQ_Symbol(Document):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "kosdaq_symbols"


class Strategy(Document):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    strategy_type: str = Field(..., max_length=50)
    parameters: Optional[schemas.StrategyParameters] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "strategies"

class BacktestResult(Document):
    name: str = Field(..., max_length=100)
    virtual_portfolio_id: PydanticObjectId
    strategy: Link[Strategy] # Link directly to the Strategy document
    start_date: datetime
    end_date: datetime
    initial_capital: float

    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "extra": "allow"
    }

    class Settings:
        name = "backtest_results"