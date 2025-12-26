from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Union, Dict, List, Literal
from beanie import PydanticObjectId
from bson import ObjectId # Import ObjectId for json_encoders

class AuthRequest(BaseModel):
    appkey: str
    appsecret: str

class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: Literal["stock_us", "stock_kr_kospi", "stock_kr_kosdaq", "cash"] # Example allowed types
    minimum_tradable_quantity: Optional[float] = 1.0

class AssetCreate(AssetBase):
    pass

class Asset(AssetBase):
    id: PydanticObjectId = Field() # Changed back to PydanticObjectId

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str} # Add custom encoder
    )

class TransactionBase(BaseModel):
    asset_id: PydanticObjectId # Changed back to PydanticObjectId
    portfolio_id: PydanticObjectId # Changed back to PydanticObjectId
    transaction_type: str
    quantity: float
    price: float
    transaction_date: Optional[datetime] = None
    fee: Optional[float] = 0.0
    tax: Optional[float] = 0.0

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: PydanticObjectId = Field() # Changed back to PydanticObjectId

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str} # Add custom encoder
    )


class VirtualTransactionBase(BaseModel):
    asset_id: PydanticObjectId
    portfolio_id: PydanticObjectId
    backtest_result_id: PydanticObjectId # Link to the BacktestResult
    transaction_type: str
    quantity: float
    price: float
    transaction_date: Optional[datetime] = None
    fee: Optional[float] = 0.0
    tax: Optional[float] = 0.0

class VirtualTransactionCreate(VirtualTransactionBase):
    pass

class VirtualTransaction(VirtualTransactionBase):
    id: PydanticObjectId = Field()

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class PortfolioBase(BaseModel):
    name: str
    manager: Optional[str] = None
    environment: str = 'live'
    status: str = 'active'
    broker_provider: Optional[str] = None
    broker_account_no: Optional[str] = None
    allowed_telegram_ids: Optional[List[int]] = None
    strategy_id: Optional[PydanticObjectId] = None


class PortfolioCreate(PortfolioBase):
    pass


class Portfolio(PortfolioBase):
    id: PydanticObjectId
    created_at: datetime
    strategy: Optional['Strategy'] = None
    last_rebalanced_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class AssetWeightInStrategy(BaseModel):
    asset: str = Field(..., description="Asset symbol or ticker")
    asset_type: Optional[str] = Field(None, description="Type of the asset (e.g., stock_us, stock_kr_kospi)")
    weight: Optional[float] = Field(None, description="Weight of the asset in the strategy. Optional for some strategies like momentum.")


class FundamentalCondition(BaseModel):
    value_metric: str = Field(..., description="Metric to use for the asset's intrinsic value (e.g., 'Net Current Asset Value', 'Book Value Per Share', 'EPS')")
    comparison_metric: str = Field(..., description="Metric to compare against the value metric (e.g., 'Market Cap', 'Price Per Share', 'Revenue')")
    comparison_operator: str = Field(..., description="Operator for comparison (e.g., '>', '<', '>=', '<=', '=')")
    comparison_multiplier: Optional[float] = Field(None, description="Multiplier for the comparison metric")


class StrategyParameters(BaseModel):

    asset_weights: Optional[List[AssetWeightInStrategy]] = Field(None, description="List of assets and their target weights")

    rebalancing_frequency: Optional[str] = Field('monthly', description="Frequency of rebalancing (e.g., 'monthly', 'quarterly', 'annual', 'never')")
    rebalancing_threshold: Optional[float] = Field(None, description="Percentage deviation from target weight to trigger rebalancing (e.g., 0.05 for 5%)")

    # Momentum Strategy Parameters
    asset_pool: Optional[List[str]] = Field(None, description="List of asset symbols to consider for momentum strategy")
    lookback_period_months: Optional[int] = Field(None, description="Lookback period in months for momentum calculation")
    top_n_assets: Optional[int] = Field(None, description="Number of top assets to select based on momentum")
    risk_free_asset_ticker: Optional[str] = Field(None, description="Ticker for the risk-free asset (e.g., FRED series ID for 1-Year Treasury)")

    # Example for strategy-specific parameters (optional)
    moving_average_period_short: Optional[int] = None
    moving_average_period_long: Optional[int] = None

    # New fields for Fundamental Value (Indicator-Based) strategy
    fundamental_conditions: Optional[List[FundamentalCondition]] = Field(None, description="List of fundamental conditions to evaluate")
    re_evaluation_frequency: Optional[str] = Field(None, description="Frequency to re-evaluate fundamental criteria (e.g., 'annual', 'quarterly')")
    fundamental_data_region: Optional[str] = Field(None, description="Region for fundamental data (e.g., 'KR', 'US')")
    top_n: Optional[int] = Field(None, description="Number of top assets to select after filtering by fundamental conditions")
    ranking_metric: Optional[str] = Field(None, description="Metric to rank assets for Top N selection (e.g., 'market_cap')")
    ranking_order: Optional[Literal['asc', 'desc']] = Field('desc', description="Order to rank assets (ascending or descending)")

class StrategyCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    strategy_type: str = Field(..., max_length=50)
    parameters: StrategyParameters # Use the detailed parameters schema

class StrategyBacktestRequest(BaseModel):
    strategy_id: PydanticObjectId
    start_date: str
    end_date: str
    initial_capital: float = 100000000.0
    debug: bool = False

class BacktestDetailsRequest(BaseModel):
    virtual_portfolio_id: PydanticObjectId
    start_date: str
    end_date: str
    initial_capital: float
    strategy_id: PydanticObjectId # Add strategy_id
    strategy_name: str # Add strategy_name
    transactions_log: List[VirtualTransactionCreate]
    debug_logs: Optional[List[str]] = None

class Strategy(StrategyCreate):
    id: PydanticObjectId = Field(...)
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class BacktestResultBase(BaseModel):
    name: str
    virtual_portfolio_id: PydanticObjectId
    start_date: datetime
    end_date: datetime
    initial_capital: float

class BacktestResultCreate(BacktestResultBase):
    strategy_id: PydanticObjectId # Accept only the strategy ID

class BacktestSaveRequest(BacktestResultCreate): # Inherit metadata
    strategy_name: str # Add strategy_name for saving
    transactions_log: List[VirtualTransactionCreate]
    debug_logs: Optional[List[str]] = None # Include debug logs for saving

class BacktestResult(BacktestResultBase):
    id: PydanticObjectId = Field(...)
    strategy: Strategy # Changed from strategy_id
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class BacktestResultDetails(BacktestResult): # Inherit metadata from BacktestResult
    final_capital: float
    annualized_return: float
    volatility: float
    max_drawdown: float
    sharpe_ratio: float

    portfolio_value: List[Dict]
    returns: Dict[str, float]
    cumulative_returns: Dict[str, float]
    transactions: List[Dict]
    debug_logs: Optional[List[str]] = None