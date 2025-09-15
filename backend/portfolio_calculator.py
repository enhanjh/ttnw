import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session

from .data_collector import get_stock_data, get_historical_data
from . import models

def calculate_portfolio_value(transactions: List[Dict], historical_prices: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculates the daily value of the portfolio based on transactions and historical prices.
    Then resamples to monthly values.
    :param transactions: List of transaction dictionaries (e.g., from database).
    :param historical_prices: Dictionary of asset symbols to their historical price DataFrames.
    :return: DataFrame with monthly portfolio value.
    """
    if not transactions:
        return pd.DataFrame(columns=['Date', 'Value'])

    # Create a DataFrame from transactions
    trans_df = pd.DataFrame(transactions)
    trans_df['transaction_date'] = pd.to_datetime(trans_df['transaction_date'])
    trans_df['symbol'] = trans_df['asset'].apply(lambda x: x['symbol'])
    
    # Adjust quantity based on transaction type
    def adjust_quantity(row):
        if row['transaction_type'] in ['buy', 'deposit']:
            return row['quantity']
        if row['transaction_type'] == 'dividend':
            return row['quantity'] - (row['tax'] or 0)
        if row['transaction_type'] in ['sell', 'withdrawal']:
            return -row['quantity']
        return 0

    trans_df['quantity_adj'] = trans_df.apply(adjust_quantity, axis=1)
    
    # Determine the overall date range for the portfolio
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

    # Calculate daily holdings
    holdings_df = trans_df.groupby(['transaction_date', 'symbol'])['quantity_adj'].sum().unstack().fillna(0)
    holdings_df = holdings_df.reindex(date_range).fillna(0).cumsum()

    # Prepare prices DataFrame
    prices_df = pd.DataFrame(index=date_range)
    for symbol, df in historical_prices.items():
        if symbol in holdings_df.columns: # Only need prices for assets we hold
            prices_df[symbol] = df['Close'].reindex(date_range, method='pad')

    # Forward fill missing prices (for weekends/holidays)
    prices_df.ffill(inplace=True)
    # Backward fill for any initial NaNs
    prices_df.bfill(inplace=True)

    # Calculate daily portfolio value
    # Ensure columns match for multiplication
    common_symbols = holdings_df.columns.intersection(prices_df.columns)
    daily_portfolio_value = (holdings_df[common_symbols] * prices_df[common_symbols]).sum(axis=1)

    if daily_portfolio_value.empty:
        return pd.DataFrame(columns=['Date', 'Value'])
        
    return pd.DataFrame({'Date': daily_portfolio_value.index, 'Value': daily_portfolio_value.values})

def calculate_returns(portfolio_value: pd.DataFrame) -> pd.Series:
    """
    Calculates returns from portfolio value.
    :param portfolio_value: DataFrame with portfolio value (daily or monthly).
    :return: Series with returns.
    """
    if portfolio_value.empty or len(portfolio_value) < 2:
        return pd.Series()
    portfolio_value = portfolio_value.set_index('Date')
    returns = portfolio_value['Value'].pct_change().dropna()
    returns.replace([np.inf, -np.inf], 0, inplace=True)  # Replace inf with 0
    return returns

def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    Calculates cumulative returns from returns.
    :param returns: Series with returns.
    :return: Series with cumulative returns.
    """
    if returns.empty:
        return pd.Series()
    cumulative_returns = (1 + returns).cumprod() - 1
    return cumulative_returns

def calculate_volatility(returns: pd.Series, annualization_factor: int = 12) -> float:
    """
    Calculates annualized volatility.
    :param returns: Series with returns (monthly).
    :param annualization_factor: Number of periods in a year (12 for monthly).
    :return: Annualized volatility.
    """
    if returns.empty:
        return 0.0
    volatility = returns.std() * (annualization_factor ** 0.5)
    return volatility if np.isfinite(volatility) else 0.0

def calculate_max_drawdown(cumulative_returns: pd.Series) -> float:
    """
    Calculates the maximum drawdown.
    :param cumulative_returns: Series with cumulative returns.
    :return: Maximum drawdown as a percentage.
    """
    if cumulative_returns.empty:
        return 0.0
    cumulative_returns = cumulative_returns.replace([np.inf, -np.inf], np.nan).dropna()
    if cumulative_returns.empty:
        return 0.0
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns - peak) / (peak + 1) # Add 1 to peak to avoid division by zero if peak is -1
    max_drawdown = drawdown.min()
    return max_drawdown if np.isfinite(max_drawdown) else 0.0

