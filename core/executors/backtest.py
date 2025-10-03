import pandas as pd
from typing import Dict
from beanie import PydanticObjectId

from .base import BaseExecutor
from ..strategies.base import DataContext, BaseStrategy
from ..data_providers import BacktestDataContext
from backend import models

class BacktestExecutor(BaseExecutor):
    """
    Executes a strategy against historical data to simulate performance.
    """
    def __init__(self, strategy: BaseStrategy, data_context: DataContext, backtest_result_id: PydanticObjectId, virtual_portfolio_id: PydanticObjectId, initial_capital: float = 1000000.0, commission_pct: float = 0.0, slippage_pct: float = 0.0, debug: bool = False):
        self.strategy = strategy
        self.data_context = data_context
        self.backtest_result_id = backtest_result_id # Store backtest_result_id
        self.virtual_portfolio_id = virtual_portfolio_id # Store virtual_portfolio_id
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.debug = debug # debug 인자를 인스턴스 속성으로 저장

        self.cash = initial_capital
        
        # Extract symbols from asset_weights list for initial holdings
        raw_weights = strategy.params.get('asset_weights', [])
        initial_symbols = []
        if isinstance(raw_weights, list):
            for item in raw_weights:
                asset = getattr(item, 'asset', None) or (item.get('asset') if isinstance(item, dict) else None)
                if asset:
                    initial_symbols.append(asset)
        elif isinstance(raw_weights, dict):
             initial_symbols = list(raw_weights.keys())

        self.holdings = {symbol: 0.0 for symbol in initial_symbols}
        self.transactions_log = [] # New: Store virtual transactions in memory
        self.debug_logs = [] # New: Collect debug logs
        # self.portfolio_history = [] # Remove this
        # self.transactions = [] # Remove this

    async def run(self, start_date: str, end_date: str, rebalancing_frequency: str = 'monthly'):
        """
        Runs the backtest simulation.

        Args:
            start_date (str): The start date of the backtest (YYYY-MM-DD).
            end_date (str): The end date of the backtest (YYYY-MM-DD).
            rebalancing_frequency (str): How often to rebalance (e.g., 'daily', 'monthly').
        """
        self.start_date = start_date
        self.end_date = end_date

        # Determine the universe of symbols from the strategy parameters
        symbols = []
        if hasattr(self.strategy.params, 'asset_pool') and self.strategy.params.get('asset_pool'):
            symbols = self.strategy.params.get('asset_pool', [])
        elif self.strategy.params.get('asset_weights'):
            # Extract symbols from asset_weights list
            raw_weights = self.strategy.params.get('asset_weights', [])
            if isinstance(raw_weights, list):
                for item in raw_weights:
                    asset = getattr(item, 'asset', None) or (item.get('asset') if isinstance(item, dict) else None)
                    if asset:
                        symbols.append(asset)
            elif isinstance(raw_weights, dict):
                symbols = list(raw_weights.keys())
        
        # For momentum, we also need the risk-free asset
        if hasattr(self.strategy, 'risk_free_ticker'):
            if self.strategy.risk_free_ticker not in symbols:
                symbols.append(self.strategy.risk_free_ticker)

        # If symbols are predefined, fetch all data at once.
        # If not (e.g., fundamental strategy), symbols will be discovered dynamically.
        if symbols:
            historical_data = self.data_context.get_historical_data_by_range(symbols, start_date, end_date)
            if not historical_data:
                self.debug_logs.append("Error: No historical data available for the given symbols and date range.")
                return None
            
            price_df = pd.DataFrame({sym: df['Close'] for sym, df in historical_data.items()})
            price_df.index = pd.to_datetime(price_df.index)
            price_df = price_df.ffill().bfill()
        else:
            # For dynamic universe strategies, we can't pre-fetch all data.
            # This part of the logic needs to be more dynamic, fetching data as needed.
            # For now, we will handle this by fetching data for the whole universe, which can be slow.
            # A better implementation would be to fetch data on demand.
            self.debug_logs.append("Warning: No initial symbols provided. This may be slow for dynamic universe strategies.")
            # As a temporary workaround, we will not pre-populate price_df
            price_df = pd.DataFrame()
            historical_data = {}

        trading_days = pd.date_range(start=start_date, end=end_date, freq='B') # Business days
        last_rebalance_date = None

        for date in trading_days:
            # --- Dynamic data fetching for strategies without predefined symbols ---
            if price_df.empty or date not in price_df.index:
                # This is a simplified logic. A robust implementation would be needed here.
                # For now, we assume that generate_signals will trigger data fetching via the context.
                pass

            # Generate new signals from the strategy at each rebalance point
            target_weights = self.strategy.generate_signals(date, self.data_context)

            # If target_weights is None (e.g. not a rebalance day), skip
            if target_weights is None:
                # Need to still calculate portfolio value with last prices
                # if not price_df.empty and date in price_df.index:
                #     current_prices = price_df.loc[date].to_dict()
                #     portfolio_value = self.cash + sum(self.holdings.get(s, 0) * current_prices.get(s, 0) for s in self.holdings if s in current_prices)
                #     self.portfolio_history.append({'Date': date, 'Value': portfolio_value})
                continue

            # Dynamically add new symbols to our dataframes
            new_symbols = [s for s in target_weights.keys() if s not in price_df.columns]
            if new_symbols:
                new_data = self.data_context.get_historical_data_by_range(new_symbols, start_date, end_date)
                for sym, df in new_data.items():
                    historical_data[sym] = df
                    price_df[sym] = df['Close']
                price_df = price_df.ffill().bfill()

            if date not in price_df.index:
                continue # Skip if no pricing data for the day

            current_prices = price_df.loc[date].to_dict()

            # --- Rebalancing Logic ---
            rebalance_needed = self._check_rebalance_needed(date, last_rebalance_date, rebalancing_frequency)

            if rebalance_needed:
                await self._rebalance_portfolio(date, target_weights, current_prices) # Await this call
                last_rebalance_date = date

            # --- Record Daily Portfolio Value ---
            # portfolio_value = self.cash + sum(self.holdings.get(s, 0) * current_prices.get(s, 0) for s in self.holdings if s in current_prices)
            # self.portfolio_history.append({'Date': date, 'Value': portfolio_value})

        # No longer calls _generate_results()
        return {
            "backtest_result_id": self.backtest_result_id,
            "virtual_portfolio_id": self.virtual_portfolio_id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "transactions_log": self.transactions_log, # New: Return the collected transactions
            "debug_logs": self.debug_logs, # Return collected debug logs
        }

    def _check_rebalance_needed(self, current_date, last_rebalance_date, frequency):
        if last_rebalance_date is None: # Initial buy
            return True
        if frequency == 'daily':
            return True
        if frequency == 'monthly' and current_date.month != last_rebalance_date.month:
            return True
        if frequency == 'quarterly' and (current_date.month - 1) // 3 != (last_rebalance_date.month - 1) // 3:
            return True
        # Add other frequencies as needed
        return False

    async def _rebalance_portfolio(self, date: pd.Timestamp, target_weights: Dict[str, float], current_prices: Dict[str, float]):
        """Core logic to adjust the portfolio to match target weights."""
        portfolio_value = self.cash + sum(self.holdings[s] * current_prices.get(s, 0) for s in self.holdings)

        for symbol, target_weight in target_weights.items():
            price = current_prices.get(symbol)
            if price is None or price <= 0:
                continue

            target_value = portfolio_value * target_weight
            current_value = self.holdings.get(symbol, 0) * price
            quantity_diff = (target_value - current_value) / price

            if quantity_diff > 0: # Buy
                # 수수료와 슬리피지를 고려하여 매수 가능한 최대 수량을 계산
                # target_value = quantity * (price + slippage_cost) + quantity * (price + slippage_cost) * commission_pct
                # target_value = quantity * (price * (1 + slippage_pct) * (1 + commission_pct))
                # quantity = target_value / (price * (1 + slippage_pct) * (1 + commission_pct))
                effective_price_per_share = price * (1 + self.slippage_pct) * (1 + self.commission_pct)
                if effective_price_per_share > 0:
                    max_buy_quantity = target_value / effective_price_per_share
                    quantity_to_buy = min(quantity_diff, max_buy_quantity)
                    if quantity_to_buy > 0:
                        await self._execute_trade(date, symbol, 'buy', quantity_to_buy, price)
            elif quantity_diff < 0: # Sell
                await self._execute_trade(date, symbol, 'sell', abs(quantity_diff), price)

    async def _execute_trade(self, date: pd.Timestamp, symbol: str, trade_type: str, quantity: float, price: float):
        """Simulates a single trade, including commission and slippage, and saves it as a VirtualTransaction."""
        if self.debug:
            self.debug_logs.append(f"[DEBUG] _execute_trade called: Date={date.strftime('%Y-%m-%d')}, Symbol={symbol}, Type={trade_type}, Quantity={quantity:.4f}, Price={price:.2f}")

        # Fetch asset_id for the symbol. This is a simplification; in a real system,
        # assets would be pre-loaded or fetched more robustly.
        asset = await models.Asset.find_one(models.Asset.symbol == symbol)
        if not asset:
            # Create a dummy asset for backtesting if it doesn't exist
            asset = models.Asset(symbol=symbol, name=symbol, asset_type="stock_us") # Default to stock_us
            await asset.insert()
            if self.debug:
                self.debug_logs.append(f"[DEBUG] Created dummy asset for {symbol} in backtest.")

        if trade_type == 'buy':
            slippage_cost = price * self.slippage_pct
            effective_price = price + slippage_cost
            cost = quantity * effective_price
            commission = cost * self.commission_pct
            total_cost = cost + commission

            if self.debug:
                self.debug_logs.append(f"[DEBUG]   Buy details: Effective Price={effective_price:.2f}, Cost={cost:.2f}, Commission={commission:.2f}, Total Cost={total_cost:.2f}, Current Cash={self.cash:.2f}")

            if self.cash >= total_cost:
                self.cash -= total_cost
                self.holdings[symbol] += quantity
                
                # Save VirtualTransaction to DB
                virtual_transaction = models.VirtualTransaction(
                    asset_id=asset.id,
                    portfolio_id=self.virtual_portfolio_id,
                    backtest_result_id=self.backtest_result_id,
                    transaction_type=trade_type,
                    quantity=quantity,
                    price=effective_price,
                    fee=commission,
                    tax=0.0, # Assuming no tax for buy in backtest
                    transaction_date=date
                )
                self.transactions_log.append(virtual_transaction) # Append to log instead of inserting to DB

                if self.debug:
                    self.debug_logs.append(f"[DEBUG]   BUY executed. New Cash={self.cash:.2f}, Holdings[{symbol}]={self.holdings[symbol]:.4f}")
            else:
                if self.debug:
                    self.debug_logs.append(f"[DEBUG]   BUY failed: Not enough cash. Needed {total_cost:.2f}, Have {self.cash:.2f}")

        elif trade_type == 'sell':
            slippage_cost = price * self.slippage_pct
            effective_price = price - slippage_cost
            revenue = quantity * effective_price
            commission = revenue * self.commission_pct
            total_revenue = revenue - commission

            if self.debug:
                self.debug_logs.append(f"[DEBUG]   Sell details: Effective Price={effective_price:.2f}, Revenue={revenue:.2f}, Commission={commission:.2f}, Total Revenue={total_revenue:.2f}, Current Holdings[{symbol}]={self.holdings.get(symbol, 0):.4f}")

            if self.holdings.get(symbol, 0) >= quantity:
                self.cash += total_revenue
                self.holdings[symbol] -= quantity

                # Save VirtualTransaction to DB
                virtual_transaction = models.VirtualTransaction(
                    asset_id=asset.id,
                    portfolio_id=self.virtual_portfolio_id,
                    backtest_result_id=self.backtest_result_id,
                    transaction_type=trade_type,
                    quantity=quantity,
                    price=effective_price,
                    fee=commission,
                    tax=0.0, # Assuming no tax for sell in backtest
                    transaction_date=date
                )
                self.transactions_log.append(virtual_transaction) # Append to log instead of inserting to DB

                if self.debug:
                    self.debug_logs.append(f"[DEBUG]   SELL executed. New Cash={self.cash:.2f}, Holdings[{symbol}]={self.holdings[symbol]:.4f}")
            else:
                if self.debug:
                    self.debug_logs.append(f"[DEBUG]   SELL failed: Not enough holdings. Needed {quantity:.4f}, Have {self.holdings.get(symbol, 0):.4f}")
