import pandas as pd

from .base import BaseExecutor
from ..strategies.base import BaseStrategy
from ..data_providers import LiveDataContext
from ..api_clients.hantoo_client import HantooClient

class LiveExecutor(BaseExecutor):
    """
    Executes a strategy in a live trading environment.
    """
    def __init__(self, strategy: BaseStrategy, broker_provider: str, broker_account_no: str):
        self.strategy = strategy
        self.client = HantooClient(broker_provider, broker_account_no)
        self.data_context = LiveDataContext(self.client)

    def run(self):
        """
        Runs a single iteration of the live execution logic.
        This method is intended to be called periodically by a scheduler (e.g., Celery Beat).
        """
        print("--- Running LiveExecutor ---")
        # 1. Get current account status
        balance_info = self.client.get_balance()
        if not balance_info:
            print("Could not get account balance. Aborting.")
            return

        total_value = balance_info['total_value']
        current_holdings = {h['symbol']: h for h in balance_info['holdings']}

        # 2. Get target portfolio from the strategy
        # For live trading, we always use the current date.
        now = pd.Timestamp.now()
        target_weights = self.strategy.generate_signals(now, self.data_context)
        
        if target_weights is None:
            print("Strategy returned no signals. Nothing to do.")
            return

        print(f"Target weights: {target_weights}")

        # 3. Determine trades to be executed
        trades_to_execute = []
        all_symbols = set(current_holdings.keys()) | set(target_weights.keys())

        for symbol in all_symbols:
            current_qty = current_holdings.get(symbol, {}).get('quantity', 0)
            current_price = self.data_context.get_current_prices([symbol])[symbol]
            if not current_price:
                print(f"Could not get price for {symbol}. Skipping.")
                continue

            current_value = current_qty * current_price
            target_value = total_value * target_weights.get(symbol, 0)
            
            value_diff = target_value - current_value
            quantity_diff = value_diff / current_price

            if abs(value_diff) < 1000: # Minimum trade value to avoid tiny trades
                continue

            if quantity_diff > 0:
                trades_to_execute.append({'side': 'buy', 'symbol': symbol, 'quantity': int(quantity_diff)})
            elif quantity_diff < 0:
                trades_to_execute.append({'side': 'sell', 'symbol': symbol, 'quantity': int(abs(quantity_diff))})

        # 4. Execute trades (sell first, then buy)
        print(f"Trades to execute: {trades_to_execute}")
        sells = [t for t in trades_to_execute if t['side'] == 'sell']
        for trade in sells:
            # For live trading, we might want to use market orders or more complex logic.
            # For now, we place a limit order at the current price.
            price = self.data_context.get_current_prices([trade['symbol']])
            if price:
                self.client.place_order(trade['symbol'], trade['quantity'], int(price[trade['symbol']]), 'sell')

        # In a real scenario, we should wait for sells to confirm before buying.
        # For this example, we proceed directly.

        buys = [t for t in trades_to_execute if t['side'] == 'buy']
        for trade in buys:
            price = self.data_context.get_current_prices([trade['symbol']])
            if price:
                self.client.place_order(trade['symbol'], trade['quantity'], int(price[trade['symbol']]), 'buy')

        print("--- LiveExecutor run finished ---")
