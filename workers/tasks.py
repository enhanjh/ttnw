import asyncio # Added this import
import requests # Added for exception handling
import logging # Added for logging
import time # Added for logging configuration
from .celery_app import app
from core import strategies
from core.data_providers.backtest import BacktestDataContext
from core.executors import BacktestExecutor, LiveExecutor, OrderManager # Added OrderManager
from core.api_clients.hantoo_client import HantooClient
from typing import Dict
from beanie import PydanticObjectId, init_beanie # Added init_beanie
from backend import models, schemas # Added this import
from core.utils.market_schedule import is_market_open_time
from backend.portfolio_calculator import calculate_portfolio_value, calculate_returns, calculate_cumulative_returns, calculate_volatility, calculate_max_drawdown # Added this import
from datetime import datetime # Added this import
import pandas as pd # Added this import
import motor.motor_asyncio # Added this import
import os # Added this import
from dotenv import load_dotenv # Added this import

# Configure logging to use local time
logging.Formatter.converter = time.localtime
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load .env file from the same directory
dotenv_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")

# A mapping from strategy names to their actual classes
STRATEGY_MAP = {
    'BuyAndHoldStrategy': strategies.BuyAndHoldStrategy,
    'AssetAllocationStrategy': strategies.AssetAllocationStrategy,
    'MomentumStrategy': strategies.MomentumStrategy,
    'FundamentalIndicatorStrategy': strategies.FundamentalIndicatorStrategy,
}

@app.task
def run_backtest_task(
    strategy_id: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
    debug: bool = False,
):
    async def _run_and_cleanup():
        backtest_result_id = None
        virtual_portfolio_id = None
        
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

        backtest_result = None
        try:
            # Fetch the strategy inside the task
            strategy_doc = await models.Strategy.get(PydanticObjectId(strategy_id))
            if not strategy_doc:
                raise ValueError(f"Strategy with ID {strategy_id} not found.")

            strategy_params = strategy_doc.parameters.model_dump() if strategy_doc.parameters else {}

            # 1. Create a Virtual Portfolio and a placeholder BacktestResult
            virtual_portfolio = models.Portfolio(
                name=f"VP: {strategy_doc.name[:25]} ({datetime.now().strftime('%m/%d %H:%M')})",
                environment="backtest"
            )
            await virtual_portfolio.insert()

            backtest_result = models.BacktestResult(
                name=f"Auto-saved backtest for {strategy_doc.name} on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                strategy=strategy_doc,
                virtual_portfolio_id=virtual_portfolio.id,
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                initial_capital=initial_capital,
                status="RUNNING",
                debug_logs=[],
            )
            await backtest_result.insert()

            # 2. Dynamically get the strategy class
            strategy_type = strategy_doc.strategy_type
            strategy_class_name = ''.join(word.capitalize() for word in strategy_type.split('_')) + 'Strategy'
            StrategyClass = STRATEGY_MAP.get(strategy_class_name)
            if not StrategyClass:
                raise ValueError(f"Unknown strategy type: {strategy_type}")

            if debug:
                logger.info(f"[DEBUG] run_backtest_task received strategy_params: {strategy_params}")

            # 3. Initialize and run the executor
            strategy_instance = StrategyClass(strategy_params=strategy_params)
            data_context = BacktestDataContext()
            executor = BacktestExecutor(
                strategy=strategy_instance,
                data_context=data_context,
                backtest_result_id=backtest_result.id,
                virtual_portfolio_id=virtual_portfolio.id,
                initial_capital=initial_capital,
                commission_pct=0.001,
                slippage_pct=0.0005,
                debug=debug
            )

            executor_run_result = await executor.run(start_date=start_date, end_date=end_date, rebalancing_frequency='monthly')

            if executor_run_result is None:
                raise Exception("BacktestExecutor.run() returned None.")

            transactions_log = executor_run_result.get("transactions_log", [])
            debug_logs = executor_run_result.get("debug_logs", [])

            # 4. Save transactions
            if transactions_log:
                await models.VirtualTransaction.insert_many(transactions_log)

            # 5. Update BacktestResult with logs and final status
            backtest_result.debug_logs = debug_logs
            backtest_result.status = "COMPLETED"
            await backtest_result.save()

            # 6. Return the ID and other essential info of the saved result.
            # The frontend will use this to fetch the full, calculated results.
            return {
                "backtest_result_id": str(backtest_result.id),
                "virtual_portfolio_id": str(virtual_portfolio.id),
                "strategy_id": str(strategy_doc.id),
                "strategy_name": strategy_doc.name,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
            }
        except Exception as e:
            logger.error(f"An error occurred during backtest task: {e}")
            # If the backtest_result was created, update its status to FAILED
            if backtest_result:
                backtest_result.status = "FAILED"
                if hasattr(backtest_result, 'debug_logs') and backtest_result.debug_logs is not None:
                    backtest_result.debug_logs.append(f"Error: {type(e).__name__} - {e}")
                else:
                    backtest_result.debug_logs = [f"Error: {type(e).__name__} - {e}"]
                await backtest_result.save()
            return {"error": f"Backtest task failed: {type(e).__name__} - {e}"}

    return asyncio.run(_run_and_cleanup())


