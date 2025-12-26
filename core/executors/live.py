import pandas as pd
import time
import logging
from datetime import datetime

from .base import BaseExecutor
from .order_manager import OrderManager
from ..strategies.base import BaseStrategy
from ..data_providers import LiveDataContext
from ..utils.market_schedule import is_market_open_time
from backend.models import Portfolio

# Configure logging to use local time
logging.Formatter.converter = time.localtime
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class LiveExecutor(BaseExecutor):
    """
    Executes a strategy in a live trading environment and records transactions via backend API.
    Uses OrderManager for actual trade execution and recording.
    """
    def __init__(self, strategy: BaseStrategy, broker_provider: str, broker_account_no: str):
        self.strategy = strategy
        self.broker_provider = broker_provider
        self.broker_account_no = broker_account_no
        
        # Initialize OrderManager to handle trades and recording
        self.order_manager = OrderManager(broker_provider, broker_account_no)
        
        # Reuse the client from order_manager for data fetching
        self.client = self.order_manager.client
        self.data_context = LiveDataContext(self.client)

    async def run(self):
        """
        Runs a single iteration of the live execution logic.
        Checks rebalancing frequency and threshold before executing trades.
        """
        logger.info("--- Running LiveExecutor ---")

        # 0. Check Market Schedule
        if not is_market_open_time():
            logger.info("Market is closed. LiveExecutor will skip this run.")
            return

        # 1. Get current account status
        # TODO: Make HantooClient async and await this call
        balance_info = self.client.get_balance()
        if not balance_info:
            logger.error("Could not get account balance. Aborting LiveExecutor run.")
            return

        total_value = balance_info['total_value']
        current_holdings = {h['symbol']: h for h in balance_info['holdings']}
        
        available_cash_for_this_run = balance_info['cash']

        logger.info(f"Total Value: {total_value:.0f}, Cash: {available_cash_for_this_run:.0f}, Holdings Count: {len(current_holdings)} assets")
        if current_holdings:
            for symbol, holding in current_holdings.items():
                logger.info(f"  - {symbol}: {holding['quantity']} shares @ {holding['average_price']:.0f} (Value: {holding['eval_amount']:.0f})")

        # 2. Get target portfolio from the strategy
        now = pd.Timestamp.now()
        target_weights = self.strategy.generate_signals(now, self.data_context)
        
        if target_weights is None:
            logger.info("Strategy returned no signals. Nothing to do.")
            return

        logger.info(f"Target weights: {target_weights}")

        # --- Rebalancing Condition Check ---
        portfolio_doc = await Portfolio.find_one(
            Portfolio.broker_provider == self.broker_provider,
            Portfolio.broker_account_no == self.broker_account_no
        )
        
        if not portfolio_doc:
            logger.error(f"Could not find portfolio document for {self.broker_account_no}. Aborting.")
            return

        rebalancing_frequency = self.strategy.params.get('rebalancing_frequency', 'monthly')
        rebalancing_threshold = float(self.strategy.params.get('rebalancing_threshold', 0.05)) # Default 5%

        # 1. Calculate Max Drift first
        max_drift = 0.0
        all_symbols_check = set(current_holdings.keys()) | set(target_weights.keys())
        for sym in all_symbols_check:
            target_w = target_weights.get(sym, 0)
            
            # Calculate current weight
            current_holding = current_holdings.get(sym)
            current_val = current_holding['eval_amount'] if current_holding else 0
            current_w = current_val / total_value if total_value > 0 else 0
            
            drift = abs(current_w - target_w)
            if drift > max_drift: 
                max_drift = drift

        # 2. Check Time Schedule
        last_rebal = portfolio_doc.last_rebalanced_at
        is_time_due = False
        
        if not last_rebal or rebalancing_frequency == 'always':
            is_time_due = True # First run or 'always' mode is always due
        else:
            days_since = (datetime.now() - last_rebal).days
            if rebalancing_frequency == 'daily' and days_since >= 1: is_time_due = True
            elif rebalancing_frequency == 'weekly' and days_since >= 7: is_time_due = True
            elif rebalancing_frequency == 'monthly' and days_since >= 28: is_time_due = True
            elif rebalancing_frequency == 'quarterly' and days_since >= 90: is_time_due = True

        # 3. Decision Logic
        should_trade = False
        should_update_timestamp = False
        reason = ""

        if is_time_due:
            # If it's time, we mark the schedule as "checked" (reset timer)
            should_update_timestamp = True
            
            if rebalancing_frequency == 'always':
                 # 'always' mode implies we check aggressively. 
                 if max_drift > rebalancing_threshold or rebalancing_threshold == 0:
                     should_trade = True
                     reason = f"Freq: always & Drift {max_drift:.2%} > {rebalancing_threshold:.2%}"
                 else:
                     reason = f"Freq: always but Drift {max_drift:.2%} <= {rebalancing_threshold:.2%} (Skipping)"
            
            # Normal periodic schedule
            elif max_drift > rebalancing_threshold or rebalancing_threshold == 0:
                should_trade = True
                reason = f"Scheduled ({rebalancing_frequency}) & Drift {max_drift:.2%} > {rebalancing_threshold:.2%}"
            else:
                should_trade = False
                reason = f"Scheduled ({rebalancing_frequency}) but Drift {max_drift:.2%} <= {rebalancing_threshold:.2%} (Skipping)"
        
        elif max_drift > rebalancing_threshold:
            # Off-schedule but threshold exceeded
            should_trade = True
            should_update_timestamp = True
            reason = f"Threshold Exceeded: Drift {max_drift:.2%} > {rebalancing_threshold:.2%}"

        if not should_trade:
            logger.info(f"No rebalancing needed. Reason: {reason if reason else 'Drift stable & Not scheduled'}. Last: {last_rebal}")
            if should_update_timestamp and portfolio_doc:
                # We update timestamp even if we didn't trade, to reset the schedule
                portfolio_doc.last_rebalanced_at = datetime.now()
                await portfolio_doc.save()
                logger.info(f"Updated last_rebalanced_at to {portfolio_doc.last_rebalanced_at} (Schedule Check Completed)")
            return

        logger.info(f"Rebalancing Triggered. Reason: {reason}")
        # -----------------------------------

        # 2.5 Get open orders (pending) to prevent double spending
        try:
            # TODO: Make HantooClient async and await this call
            open_orders = self.client.get_open_orders()
            logger.info(f"Open orders: {len(open_orders)} found.")
        except Exception as e:
            logger.error(f"Failed to fetch open orders. Aborting run for safety. Error: {e}")
            return

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

        current_prices_fetched = {}
        for symbol in all_symbols:
            # TODO: Make data_context async and await this call
            price_dict = self.data_context.get_current_prices([symbol])
            price = price_dict.get(symbol)
            if price:
                current_prices_fetched[symbol] = price
            else:
                logger.warning(f"Could not get price for {symbol}. Will try to proceed with 0 if no price.")
                current_prices_fetched[symbol] = 0

        for symbol in all_symbols:
            current_qty = current_holdings.get(symbol, {}).get('quantity', 0)
            current_price = current_prices_fetched.get(symbol, 0)
            
            if current_price <= 0:
                logger.warning(f"Skipping trade for {symbol} due to invalid current price ({current_price}).")
                continue

            current_value = current_qty * current_price
            target_value = total_value * target_weights.get(symbol, 0)
            
            value_diff = target_value - current_value
            quantity_diff = value_diff / current_price

            if abs(quantity_diff) < 1:
                logger.info(f"Skipping {symbol}: Quantity diff {quantity_diff:.2f} < 1")
                continue

            if abs(value_diff) < 1000:
                logger.info(f"Skipping {symbol}: Value diff {value_diff:.0f} < 1000 KRW")
                continue
            
            raw_quantity = int(abs(quantity_diff))
            if raw_quantity == 0:
                continue

            if quantity_diff > 0: # Buy Signal
                pending_buy_qty = pending_buys.get(symbol, 0)
                final_buy_qty = raw_quantity - pending_buy_qty
                
                if final_buy_qty > 0:
                    trades_to_execute.append({'side': 'buy', 'symbol': symbol, 'quantity': final_buy_qty})
                elif pending_buy_qty > 0:
                    logger.info(f"Skipping BUY for {symbol}. Target: {raw_quantity}, Pending: {pending_buy_qty}. Already covered.")

            elif quantity_diff < 0: # Sell Signal
                pending_sell_qty = pending_sells.get(symbol, 0)
                final_sell_qty = raw_quantity - pending_sell_qty

                if final_sell_qty > 0:
                    trades_to_execute.append({'side': 'sell', 'symbol': symbol, 'quantity': final_sell_qty})
                elif pending_sell_qty > 0:
                    logger.info(f"Skipping SELL for {symbol}. Target: {raw_quantity}, Pending: {pending_sell_qty}. Already covered.")

        # 4. Execute trades (sell first, then buy) via OrderManager
        logger.info(f"Trades to execute: {trades_to_execute}")
        
        # Track if we actually did anything
        executed_any = False
        
        sells = [t for t in trades_to_execute if t['side'] == 'sell']
        for trade in sells:
            symbol = trade['symbol']
            quantity = trade['quantity']
            
            price = current_prices_fetched.get(symbol)
            if not price or price <= 0:
                logger.error(f"Cannot place SELL order for {symbol}: invalid price {price}. Skipping.")
                continue

            logger.info(f"Attempting to SELL {quantity} shares of {symbol} at Market Price")
            
            # Use OrderManager to execute
            result = await self.order_manager.execute_order(symbol, quantity, price, 'sell', order_type='market')
            
            if result['status'] == 'success':
                logger.info(f"SELL executed for {symbol}.")
                executed_any = True
            else:
                error_msg = result.get('message', 'Unknown error')
                if "초당 거래건수를 초과" in error_msg:
                    logger.error(f"SELL for {symbol} hit rate limit. Waiting 5s.")
                    time.sleep(5)
                else:
                    logger.error(f"SELL for {symbol} failed: {error_msg}")

        buys = [t for t in trades_to_execute if t['side'] == 'buy']
        for trade in buys:
            symbol = trade['symbol']
            quantity = trade['quantity']
            
            price = current_prices_fetched.get(symbol)
            if not price or price <= 0:
                logger.error(f"Cannot place BUY order for {symbol}: invalid price {price}. Skipping.")
                continue

            estimated_cost = quantity * price * 1.005
            if available_cash_for_this_run < estimated_cost:
                logger.warning(f"Skipping BUY order for {symbol} due to insufficient estimated cash. Need ~{estimated_cost:.0f}, Have {available_cash_for_this_run:.0f}.")
                continue

            logger.info(f"Attempting to BUY {quantity} shares of {symbol} at Market Price")
            
            # Use OrderManager to execute
            result = await self.order_manager.execute_order(symbol, quantity, price, 'buy', order_type='market')

            if result['status'] == 'success':
                logger.info(f"BUY executed for {symbol}.")
                available_cash_for_this_run -= estimated_cost
                executed_any = True
            else:
                error_msg = result.get('message', 'Unknown error')
                if "초당 거래건수를 초과" in error_msg:
                    logger.error(f"BUY for {symbol} hit rate limit. Waiting 5s.")
                    time.sleep(5)
                else:
                    logger.error(f"BUY for {symbol} failed: {error_msg}")

        # Update last_rebalanced_at if logic triggered and we processed the run
        # Note: Even if trades_to_execute was empty (e.g. drift < 1000 won), we consider the check done.
        # However, strictly speaking, we might only want to update if we *could* have traded or if the check passed.
        # Since 'should_rebalance' was True, we have officially 'performed' a rebalancing act (even if result was "do nothing").
        if portfolio_doc:
            portfolio_doc.last_rebalanced_at = datetime.now()
            await portfolio_doc.save()
            logger.info(f"Updated last_rebalanced_at to {portfolio_doc.last_rebalanced_at}")

        logger.info("--- LiveExecutor run finished ---")