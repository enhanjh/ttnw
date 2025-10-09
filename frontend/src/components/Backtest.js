import React, { useState, useEffect, useMemo, useCallback } from 'react';
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
import { fetchApi } from '../api';
import { FormControl, InputLabel, Select, MenuItem, TextField, Button, Box, Typography, CircularProgress, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Tooltip as MuiTooltip, Dialog as MuiDialog, DialogTitle as MuiDialogTitle, DialogContent as MuiDialogContent, DialogActions as MuiDialogActions, List, ListItem, ListItemText, FormControlLabel, Checkbox } from '@mui/material'; // Import Material-UI components

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
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [initialCapital, setInitialCapital] = useState('100,000,000'); // Changed to string for formatting
  const [backtestResults, setBacktestResults] = useState(null);

  const handleCapitalChange = (e) => {
    const rawValue = e.target.value.replace(/,/g, '');
    if (rawValue === '') {
      setInitialCapital('');
    } else if (!isNaN(rawValue) && !rawValue.includes('.')) { // Only handle integers for simplicity
      const numericValue = parseInt(rawValue, 10);
      setInitialCapital(numericValue.toLocaleString());
    }
  };
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [debug, setDebug] = useState(false);

  const [savedBacktests, setSavedBacktests] = useState([]); // New state for saved backtests
  const [showSaveDialog, setShowSaveDialog] = useState(false); // New state for save dialog

  // Fetch strategies on component mount
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const data = await fetchApi('/api/strategies/');
        setStrategies(data);
      } catch (err) {
        console.error("Error fetching strategies:", err);
        setError("Failed to load strategies.");
      }
    };
    fetchStrategies();
  }, []);



  // New useEffect to fetch saved backtests
  useEffect(() => {
    const fetchSavedBacktests = async () => {
      try {
        const data = await fetchApi('/api/backtest_results/');
        setSavedBacktests(data);
      } catch (err) {
        console.error("Error fetching saved backtests:", err);
        // setError("Failed to load saved backtests."); // Don't block main functionality
      }
    };
    fetchSavedBacktests();
  }, []);

  const handleBacktest = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setBacktestResults(null);

    if (!selectedStrategyId) {
      setError("Please select a strategy.");
      setLoading(false);
      return;
    }

    try {
      const data = await fetchApi('/api/backtest/strategy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          strategy_id: selectedStrategyId,
          start_date: startDate,
          end_date: endDate,
          initial_capital: parseFloat(initialCapital.replace(/,/g, '')),
          debug: debug,
        }),
      });

      setBacktestResults(data);
    } catch (err) {
      setError(err.message);
      console.error("Error during strategy backtest:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBacktestResult = async (resultNameFromDialog) => {
    if (!resultNameFromDialog.trim()) {
      setError("Result name cannot be empty.");
      return;
    }
    if (!backtestResults) {
      setError("No backtest results to save.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const dataToSave = {
        name: resultNameFromDialog,
        strategy_id: selectedStrategyId, // Assuming selectedStrategyId is the ID of the strategy used
        start_date: startDate,
        end_date: endDate,
        initial_capital: parseFloat(initialCapital.replace(/,/g, '')),
        final_capital: backtestResults.final_capital,
        annualized_return: backtestResults.annualized_return,
        volatility: backtestResults.volatility,
        max_drawdown: backtestResults.max_drawdown,
        sharpe_ratio: backtestResults.sharpe_ratio,
        portfolio_value: backtestResults.portfolio_value,
        returns: backtestResults.returns,
        cumulative_returns: backtestResults.cumulative_returns,
        transactions: backtestResults.transactions,
      };

      await fetchApi('/api/backtest_results/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dataToSave),
      });

      setShowSaveDialog(false);
      // Refresh saved backtests list
      const updatedSavedBacktests = await fetchApi('/api/backtest_results/');
      setSavedBacktests(updatedSavedBacktests);
      alert('Backtest results saved successfully!');
    } catch (err) {
      setError(err.message);
      console.error("Error saving backtest results:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadBacktestResult = useCallback(async (resultId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi(`/api/backtest_results/${resultId}`);

      // Fetch benchmark data for the loaded result's period
      const benchmarkResponse = await fetchApi(
        `/api/backtest/benchmarks?start_date=${new Date(data.start_date).toISOString().split('T')[0]}&end_date=${new Date(data.end_date).toISOString().split('T')[0]}&initial_capital=${data.initial_capital}`
      );

      // Merge benchmark data into the loaded backtest data
      const mergedData = { ...data, benchmark_data: benchmarkResponse.benchmark_data };

      setBacktestResults(mergedData);
      // Also set the selected strategy and dates from the loaded result for context
      setSelectedStrategyId(data.strategy.id);
      setStartDate(new Date(data.start_date).toISOString().split('T')[0]);
      setEndDate(new Date(data.end_date).toISOString().split('T')[0]);
      setInitialCapital(data.initial_capital.toLocaleString());
      alert(`Backtest result "${data.name}" loaded successfully!`);
    } catch (err) {
      setError(err.message);
      console.error("Error loading backtest result:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDeleteBacktestResult = useCallback(async (resultId) => {
    if (!window.confirm("Are you sure you want to delete this saved backtest result?")) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await fetchApi(`/api/backtest_results/${resultId}`, {
        method: 'DELETE',
      });
      // Refresh saved backtests list
      const updatedSavedBacktests = await fetchApi('/api/backtest_results/');
      setSavedBacktests(updatedSavedBacktests);
      alert('Backtest result deleted successfully!');
    } catch (err) {
      setError(err.message);
      console.error("Error deleting backtest result:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Chart data and options remain largely the same, assuming backend returns similar structure
  const benchmarkColors = {
    "S&P 500": 'rgb(255, 159, 64)',
    "KOSPI": 'rgb(0, 128, 0)', // Green color for KOSPI
    "Nikkei 225": 'rgb(255, 0, 0)', // Red color for Nikkei 225
    // Add more benchmarks and colors here
  };

  const chartData = useMemo(() => ({
    labels: backtestResults?.portfolio_value?.map(data => new Date(data.Date).toLocaleDateString()),
    datasets: [
      {
        label: 'Portfolio Value',
        data: backtestResults?.portfolio_value?.map(data => data.Value),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        tension: 0.1,
        yAxisID: 'y', // Assign to primary Y-axis
      },
      {
        label: 'Cumulative Returns (%)',
        data: backtestResults?.cumulative_returns ? Object.values(backtestResults.cumulative_returns).map(val => val * 100) : [],
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        tension: 0.1,
        yAxisID: 'y1', // Assign to secondary Y-axis
      },
      ...(backtestResults?.benchmark_data ? Object.entries(backtestResults.benchmark_data).map(([name, data]) => ({
        label: `${name} Benchmark`,
        data: data.map(item => item.Value),
        borderColor: benchmarkColors[name] || 'rgb(153, 102, 255)', // Fallback color
        backgroundColor: benchmarkColors[name] ? benchmarkColors[name].replace('rgb', 'rgba').replace(')', ', 0.5)') : 'rgba(153, 102, 255, 0.5)',
        tension: 0.1,
        yAxisID: 'y', // Benchmarks also use the primary Y-axis for value
        borderDash: [5, 5], // Dotted line for benchmarks
        pointRadius: 0, // Remove point markers for benchmarks
      })) : []),
    ],
  }), [backtestResults]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Portfolio Value and Cumulative Returns Over Time',
      },
    },
    scales: {
      y: { // Primary Y-axis for Portfolio Value
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Portfolio Value (₩)'
        },
        ticks: {
          callback: function(value) {
            return '₩' + value.toLocaleString();
          }
        }
      },
      y1: { // Secondary Y-axis for Cumulative Returns
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Cumulative Returns (%)'
        },
        grid: {
          drawOnChartArea: false, // Only draw grid lines for the first axis
        },
        ticks: {
          callback: function(value) {
            return value + '%';
          }
        }
      },
    },
  }), []);

  const savedBacktestsItems = useMemo(() => savedBacktests.map((result) => (
      <ListItem
        key={result.id}
        secondaryAction={
          <>
            <Button size="small" onClick={() => handleLoadBacktestResult(result.id)} sx={{ mr: 1 }}>Load</Button>
            <Button size="small" color="error" onClick={() => handleDeleteBacktestResult(result.id)}>Delete</Button>
          </>
        }
      >
        <ListItemText
          primary={result.name}
          secondary={`Strategy: ${result.strategy.name} | ${new Date(result.start_date).toLocaleDateString()} - ${new Date(result.end_date).toLocaleDateString()}`}
        />
      </ListItem>
  )), [savedBacktests, handleLoadBacktestResult, handleDeleteBacktestResult]);

  const transactionsTableRows = useMemo(() => backtestResults?.transactions.map((tx, index) => (
    <TableRow key={index}>
      <TableCell>{new Date(tx.transaction_date).toLocaleDateString()}</TableCell>
      <TableCell>{tx.asset.name}</TableCell>
      <TableCell>{tx.transaction_type}</TableCell>
      <TableCell align="right">{tx.quantity?.toFixed(2)}</TableCell>
      <TableCell align="right">₩{tx.price?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}</TableCell>
      <TableCell align="right">₩{(tx.quantity * tx.price)?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</TableCell>
      <TableCell align="right">₩{tx.cash_balance?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</TableCell>
      <TableCell align="right">₩{tx.portfolio_value?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</TableCell>
    </TableRow>
  )), [backtestResults]);


  return (
    <Box sx={{ padding: 2 }}>
      <Typography variant="h5" gutterBottom>Backtesting Engine</Typography>

      <form onSubmit={handleBacktest}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}> {/* New Box for horizontal layout */}


          <FormControl sx={{ flex: '1 1 300px' }}> {/* Adjust flex basis as needed */}
            <InputLabel id="strategy-select-label">Select Strategy</InputLabel>
            <Select
              labelId="strategy-select-label"
              value={selectedStrategyId}
              label="Select Strategy"
              onChange={(e) => setSelectedStrategyId(e.target.value)}
              required
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {strategies.map((strategy) => (
                <MenuItem key={strategy.id} value={strategy.id}>
                  {strategy.name} ({strategy.strategy_type})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Start Date"
            type="date"
            sx={{ flex: '1 1 150px' }} // Adjust flex basis as needed
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            required
          />
          <TextField
            label="End Date"
            type="date"
            sx={{ flex: '1 1 150px' }} // Adjust flex basis as needed
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            required
          />
          <TextField
            label="Initial Capital"
            type="text" // Changed to text for formatting
            sx={{ flex: '1 1 150px' }} // Adjust flex basis as needed
            value={initialCapital}
            onChange={handleCapitalChange} // Use custom handler
            required
          />
        <FormControlLabel
          control={<Checkbox checked={debug} onChange={(e) => setDebug(e.target.checked)} />}
          label="Enable Debug Log"
        />
        <Button
          type="submit"
          variant="contained"
          disabled={loading || !selectedStrategyId || !startDate || !endDate}
          sx={{ height: '56px' }} // Match text field height
        >
          {loading ? <CircularProgress size={24} /> : 'Run Strategy Backtest'}
        </Button>
        </Box> {/* End of new Box */}
      </form>

      {error && <Alert severity="error" sx={{ mt: 2 }}>Error: {error}</Alert>}

      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>Saved Backtest Results</Typography>
        {savedBacktests.length === 0 ? (
          <Typography>No saved backtest results yet.</Typography>
        ) : (
          <List component={Paper}>
            {savedBacktestsItems}
          </List>
        )}
      </Box>

      {backtestResults && (
        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Backtest Results for {backtestResults.strategy?.name}:</Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={() => setShowSaveDialog(true)}
              disabled={!backtestResults}
            >
              Save Results
            </Button>
          </Box>

          <SaveBacktestResultDialog
            open={showSaveDialog}
            onClose={() => setShowSaveDialog(false)}
            onSave={handleSaveBacktestResult}
          />
          <TableContainer component={Paper} sx={{ mt: 2, mb: 3 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Final Capital</TableCell>
                  <TableCell>Annualized Return</TableCell>
                  <TableCell>Annualized Volatility</TableCell>
                  <TableCell>Max Drawdown</TableCell>
                  <TableCell>Sharpe Ratio</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell align="right">₩{backtestResults.final_capital?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</TableCell>
                  <TableCell align="right">
                    <MuiTooltip title="Annualized Return = ( (Final Capital / Initial Capital)^(252 / Number of Trading Days) ) - 1">
                      <span>{(backtestResults.annualized_return * 100)?.toFixed(2)}%</span>
                    </MuiTooltip>
                  </TableCell>
                  <TableCell align="right">
                    <MuiTooltip title="Annualized Volatility = Standard Deviation of Daily Returns * sqrt(252)">
                      <span>{(backtestResults.volatility * 100)?.toFixed(2)}%</span>
                    </MuiTooltip>
                  </TableCell>
                  <TableCell align="right">
                    <MuiTooltip title="Max Drawdown = (Trough Value - Peak Value) / Peak Value">
                      <span>{(backtestResults.max_drawdown * 100)?.toFixed(2)}%</span>
                    </MuiTooltip>
                  </TableCell>
                  <TableCell align="right">
                    <MuiTooltip title="Sharpe Ratio = (Annualized Return - Risk-Free Rate) / Annualized Volatility (assuming Risk-Free Rate = 0)">
                      <span>{backtestResults.sharpe_ratio?.toFixed(2)}</span>
                    </MuiTooltip>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>

          <div style={{ width: '80%', margin: 'auto' }}>
            <Line data={chartData} options={chartOptions} />
          </div>




          <h4>Transactions:</h4>
          <TableContainer component={Paper} sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell align="right">Cash Balance</TableCell>
                  <TableCell align="right">Portfolio Value</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactionsTableRows}
              </TableBody>
            </Table>
          </TableContainer>

          {backtestResults && backtestResults.debug_logs && backtestResults.debug_logs.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Typography variant="h6">Debug Logs</Typography>
              <Paper sx={{ p: 2, mt: 1, maxHeight: 400, overflow: 'auto', backgroundColor: '#f5f5f5' }}>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0, fontFamily: 'monospace' }}>
                  {backtestResults.debug_logs.join('\n')}
                </pre>
              </Paper>
            </Box>
          )}

        </Box>
      )}
    </Box>
  );
}

function SaveBacktestResultDialog({ open, onClose, onSave }) {
  const [dialogResultName, setDialogResultName] = useState('');

  useEffect(() => {
    if (open) {
      setDialogResultName(''); // Clear previous name when opening
    }
  }, [open]);

  const handleInternalSave = () => {
    onSave(dialogResultName); // Pass internal state to parent's onSave
  };

  return (
    <MuiDialog open={open} onClose={onClose}>
      <MuiDialogTitle>Save Backtest Results</MuiDialogTitle>
      <MuiDialogContent>
        <TextField
          autoFocus
          margin="dense"
          label="Result Name"
          type="text"
          fullWidth
          variant="standard"
          value={dialogResultName}
          onChange={(e) => setDialogResultName(e.target.value)}
        />
      </MuiDialogContent>
      <MuiDialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleInternalSave} disabled={!dialogResultName.trim()}>Save</Button>
      </MuiDialogActions>
    </MuiDialog>
  );
}

export default Backtest;
