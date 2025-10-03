import os
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from beanie import PydanticObjectId
from .. import models, schemas
from datetime import datetime
import json # Added this import
import pandas as pd # Add this import

router = APIRouter(
    tags=["backtesting"],
)

# --- Backtest Result Endpoints ---

@router.post("/api/backtest_results/", status_code=status.HTTP_201_CREATED)
async def create_backtest_result(request: schemas.BacktestSaveRequest):
    db_strategy_doc = await models.Strategy.get(request.strategy_id)
    if not db_strategy_doc:
        raise HTTPException(status_code=404, detail="Strategy not found in DB for linking")

    # 1. Create and insert the virtual portfolio
    # Shorten the name to fit within 50 characters
    portfolio_name_suffix = f"{request.name[:20]} {datetime.now().strftime('%Y%m%d%H%M%S')}"
    virtual_portfolio = models.Portfolio(
        name=f"VP {portfolio_name_suffix}",
        environment="backtest",
        # Other portfolio details can be added if needed
    )
    await virtual_portfolio.insert()

    # 2. Create and insert the BacktestResult document
    db_result = models.BacktestResult(
        name=request.name,
        virtual_portfolio_id=virtual_portfolio.id, # Link to the newly created virtual portfolio
        strategy=db_strategy_doc,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        debug_logs=request.debug_logs, # Save debug logs
    )
    await db_result.insert()

    # 3. Insert all VirtualTransactions
    for vt_data in request.transactions_log:
        # Ensure asset_id, portfolio_id, backtest_result_id are correctly set
        # Unpack vt_data.model_dump() and then override portfolio_id and backtest_result_id
        vt_data_dict = vt_data.model_dump()
        vt_data_dict['portfolio_id'] = virtual_portfolio.id
        vt_data_dict['backtest_result_id'] = db_result.id
        virtual_transaction = models.VirtualTransaction(**vt_data_dict)
        await virtual_transaction.insert()

    # Explicitly convert PydanticObjectId to string for the returned ID
    if not db_result.id:
        raise HTTPException(status_code=500, detail="Failed to get ID for saved BacktestResult.")
    
    await db_result.fetch_link(models.BacktestResult.strategy) # Fetch strategy for response

    # Return a dictionary representation to ensure ID is a string
    return {
        "id": str(db_result.id),
        "name": db_result.name,
        "virtual_portfolio_id": str(db_result.virtual_portfolio_id),
        "strategy": db_result.strategy.model_dump(), # Assuming strategy is fetched
        "start_date": db_result.start_date.isoformat(),
        "end_date": db_result.end_date.isoformat(),
        "initial_capital": db_result.initial_capital,
        "created_at": db_result.created_at.isoformat(),
        "debug_logs": db_result.debug_logs, # Include debug logs
    }

@router.get("/api/backtest_results/", response_model=List[schemas.BacktestResult])
async def read_backtest_results(skip: int = 0, limit: int = 100):
    results_from_db = await models.BacktestResult.find_all().skip(skip).limit(limit).to_list()
    
    # Fetch linked strategy for each result
    for result in results_from_db:
        await result.fetch_link(models.BacktestResult.strategy)
    
    return results_from_db

