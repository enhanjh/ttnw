from fastapi import APIRouter, HTTPException, status
from typing import List
from beanie import PydanticObjectId
from .. import models, schemas

router = APIRouter(
    prefix="/api/strategies",
    tags=["strategies"],
)

@router.post("/", response_model=schemas.Strategy)
async def create_strategy(strategy: schemas.StrategyCreate):
    db_strategy = await models.Strategy.find_one(models.Strategy.name == strategy.name)
    if db_strategy:
        raise HTTPException(status_code=400, detail="Strategy with this name already exists")
    db_strategy = models.Strategy(**strategy.dict())
    await db_strategy.insert()
    return schemas.Strategy.model_validate(db_strategy)

@router.get("/", response_model=List[schemas.Strategy])
async def read_strategies(skip: int = 0, limit: int = 100):
    strategies_from_db = await models.Strategy.find_all().skip(skip).limit(limit).to_list()
    # Manually serialize to dictionaries and convert ObjectId to string
    serialized_strategies = []
    for s in strategies_from_db:
        strategy_data = s.model_dump()
        strategy_data['id'] = str(s.id) # Ensure id is a string
        # The created_at is already a datetime object, Pydantic will handle it.
        # The parameters are already a dict.
        serialized_strategies.append(strategy_data)
    return serialized_strategies

@router.get("/{strategy_id}", response_model=schemas.Strategy)
async def read_strategy(strategy_id: PydanticObjectId):
    strategy = await models.Strategy.get(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return schemas.Strategy.model_validate(strategy)

@router.put("/{strategy_id}", response_model=schemas.Strategy)
async def update_strategy(strategy_id: PydanticObjectId, strategy: schemas.StrategyCreate):
    db_strategy = await models.Strategy.get(strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check for name conflict
    if strategy.name != db_strategy.name:
        existing_strategy_with_name = await models.Strategy.find_one(models.Strategy.name == strategy.name)
        if existing_strategy_with_name:
            raise HTTPException(status_code=400, detail="Strategy with this name already exists")

    update_data = strategy.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_strategy, key, value)
    await db_strategy.save()
    return schemas.Strategy.model_validate(db_strategy)

@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: PydanticObjectId):
    db_strategy = await models.Strategy.get(strategy_id)
    if db_strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db_strategy.delete()
    return {"message": "Strategy deleted successfully"}