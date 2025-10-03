import motor.motor_asyncio
from beanie import init_beanie
from typing import Optional
import os

from . import models

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
        ],
    )

def get_db():
    """
    Returns the database instance.
    """
    return db

def close_db():
    """
    Closes the database connection.
    """
    global client
    if client:
        client.close()