@app.task(autoretry_for=(requests.exceptions.RequestException,), retry_backoff=True, max_retries=3)
def run_live_strategy_task(portfolio_id: str):
    async def _run_live_strategy():
        if not is_market_open_time():
            logger.info(f"Market is closed. Skipping live strategy run for portfolio {portfolio_id}.")
            return {"status": "skipped", "reason": "Market is closed"}

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

        try:
            portfolio_obj = await models.Portfolio.get(PydanticObjectId(portfolio_id), fetch_links=True)
            if not portfolio_obj:
                raise ValueError(f"Portfolio with ID {portfolio_id} not found.")
            if not portfolio_obj.strategy:
                raise ValueError(f"Portfolio {portfolio_id} has no strategy linked.")
            if not portfolio_obj.broker_provider or not portfolio_obj.broker_account_no:
                raise ValueError(f"Portfolio {portfolio_id} is missing broker details.")
            if portfolio_obj.environment != "live":
                raise ValueError(f"Portfolio {portfolio_id} is not configured for live trading (environment is '{portfolio_obj.environment}').")


            strategy_doc = portfolio_obj.strategy
            strategy_params = strategy_doc.parameters.model_dump() if strategy_doc.parameters else {}

            strategy_type = strategy_doc.strategy_type
            strategy_class_name = ''.join(word.capitalize() for word in strategy_type.split('_')) + 'Strategy'
            StrategyClass = STRATEGY_MAP.get(strategy_class_name)
            if not StrategyClass:
                raise ValueError(f"Unknown strategy type: {strategy_type}")

            strategy_instance = StrategyClass(strategy_params=strategy_params)

            live_executor = LiveExecutor(
                strategy=strategy_instance,
                broker_provider=portfolio_obj.broker_provider,
                broker_account_no=portfolio_obj.broker_account_no
            )
            
            await live_executor.run() # This will execute one iteration of the strategy

            return {"status": "success", "message": f"Live strategy run for portfolio {portfolio_id} completed."}

        except requests.exceptions.RequestException:
            # Re-raise network exceptions to trigger Celery retry.
            # LiveExecutor's idempotency check (get_open_orders) prevents double spending.
            logger.warning(f"[Retryable Error] Network issue during live strategy run for portfolio {portfolio_id}. Celery will retry.")
            raise
        except Exception as e:
            logger.error(f"An error occurred during live strategy task for portfolio {portfolio_id}: {e}")
            return {"status": "error", "error": str(e)}

    return asyncio.run(_run_live_strategy())


@app.task(autoretry_for=(requests.exceptions.RequestException,), retry_backoff=True, max_retries=3)
def execute_trade_task(symbol: str, side: str, quantity: int, price: int, broker_provider: str, broker_account_no: str, order_type: str = 'limit'):
    """
    A simple Celery task that executes a single trade order.
    This is intended to be called by the MarketMonitor when a strategy generates a signal.
    """
    async def _execute():
        # Import OrderManager here to avoid circular imports if any (though unlikely given the file structure)
        # or use the one imported at module level if added.
        # Ideally, add `from core.executors.order_manager import OrderManager` at the top of the file
        # But since I'm editing the function, I'll rely on the top-level import I'm about to add/verify.
        # Assuming top level import is added.
        try:
            order_manager = OrderManager(broker_provider, broker_account_no)
            result = await order_manager.execute_order(symbol, quantity, price, side, order_type=order_type)
            logger.info(f"Trade execution result: {result}")
            if result.get("status") == "error":
                 raise ValueError(result.get("message")) # Raise to potentially trigger retry or just report failure
            return {"status": "success", "result": result}
        except ValueError as e:
            logger.error(f"Validation/Broker error in trade execution task: {e}")
            return {"status": "error", "error": str(e)}
            
    return asyncio.run(_execute())

# Example of how to call this task from another part of the application (e.g., the web service):
# from workers.tasks import run_backtest_task
#
# strategy_config = {
#     'asset_weights': {'SPY': 0.6, 'AGG': 0.4} # Example for a 60/40 portfolio
# }
#
# # This sends the task to the message queue. A Celery worker will pick it up.
# task = run_backtest_task.delay(strategy_params=strategy_config, start_date='2021-01-01', end_date='2023-01-01')
#
# # You can then check the status of the task and get the result
# print(f"Task ID: {task.id}")
# print(f"Task status: {task.status}")
# # result = task.get() # This will block until the task is finished