def get_portfolio_returns(
    db: Session, portfolio_id: int, start_date: str, end_date: str
) -> Dict:
    """
    Calculates and returns various performance metrics for a given portfolio.
    """
    # Fetch assets and transactions for the portfolio
    assets = db.query(models.Asset).filter(models.Asset.portfolio_id == portfolio_id).all()
    transactions = db.query(models.Transaction).filter(models.Transaction.portfolio_id == portfolio_id).all()

    if not assets or not transactions:
        return {"error": "No assets or transactions found for this portfolio."}

    # Prepare data for portfolio calculation
    transaction_dicts = []
    for t in transactions:
        asset = db.query(models.Asset).filter(models.Asset.id == t.asset_id).first()
        if asset: # Ensure asset exists before adding to transaction_dicts
            transaction_dicts.append({
                "asset": {"symbol": asset.symbol, "asset_type": asset.asset_type},
                "transaction_type": t.transaction_type,
                "quantity": t.quantity,
                "price": t.price,
                "tax": t.tax, # Add tax to the dictionary
                "transaction_date": t.transaction_date,
            })

    # Fetch historical prices for all symbols
    historical_prices = {}
    for asset in assets:
        if asset.asset_type == "cash":
            # For cash assets, create a dummy DataFrame with price 1
            data = pd.DataFrame({'Close': 1.0}, index=pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D')))
        elif "stock_us" in asset.asset_type:
            data = get_stock_data(asset.symbol, start_date, end_date)
        elif "stock_kr" in asset.asset_type:
            data = get_historical_data(asset.symbol, start_date, end_date)
        else:
            data = pd.DataFrame() # Handle other asset types as needed

        if not data.empty:
            historical_prices[asset.symbol] = data

    if not historical_prices:
        return {"error": "Could not fetch historical data for assets in this portfolio."}

    # Calculate portfolio value
    portfolio_value = calculate_portfolio_value(transaction_dicts, historical_prices)

    if portfolio_value.empty:
        return {"error": "Could not calculate portfolio value."}

    # Calculate performance metrics
    daily_returns = calculate_returns(portfolio_value)
    cumulative_returns = calculate_cumulative_returns(daily_returns)
    volatility = calculate_volatility(daily_returns, annualization_factor=12) # Monthly data
    max_drawdown = calculate_max_drawdown(cumulative_returns)

    return {
        "portfolio_value": portfolio_value.to_dict(orient="records"),
        "daily_returns": daily_returns.to_dict(),
        "cumulative_returns": cumulative_returns.to_dict(),
        "volatility": volatility,
        "max_drawdown": max_drawdown,
    }

# Example usage (for testing purposes)
if __name__ == "__main__":
    # This part requires a running database with assets and transactions
    # For demonstration, let's mock some data
    print("Running portfolio_calculator example (mock data)...")

    # Mock historical prices
    mock_historical_prices = {
        "AAPL": pd.DataFrame({
            'Close': [150, 151, 152, 153, 154, 155, 156, 157, 158, 159],
        }, index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=10, freq='D'))),
        "MSFT": pd.DataFrame({
            'Close': [250, 251, 252, 253, 254, 255, 256, 257, 258, 259],
        }, index=pd.to_datetime(pd.date_range(start='2023-01-01', periods=10, freq='D'))),
    }

    # Mock transactions
    mock_transactions = [
        {'asset': {'symbol': 'AAPL'}, 'transaction_type': 'buy', 'quantity': 10, 'price': 150, 'transaction_date': datetime(2023, 1, 1)},
        {'asset': {'symbol': 'MSFT'}, 'transaction_type': 'buy', 'quantity': 5, 'price': 250, 'transaction_date': datetime(2023, 1, 2)},
        {'asset': {'symbol': 'AAPL'}, 'transaction_type': 'sell', 'quantity': 2, 'price': 155, 'transaction_date': datetime(2023, 1, 5)},
    ]

    portfolio_val = calculate_portfolio_value(mock_transactions, mock_historical_prices)
    print("\nPortfolio Value:")
    print(portfolio_val)

    if not portfolio_val.empty:
        daily_returns = calculate_returns(portfolio_val)
        print("\nDaily Returns:")
        print(daily_returns.head())

        cumulative_returns = calculate_cumulative_returns(daily_returns)
        print("\nCumulative Returns:")
        print(cumulative_returns.head())

        volatility = calculate_volatility(daily_returns)
        print(f"\nAnnualized Volatility: {volatility:.2f}")

        max_drawdown = calculate_max_drawdown(cumulative_returns)
        print(f"Max Drawdown: {max_drawdown:.2f}")