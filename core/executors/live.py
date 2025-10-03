import pandas as pd
import time
import asyncio # for future async HantooClient
import os
from datetime import datetime

from .base import BaseExecutor
from ..strategies.base import BaseStrategy
from ..data_providers import LiveDataContext
from ..api_clients.hantoo_client import HantooClient
from ..utils.market_schedule import is_market_open_time

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

        # 0. Check Market Schedule
        if not is_market_open_time():
            print("[INFO] Market is closed. LiveExecutor will skip this run.")
            return

        # 1. Get current account status
        # Note: balance_info should reflect pending orders if possible, but HantooClient doesn't support it yet.
        balance_info = self.client.get_balance()
        if not balance_info:
            print("[ERROR] Could not get account balance. Aborting LiveExecutor run.")
            return

        total_value = balance_info['total_value']
        current_holdings = {h['symbol']: h for h in balance_info['holdings']}
        
        # Keep track of current cash available for buying within this run,
        # considering orders already placed within this run.
        available_cash_for_this_run = balance_info['cash']

        # 2. Get target portfolio from the strategy
        # For live trading, we always use the current date.
        now = pd.Timestamp.now()
        target_weights = self.strategy.generate_signals(now, self.data_context)
        
        if target_weights is None:
            print("[INFO] Strategy returned no signals. Nothing to do.")
            return

        print(f"[INFO] Target weights: {target_weights}")

        # 2.5 Get open orders (pending) to prevent double spending
        try:
            open_orders = self.client.get_open_orders()
            print(f"[INFO] Open orders: {len(open_orders)} found.")
        except Exception as e:
            print(f"[ERROR] Failed to fetch open orders. Aborting run for safety. Error: {e}")
            return

        # Aggregate open order quantities by symbol and side
        pending_buys = {}
        pending_sells = {}
        for order in open_orders:
            sym = order['symbol']
            qty = order['quantity']
            if order['side'] == 'buy':
                pending_buys[sym] = pending_buys.get(sym, 0) + qty
            elif order['side'] == 'sell':
                pending_sells[sym] = pending_sells.get(sym, 0) + qty

        # 3. Determine trades to be executed
        trades_to_execute = []
        all_symbols = set(current_holdings.keys()) | set(target_weights.keys())

        # For accurate target value calculation, fetch current prices for all relevant symbols first
        current_prices_fetched = {}
        for symbol in all_symbols:
            price_dict = self.data_context.get_current_prices([symbol])
            price = price_dict.get(symbol)
            if price:
                current_prices_fetched[symbol] = price
            else:
                print(f"[WARNING] Could not get price for {symbol}. Will try to proceed with 0 if no price.")
                current_prices_fetched[symbol] = 0 # Assume 0 if price fetch fails

        for symbol in all_symbols:
            current_qty = current_holdings.get(symbol, {}).get('quantity', 0)
            current_price = current_prices_fetched.get(symbol, 0)
            
            if current_price <= 0:
                print(f"[WARNING] Skipping trade for {symbol} due to invalid current price ({current_price}).")
                continue

            current_value = current_qty * current_price
            target_value = total_value * target_weights.get(symbol, 0)
            
            value_diff = target_value - current_value
            quantity_diff = value_diff / current_price

            # Consider minimum tradable quantity or value (e.g., 1 share, or minimum trade amount)
            # KIS API for domestic stock usually allows fractional shares for selling, but buying is integer.
            # For simplicity, convert to int for now.
            if abs(quantity_diff) < 1: # Only trade whole shares for now
                continue

            # Check minimum trade value
            if abs(value_diff) < 1000: # Minimum trade value (e.g., 1000 KRW) to avoid tiny trades
                continue
            
            # Ensure quantity is positive for buy/sell
            raw_quantity = int(abs(quantity_diff))
            if raw_quantity == 0:
                continue

            if quantity_diff > 0: # Buy Signal
                # Adjust for pending buys
                pending_buy_qty = pending_buys.get(symbol, 0)
                final_buy_qty = raw_quantity - pending_buy_qty
                
                if final_buy_qty > 0:
                    trades_to_execute.append({'side': 'buy', 'symbol': symbol, 'quantity': final_buy_qty})
                elif pending_buy_qty > 0:
                    print(f"[INFO] Skipping BUY for {symbol}. Target: {raw_quantity}, Pending: {pending_buy_qty}. Already covered.")

            elif quantity_diff < 0: # Sell Signal
                # Adjust for pending sells
                pending_sell_qty = pending_sells.get(symbol, 0)
                final_sell_qty = raw_quantity - pending_sell_qty

                if final_sell_qty > 0:
                    trades_to_execute.append({'side': 'sell', 'symbol': symbol, 'quantity': final_sell_qty})
                elif pending_sell_qty > 0:
                    print(f"[INFO] Skipping SELL for {symbol}. Target: {raw_quantity}, Pending: {pending_sell_qty}. Already covered.")

        # 4. Execute trades (sell first, then buy) with smart error handling
        print(f"[INFO] Trades to execute: {trades_to_execute}")
        
        # Process Sells
        sells = [t for t in trades_to_execute if t['side'] == 'sell']
        for trade in sells:
            symbol = trade['symbol']
            quantity = trade['quantity']
            
            price = current_prices_fetched.get(symbol) # Use pre-fetched price
            if not price or price <= 0:
                print(f"[ERROR] Cannot place SELL order for {symbol}: invalid price {price}. Skipping.")
                continue

            print(f"[INFO] Attempting to SELL {quantity} shares of {symbol} at Market Price")
            order_result = self.client.place_order(symbol, quantity, 0, 'sell', order_type='market')
            
            if order_result and order_result.get('status') == 'success':
                print(f"[SUCCESS] SELL order for {symbol} placed. Result: {order_result}")
                # Optimistically update holdings for subsequent calculations in this run (if any)
                # Not strictly needed since next run will fetch fresh balance, but good practice.
            else:
                error_msg = order_result.get('message', 'Unknown error') if order_result else 'No response'
                if "초당 거래건수를 초과" in error_msg:
                    print(f"[RATE_LIMIT_ERROR] SELL order for {symbol} failed due to rate limit. Waiting 5 seconds. Error: {error_msg}")
                    time.sleep(5) # Severe delay for rate limit error
                else:
                    print(f"[ERROR] SELL order for {symbol} failed. Error: {error_msg}. Skipping this trade.")
                # Important: Do not re-attempt order within this run. Next scheduler cycle will try again.


        # Process Buys
        buys = [t for t in trades_to_execute if t['side'] == 'buy']
        for trade in buys:
            symbol = trade['symbol']
            quantity = trade['quantity']
            
            price = current_prices_fetched.get(symbol) # Use pre-fetched price
            if not price or price <= 0:
                print(f"[ERROR] Cannot place BUY order for {symbol}: invalid price {price}. Skipping.")
                continue

            # Double-check available_cash_for_this_run before buying
            estimated_cost = quantity * price * 1.005 # Factor in ~0.5% for commission/fees for safety
            if available_cash_for_this_run < estimated_cost:
                print(f"[WARNING] Skipping BUY order for {symbol} due to insufficient estimated cash. Need ~{estimated_cost:.0f}, Have {available_cash_for_this_run:.0f}.")
                continue

            print(f"[INFO] Attempting to BUY {quantity} shares of {symbol} at Market Price")
            order_result = self.client.place_order(symbol, quantity, 0, 'buy', order_type='market')

            if order_result and order_result.get('status') == 'success':
                print(f"[SUCCESS] BUY order for {symbol} placed. Result: {order_result}")
                available_cash_for_this_run -= estimated_cost # Optimistically update cash for this run
            else:
                error_msg = order_result.get('message', 'Unknown error') if order_result else 'No response'
                if "초당 거래건수를 초과" in error_msg:
                    print(f"[RATE_LIMIT_ERROR] BUY order for {symbol} failed due to rate limit. Waiting 5 seconds. Error: {error_msg}")
                    time.sleep(5) # Severe delay for rate limit error
                else:
                    print(f"[ERROR] BUY order for {symbol} failed. Error: {error_msg}. Skipping this trade.")
                # Important: Do not re-attempt order within this run. Next scheduler cycle will try again.

        print("--- LiveExecutor run finished ---")