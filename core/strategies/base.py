
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List

class DataContext(ABC):
    """
    Provides the necessary market data for a strategy.
    This is an abstract base class that can be implemented for backtesting (historical data)
    or live trading (real-time data).
    """
    @abstractmethod
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Returns the most recent prices for the given symbols.
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbols: List[str], end_date: pd.Timestamp, lookback_days: int) -> Dict[str, pd.DataFrame]:
        """
        Returns historical price data for the given symbols for a specified lookback period
        ending on `end_date`.
        """
        pass

    @abstractmethod
    def get_asset_universe(self, date: pd.Timestamp, region: str, top_n: int = None, ranking_metric: str = None) -> pd.DataFrame:
        """
        Returns the universe of assets for a given region at a specific date.
        """
        pass

    @abstractmethod
    def get_fundamental_data(self, symbol: str, date: pd.Timestamp) -> Dict:
        """
        Returns fundamental data for a given symbol at a specific date.
        """
        pass

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    The core logic of a strategy is encapsulated here, independent of whether
    it's being backtested or run live.
    """
    def __init__(self, strategy_params: Dict):
        self.params = strategy_params
        self.last_signals = None

    def on_tick(self, tick_data: Dict):
        """
        (Optional) Handles real-time tick data for event-driven strategies.
        This method is called by the MarketMonitor for each incoming tick.

        Args:
            tick_data (Dict): A dictionary containing the latest tick information
                              (e.g., {'symbol': '005930', 'price': 75000, ...}).

        Returns:
            A trade signal dictionary if an action is required, otherwise None.
            e.g., {'side': 'buy', 'symbol': '005930', 'quantity': 10}
        """
        pass

    @abstractmethod
    def generate_signals(self, date: pd.Timestamp, data_context: DataContext) -> Dict[str, float]:
        """
        The core method of the strategy for generating periodic signals.
        Based on the data provided by the DataContext for a specific date, this method
        generates the target asset allocation (signals).

        Args:
            date (pd.Timestamp): The current date for which to generate signals.
            data_context (DataContext): The data provider.

        Returns:
            A dictionary where keys are asset symbols and values are their
            target weights in the portfolio (e.g., {'SPY': 0.6, 'AGG': 0.4}).
        """
        pass
