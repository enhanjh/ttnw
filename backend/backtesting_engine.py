import pandas as pd
from typing import List, Dict, Callable

from .data_collector import get_stock_data
from .portfolio_calculator import calculate_portfolio_value, calculate_returns, calculate_cumulative_returns, calculate_volatility, calculate_max_drawdown

class BacktestingEngine:
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.portfolio_history = []
        self.transactions = []

    def run_backtest(
        self,
        strategy: Callable[[pd.DataFrame, Dict[str, float], float], List[Dict]],
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict:
        """
        Runs a backtest for a given strategy.
        :param strategy: A function that implements the trading strategy.
                         It should take (historical_data, current_holdings, current_cash) and return a list of transactions.
        :param symbols: List of stock symbols to backtest.
        :param start_date: Start date for historical data and backtest.
        :param end_date: End date for historical data and backtest.
        :return: Dictionary containing backtest results (portfolio value, returns, etc.).
        """
        historical_data = {}
        for symbol in symbols:
            data = get_stock_data(symbol, start_date, end_date)
            if not data.empty:
                historical_data[symbol] = data
            else:
                print(f"Warning: No data found for {symbol}. Skipping.")

        if not historical_data:
            return {"error": "No historical data available for backtesting."}

        # Get a common date range for all available data
        all_dates = []
        for symbol, df in historical_data.items():
            all_dates.extend(df.index.tolist())
        if not all_dates:
            return {"error": "No common dates for historical data."}

        trading_days = pd.to_datetime(sorted(list(set(all_dates)))).normalize()
        trading_days = trading_days[(trading_days >= pd.to_datetime(start_date)) & (trading_days <= pd.to_datetime(end_date))]

        current_holdings = {symbol: 0.0 for symbol in symbols}
        current_cash = self.initial_capital
        self.transactions = [] # Reset transactions for each backtest run

        daily_portfolio_values = []

        for date in trading_days:
            # Get current day's prices
            current_prices = {}
            for symbol in symbols:
                if symbol in historical_data and date in historical_data[symbol].index:
                    current_prices[symbol] = historical_data[symbol].loc[date]['Close']
                else:
                    # Use previous day's price if current day's price is not available
                    prev_day_data = historical_data[symbol][historical_data[symbol].index < date]
                    if not prev_day_data.empty:
                        current_prices[symbol] = prev_day_data.iloc[-1]['Close']
                    else:
                        current_prices[symbol] = 0.0 # Or handle as error

            # Execute strategy for the current day
            daily_transactions = strategy(historical_data, current_holdings, current_cash, current_prices, date)

            # Process transactions
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
                        self.transactions.append({
                            'asset': {'symbol': symbol}, # Mock asset for portfolio_calculator
                            'transaction_type': 'buy',
                            'quantity': quantity,
                            'price': price,
                            'transaction_date': date
                        })
                    else:
                        print(f"Not enough cash to buy {quantity} of {symbol} on {date.date()}")
                elif transaction_type == 'sell':
                    if current_holdings[symbol] >= quantity:
                        revenue = quantity * price
                        current_holdings[symbol] -= quantity
                        current_cash += revenue
                        self.transactions.append({
                            'asset': {'symbol': symbol}, # Mock asset for portfolio_calculator
                            'transaction_type': 'sell',
                            'quantity': quantity,
                            'price': price,
                            'transaction_date': date
                        })
                    else:
                        print(f"Not enough {symbol} to sell {quantity} on {date.date()}")

            # Calculate portfolio value at the end of the day
            current_portfolio_value = current_cash
            for symbol, qty in current_holdings.items():
                if symbol in current_prices and current_prices[symbol] > 0:
                    current_portfolio_value += qty * current_prices[symbol]
            daily_portfolio_values.append({'Date': date, 'Value': current_portfolio_value})

        portfolio_value_df = pd.DataFrame(daily_portfolio_values)
        if portfolio_value_df.empty:
            return {"error": "No portfolio value generated."}

        portfolio_value_df['Date'] = pd.to_datetime(portfolio_value_df['Date'])
        portfolio_value_df = portfolio_value_df.set_index('Date').sort_index()

        returns = calculate_returns(portfolio_value_df.reset_index())
        cumulative_returns = calculate_cumulative_returns(returns)
        volatility = calculate_volatility(returns)
        max_drawdown = calculate_max_drawdown(cumulative_returns)

        return {
            "portfolio_value": portfolio_value_df.to_dict(orient="records"),
            "returns": returns.to_dict(),
            "cumulative_returns": cumulative_returns.to_dict(),
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "final_capital": current_cash + sum(current_holdings[s] * current_prices.get(s, 0) for s in current_holdings),
            "transactions": self.transactions
        }

# Example Strategy (Buy and Hold)
def buy_and_hold_strategy(historical_data, current_holdings, current_cash, current_prices, date):
    transactions = []
    # On the first day, buy as much as possible of each asset
    if date == pd.to_datetime(min(historical_data[list(historical_data.keys())[0]].index)).normalize():
        for symbol in historical_data.keys():
            if symbol in current_prices and current_prices[symbol] > 0:
                quantity_to_buy = current_cash / len(historical_data) / current_prices[symbol]
                if quantity_to_buy > 0:
                    transactions.append({'symbol': symbol, 'type': 'buy', 'quantity': quantity_to_buy, 'price': current_prices[symbol]})
    return transactions

if __name__ == "__main__":
    print("Running backtesting_engine example...")
    engine = BacktestingEngine(initial_capital=100000)
    results = engine.run_backtest(
        strategy=buy_and_hold_strategy,
        symbols=["AAPL", "MSFT"],
        start_date="2023-01-01",
        end_date="2023-01-10",
    )

    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        print("\nBacktest Results:")
        print(f"Final Capital: {results['final_capital']:.2f}")
        print(f"Annualized Volatility: {results['volatility']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2f}")
        print("Portfolio Value History (first 5):")
        print(results['portfolio_value'][:5])
        print("Transactions (first 5):")
        print(results['transactions'][:5])
