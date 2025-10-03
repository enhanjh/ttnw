
import pandas as pd
from typing import Dict

from .base import BaseStrategy, DataContext

class FundamentalIndicatorStrategy(BaseStrategy):
    """
    A strategy that dynamically selects stocks based on fundamental indicators.
    It screens and ranks assets from a universe and re-evaluates periodically.
    """
    def __init__(self, strategy_params: Dict):
        super().__init__(strategy_params)
        self.region = self.params.get('fundamental_data_region', 'KR')
        self.conditions = self.params.get('fundamental_conditions', [])
        self.ranking_metric = self.params.get('ranking_metric', 'Marcap')
        self.ranking_order = self.params.get('ranking_order', 'desc')
        self.top_n = self.params.get('top_n', 20)
        self.re_evaluation_frequency = self.params.get('re_evaluation_frequency', 'quarterly')
        self.last_rebalance_date = None

    def _is_re_evaluation_date(self, date: pd.Timestamp) -> bool:
        """ Checks if the current date is a re-evaluation point. """
        if self.last_rebalance_date is None:
            return True
        if self.re_evaluation_frequency == 'quarterly':
            return (date.month - 1) // 3 != (self.last_rebalance_date.month - 1) // 3
        if self.re_evaluation_frequency == 'annual':
            return date.year != self.last_rebalance_date.year
        return False

    def on_tick(self, tick_data: Dict):
        """Fundamental Indicator does not react to individual ticks."""
        pass

        """
        Generates signals by screening and ranking the asset universe.
        If it's not a re-evaluation date, it returns the last computed signals.
        """
        if not self._is_re_evaluation_date(date):
            return self.last_signals

        print(f"--- Re-evaluating FundamentalIndicatorStrategy on {date.date()} ---")
        self.last_rebalance_date = date

        # 1. Get asset universe
        universe_df = data_context.get_asset_universe(date, self.region, top_n=self.top_n, ranking_metric=self.ranking_metric)
        if universe_df.empty:
            return self.last_signals # Return old signals if universe is not available

        # 2. Screen assets
        qualified_assets = []
        for _, row in universe_df.iterrows():
            symbol = row['Code'] # Assuming 'Code' column for symbol
            fundamental_data = data_context.get_fundamental_data(symbol, date)
            if not fundamental_data:
                continue

            # This is a simplified placeholder for the condition evaluation logic
            # A full implementation would parse `self.conditions` and apply them.
            # For now, let's assume a simple condition: positive EPS.
            if fundamental_data.get('eps', 0) > 0:
                rank_value = fundamental_data.get(self.ranking_metric, 0)
                qualified_assets.append({'symbol': symbol, 'rank_value': rank_value})

        if not qualified_assets:
            # If no assets qualify, go to cash
            self.last_signals = {}
            return self.last_signals

        # 3. Rank and select top N
        reverse_sort = (self.ranking_order == 'desc')
        sorted_assets = sorted(qualified_assets, key=lambda x: x['rank_value'], reverse=reverse_sort)
        top_assets = [item['symbol'] for item in sorted_assets[:self.top_n]]

        # 4. Generate equal-weight signals
        if not top_assets:
            self.last_signals = {}
            return self.last_signals
            
        weight_per_asset = 1.0 / len(top_assets)
        target_weights = {symbol: weight_per_asset for symbol in top_assets}
        
        self.last_signals = target_weights
        return self.last_signals
