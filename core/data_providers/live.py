
import pandas as pd
from typing import Dict, List
import datetime
import os

from backend.data_collector import get_historical_data as fetch_historical_data_by_range
from backend.data_collector import get_asset_universe as fetch_asset_universe
from backend.data_collector import get_korean_fundamental_data as fetch_korean_fundamental_data
from core.api_clients.hantoo_client import HantooClient

from core.strategies.base import DataContext

class LiveDataContext(DataContext):
    """
    A data context for live trading. It fetches real-time data from a broker API.
    """
    def __init__(self, hantoo_client: HantooClient):
        self.client = hantoo_client

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """ Fetches the current market price for a list of symbols. """
        prices = {}
        for symbol in symbols:
            price = self.client.get_current_price(symbol)
            prices[symbol] = price
        return prices

    def get_historical_data(self, symbols: List[str], end_date: pd.Timestamp, lookback_days: int) -> Dict[str, pd.DataFrame]:
        """
        Fetches historical data. For live trading, this might use a different source
        or could be a placeholder if not directly needed for the strategy logic.
        For now, we can re-use the backtest data fetching logic for simplicity.
        """
        start_date = end_date - pd.Timedelta(days=lookback_days)
        # This re-uses the logic from the global scope, which is not ideal but works for now.
        return fetch_historical_data_by_range(symbols, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    def get_asset_universe(self, date: pd.Timestamp, region: str, top_n: int = None, ranking_metric: str = None) -> pd.DataFrame:
        """
        Implements fetching the asset universe.
        For live trading, this might involve querying a real-time asset database or a pre-defined universe.
        For now, we can re-use the backtest data fetching logic for simplicity.
        """
        # For simplicity, we fetch it every time it's requested, but caching would be beneficial.
        # The date, top_n, ranking_metric arguments are passed to fetch_asset_universe if it supports them.
        return fetch_asset_universe(region=region) # Assuming fetch_asset_universe only takes region for now

    def get_fundamental_data(self, symbol: str, date: pd.Timestamp) -> Dict:
        """
        Implements fetching fundamental data for a specific date.
        It determines the correct year and quarter to fetch based on the date.
        """
        # Determine the year and quarter for the given date
        year = date.year
        quarter = (date.month - 1) // 3 + 1

        # For now, we assume re_evaluation_frequency is always quarterly for simplicity.
        # This could be made more sophisticated.
        # The region is not part of the DataContext abstract method, so it needs to be handled internally or passed differently.
        # For now, we assume KR for fundamental data if not specified.
        opendart_api_key = os.getenv("OPENDART_API_KEY")
        if not opendart_api_key:
            print("Error: OPENDART_API_KEY environment variable not set for Korean fundamental data.")
            return {}
        return fetch_korean_fundamental_data(symbol=symbol, opendart_api_key=opendart_api_key, year=year, quarter=quarter) # Assuming KR region for now
