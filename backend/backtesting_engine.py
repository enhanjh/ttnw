import os
from fredapi import Fred
import pandas as pd
import numpy as np
from typing import List, Dict, Callable, Optional
from uuid import UUID

from . import models
from .data_collector import get_historical_data, get_fred_yield_curve, get_korean_fundamental_data
from .portfolio_calculator import calculate_portfolio_value, calculate_returns, calculate_cumulative_returns, calculate_volatility, calculate_max_drawdown

class BacktestingEngine:
    def __init__(self, initial_capital: float = 100000000.0):
        self.initial_capital = initial_capital
        self.portfolio_history = []
        self.transactions = []

    def _fetch_and_calculate_benchmarks(self, start_date: str, end_date: str, initial_capital: float, debug_logs: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        benchmark_data = {}
        fred_api_key = os.getenv("FRED_API_KEY")

        # S&P 500
        try:
            sp500_df = get_historical_data("S&P500", start_date, end_date)
            if not sp500_df.empty:
                sp500_df = sp500_df.dropna(subset=['Close']).ffill()
                if not sp500_df.empty:
                    sp500_df['Date'] = sp500_df.index.strftime('%Y-%m-%d')
                    sp500_df['Value'] = (sp500_df['Close'] / sp500_df['Close'].iloc[0]) * initial_capital
                    benchmark_data["S&P 500"] = sp500_df[['Date', 'Value']].to_dict(orient='records')
                else:
                    if debug_logs is not None: debug_logs.append("Warning: S&P 500 data became empty after NaN handling.")
            else:
                if debug_logs is not None: debug_logs.append("Warning: No historical data for S&P 500.")
        except Exception as e:
            if debug_logs is not None: debug_logs.append(f"Error fetching S&P 500 data: {e}")

        # KOSPI (KS11)
        try:
            kospi_df = get_historical_data("KS11", start_date, end_date)
            if not kospi_df.empty:
                kospi_df = kospi_df.dropna(subset=['Close']).ffill()
                if not kospi_df.empty:
                    kospi_df['Date'] = kospi_df.index.strftime('%Y-%m-%d')
                    kospi_df['Value'] = (kospi_df['Close'] / kospi_df['Close'].iloc[0]) * initial_capital
                    benchmark_data["KOSPI"] = kospi_df[['Date', 'Value']].to_dict(orient='records')
                else:
                    if debug_logs is not None: debug_logs.append("Warning: KOSPI (KS11) data became empty after NaN handling.")
            else:
                if debug_logs is not None: debug_logs.append("Warning: No historical data for KOSPI (KS11).")
        except Exception as e:
            if debug_logs is not None: debug_logs.append(f"Error fetching KOSPI (KS11) data: {e}")

        # Nikkei 225 (N225)
        try:
            nikkei_df = get_historical_data("N225", start_date, end_date)
            if not nikkei_df.empty:
                nikkei_df = nikkei_df.dropna(subset=['Close']).ffill()
                if not nikkei_df.empty:
                    nikkei_df['Date'] = nikkei_df.index.strftime('%Y-%m-%d')
                    nikkei_df['Value'] = (nikkei_df['Close'] / nikkei_df['Close'].iloc[0]) * initial_capital
                    benchmark_data["Nikkei 225"] = nikkei_df[['Date', 'Value']].to_dict(orient='records')
                else:
                    if debug_logs is not None: debug_logs.append("Warning: Nikkei 225 (N225) data became empty after NaN handling.")
            else:
                if debug_logs is not None: debug_logs.append("Warning: No historical data for Nikkei 225 (N225).")
        except Exception as e:
            if debug_logs is not None: debug_logs.append(f"Error fetching Nikkei 225 (N225) data: {e}")

        return benchmark_data

    async def run_backtest(self, strategy_details, start_date, end_date, debug: bool = False):
        debug_logs = []
        
        fred_api_key = os.getenv("FRED_API_KEY")
        if strategy_details.strategy_type == "momentum" and not fred_api_key:
            return {"error": "FRED_API_KEY environment variable not set for Momentum strategy."}

        # Pre-fetch all required FRED data once to avoid rate limiting.
        fred_data_df = pd.DataFrame()
        if strategy_details.strategy_type == "momentum":
            try:
                fred_data_df = get_fred_yield_curve(api_key=fred_api_key, start_date=start_date, end_date=end_date)
                if fred_data_df.empty:
                    debug_logs.append(f"Warning: Pre-fetching FRED data returned no results for the backtest period.")
            except Exception as e:
                return {"error": f"Failed to pre-fetch FRED data: {e}"}

        # Pre-fetch fundamental data for fundamental_indicator strategy
        fundamental_data_cache = {}
        if strategy_details.strategy_type == "fundamental_indicator":
            opendart_api_key = os.getenv("OPENDART_API_KEY")
            if not opendart_api_key:
                return {"error": "OPENDART_API_KEY environment variable not set for Fundamental Indicator strategy."}

            fundamental_data_region = strategy_details.parameters.fundamental_data_region
            if not fundamental_data_region:
                return {"error": "Fundamental data region not specified for Fundamental Indicator strategy."}

            # Determine unique year/quarter combinations within the backtest period
            # This is a simplified approach; a more robust solution would handle monthly/daily data points
            # and map them to the correct quarterly/annual reports.
            unique_periods = set()
            for d in pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D')):
                year = d.year
                quarter = (d.month - 1) // 3 + 1 # 1-4
                unique_periods.add((year, quarter))
            
            for symbol in symbols:
                fundamental_data_cache[symbol] = {}
                for year, quarter in unique_periods:
                    if fundamental_data_region == "KR":
                        try:
                            data = get_korean_fundamental_data(symbol, opendart_api_key, year, quarter)
                            if data:
                                fundamental_data_cache[symbol][(year, quarter)] = data
                            else:
                                if debug_logs is not None: debug_logs.append(f"Warning: No fundamental data for {symbol} in {year} Q{quarter}.")
                        except Exception as e:
                            if debug_logs is not None: debug_logs.append(f"Error fetching fundamental data for {symbol} in {year} Q{quarter}: {e}")
                    elif fundamental_data_region == "US":
                        try:
                            data = get_us_fundamental_data(symbol, year, quarter)
                            if data:
                                fundamental_data_cache[symbol][(year, quarter)] = data
                            else:
                                if debug_logs is not None: debug_logs.append(f"Warning: No US fundamental data for {symbol} in {year} Q{quarter}.")
                        except Exception as e:
                            if debug_logs is not None: debug_logs.append(f"Error fetching US fundamental data for {symbol} in {year} Q{quarter}: {e}")
                    else:
                        return {"error": f"Unsupported fundamental data region: {fundamental_data_region}"}

            if not fundamental_data_cache:
                return {"error": "No fundamental data available for backtesting."}
        # Normalize strategy parameters for backtesting if the new format is used
        params = strategy_details.parameters
        if 'asset_weights' in params and params['asset_weights'] and isinstance(params['asset_weights'][0], dict):
            asset_list = params['asset_weights']
            if strategy_details.strategy_type == 'momentum':
                # For momentum, asset_pool is a list of tickers, and weights are not used.
                params['asset_pool'] = [item['asset'] for item in asset_list]
                # The engine still uses asset_weights to get all symbols, so create a dummy dict.
                params['asset_weights'] = {item['asset']: 0 for item in asset_list}
            else:
                # For other strategies, convert list of dicts to the dict format the engine expects.
                params['asset_weights'] = {item['asset']: item.get('weight', 0) for item in asset_list}

        symbols = list(strategy_details.parameters['asset_weights'].keys()) if strategy_details.strategy_type != "momentum" else strategy_details.parameters.get('asset_pool', [])
        if not symbols:
            return {"error": "Strategy has no asset weights or asset pool defined."}

        # Fetch asset metadata globally for all symbols in the strategy
        assets = await models.Asset.find({"symbol": {"$in": symbols}}).to_list()
        symbol_to_asset_map = {asset.symbol: asset for asset in assets}
        if not symbols:
            return {"error": "Strategy has no asset weights or asset pool defined."}

        # Adjust data fetch start date to account for lookback periods in strategies like momentum.
        data_fetch_start_date = start_date
        if strategy_details.strategy_type == 'momentum':
            lookback_months = strategy_details.parameters.get('lookback_period_months', 6)
            if lookback_months:
                earliest_date = pd.to_datetime(start_date) - pd.DateOffset(months=lookback_months)
                data_fetch_start_date = earliest_date.strftime('%Y-%m-%d')

        historical_data = {}
        for symbol in symbols:
            data = get_historical_data(symbol, data_fetch_start_date, end_date)
            if not data.empty:
                historical_data[symbol] = data
            else:
                # It might be okay for some symbols to have no data if the pool is large,
                # but for now, we'll treat it as an error.
                return {"error": f"No historical data found for symbol {symbol} in the given date range."}

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
            
            elif strategy_details.strategy_type == "asset_allocation":
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
                    momentum_transactions = self._execute_momentum_strategy(strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map, fred_data_df, debug_logs if debug else None)
                    daily_transactions.extend(momentum_transactions)
                    last_rebalance_date = date

            elif strategy_details.strategy_type == "moving_average_crossover":
                pass

            elif strategy_details.strategy_type == "fundamental_indicator":
                fundamental_transactions = self._execute_fundamental_value_strategy(strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map, fundamental_data_cache, debug_logs if debug else None)
                daily_transactions.extend(fundamental_transactions)

            # Process sell transactions first to free up cash
            sells = [t for t in daily_transactions if t['type'] == 'sell']
            for t in sells:
                symbol = t['symbol']
                quantity = t['quantity']
                price = t['price']
                if current_holdings.get(symbol, 0) >= quantity:
                    revenue = quantity * price
                    current_holdings[symbol] -= quantity
                    current_cash += revenue
                    portfolio_value = current_cash + sum(qty * current_prices.get(s, 0) for s, qty in current_holdings.items() if s in current_prices and pd.notna(current_prices[s]))
                    self.transactions.append({
                        'asset': {'symbol': symbol, 'name': symbol_to_asset_map.get(symbol, models.Asset(symbol=symbol, name="Unknown Asset", asset_type="UNKNOWN")).name},
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

            # Then, process buy transactions with the updated cash balance
            buys = [t for t in daily_transactions if t['type'] == 'buy']
            for t in buys:
                symbol = t['symbol']
                quantity = t['quantity']
                price = t['price']
                cost = quantity * price
                if current_cash >= cost:
                    current_holdings[symbol] += quantity
                    current_cash -= cost
                    portfolio_value = current_cash + sum(qty * current_prices.get(s, 0) for s, qty in current_holdings.items() if s in current_prices and pd.notna(current_prices[s]))
                    self.transactions.append({
                        'asset': {'symbol': symbol, 'name': symbol_to_asset_map.get(symbol, models.Asset(symbol=symbol, name="Unknown Asset", asset_type="UNKNOWN")).name},
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

        # Fetch and calculate benchmark data
        benchmark_data = self._fetch_and_calculate_benchmarks(start_date, end_date, self.initial_capital, debug_logs if debug else None)

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
            "debug_logs": debug_logs,
            "benchmark_data": benchmark_data
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
                    if quantity_to_buy > 0:
                        if debug_logs is not None: debug_logs.append(f"    - Proposing Transaction: BUY {quantity_to_buy:.4f} shares of {symbol} for {cost:,.0f}")
                        transactions.append({'symbol': symbol, 'type': 'buy', 'quantity': quantity_to_buy, 'price': current_prices[symbol]})
                    elif debug_logs is not None:
                        debug_logs.append(f"    - SKIPPED proposing BUY (zero quantity)")

                elif target_value < current_value:
                    amount_to_sell_value = current_value - target_value
                    quantity_to_sell = amount_to_sell_value / current_prices[symbol]
                    if debug_logs is not None: debug_logs.append(f"    - Action: SELL {amount_to_sell_value:,.0f} worth")

                    if min_trade_qty > 0:
                        quantity_to_sell = (quantity_to_sell // min_trade_qty) * min_trade_qty

                    if quantity_to_sell > 0:
                        revenue = quantity_to_sell * current_prices[symbol]
                        if debug_logs is not None: debug_logs.append(f"    - Proposing Transaction: SELL {quantity_to_sell:.4f} shares of {symbol} for {revenue:,.0f}")
                        transactions.append({'symbol': symbol, 'type': 'sell', 'quantity': quantity_to_sell, 'price': current_prices[symbol]})
                    elif debug_logs is not None:
                        debug_logs.append(f"    - SKIPPED SELL (Not enough shares or zero quantity)")
            elif debug_logs is not None:
                debug_logs.append(f"    => No rebalance needed (deviation within threshold).")
        
        if debug_logs is not None:
            debug_logs.append(f"--- End Rebalancing Debug ---\n")
        return transactions

    def _execute_momentum_strategy(self, strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map: Dict[str, any], fred_data: pd.DataFrame, debug_logs: List[str] = None) -> List[Dict]:
        transactions = []
        asset_pool = strategy_details.parameters.get('asset_pool', [])
        lookback_period_months = strategy_details.parameters.get('lookback_period_months', 6) # Default to 6 months
        top_n_assets = strategy_details.parameters.get('top_n_assets', 1) # Default to top 1 asset

        risk_free_asset_ticker = strategy_details.parameters.get('risk_free_asset_ticker')
        if not risk_free_asset_ticker: # Handles None or empty string
            risk_free_asset_ticker = 'DGS1'

        if debug_logs is not None:
            debug_logs.append(f"--- Momentum Strategy Debug on {date.date()} ---")
            debug_logs.append(f"  Asset Pool: {asset_pool}")
            debug_logs.append(f"  Lookback Period: {lookback_period_months} months")
            debug_logs.append(f"  Top N Assets: {top_n_assets}")
            debug_logs.append(f"  Risk-Free Asset: {risk_free_asset_ticker}")

        # 1. Calculate lookback start date
        lookback_start_date = (date - pd.DateOffset(months=lookback_period_months)).strftime('%Y-%m-%d')
        current_date_str = date.strftime('%Y-%m-%d')

        # 2. Look up risk-free rate from pre-fetched data
        risk_free_rate_annualized = 0.0 # Rename for clarity
        try:
            if not fred_data.empty and risk_free_asset_ticker in fred_data.columns:
                rates_up_to_date = fred_data.loc[fred_data.index <= date]
                if not rates_up_to_date.empty:
                    latest_rate = rates_up_to_date[risk_free_asset_ticker].dropna().iloc[-1] if not rates_up_to_date[risk_free_asset_ticker].dropna().empty else 0.0
                    risk_free_rate_annualized = latest_rate # FRED data is already in decimal form
            if debug_logs is not None: debug_logs.append(f"  Looked up Annualized Risk-Free Rate ({risk_free_asset_ticker}) for {date.date()}: {risk_free_rate_annualized:.4f}")
        except Exception as e:
            if debug_logs is not None: debug_logs.append(f"  Error looking up annualized risk-free rate from pre-fetched data: {e}")
            # Continue with risk_free_rate_annualized = 0.0 if an error occurs

        # Convert annualized risk-free rate to lookback period rate
        period_in_years = lookback_period_months / 12
        risk_free_rate = (1 + risk_free_rate_annualized)**period_in_years - 1
        if debug_logs is not None: debug_logs.append(f"  Converted Risk-Free Rate for {lookback_period_months} months: {risk_free_rate:.4f}")

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

        # 5. Generate Transactions based on rebalancing to target assets
        
        # Determine the target assets for this period
        target_assets = set()
        if not go_to_cash:
            sorted_assets = sorted(asset_returns.items(), key=lambda item: item[1], reverse=True)
            target_assets = {asset for asset, ret in sorted_assets[:top_n_assets]}

        if debug_logs is not None: debug_logs.append(f"  Target assets for this period: {list(target_assets)}")

        current_held_assets = {symbol for symbol, quantity in current_holdings.items() if quantity > 0}

        # If target portfolio is the same as current, no trades are needed.
        if target_assets == current_held_assets:
            if debug_logs: debug_logs.append("  Target is same as holdings. No rebalancing needed.")
            return transactions

        # --- Rebalancing Logic ---
        # Calculate current total portfolio value, which will be reallocated.
        current_portfolio_value = current_cash + sum(
            qty * current_prices.get(s, 0) for s, qty in current_holdings.items() if s in current_prices and pd.notna(current_prices[s])
        )

        # Determine target value for each asset in the new portfolio.
        target_value_per_asset = 0
        if target_assets:
            target_value_per_asset = current_portfolio_value / len(target_assets)

        # Generate trades by comparing current position to target position for all assets involved.
        all_involved_assets = current_held_assets.union(target_assets)

        for symbol in all_involved_assets:
            current_value = current_holdings.get(symbol, 0) * current_prices.get(symbol, 0)
            target_value = target_value_per_asset if symbol in target_assets else 0
            value_diff = target_value - current_value
            
            # Ignore negligible trades
            if abs(value_diff) < 0.01:
                continue

            price = current_prices.get(symbol)
            if not price or pd.isna(price) or price <= 0:
                if debug_logs: debug_logs.append(f"  Skipping trade for {symbol} due to invalid price.")
                continue

            quantity_diff = value_diff / price
            trade_type = 'buy' if quantity_diff > 0 else 'sell'
            
            min_trade_qty = symbol_to_asset_map.get(symbol, {}).minimum_tradable_quantity if symbol_to_asset_map.get(symbol) else 1.0
            
            abs_quantity = abs(quantity_diff)
            if min_trade_qty > 0:
                # Floor the quantity to the nearest tradable unit
                abs_quantity = (abs_quantity // min_trade_qty) * min_trade_qty

            if abs_quantity > 0:
                transactions.append({
                    'symbol': symbol,
                    'type': trade_type,
                    'quantity': abs_quantity,
                    'price': price
                })
                if debug_logs:
                    debug_logs.append(f"  Proposing to {trade_type.upper()} {abs_quantity:.4f} shares of {symbol}")

        if debug_logs is not None:
            debug_logs.append(f"--- End Momentum Strategy Debug ---\n")
        return transactions

    def _execute_fundamental_value_strategy(self, strategy_details, historical_data, current_holdings, current_cash, current_prices, date, symbol_to_asset_map: Dict[str, any], fundamental_data_cache: Dict, debug_logs: List[str] = None) -> List[Dict]:
        transactions = []
        
        if debug_logs is not None:
            debug_logs.append(f"--- Fundamental Value Strategy Debug on {date.date()} ---")
            debug_logs.append(f"  Strategy Parameters: {strategy_details.parameters.model_dump_json()}")

        fundamental_conditions = strategy_details.parameters.fundamental_conditions
        re_evaluation_frequency = strategy_details.parameters.re_evaluation_frequency
        fundamental_data_region = strategy_details.parameters.fundamental_data_region

        if not fundamental_conditions:
            if debug_logs is not None: debug_logs.append("  No fundamental conditions defined. Skipping strategy.")
            return transactions

        # Determine if re-evaluation is needed (simplified for now, assuming annual/quarterly)
        # A more robust implementation would track last re-evaluation date
        re_evaluate_this_period = False
        if re_evaluation_frequency == 'annual' and date.month == 1 and date.day == 1: # Re-evaluate on Jan 1st
            re_evaluate_this_period = True
        elif re_evaluation_frequency == 'quarterly' and date.day == 1 and date.month in [1, 4, 7, 10]: # Re-evaluate on Q1 start
            re_evaluate_this_period = True
        # If no re-evaluation needed, return empty transactions
        if not re_evaluate_this_period:
            if debug_logs is not None: debug_logs.append("  No re-evaluation needed this period.")
            return transactions

        # Get current quarter/year for fundamental data lookup
        current_year = date.year
        current_quarter = (date.month - 1) // 3 + 1

        # Collect all assets to consider (current holdings + asset pool from strategy)
        asset_pool = [item.asset for item in strategy_details.parameters.asset_weights] if strategy_details.parameters.asset_weights else []
        all_assets_to_consider = set(current_holdings.keys()).union(set(asset_pool))

        # Evaluate conditions for each asset
        assets_meeting_criteria = []
        for symbol in all_assets_to_consider:
            if symbol not in current_prices or pd.isna(current_prices[symbol]) or current_prices[symbol] <= 0:
                if debug_logs is not None: debug_logs.append(f"  Skipping {symbol}: No valid price for current date.")
                continue

            # Get fundamental data for the current period
            # Need to find the most recent available fundamental data for the current date
            # This is a simplified lookup; a robust solution would handle data availability and lag
            fundamental_data = fundamental_data_cache.get(symbol, {}).get((current_year, current_quarter))
            if fundamental_data is None:
                # Try previous quarter if current quarter data is not available
                prev_quarter = current_quarter - 1
                prev_year = current_year
                if prev_quarter == 0:
                    prev_quarter = 4
                    prev_year -= 1
                fundamental_data = fundamental_data_cache.get(symbol, {}).get((prev_year, prev_quarter))
            
            if fundamental_data is None:
                if debug_logs is not None: debug_logs.append(f"  Skipping {symbol}: No fundamental data found for {current_year} Q{current_quarter} or previous.")
                continue

            all_conditions_met = True
            for condition in fundamental_conditions:
                value_metric_val = 0.0
                if condition.value_metric == "net_current_asset_value":
                    current_assets = fundamental_data.get("current_assets", 0)
                    total_liabilities = fundamental_data.get("total_liabilities", 0)
                    value_metric_val = current_assets - total_liabilities
                else:
                    value_metric_val = fundamental_data.get(condition.value_metric)
                comparison_metric_val = 0.0
                if condition.comparison_metric == "constant":
                    comparison_metric_val = 1.0 # Use 1.0 as a base for the multiplier to act as the constant
                else:
                    comparison_metric_val = fundamental_data.get(condition.comparison_metric)
                
                # Handle market cap separately as it needs current price
                if condition.comparison_metric == "market_cap":
                    # Assuming shares outstanding is available in fundamental_data or Asset model
                    # For now, let's assume we can get shares outstanding from fundamental_data
                    shares_outstanding = fundamental_data.get("shares_outstanding", 0) # Placeholder
                    if shares_outstanding > 0 and current_prices.get(symbol, 0) > 0:
                        comparison_metric_val = current_prices[symbol] * shares_outstanding
                    else:
                        comparison_metric_val = 0 # Cannot calculate market cap
                
                if value_metric_val is None or comparison_metric_val is None:
                    if debug_logs is not None: debug_logs.append(f"  Skipping condition for {symbol}: Missing metric data ({condition.value_metric} or {condition.comparison_metric}).")
                    all_conditions_met = False
                    break

                # Evaluate the condition
                condition_met = False
                if condition.comparison_operator == '>':
                    condition_met = value_metric_val > (comparison_metric_val * condition.comparison_multiplier)
                elif condition.comparison_operator == '<':
                    condition_met = value_metric_val < (comparison_metric_val * condition.comparison_multiplier)
                elif condition.comparison_operator == '>=':
                    condition_met = value_metric_val >= (comparison_metric_val * condition.comparison_multiplier)
                elif condition.comparison_operator == '<=':
                    condition_met = value_metric_val <= (comparison_metric_val * condition.comparison_multiplier)
                elif condition.comparison_operator == '=':
                    condition_met = value_metric_val == (comparison_metric_val * condition.comparison_multiplier)
                
                if not condition_met:
                    all_conditions_met = False
                    break
            
            if all_conditions_met:
                assets_meeting_criteria.append(symbol)
                if debug_logs is not None: debug_logs.append(f"  {symbol} meets all fundamental criteria.")
            else:
                if debug_logs is not None: debug_logs.append(f"  {symbol} does NOT meet all fundamental criteria.")

        # Generate transactions based on criteria
        # Sell assets no longer meeting criteria
        for symbol in current_holdings.keys():
            if current_holdings[symbol] > 0 and symbol not in assets_meeting_criteria:
                if symbol in current_prices and pd.notna(current_prices[symbol]) and current_prices[symbol] > 0:
                    transactions.append({
                        'symbol': symbol,
                        'type': 'sell',
                        'quantity': current_holdings[symbol], # Sell all
                        'price': current_prices[symbol]
                    })
                    if debug_logs is not None: debug_logs.append(f"  Proposing SELL all {symbol} (no longer meets criteria).")
                else:
                    if debug_logs is not None: debug_logs.append(f"  Skipping SELL for {symbol}: No valid price.")

        # Buy assets meeting criteria (if not already held or not enough)
        # This is a simplified allocation: allocate remaining cash equally among qualifying assets
        qualifying_assets_to_buy = [s for s in assets_meeting_criteria if s not in current_holdings or current_holdings[s] == 0]
        if qualifying_assets_to_buy and current_cash > 0:
            cash_per_asset = current_cash / len(qualifying_assets_to_buy)
            for symbol in qualifying_assets_to_buy:
                if symbol in current_prices and pd.notna(current_prices[symbol]) and current_prices[symbol] > 0:
                    min_trade_qty = symbol_to_asset_map.get(symbol, {}).minimum_tradable_quantity if symbol_to_asset_map.get(symbol) else 1.0
                    quantity_to_buy = cash_per_asset / current_prices[symbol]
                    if min_trade_qty > 0:
                        quantity_to_buy = (quantity_to_buy // min_trade_qty) * min_trade_qty
                    
                    if quantity_to_buy > 0:
                        transactions.append({
                            'symbol': symbol,
                            'type': 'buy',
                            'quantity': quantity_to_buy,
                            'price': current_prices[symbol]
                        })
                        if debug_logs is not None: debug_logs.append(f"  Proposing BUY {quantity_to_buy:.4f} shares of {symbol}.")
                else:
                    if debug_logs is not None: debug_logs.append(f"  Skipping BUY for {symbol}: No valid price.")

        if debug_logs is not None:
            debug_logs.append(f"--- End Fundamental Value Strategy Debug ---\n")
        return transactions
