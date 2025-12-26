
import asyncio
import os
import sys
import time
import logging
from datetime import datetime
import motor.motor_asyncio
from beanie import init_beanie
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models
from workers.tasks import run_live_strategy_task
from core.utils.market_schedule import is_market_open_time

# Configure logging to use local time
logging.Formatter.converter = time.localtime
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
    logger.info("Checking for active live portfolios...")
    try:
        # Find all active live portfolios that have a strategy linked
        portfolios = await models.Portfolio.find(
            models.Portfolio.environment == "live",
            models.Portfolio.status == "active",
            models.Portfolio.strategy != None # Must have a strategy
        ).to_list()

        if not portfolios:
            logger.info("No active live portfolios found.")
            return

        for portfolio in portfolios:
            logger.info(f"Triggering strategy for portfolio: {portfolio.name} (ID: {portfolio.id})")
            # Trigger the Celery task
            run_live_strategy_task.delay(str(portfolio.id))
            
    except Exception as e:
        logger.error(f"Error in check_and_run_strategies: {e}")

async def main():
    await init_db()
    logger.info("Scheduler started. Running strategy checks every 60 seconds.")
    
    while True:
        if is_market_open_time():
            await check_and_run_strategies()
        else:
            logger.info("Market is closed. Skipping strategy checks.")
            
        # Sleep for 60 seconds (or configurable interval)
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")
