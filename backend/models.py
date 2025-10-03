from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict

class Portfolio(Document):
    name: str = Field(..., max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "portfolios"

class Asset(Document):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    asset_type: str = Field(..., max_length=50)
    portfolio_id: PydanticObjectId
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
    parameters: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "strategies"

class BacktestResult(Document):
    name: str = Field(..., max_length=100)
    strategy_id: PydanticObjectId # Store ObjectId of the Strategy used
    start_date: datetime
    end_date: datetime
    initial_capital: float

    # Performance Metrics
    final_capital: float
    annualized_return: float
    volatility: float
    max_drawdown: float
    sharpe_ratio: float

    # Detailed Data
    portfolio_value: List[Dict] # List of {'Date': 'YYYY-MM-DD', 'Value': float}
    returns: Dict[str, float] # Dictionary of {'YYYY-MM-DD': float}
    cumulative_returns: Dict[str, float] # Dictionary of {'YYYY-MM-DD': float}
    transactions: List[Dict] # List of transaction dictionaries

    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "extra": "allow"
    }

    class Settings:
        name = "backtest_results"