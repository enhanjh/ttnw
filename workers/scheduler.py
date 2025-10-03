
import asyncio
import os
import sys
import time
from datetime import datetime
import motor.motor_asyncio
from beanie import init_beanie
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models
from workers.tasks import run_live_strategy_task
from core.utils.market_schedule import is_market_open_time

# Load .env
dotenv_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")

async def init_db():
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

async def check_and_run_strategies():
    print(f"[{datetime.now()}] Checking for active live portfolios...")
    try:
        # Find all active live portfolios that have a strategy linked
        portfolios = await models.Portfolio.find(
            models.Portfolio.environment == "live",
            models.Portfolio.status == "active",
            models.Portfolio.strategy != None # Must have a strategy
        ).to_list()

        if not portfolios:
            print("No active live portfolios found.")
            return

        for portfolio in portfolios:
            print(f"Triggering strategy for portfolio: {portfolio.name} (ID: {portfolio.id})")
            # Trigger the Celery task
            run_live_strategy_task.delay(str(portfolio.id))
            
    except Exception as e:
        print(f"Error in check_and_run_strategies: {e}")

async def main():
    await init_db()
    print("Scheduler started. Running strategy checks every 60 seconds.")
    
    while True:
        if is_market_open_time():
            await check_and_run_strategies()
        else:
            print(f"[{datetime.now()}] Market is closed. Skipping strategy checks.")
            
        # Sleep for 60 seconds (or configurable interval)
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Scheduler stopped.")
