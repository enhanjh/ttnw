import os
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from beanie import PydanticObjectId
from .. import models, schemas
from ..backtesting_engine import BacktestingEngine
from datetime import datetime

router = APIRouter(
    tags=["backtesting"],
)

# --- Backtest Result Endpoints ---

@router.post("/api/backtest_results/", status_code=status.HTTP_201_CREATED)
async def create_backtest_result(result: schemas.BacktestResultCreate):
    db_strategy = await models.Strategy.get(result.strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    db_result = models.BacktestResult(
        name=result.name,
        strategy_id=db_strategy.id, # Store the ID of the strategy
        start_date=result.start_date,
        end_date=result.end_date,
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        annualized_return=result.annualized_return,
        volatility=result.volatility,
        max_drawdown=result.max_drawdown,
        sharpe_ratio=result.sharpe_ratio,
        portfolio_value=result.portfolio_value,
        returns=result.returns,
        cumulative_returns=result.cumulative_returns,
        transactions=result.transactions,
    )
    await db_result.insert()
    return db_result

@router.get("/api/backtest_results/", response_model=List[schemas.BacktestResult])
async def read_backtest_results(skip: int = 0, limit: int = 100):
    results_from_db = await models.BacktestResult.find_all().skip(skip).limit(limit).to_list()
    
    # Manually fetch linked strategy for each result
    for result in results_from_db:
        result.strategy = await models.Strategy.get(result.strategy_id)
    
    return results_from_db

@router.get("/api/backtest_results/{result_id}", response_model=schemas.BacktestResult)
async def read_backtest_result(result_id: PydanticObjectId):
    result = await models.BacktestResult.get(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    
    # Manually fetch linked strategy
    result.strategy = await models.Strategy.get(result.strategy_id)
    
    return result

@router.delete("/api/backtest_results/{result_id}")
async def delete_backtest_result(result_id: PydanticObjectId):
    result = await models.BacktestResult.get(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    await result.delete()
    return {"message": "Backtest result deleted successfully"}

# --- Backtesting Endpoint ---

@router.post("/api/backtest/strategy")
async def run_strategy_backtest(request: schemas.StrategyBacktestRequest, save_result: bool = False, result_name: Optional[str] = None):
    strategy = await models.Strategy.get(request.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    engine = BacktestingEngine(initial_capital=request.initial_capital)
    results = await engine.run_backtest(
        strategy_details=strategy,
        start_date=request.start_date,
        end_date=request.end_date,
        debug=request.debug
    )

    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    
    if save_result:
        if not result_name:
            raise HTTPException(status_code=400, detail="Result name is required to save backtest results.")
        
        # Prepare data for saving
        backtest_data_to_save = {
            "name": result_name,
            "strategy_id": strategy.id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_capital": request.initial_capital,
            "final_capital": results["final_capital"],
            "annualized_return": results["annualized_return"],
            "volatility": results["volatility"],
            "max_drawdown": results["max_drawdown"],
            "sharpe_ratio": results["sharpe_ratio"],
            "portfolio_value": results["portfolio_value"],
            "returns": results["returns"],
            "cumulative_returns": results["cumulative_returns"],
            "transactions": results["transactions"],
        }
        
        db_result = models.BacktestResult(
            name=backtest_data_to_save["name"],
            strategy_id=strategy.id, # Store the ID of the strategy
            start_date=datetime.strptime(backtest_data_to_save["start_date"], '%Y-%m-%d'), # Convert string to datetime
            end_date=datetime.strptime(backtest_data_to_save["end_date"], '%Y-%m-%d'), # Convert string to datetime
            initial_capital=backtest_data_to_save["initial_capital"],
            final_capital=backtest_data_to_save["final_capital"],
            annualized_return=backtest_data_to_save["annualized_return"],
            volatility=backtest_data_to_save["volatility"],
            max_drawdown=backtest_data_to_save["max_drawdown"],
            sharpe_ratio=backtest_data_to_save["sharpe_ratio"],
            portfolio_value=backtest_data_to_save["portfolio_value"],
            returns=backtest_data_to_save["returns"],
            cumulative_returns=backtest_data_to_save["cumulative_returns"],
            transactions=backtest_data_to_save["transactions"],
        )
        await db_result.insert()
        results["saved_result_id"] = str(db_result.id) # Add saved ID to response
        results["message"] = "Backtest results saved successfully!"

    return results

@router.get("/api/backtest/benchmarks")
async def get_benchmarks(
    start_date: str,
    end_date: str,
    initial_capital: float,
    debug: bool = False
):
    engine = BacktestingEngine(initial_capital=initial_capital)
    benchmark_data = engine._fetch_and_calculate_benchmarks(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        debug_logs=[] if debug else None
    )
    return {"benchmark_data": benchmark_data}
