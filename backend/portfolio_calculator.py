import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict
from beanie import PydanticObjectId

from .data_collector import get_stock_data, get_historical_data
from . import models

def calculate_portfolio_value(transactions: List[Dict], historical_prices: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=['Date', 'Value'])

    trans_df = pd.DataFrame(transactions)
    trans_df['transaction_date'] = pd.to_datetime(trans_df['transaction_date'])
    trans_df['symbol'] = trans_df['asset'].apply(lambda x: x['symbol'])
    
    def adjust_quantity(row):
        if row['transaction_type'] in ['buy', 'deposit']:
            return row['quantity']
        if row['transaction_type'] == 'dividend':
            return row['quantity'] - (row['tax'] or 0)
        if row['transaction_type'] in ['sell', 'withdrawal']:
            return -row['quantity']
        return 0

    trans_df['quantity_adj'] = trans_df.apply(adjust_quantity, axis=1)
    
    all_dates = []
    if not trans_df.empty:
        all_dates.extend(trans_df['transaction_date'].tolist())
    
    for symbol, df in historical_prices.items():
        if not df.empty:
            all_dates.extend(df.index.tolist())
    
    if not all_dates:
        return pd.DataFrame(columns=['Date', 'Value'])

    start_date = min(all_dates)
    end_date = max(all_dates)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    holdings_df = trans_df.groupby(['transaction_date', 'symbol'])['quantity_adj'].sum().unstack().fillna(0)
    holdings_df = holdings_df.reindex(date_range).fillna(0).cumsum()

    prices_df = pd.DataFrame(index=date_range)
    for symbol, df in historical_prices.items():
        if symbol in holdings_df.columns:
            # Use bfill to propagate first available price backwards
            prices_df[symbol] = df['Close'].reindex(date_range, method='bfill')

    prices_df.ffill(inplace=True) # Then ffill to fill any remaining gaps

    common_symbols = holdings_df.columns.intersection(prices_df.columns)
    daily_portfolio_value = (holdings_df[common_symbols] * prices_df[common_symbols]).sum(axis=1)

    if daily_portfolio_value.empty:
        return pd.DataFrame(columns=['Date', 'Value'])
        
    return pd.DataFrame({'Date': daily_portfolio_value.index, 'Value': daily_portfolio_value.values})

def calculate_returns(portfolio_value: pd.DataFrame) -> pd.Series:
    if portfolio_value.empty or len(portfolio_value) < 2:
        return pd.Series()
    portfolio_value = portfolio_value.set_index('Date')
    returns = portfolio_value['Value'].pct_change().dropna()
    returns.replace([np.inf, -np.inf], 0, inplace=True)
    return returns

def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    if returns.empty:
        return pd.Series()
    cumulative_returns = (1 + returns).cumprod() - 1
    return cumulative_returns

def calculate_volatility(returns: pd.Series, annualization_factor: int = 12) -> float:
    if returns.empty:
        return 0.0
    volatility = returns.std() * (annualization_factor ** 0.5)
    return volatility if np.isfinite(volatility) else 0.0

def calculate_max_drawdown(cumulative_returns: pd.Series) -> float:
    if cumulative_returns.empty:
        return 0.0
    cumulative_returns = cumulative_returns.replace([np.inf, -np.inf], np.nan).dropna()
    if cumulative_returns.empty:
        return 0.0
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns - peak) / (peak + 1)
    max_drawdown = drawdown.min()
    return max_drawdown if np.isfinite(max_drawdown) else 0.0

async def get_portfolio_returns(
    portfolio_id: PydanticObjectId, start_date: str, end_date: str
) -> Dict:
    assets = await models.Asset.find(models.Asset.portfolio_id == portfolio_id).to_list()
    transactions = await models.Transaction.find(models.Transaction.portfolio_id == portfolio_id).to_list()

    if not assets or not transactions:
        return {"error": "No assets or transactions found for this portfolio."}

    # Create a map of asset_id to asset for easy lookup
    asset_map = {asset.id: asset for asset in assets}

    transaction_dicts = []
    for t in transactions:
        asset = asset_map.get(t.asset_id)

        if asset:
            transaction_dicts.append({
                "asset": {"symbol": asset.symbol, "asset_type": asset.asset_type},
                "transaction_type": t.transaction_type,
                "quantity": t.quantity,
                "price": t.price,
                "tax": t.tax,
                "transaction_date": t.transaction_date,
            })

    historical_prices = {}
    for asset in assets:
        if asset.asset_type == "cash":
            data = pd.DataFrame({'Close': 1.0}, index=pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D')))
        elif "stock_us" in asset.asset_type:
            data = get_historical_data(asset.symbol, start_date, end_date)
        elif "stock_kr" in asset.asset_type:
            data = get_historical_data(asset.symbol, start_date, end_date)
        else:
            data = pd.DataFrame()

        if not data.empty:
            historical_prices[asset.symbol] = data

    if not historical_prices:
        return {"error": "Could not fetch historical data for assets in this portfolio."}

    portfolio_value = calculate_portfolio_value(transaction_dicts, historical_prices)

    if portfolio_value.empty:
        return {"error": "Could not calculate portfolio value."}

    daily_returns = calculate_returns(portfolio_value)
    cumulative_returns = calculate_cumulative_returns(daily_returns)
    volatility = calculate_volatility(daily_returns, annualization_factor=252)
    max_drawdown = calculate_max_drawdown(cumulative_returns)

    return {
        "portfolio_value": portfolio_value.to_dict(orient="records"),
        "daily_returns": daily_returns.to_dict(),
        "cumulative_returns": cumulative_returns.to_dict(),
        "volatility": volatility,
        "max_drawdown": max_drawdown,
    }
