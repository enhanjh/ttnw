
import pandas as pd
from typing import Dict

from .base import BaseStrategy, DataContext

class AssetAllocationStrategy(BaseStrategy):
    """
    A strategy that maintains a static, predefined mix of assets.
    The executor is responsible for periodically rebalancing the portfolio
    to match the target weights returned by this strategy.
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
            raise ValueError("AssetAllocationStrategy requires a non-empty 'asset_weights' list in strategy_params.")

    def on_tick(self, tick_data: Dict):
        """Asset Allocation does not react to individual ticks."""
        pass

    def generate_signals(self, date: pd.Timestamp, data_context: DataContext) -> Dict[str, float]:
        """
        For a static asset allocation strategy, the signal is always the predefined target weights.
        The date and data_context are not used, but are part of the standard interface.
        """
        total_weight = sum(self.asset_weights.values())
        if total_weight <= 0:
            return {symbol: 0.0 for symbol in self.asset_weights.keys()}

        normalized_weights = {symbol: weight / total_weight for symbol, weight in self.asset_weights.items()}
        return normalized_weights
