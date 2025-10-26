
import pandas as pd
from typing import Dict

from .base import BaseStrategy, DataContext

class BuyAndHoldStrategy(BaseStrategy):
    """
    A simple strategy that buys a predefined set of assets and holds them.
    The signals are generated only once at the beginning.
    """
    def __init__(self, strategy_params: Dict):
        """
        Args:
            strategy_params (Dict): Expected key: 'asset_weights', a dict mapping
                                    symbols to their target weights.
        """
        super().__init__(strategy_params)
        self.asset_weights = self.params.get('asset_weights', {})
        if not self.asset_weights or not isinstance(self.asset_weights, dict):
            raise ValueError("BuyAndHoldStrategy requires 'asset_weights' in strategy_params.")

    def on_tick(self, tick_data: Dict):
        """Buy and Hold does not react to individual ticks."""
        pass

        """
        For a Buy and Hold strategy, the signal is simply the predefined target weights.
        The date and data_context are not used, but are part of the standard interface.
        """
        total_weight = sum(self.asset_weights.values())
        if total_weight <= 0:
            return {symbol: 0.0 for symbol in self.asset_weights.keys()}

        normalized_weights = {symbol: weight / total_weight for symbol, weight in self.asset_weights.items()}
        return normalized_weights
