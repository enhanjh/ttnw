import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function Backtest() {
  const [symbols, setSymbols] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [backtestResults, setBacktestResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleBacktest = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setBacktestResults(null);

    const symbolsArray = symbols.split(',').map(s => s.trim().toUpperCase()).filter(s => s);

    try {
      const response = await fetch('/backtest/buy_and_hold', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbols: symbolsArray,
          start_date: startDate,
          end_date: endDate,
          initial_capital: parseFloat(initialCapital),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setBacktestResults(data);
    } catch (err) {
      setError(err.message);
      console.error("Error during backtest:", err);
    } finally {
      setLoading(false);
    }
  };

  const chartData = {
    labels: backtestResults?.portfolio_value.map(data => new Date(data.Date).toLocaleDateString()),
    datasets: [
      {
        label: 'Portfolio Value',
        data: backtestResults?.portfolio_value.map(data => data.Value),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        tension: 0.1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Portfolio Value Over Time',
      },
    },
  };

  return (
    <div>
      <h2>Backtesting Engine</h2>

      <form onSubmit={handleBacktest}>
        <div>
          <label>Symbols (comma-separated):</label>
          <input
            type="text"
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
            placeholder="e.g., AAPL,MSFT"
            required
          />
        </div>
        <div>
          <label>Start Date:</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>
        <div>
          <label>End Date:</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>
        <div>
          <label>Initial Capital:</label>
          <input
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Running Backtest...' : 'Run Buy & Hold Backtest'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {backtestResults && (
        <div>
          <h3>Backtest Results:</h3>
          <p>Final Capital: ${backtestResults.final_capital?.toFixed(2)}</p>
          <p>Annualized Volatility: {backtestResults.volatility?.toFixed(2)}</p>
          <p>Max Drawdown: {backtestResults.max_drawdown?.toFixed(2)}</p>

          <div style={{ width: '80%', margin: 'auto' }}>
            <Line data={chartData} options={chartOptions} />
          </div>

          <h4>Portfolio Value History:</h4>
          <ul>
            {backtestResults.portfolio_value.map((data, index) => (
              <li key={index}>
                {new Date(data.Date).toLocaleDateString()}: ${data.Value?.toFixed(2)}
              </li>
            ))}
          </ul>

          <h4>Transactions:</h4>
          <ul>
            {backtestResults.transactions.map((tx, index) => (
              <li key={index}>
                {new Date(tx.transaction_date).toLocaleDateString()} - {tx.asset.symbol}: {tx.transaction_type} {tx.quantity?.toFixed(2)} @ ${tx.price?.toFixed(2)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default Backtest;