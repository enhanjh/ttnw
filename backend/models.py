from beanie import Document, Link
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class Portfolio(Document):
    name: str = Field(..., max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "portfolios"

class Asset(Document):
    symbol: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    asset_type: str = Field(..., max_length=50)
    portfolio: Link[Portfolio]

    class Settings:
        name = "assets"

class Transaction(Document):
    asset: Link[Asset]
    portfolio: Link[Portfolio]
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