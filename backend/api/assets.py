from fastapi import APIRouter, HTTPException
from typing import List, Optional
from beanie import PydanticObjectId
from .. import models, schemas
import re

router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
)

@router.post("/", response_model=schemas.Asset)
async def create_asset(asset: schemas.AssetCreate):
    db_portfolio = await models.Portfolio.get(asset.portfolio_id)
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # For cash assets, check case-insensitively
    if asset.asset_type.lower() == 'cash':
        cash_symbol_pattern = re.compile(asset.symbol, re.IGNORECASE)
        db_asset = await models.Asset.find_one(
            models.Asset.asset_type == 'cash',
            models.Asset.symbol == cash_symbol_pattern,
            models.Asset.portfolio_id == asset.portfolio_id
        )
    else:
        db_asset = await models.Asset.find_one(
            models.Asset.symbol == asset.symbol,
            models.Asset.portfolio_id == asset.portfolio_id
        )
    
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists in this portfolio")

    if asset.symbol.lower() == "cash_krw":
        asset.name = "Korean Won Cash"
        asset.asset_type = "cash"
    elif asset.symbol.lower() == "cash_usd":
        asset.name = "US Dollar Cash"
        asset.asset_type = "cash"

    asset_data = asset.dict()
    db_asset = models.Asset(**asset_data)
    await db_asset.insert()
    return db_asset

@router.get("/", response_model=List[schemas.Asset])
async def read_assets(portfolio_id: Optional[PydanticObjectId] = None, skip: int = 0, limit: int = 100):
    if portfolio_id:
        assets_from_db = await models.Asset.find(
            models.Asset.portfolio_id == portfolio_id
        ).skip(skip).limit(limit).to_list()
    else:
        assets_from_db = await models.Asset.find_all().skip(skip).limit(limit).to_list()
    return assets_from_db

@router.get("/{asset_id}", response_model=schemas.Asset)
async def read_asset(asset_id: PydanticObjectId):
    asset = await models.Asset.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.put("/{asset_id}", response_model=schemas.Asset)
async def update_asset(asset_id: PydanticObjectId, asset: schemas.AssetCreate):
    db_asset = await models.Asset.get(asset_id)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    db_portfolio = await models.Portfolio.get(asset.portfolio_id)
    if not db_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    existing_asset_with_symbol = await models.Asset.find_one(
        models.Asset.symbol == asset.symbol,
        models.Asset.portfolio_id == asset.portfolio_id,
        models.Asset.id != asset_id
    )
    if existing_asset_with_symbol:
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists in this portfolio")

    update_data = asset.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_asset, key, value)
    await db_asset.save()
    return db_asset

@router.delete("/{asset_id}")
async def delete_asset(asset_id: PydanticObjectId):
    db_asset = await models.Asset.get(asset_id)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db_asset.delete()
    return {"message": "Asset deleted successfully"}