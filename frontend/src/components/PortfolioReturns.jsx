import React, { useState, useEffect, useCallback } from 'react';
import { TextField, Button, Select, MenuItem, InputLabel, FormControl, Paper, Typography, Box } from '@mui/material';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { fetchApi } from '../api';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function PortfolioReturns() {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [returnsData, setReturnsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Set initial end date to today
  useEffect(() => {
    const today = new Date();
    setEndDate(today.toISOString().slice(0, 10));
  }, []);

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const fetchPortfolios = async () => {
    try {
      const data = await fetchApi('/api/portfolios/');
      setPortfolios(data);
    } catch (error) {
      console.error("Error fetching portfolios:", error);
      setError("Failed to load portfolios.");
    }
  };

  const fetchOldestTransactionDate = useCallback(async (portfolioId) => {
    try {
      const data = await fetchApi(`/api/transactions/?portfolio_id=${portfolioId}`);
      if (data.length > 0) {
        const oldestDate = data.reduce((minDate, transaction) => {
          const transactionDate = new Date(transaction.transaction_date);
          return transactionDate < minDate ? transactionDate : minDate;
        }, new Date());
        setStartDate(oldestDate.toISOString().slice(0, 10));
      } else {
        setStartDate(''); // No transactions, clear start date
      }
    } catch (error) {
      console.error("Error fetching transactions for oldest date:", error);
      setStartDate('');
    }
  }, []);

  useEffect(() => {
    if (selectedPortfolio) {
      fetchOldestTransactionDate(selectedPortfolio);
    } else {
      setStartDate(''); // Clear start date if no portfolio is selected
    }
  }, [selectedPortfolio, fetchOldestTransactionDate]);

  const handlePortfolioChange = (event) => {
    setSelectedPortfolio(event.target.value);
  };

  const handleStartDateChange = (event) => {
    setStartDate(event.target.value);
  };

  const handleEndDateChange = (event) => {
    setEndDate(event.target.value);
  };

  const fetchPortfolioReturns = async () => {
    setLoading(true);
    setError(null);
    setReturnsData(null);
    try {
      const data = await fetchApi(`/api/portfolio_returns/${selectedPortfolio}?start_date=${startDate}&end_date=${endDate}`);
      setReturnsData(data);
    } catch (error) {
      console.error("Error fetching portfolio returns:", error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const chartData = {
    labels: returnsData?.portfolio_value.map(item => {
      const date = new Date(item.Date);
      return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
    }) || [],
    datasets: [
      {
        label: 'Portfolio Value',
        data: returnsData?.portfolio_value.map(item => item.Value) || [],
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
        yAxisID: 'y',
      },
      {
        label: 'Daily Returns',
        data: Object.values(returnsData?.daily_returns || {}),
        borderColor: 'rgb(255, 99, 132)',
        tension: 0.1,
        yAxisID: 'y1',
      },
      {
        label: 'Cumulative Returns',
        data: Object.values(returnsData?.cumulative_returns || {}),
        borderColor: 'rgb(53, 162, 235)',
        tension: 0.1,
        yAxisID: 'y1',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Portfolio Performance Over Time',
      },
    },
    scales: {
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Portfolio Value',
        },
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'Returns',
        },
      },
    },
  };

  // Calculate Annualized Return (CAGR)
  const calculateAnnualizedReturn = (portfolioValueData) => {
    if (!portfolioValueData || portfolioValueData.length < 2) {
      return 0;
    }

    const firstValue = portfolioValueData[0].Value;
    const lastValue = portfolioValueData[portfolioValueData.length - 1].Value;

    const firstDate = new Date(portfolioValueData[0].Date);
    const lastDate = new Date(portfolioValueData[portfolioValueData.length - 1].Date);

    const years = (lastDate - firstDate) / (1000 * 60 * 60 * 24 * 365.25);

    if (firstValue <= 0 || years <= 0) {
      return 0;
    }

    return Math.pow(lastValue / firstValue, 1 / years) - 1;
  };

  const annualizedReturn = returnsData?.portfolio_value ? calculateAnnualizedReturn(returnsData.portfolio_value) : 0;

  return (
    <Box sx={{ padding: 2 }}>
      <Typography variant="h5" gutterBottom>Portfolio Returns</Typography>

      <Box sx={{ display: 'flex', gap: '10px', flexWrap: 'wrap', mb: 2 }}>
        <FormControl sx={{ flex: 1, minWidth: '180px' }}>
          <InputLabel id="portfolio-select-label">Select Portfolio</InputLabel>
          <Select
            labelId="portfolio-select-label"
            value={selectedPortfolio}
            onChange={handlePortfolioChange}
            label="Select Portfolio"
          >
            <MenuItem value="">Select a Portfolio</MenuItem>
            {portfolios.map((portfolio) => (
              <MenuItem key={portfolio.id} value={portfolio.id}>
                {portfolio.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          label="Start Date"
          type="date"
          value={startDate}
          onChange={handleStartDateChange}
          InputLabelProps={{
            shrink: true,
          }}
          sx={{ flex: 1, minWidth: '180px' }}
        />
        <TextField
          label="End Date"
          type="date"
          value={endDate}
          onChange={handleEndDateChange}
          InputLabelProps={{
            shrink: true,
          }}
          sx={{ flex: 1, minWidth: '180px' }}
        />
      </Box>

      <Button
        variant="contained"
        onClick={fetchPortfolioReturns}
        disabled={!selectedPortfolio || !startDate || !endDate || loading}
        sx={{ mb: 2 }}
      >
        {loading ? 'Loading...' : 'Calculate Returns'}
      </Button>

      {error && <Typography color="error">Error: {error}</Typography>}

      {returnsData && (
        <Paper elevation={3} sx={{ p: 2, mt: 2 }}>
          <Typography variant="h6" gutterBottom>Performance Metrics</Typography>
          <Typography>Annualized Return: {(annualizedReturn * 100).toFixed(2)}%</Typography>
          <Typography>Annualized Volatility: {returnsData.volatility.toFixed(2)}</Typography>
          <Typography>Max Drawdown: {(returnsData.max_drawdown * 100).toFixed(2)}%</Typography>

          <Box sx={{ mt: 3 }}>
            <Line data={chartData} options={chartOptions} />
          </Box>
        </Paper>
      )}
    </Box>
  );
}

export default PortfolioReturns;
