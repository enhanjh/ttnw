import motor.motor_asyncio
from beanie import init_beanie
from typing import Optional, List
from uuid import UUID

import motor.motor_asyncio
from beanie import init_beanie
import os
from dotenv import load_dotenv

# Load .env file from the same directory
dotenv_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from . import models
from .models import Strategy, Portfolio, Asset

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db = None

async def init_db():
    """
    Initializes the database connection and Beanie ODM.
    """
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URL)
    db = client.ttnw
    
    await init_beanie(
        database=db,
        document_models=[
            models.Portfolio,
            models.Asset,
            models.Transaction,
            models.US_Symbol,
            models.KOSPI_Symbol,
            models.KOSDAQ_Symbol,
            models.Strategy,
            models.BacktestResult,
            models.VirtualTransaction,
        ],
    )

async def get_portfolio_assets(portfolio_id: UUID) -> List[Asset]:
    """
    Retrieves all assets associated with a given portfolio ID.
    """
    portfolio = await Portfolio.get(portfolio_id)
    if not portfolio:
        return []
    
    assets = await Asset.find(Asset.portfolio_id == portfolio_id).to_list()
    return assets

def get_db():
    """
    Returns the database instance.
    """
    return db

def get_client():
    """
    Returns the database client instance.
    """
    return client

def close_db():
    """
    Closes the database connection.
    """
    global client
    if client:
        client.close()
