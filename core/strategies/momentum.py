
import pandas as pd
from typing import Dict, List

from .base import BaseStrategy, DataContext

class MomentumStrategy(BaseStrategy):
    """
    A strategy that invests in assets with the strongest recent performance (momentum).
    It combines relative momentum (ranking assets) and absolute momentum (checking against a risk-free asset).
    """
    def __init__(self, strategy_params: Dict):
        """
        Args:
            strategy_params (Dict): Expected keys:
                - 'asset_pool': A list of symbols to consider for investment.
                - 'lookback_period_months': The number of months to look back to calculate returns.
                - 'top_n_assets': The number of top-performing assets to invest in.
                - 'risk_free_asset_ticker': The ticker for the risk-free asset (e.g., 'DGS1' for 1-Year Treasury).
        """
        super().__init__(strategy_params)
        # Set default values for parameters if they are not provided
        self.asset_pool = self.params.get('asset_pool', [])
        self.lookback_months = self.params.get('lookback_period_months', 6)
        self.top_n = self.params.get('top_n_assets', 1)
        self.risk_free_ticker = self.params.get('risk_free_asset_ticker', 'DGS1')

        if not self.asset_pool:
            raise ValueError("MomentumStrategy requires 'asset_pool' in strategy_params.")

    def on_tick(self, tick_data: Dict):
        """Momentum does not react to individual ticks."""
        pass

        """
        Generates trading signals based on momentum.
        """
        # 1. Get historical data for the asset pool and the risk-free asset
        all_symbols = self.asset_pool + [self.risk_free_ticker]
        historical_data = data_context.get_historical_data(all_symbols, date, self.lookback_months * 31) # Approx days

        # 2. Calculate returns for each asset in the pool
        asset_returns = {}
        for symbol in self.asset_pool:
            if symbol in historical_data and not historical_data[symbol].empty:
                series = historical_data[symbol]['Close']
                if len(series) > 1:
                    start_price = series.iloc[0]
                    end_price = series.iloc[-1]
                    if pd.notna(start_price) and pd.notna(end_price) and start_price > 0:
                        asset_returns[symbol] = (end_price / start_price) - 1

        if not asset_returns:
            return {symbol: 0.0 for symbol in self.asset_pool} # Go to cash if no returns data

        # 3. Get the risk-free rate for the lookback period
        risk_free_return = 0.0
        if self.risk_free_ticker in historical_data and not historical_data[self.risk_free_ticker].empty:
            rf_series = historical_data[self.risk_free_ticker]['Close']
            if len(rf_series) > 1:
                # FRED data is typically an annualized rate, needs conversion
                annualized_rate = rf_series.iloc[-1] / 100.0 # Convert from percentage to decimal
                period_in_years = self.lookback_months / 12.0
                risk_free_return = (1 + annualized_rate)**period_in_years - 1

        # 4. Absolute Momentum Check: invest only if the top asset's return > risk-free return
        best_asset = max(asset_returns, key=asset_returns.get)
        if asset_returns[best_asset] < risk_free_return:
            return {symbol: 0.0 for symbol in self.asset_pool} # Go to cash

        # 5. Relative Momentum: Rank assets by return and select the top N
        sorted_assets = sorted(asset_returns.items(), key=lambda item: item[1], reverse=True)
        top_assets = [asset for asset, ret in sorted_assets[:self.top_n]]

        # 6. Generate equal-weight signals for the top assets
        target_weights = {symbol: 0.0 for symbol in self.asset_pool}
        if top_assets:
            weight_per_asset = 1.0 / len(top_assets)
            for symbol in top_assets:
                target_weights[symbol] = weight_per_asset
        
        return target_weights
