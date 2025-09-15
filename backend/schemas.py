from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Union

class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: str
    portfolio_id: int

class AssetCreate(AssetBase):
    pass

class Asset(AssetBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class TransactionBase(BaseModel):
    asset_id: Union[int, str]
    portfolio_id: int
    transaction_type: str
    quantity: float
    price: float
    transaction_date: Optional[datetime] = None
    fee: Optional[float] = 0.0
    tax: Optional[float] = 0.0

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class PortfolioBase(BaseModel):
    name: str

class PortfolioCreate(PortfolioBase):
    pass

class Portfolio(PortfolioBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