@router.get("/api/backtest_results/{result_id}", response_model=schemas.BacktestResult)
async def read_backtest_result(result_id: PydanticObjectId):
    result = await models.BacktestResult.get(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    
    # Fetch linked strategy
    await result.fetch_link(models.BacktestResult.strategy)
    
    return result

@router.delete("/api/backtest_results/{result_id}")
async def delete_backtest_result(result_id: PydanticObjectId):
    result = await models.BacktestResult.get(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    
    # Get virtual_portfolio_id before deleting the result
    virtual_portfolio_id = result.virtual_portfolio_id

    # Delete all associated VirtualTransactions
    await models.VirtualTransaction.find(
        models.VirtualTransaction.backtest_result_id == result_id
    ).delete()

    # Delete the associated VirtualPortfolio
    portfolio = await models.Portfolio.get(virtual_portfolio_id)
    if portfolio:
        await portfolio.delete()

    # Delete the BacktestResult itself
    await result.delete()
    return {"message": "Backtest result and associated data deleted successfully"}

@router.get("/api/backtest_results/{backtest_result_id}/transactions", response_model=List[schemas.VirtualTransaction])
async def get_backtest_transactions(backtest_result_id: PydanticObjectId):
    virtual_transactions = await models.VirtualTransaction.find(
        models.VirtualTransaction.backtest_result_id == backtest_result_id
    ).to_list()
    
    # Populate asset details for each transaction
    transaction_dicts = []
    for vt in virtual_transactions:
        asset = await models.Asset.get(vt.asset_id)
        if asset:
            transaction_dicts.append({
                "id": str(vt.id),
                "asset_id": str(vt.asset_id),
                "asset": {"symbol": asset.symbol, "name": asset.name, "asset_type": asset.asset_type},
                "transaction_type": vt.transaction_type,
                "quantity": vt.quantity,
                "price": vt.price,
                "fee": vt.fee,
                "tax": vt.tax,
                "transaction_date": vt.transaction_date,
                "portfolio_id": str(vt.portfolio_id),
                "backtest_result_id": str(vt.backtest_result_id),
            })
    return transaction_dicts

from workers.tasks import run_backtest_task
from backend.data_collector import get_benchmark_historical_data # Import the new benchmark data function
from backend.portfolio_calculator import calculate_portfolio_value, calculate_returns, calculate_cumulative_returns, calculate_volatility, calculate_max_drawdown # Added this import

@router.post("/api/backtest/strategy")
async def run_strategy_backtest(request: schemas.StrategyBacktestRequest):
    strategy = await models.Strategy.get(request.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Convert strategy_type (e.g., 'buy_and_hold') to strategy class name (e.g., 'BuyAndHoldStrategy')
    strategy_name = ''.join(word.capitalize() for word in strategy.strategy_type.split('_')) + 'Strategy'

    # Delegate the backtest execution to the Celery worker
    task = run_backtest_task.delay(
        strategy_id=str(strategy.id),
        initial_capital=request.initial_capital,
        start_date=request.start_date,
        end_date=request.end_date,
        debug=request.debug,
    )

    # Return the task ID to the client
    return {"message": "Backtest task has been received.", "task_id": task.id}

@router.put("/api/backtest_results/{backtest_result_id}/calculate_and_get_details", response_model=schemas.BacktestResultDetails)
async def calculate_and_get_backtest_details(
    backtest_result_id: PydanticObjectId,
):
    """
    Calculates performance metrics for a completed backtest run,
    updates the BacktestResult document in the database, and returns the full details.
    This endpoint is now self-contained and fetches all required data from the DB.
    """
    # 1. Fetch the main BacktestResult document
    db_result = await models.BacktestResult.get(backtest_result_id)
    if not db_result:
        raise HTTPException(status_code=404, detail="BacktestResult not found.")

    # 2. Get required data from the document
    await db_result.fetch_link(models.BacktestResult.strategy)
    strategy_doc = db_result.strategy
    start_date = db_result.start_date.strftime('%Y-%m-%d')
    end_date = db_result.end_date.strftime('%Y-%m-%d')
    initial_capital = db_result.initial_capital
    debug_logs = db_result.debug_logs

    # 3. Fetch associated virtual transactions
    virtual_transactions = await models.VirtualTransaction.find(
        models.VirtualTransaction.backtest_result_id == backtest_result_id
    ).to_list()

    # 4. Perform calculations
    # Create a simplified transaction list for the calculator function
    calc_transaction_dicts = []
    for vt in virtual_transactions:
        asset = await models.Asset.get(vt.asset_id)
        if asset:
            calc_transaction_dicts.append({
                "asset": {"symbol": asset.symbol},
                "transaction_type": vt.transaction_type,
                "quantity": vt.quantity,
                "price": vt.price,
                "transaction_date": vt.transaction_date,
            })

    unique_asset_symbols = list(set(t['asset']['symbol'] for t in calc_transaction_dicts))
    historical_prices = {}
    from core.data_providers.backtest import BacktestDataContext
    data_context = BacktestDataContext()
    for symbol in unique_asset_symbols:
        data = data_context.get_historical_data_by_range([symbol], start_date, end_date).get(symbol)
        if data is not None and not data.empty:
            historical_prices[symbol] = data

    if not historical_prices and calc_transaction_dicts:
        portfolio_value_df = pd.DataFrame(columns=['Date', 'Value'])
        portfolio_value_df.loc[0] = [datetime.strptime(start_date, '%Y-%m-%d'), initial_capital]
    else:
        portfolio_value_df = calculate_portfolio_value(calc_transaction_dicts, historical_prices)

    if portfolio_value_df.empty:
        portfolio_value_df = pd.DataFrame(columns=['Date', 'Value'])
        portfolio_value_df.loc[0] = [datetime.strptime(start_date, '%Y-%m-%d'), initial_capital]

    # Ensure Date is string for JSON serialization
    if not portfolio_value_df.empty and 'Date' in portfolio_value_df.columns:
        # Check if Date column contains datetime objects or Timestamp objects
        if pd.api.types.is_datetime64_any_dtype(portfolio_value_df['Date']) or pd.api.types.is_object_dtype(portfolio_value_df['Date']):
             portfolio_value_df['Date'] = portfolio_value_df['Date'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, (datetime, pd.Timestamp)) else str(x))

    daily_returns = calculate_returns(portfolio_value_df)
    cumulative_returns = calculate_cumulative_returns(daily_returns)
    returns_dict = {str(k.date()): v for k, v in daily_returns.items()} if not daily_returns.empty else {}
    cumulative_returns_dict = {str(k.date()): v for k, v in cumulative_returns.items()} if not cumulative_returns.empty else {}
    volatility = calculate_volatility(daily_returns, annualization_factor=252)
    max_drawdown = calculate_max_drawdown(cumulative_returns)
    sharpe_ratio = 0.0  # Placeholder
    final_capital = portfolio_value_df['Value'].iloc[-1] if not portfolio_value_df.empty else initial_capital
    
    num_days = (db_result.end_date - db_result.start_date).days
    years = num_days / 365.25 if num_days > 0 else 1
    annualized_return = (final_capital / initial_capital) ** (1 / years) - 1 if initial_capital > 0 and years > 0 else 0


    # 5. Update the BacktestResult document with calculated metrics
    db_result.final_capital = final_capital
    db_result.annualized_return = annualized_return
    db_result.volatility = volatility
    db_result.max_drawdown = max_drawdown
    db_result.sharpe_ratio = sharpe_ratio
    db_result.portfolio_value = portfolio_value_df.to_dict(orient='records')
    db_result.returns = returns_dict
    db_result.cumulative_returns = cumulative_returns_dict
    db_result.status = "ANALYZED"
    await db_result.save()

    # 6. Construct and return the detailed response
    response_transactions = await get_backtest_transactions(backtest_result_id)

    response_data = schemas.BacktestResultDetails(
        id=db_result.id,
        name=db_result.name,
        virtual_portfolio_id=db_result.virtual_portfolio_id,
        strategy=strategy_doc,
        start_date=db_result.start_date,
        end_date=db_result.end_date,
        initial_capital=db_result.initial_capital,
        created_at=db_result.created_at,
        final_capital=final_capital,
        annualized_return=annualized_return,
        volatility=volatility,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        portfolio_value=portfolio_value_df.to_dict(orient='records'),
        returns=returns_dict,
        cumulative_returns=cumulative_returns_dict,
        transactions=response_transactions,
        debug_logs=debug_logs,
    )

    return response_data


from workers.celery_app import app as celery_app

@router.get("/api/backtest/results/task/{task_id}")
async def get_backtest_task_status(task_id: str):
    """
    Get the status and result of a backtest task.
    """
    task_result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None # Initialize result to None
    }

    if task_result.successful():
        # Only set result if task was successful and result is not None
        if task_result.result is not None:
            response["result"] = task_result.result
        else:
            # This case indicates a problem with result backend or task returning None
            response["error"] = "Task reported success but result data is None. Check Celery result backend configuration or task return value."
    elif task_result.failed():
        response["error"] = str(task_result.info)

    return response

@router.get("/api/backtest/benchmarks")
async def get_benchmarks(
    start_date: str,
    end_date: str,
    initial_capital: float
):
    """
    Fetches and calculates benchmark data for a given period and initial capital.
    """
    benchmark_dfs = await get_benchmark_historical_data(start_date, end_date)
    
    benchmark_data = {}
    for name, df in benchmark_dfs.items():
        if not df.empty:
            df = df.dropna(subset=['Close']).ffill()
            if not df.empty:
                df['Date'] = df.index.strftime('%Y-%m-%d')
                df['Value'] = (df['Close'] / df['Close'].iloc[0]) * initial_capital
                benchmark_data[name] = df[['Date', 'Value']].to_dict(orient='records')

    return {"benchmark_data": benchmark_data}

