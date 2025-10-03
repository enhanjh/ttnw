import os
from fredapi import Fred
import pandas as pd
import numpy as np
from typing import List, Dict, Callable, Optional
from uuid import UUID

from .data_collector import get_historical_data, get_fred_yield_curve
from .database import get_portfolio_assets
from .portfolio_calculator import calculate_portfolio_value, calculate_returns, calculate_cumulative_returns, calculate_volatility, calculate_max_drawdown

class BacktestingEngine:
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.portfolio_history = []
        self.transactions = []

    async def run_backtest(self, strategy_details, start_date, end_date, portfolio_id: UUID = None, debug: bool = False):
        debug_logs = []
        
        fred_api_key = os.getenv("FRED_API_KEY")
        if strategy_details.strategy_type == "momentum" and not fred_api_key:
            return {"error": "FRED_API_KEY environment variable not set for Momentum strategy."}

        assets = []
        if portfolio_id:
            assets = await get_portfolio_assets(portfolio_id)
            symbol_to_asset_map = {asset.symbol: asset for asset in assets}
        else:
            symbol_to_asset_map = {}

        symbols = list(strategy_details.parameters['asset_weights'].keys()) if strategy_details.strategy_type != "momentum" else strategy_details.parameters.get('asset_pool', [])
        if not symbols:
            return {"error": "Strategy has no asset weights or asset pool defined."}

        historical_data = {}
        for symbol in symbols:
            data = get_historical_data(symbol, start_date, end_date)
            if not data.empty:
                historical_data[symbol] = data
            else:
                return {"error": f"No historical data found for symbol {symbol}."}

        if not historical_data:
            return {"error": "No historical data available for backtesting."}

        all_dates = []
        for symbol, df in historical_data.items():
            all_dates.extend(df.index.tolist())
        if not all_dates:
            return {"error": "No common dates for historical data."}

        trading_days = pd.to_datetime(sorted(list(set(all_dates)))).normalize()
        trading_days = trading_days[(trading_days >= pd.to_datetime(start_date)) & (trading_days <= pd.to_datetime(end_date))]

        price_data = pd.DataFrame({symbol: df['Close'] for symbol, df in historical_data.items()})
        price_data.index = pd.to_datetime(price_data.index)
        price_data = price_data.reindex(trading_days, method='ffill').bfill()

        if price_data.empty or price_data.isnull().all().all():
            return {"error": "Historical data is empty or contains only missing values after processing."}

        current_holdings = {symbol: 0.0 for symbol in symbols}
        current_cash = self.initial_capital
        self.transactions = []

        last_rebalance_date = None
        daily_portfolio_values = []

        for date in trading_days:
            current_prices = {}
            for symbol in symbols:
                price = np.nan
                if symbol in historical_data and date in historical_data[symbol].index:
                    price = historical_data[symbol].loc[date]['Close']
                
                if pd.isna(price) or price <= 0:
                    if symbol in historical_data and not historical_data[symbol][historical_data[symbol].index < date].empty:
                        prev_day_data = historical_data[symbol][historical_data[symbol].index < date]
                        if not prev_day_data.empty:
                            prev_price = prev_day_data.iloc[-1]['Close']
                            if pd.notna(prev_price) and prev_price > 0:
                                price = prev_price
                
                current_prices[symbol] = price

            daily_transactions = []

            if strategy_details.strategy_type == "buy_and_hold":
                buy_hold_transactions = self._execute_buy_and_hold(strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map)
                daily_transactions.extend(buy_hold_transactions)
            
            elif strategy_details.strategy_type == "rebalancing":
                rebalance_needed = False
                if strategy_details.parameters['rebalancing_frequency'] == 'monthly':
                    if last_rebalance_date is None or date.month != last_rebalance_date.month:
                        rebalance_needed = True
                elif strategy_details.parameters['rebalancing_frequency'] == 'quarterly':
                    if last_rebalance_date is None or (date.month - 1) // 3 != (last_rebalance_date.month - 1) // 3:
                        rebalance_needed = True
                elif strategy_details.parameters['rebalancing_frequency'] == 'annual':
                    if last_rebalance_date is None or date.year != last_rebalance_date.year:
                        rebalance_needed = True

                if rebalance_needed:
                    rebalance_transactions = self._execute_rebalancing(strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map, debug_logs if debug else None)
                    daily_transactions.extend(rebalance_transactions)
                    last_rebalance_date = date

            elif strategy_details.strategy_type == "momentum":
                rebalance_needed = False
                if strategy_details.parameters['rebalancing_frequency'] == 'monthly':
                    if last_rebalance_date is None or date.month != last_rebalance_date.month:
                        rebalance_needed = True
                # Add other frequencies if needed

                if rebalance_needed:
                    momentum_transactions = self._execute_momentum_strategy(strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map, fred_api_key, debug_logs if debug else None)
                    daily_transactions.extend(momentum_transactions)
                    last_rebalance_date = date

            elif strategy_details.strategy_type == "moving_average_crossover":
                pass

            for t in daily_transactions:
                symbol = t['symbol']
                transaction_type = t['type']
                quantity = t['quantity']
                price = t['price']

                if transaction_type == 'buy':
                    cost = quantity * price
                    if current_cash >= cost:
                        current_holdings[symbol] += quantity
                        current_cash -= cost
                        portfolio_value = current_cash + sum(qty * current_prices.get(s, 0) for s, qty in current_holdings.items() if s in current_prices and pd.notna(current_prices[s]))
                        self.transactions.append({
                            'asset': {'symbol': symbol},
                            'transaction_type': 'buy',
                            'quantity': quantity,
                            'price': price,
                            'transaction_date': date,
                            'cash_balance': current_cash,
                            'portfolio_value': portfolio_value
                        })
                    else:
                        if debug:
                            debug_logs.append(f"Not enough cash to buy {quantity} of {symbol} on {date.date()}")
                elif transaction_type == 'sell':
                    if current_holdings[symbol] >= quantity:
                        revenue = quantity * price
                        current_holdings[symbol] -= quantity
                        current_cash += revenue
                        portfolio_value = current_cash + sum(qty * current_prices.get(s, 0) for s, qty in current_holdings.items() if s in current_prices and pd.notna(current_prices[s]))
                        self.transactions.append({
                            'asset': {'symbol': symbol},
                            'transaction_type': 'sell',
                            'quantity': quantity,
                            'price': price,
                            'transaction_date': date,
                            'cash_balance': current_cash,
                            'portfolio_value': portfolio_value
                        })
                    else:
                        if debug:
                            debug_logs.append(f"Not enough {symbol} to sell {quantity} on {date.date()}")

            current_portfolio_value = current_cash + sum(qty * current_prices.get(s, 0) for s, qty in current_holdings.items() if s in current_prices and pd.notna(current_prices[s]))
            daily_portfolio_values.append({'Date': date, 'Value': current_portfolio_value})

        portfolio_value_df = pd.DataFrame(daily_portfolio_values)
        if portfolio_value_df.empty:
            return {"error": "No portfolio value generated."}

        portfolio_value_df['Date'] = pd.to_datetime(portfolio_value_df['Date'])
        portfolio_value_df = portfolio_value_df.set_index('Date').sort_index()
        portfolio_value_df['FormattedDate'] = portfolio_value_df.index.strftime('%Y-%m-%d')

        returns = calculate_returns(portfolio_value_df.reset_index()) if not portfolio_value_df.empty else pd.Series()
        cumulative_returns = calculate_cumulative_returns(returns) if not returns.empty else pd.Series()

        annualized_return, volatility, max_drawdown, sharpe_ratio = 0, 0, 0, 0
        if not returns.empty:
            total_return = (portfolio_value_df['Value'].iloc[-1] / self.initial_capital) - 1
            annualized_return = (1 + total_return)**(252 / len(returns)) - 1 if len(returns) > 0 else 0
            volatility = calculate_volatility(returns, annualization_factor=252)
            max_drawdown = calculate_max_drawdown(cumulative_returns)
            sharpe_ratio = annualized_return / volatility if volatility != 0 else 0

        strategy_dict = strategy_details.model_dump()
        strategy_dict['id'] = str(strategy_details.id)

        return {
            "strategy": strategy_dict,
            "returns": returns.to_dict(),
            "cumulative_returns": cumulative_returns.to_dict(),
            "portfolio_value": daily_portfolio_values,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "final_capital": current_cash + sum(current_holdings[s] * current_prices.get(s, 0) for s in current_holdings),
            "transactions": self.transactions,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe_ratio,
            "debug_logs": debug_logs
        }

    def _execute_buy_and_hold(self, strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map: Dict[str, any]):
        transactions = []
        if all(qty == 0 for qty in current_holdings.values()) and current_cash > 0:
            total_weight = sum(strategy_details.parameters['asset_weights'].values())
            if total_weight == 0:
                return transactions

            local_cash = current_cash
            initial_capital_for_weights = current_cash

            for symbol, weight in strategy_details.parameters['asset_weights'].items():
                if symbol in current_prices and pd.notna(current_prices[symbol]) and current_prices[symbol] > 0:
                    capital_to_allocate = initial_capital_for_weights * (weight / total_weight)
                    min_trade_qty = symbol_to_asset_map.get(symbol, {}).minimum_tradable_quantity if symbol_to_asset_map.get(symbol) else 1.0
                    quantity_to_buy = capital_to_allocate / current_prices[symbol]
                    if min_trade_qty > 0:
                        quantity_to_buy = (quantity_to_buy // min_trade_qty) * min_trade_qty

                    cost = quantity_to_buy * current_prices[symbol]
                    if quantity_to_buy > 0 and local_cash >= cost:
                        transactions.append({
                            'symbol': symbol,
                            'type': 'buy',
                            'quantity': quantity_to_buy,
                            'price': current_prices[symbol]
                        })
                        local_cash -= cost
        return transactions

    def _execute_rebalancing(self, strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map: Dict[str, any], debug_logs: List[str] = None):
        transactions = []
        target_weights = strategy_details.parameters['asset_weights']
        rebalancing_threshold = strategy_details.parameters.get('rebalancing_threshold', 0.0) or 0.0

        current_portfolio_value = current_cash + sum(current_holdings[s] * current_prices.get(s, 0) for s in current_holdings if s in current_prices and pd.notna(current_prices[s]))
        
        if debug_logs is not None:
            debug_logs.append(f"--- Rebalancing Debug on {date.date()} ---")
            debug_logs.append(f"Portfolio Value before rebalance: {current_portfolio_value:,.0f}")

        if current_portfolio_value == 0:
            if debug_logs is not None:
                debug_logs.append("Portfolio value is 0. Skipping rebalance.")
                debug_logs.append(f"--- End Rebalancing Debug ---")
            return transactions

        current_weights = {}
        for symbol in current_holdings:
            if symbol in current_prices and pd.notna(current_prices[symbol]) and current_prices[symbol] > 0:
                current_weights[symbol] = (current_holdings[symbol] * current_prices[symbol]) / current_portfolio_value
            else:
                current_weights[symbol] = 0.0
        
        if debug_logs is not None:
            debug_logs.append("Current State:")
            debug_logs.append(f"  Cash: {current_cash:,.0f}")
            for s in sorted(current_holdings.keys()):
                val = current_holdings.get(s, 0) * current_prices.get(s, 0)
                weight = current_weights.get(s, 0.0)
                debug_logs.append(f"  - {s}: {current_holdings.get(s, 0):.4f} shares @ {current_prices.get(s, 0):,.2f} = {val:,.0f} (Weight: {weight:.2%})")

        is_initial_buy = all(qty == 0 for qty in current_holdings.values())

        if debug_logs is not None:
            debug_logs.append("\nRebalancing Decisions:")
        
        for symbol, target_weight in target_weights.items():
            if debug_logs is not None:
                debug_logs.append(f"  Checking Symbol: {symbol}")
            if symbol not in current_prices or pd.isna(current_prices[symbol]) or current_prices[symbol] <= 0:
                if debug_logs is not None: debug_logs.append(f"    -> Skipping: No valid price.")
                continue

            current_weight = current_weights.get(symbol, 0.0)
            deviation = abs(current_weight - target_weight)
            
            if debug_logs is not None:
                debug_logs.append(f"    - Target Weight : {target_weight:.2%}")
                debug_logs.append(f"    - Current Weight: {current_weight:.2%}")
                debug_logs.append(f"    - Deviation     : {deviation:.2%}")
                debug_logs.append(f"    - Threshold     : {rebalancing_threshold:.2%}")

            min_trade_qty = symbol_to_asset_map.get(symbol, {}).minimum_tradable_quantity if symbol_to_asset_map.get(symbol) else 1.0

            if is_initial_buy or deviation > rebalancing_threshold:
                target_value = current_portfolio_value * target_weight
                current_value = current_holdings.get(symbol, 0) * current_prices[symbol]
                
                if debug_logs is not None:
                    debug_logs.append(f"    => REBALANCE TRIGGERED (Initial Buy: {is_initial_buy}, Deviation > Threshold: {deviation > rebalancing_threshold})")
                    debug_logs.append(f"    - Target Value  : {target_value:,.0f}")
                    debug_logs.append(f"    - Current Value : {current_value:,.0f}")

                if target_value > current_value:
                    amount_to_buy_value = target_value - current_value
                    quantity_to_buy = amount_to_buy_value / current_prices[symbol]
                    if debug_logs is not None: debug_logs.append(f"    - Action: BUY {amount_to_buy_value:,.0f} worth")

                    if min_trade_qty > 0:
                        quantity_to_buy = (quantity_to_buy // min_trade_qty) * min_trade_qty
                    
                    cost = quantity_to_buy * current_prices[symbol]
                    if quantity_to_buy > 0 and current_cash >= cost:
                        if debug_logs is not None: debug_logs.append(f"    - Transaction: BUY {quantity_to_buy:.4f} shares of {symbol} for {cost:,.0f}")
                        transactions.append({'symbol': symbol, 'type': 'buy', 'quantity': quantity_to_buy, 'price': current_prices[symbol]})
                        current_cash -= cost
                    elif debug_logs is not None:
                        debug_logs.append(f"    - SKIPPED BUY (Not enough cash or zero quantity)")

                elif target_value < current_value:
                    amount_to_sell_value = current_value - target_value
                    quantity_to_sell = amount_to_sell_value / current_prices[symbol]
                    if debug_logs is not None: debug_logs.append(f"    - Action: SELL {amount_to_sell_value:,.0f} worth")

                    if min_trade_qty > 0:
                        quantity_to_sell = (quantity_to_sell // min_trade_qty) * min_trade_qty

                    if quantity_to_sell > 0 and current_holdings.get(symbol, 0) >= quantity_to_sell:
                        revenue = quantity_to_sell * current_prices[symbol]
                        if debug_logs is not None: debug_logs.append(f"    - Transaction: SELL {quantity_to_sell:.4f} shares of {symbol} for {revenue:,.0f}")
                        transactions.append({'symbol': symbol, 'type': 'sell', 'quantity': quantity_to_sell, 'price': current_prices[symbol]})
                        current_cash += revenue
                    elif debug_logs is not None:
                        debug_logs.append(f"    - SKIPPED SELL (Not enough shares or zero quantity)")
            elif debug_logs is not None:
                debug_logs.append(f"    => No rebalance needed (deviation within threshold).")
        
        if debug_logs is not None:
            debug_logs.append(f"--- End Rebalancing Debug ---\n")
        return transactions

    def _execute_momentum_strategy(self, strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map: Dict[str, any], fred_api_key: str, debug_logs: List[str] = None) -> List[Dict]:
        transactions = []
        asset_pool = strategy_details.parameters.get('asset_pool', [])
        lookback_period_months = strategy_details.parameters.get('lookback_period_months', 6) # Default to 6 months
        top_n_assets = strategy_details.parameters.get('top_n_assets', 1) # Default to top 1 asset
        risk_free_asset_ticker = strategy_details.parameters.get('risk_free_asset_ticker', 'DGS1') # Default to DGS1 (1-Year Treasury)

        if debug_logs is not None:
            debug_logs.append(f"--- Momentum Strategy Debug on {date.date()} ---")
            debug_logs.append(f"  Asset Pool: {asset_pool}")
            debug_logs.append(f"  Lookback Period: {lookback_period_months} months")
            debug_logs.append(f"  Top N Assets: {top_n_assets}")
            debug_logs.append(f"  Risk-Free Asset: {risk_free_asset_ticker}")

        # 1. Calculate lookback start date
        lookback_start_date = (date - pd.DateOffset(months=lookback_period_months)).strftime('%Y-%m-%d')
        current_date_str = date.strftime('%Y-%m-%d')

        # 2. Fetch risk-free rate
        risk_free_rate = 0.0
        try:
            fred_df = get_fred_yield_curve(api_key=fred_api_key, start_date=lookback_start_date, end_date=current_date_str)
            if not fred_df.empty and risk_free_asset_ticker in fred_df.columns:
                # Get the latest available risk-free rate for the current date or previous business day
                latest_rate = fred_df[risk_free_asset_ticker].dropna().iloc[-1] if not fred_df[risk_free_asset_ticker].dropna().empty else 0.0
                risk_free_rate = latest_rate
            if debug_logs is not None: debug_logs.append(f"  Fetched Risk-Free Rate ({risk_free_asset_ticker}): {risk_free_rate:.4f}")
        except Exception as e:
            if debug_logs is not None: debug_logs.append(f"  Error fetching FRED data for risk-free rate: {e}")
            # Continue with risk_free_rate = 0.0 if fetching fails

        # 3. Calculate returns for each asset in the pool
        asset_returns = {}
        for symbol in asset_pool:
            if symbol in historical_data:
                asset_df = historical_data[symbol]
                # Ensure enough data for lookback period
                if len(asset_df[asset_df.index >= lookback_start_date]) > 0:
                    start_price = asset_df[asset_df.index >= lookback_start_date]['Close'].iloc[0]
                    end_price = asset_df[asset_df.index <= current_date_str]['Close'].iloc[-1]
                    if pd.notna(start_price) and pd.notna(end_price) and start_price > 0:
                        asset_returns[symbol] = (end_price / start_price) - 1
                    else:
                        if debug_logs is not None: debug_logs.append(f"  Skipping {symbol}: Invalid prices for return calculation.")
                else:
                    if debug_logs is not None: debug_logs.append(f"  Skipping {symbol}: Not enough historical data for lookback period.")
            else:
                if debug_logs is not None: debug_logs.append(f"  Skipping {symbol}: No historical data available.")
        
        if debug_logs is not None: debug_logs.append(f"  Calculated Asset Returns: {asset_returns}")

        # 4. Absolute Momentum Check (Risk-off)
        # If no assets have positive returns, or if top asset return is less than risk-free rate, go to cash
        go_to_cash = True
        if asset_returns:
            # Find the best performing asset
            best_asset = max(asset_returns, key=asset_returns.get)
            best_return = asset_returns[best_asset]
            if debug_logs is not None: debug_logs.append(f"  Best Asset: {best_asset} with Return: {best_return:.2%}")

            if best_return > risk_free_rate:
                go_to_cash = False
                if debug_logs is not None: debug_logs.append(f"  Absolute Momentum: POSITIVE (Best Return > Risk-Free Rate)")
            else:
                if debug_logs is not None: debug_logs.append(f"  Absolute Momentum: NEGATIVE (Best Return <= Risk-Free Rate). Going to cash.")
        else:
            if debug_logs is not None: debug_logs.append(f"  No valid asset returns. Going to cash.")

        # 5. Generate Transactions
        # Sell all current holdings first
        for symbol, quantity in current_holdings.items():
            if quantity > 0 and symbol in current_prices and pd.notna(current_prices[symbol]) and current_prices[symbol] > 0:
                revenue = quantity * current_prices[symbol]
                transactions.append({
                    'symbol': symbol,
                    'type': 'sell',
                    'quantity': quantity,
                    'price': current_prices[symbol]
                })
                current_cash += revenue # Simulate cash change
                current_holdings[symbol] = 0.0 # Simulate holdings change
                if debug_logs is not None: debug_logs.append(f"  Transaction: SELL ALL {symbol} ({quantity:.4f} shares)")

        if not go_to_cash:
            # Relative Momentum: Select top N assets
            sorted_assets = sorted(asset_returns.items(), key=lambda item: item[1], reverse=True)
            selected_assets = [asset for asset, ret in sorted_assets[:top_n_assets]]
            if debug_logs is not None: debug_logs.append(f"  Selected Top {top_n_assets} Assets: {selected_assets}")

            # Allocate cash to selected assets (equal weight for simplicity, or based on target weights if defined)
            if current_cash > 0 and selected_assets:
                capital_per_asset = current_cash / len(selected_assets)
                for symbol in selected_assets:
                    if symbol in current_prices and pd.notna(current_prices[symbol]) and current_prices[symbol] > 0:
                        quantity_to_buy = capital_per_asset / current_prices[symbol]
                        min_trade_qty = symbol_to_asset_map.get(symbol, {}).minimum_tradable_quantity if symbol_to_asset_map.get(symbol) else 1.0
                        if min_trade_qty > 0:
                            quantity_to_buy = (quantity_to_buy // min_trade_qty) * min_trade_qty
                        
                        cost = quantity_to_buy * current_prices[symbol]
                        if quantity_to_buy > 0 and current_cash >= cost:
                            transactions.append({
                                'symbol': symbol,
                                'type': 'buy',
                                'quantity': quantity_to_buy,
                                'price': current_prices[symbol]
                            })
                            current_cash -= cost # Simulate cash change
                            current_holdings[symbol] += quantity_to_buy # Simulate holdings change
                            if debug_logs is not None: debug_logs.append(f"  Transaction: BUY {quantity_to_buy:.4f} shares of {symbol} for {cost:,.0f}")
                        elif debug_logs is not None:
                            debug_logs.append(f"  Skipped BUY {symbol}: Not enough cash or zero quantity.")
                    elif debug_logs is not None:
                        debug_logs.append(f"  Skipped BUY {symbol}: Invalid price.")
            elif debug_logs is not None:
                debug_logs.append(f"  No cash to allocate or no assets selected.")
        else:
            if debug_logs is not None: debug_logs.append(f"  Strategy is in cash position. No assets to buy.")

        if debug_logs is not None:
            debug_logs.append(f"--- End Momentum Strategy Debug ---\n")
        return transactions
