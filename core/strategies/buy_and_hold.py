
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
            strategy_params (Dict): Expected key: 'asset_weights', a list of objects/dicts
                                    with 'asset' and 'weight' keys.
        """
        super().__init__(strategy_params)
        raw_weights = self.params.get('asset_weights', [])
        
        self.asset_weights = {}
        if isinstance(raw_weights, list):
            for item in raw_weights:
                # Support both Pydantic objects and dictionaries
                asset = getattr(item, 'asset', None) or (item.get('asset') if isinstance(item, dict) else None)
                weight = getattr(item, 'weight', None) or (item.get('weight') if isinstance(item, dict) else None)
                
                if asset and weight is not None:
                    self.asset_weights[asset] = float(weight)
        
        if not self.asset_weights:
            raise ValueError("BuyAndHoldStrategy requires a non-empty 'asset_weights' list in strategy_params.")

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
