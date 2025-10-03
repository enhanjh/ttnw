from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Union
from beanie import PydanticObjectId
from bson import ObjectId # Import ObjectId for json_encoders

class AuthRequest(BaseModel):
    appkey: str
    appsecret: str

class AssetBase(BaseModel):
    symbol: str
    name: str
    asset_type: str
    portfolio_id: PydanticObjectId # Changed back to PydanticObjectId

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

class PortfolioBase(BaseModel):
    name: str

class PortfolioCreate(PortfolioBase):
    pass

class Portfolio(PortfolioBase):
    id: PydanticObjectId = Field() # Changed back to PydanticObjectId
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str} # Add custom encoder
    )