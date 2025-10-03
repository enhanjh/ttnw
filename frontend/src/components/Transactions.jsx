import React, { useState, useEffect, useCallback, memo, useMemo } from 'react';
import {
  TextField, Button, Select, MenuItem, InputLabel, FormControl, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Box, Typography,
  Dialog, DialogActions, DialogContent, DialogTitle, Checkbox, CircularProgress
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import AddIcon from '@mui/icons-material/Add';
import SystemUpdateAltIcon from '@mui/icons-material/SystemUpdateAlt';
import { fetchApi } from '../api';

// A new component for the row that can be in "edit", "add", or "view" mode.
const EditableTransactionRow = memo(function EditableTransactionRow({
  transaction,
  isEditing,
  isAdding,
  editedTransaction,
  getPortfolioName,
  getAssetName,
  portfolios,
  assets,
  handleSave,
  handleCancel,
  handleInputChange,
  handleDelete,
  handleEdit
}) {

  const data = isEditing || isAdding ? editedTransaction : transaction;
  const assetName = getAssetName(data.asset_id);
  const isCash = assetName.toLowerCase().startsWith('cash');

  const transactionTypes = useMemo(() => {
    const isCashAsset = getAssetName(data.asset_id).toLowerCase().startsWith('cash');
    if (isCashAsset) {
      return [
        { value: 'deposit', label: 'Deposit' },
        { value: 'withdrawal', label: 'Withdrawal' },
      ];
    }
    return [
      { value: 'buy', label: 'Buy' },
      { value: 'sell', label: 'Sell' },
      { value: 'dividend', label: 'Dividend' },
    ];
  }, [data.asset_id, getAssetName]);

  const filteredAssets = useMemo(() => {
    // Now that assets are global, we show all assets for selection.
    // The transaction itself will link to a portfolio.
    return assets;
  }, [assets]);


  if (isEditing || isAdding) {
    return (
      <TableRow sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
        <TableCell>
          <FormControl size="small" fullWidth>
            <Select name="portfolio_id" value={data.portfolio_id} onChange={handleInputChange}>
              {portfolios.map(p => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
        </TableCell>
        <TableCell>
          <FormControl size="small" fullWidth>
            <Select name="asset_id" value={data.asset_id} onChange={handleInputChange}>
              {filteredAssets.map(asset => (
                <MenuItem key={asset.id} value={asset.id}>
                    {asset.asset_type && asset.asset_type.toLowerCase() === 'cash' ? `Cash (${asset.symbol})` : `${asset.symbol} - ${asset.name}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </TableCell>
        <TableCell align="right">
          <FormControl size="small" sx={{ width: '100px' }}>
            <Select name="transaction_type" value={data.transaction_type} onChange={handleInputChange}>
              {transactionTypes.map(type => <MenuItem key={type.value} value={type.value}>{type.label}</MenuItem>)}
            </Select>
          </FormControl>
        </TableCell>
        <TableCell align="right">
          <TextField type="number" name="quantity" value={data.quantity} onChange={handleInputChange} size="small" sx={{ width: '80px' }} />
        </TableCell>
        <TableCell align="right">
          <TextField type="number" name="price" value={data.price} onChange={handleInputChange} size="small" sx={{ width: '100px' }} disabled={isCash || data.transaction_type === 'dividend'}/>
        </TableCell>
        <TableCell align="right">
          <TextField type="number" name="fee" value={data.fee} onChange={handleInputChange} size="small" sx={{ width: '80px' }} />
        </TableCell>
        <TableCell align="right">
          <TextField type="number" name="tax" value={data.tax} onChange={handleInputChange} size="small" sx={{ width: '80px' }} />
        </TableCell>
        <TableCell align="right">
          <TextField type="date" name="transaction_date" value={data.transaction_date} onChange={handleInputChange} size="small" sx={{ width: '140px' }} InputLabelProps={{ shrink: true }} />
        </TableCell>
        <TableCell align="right">
          <IconButton edge="end" aria-label="save" onClick={() => handleSave(data.id)}>
            <SaveIcon />
          </IconButton>
          <IconButton edge="end" aria-label="cancel" onClick={handleCancel}>
            <CancelIcon />
          </IconButton>
        </TableCell>
      </TableRow>
    );
  }

  // View mode
  return (
    <TableRow sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
      <TableCell component="th" scope="row">{getPortfolioName(transaction.portfolio_id)}</TableCell>
      <TableCell>{assetName}</TableCell>
      <TableCell align="right">{transaction.transaction_type}</TableCell>
      <TableCell align="right">{transaction.quantity.toLocaleString()}</TableCell>
      <TableCell align="right">{isCash ? '-' : transaction.price.toLocaleString()}</TableCell>
      <TableCell align="right">{transaction.fee ? transaction.fee.toLocaleString() : '-'}</TableCell>
      <TableCell align="right">{transaction.tax ? transaction.tax.toLocaleString() : '-'}</TableCell>
      <TableCell align="right">{new Date(transaction.transaction_date).toLocaleDateString()}</TableCell>
      <TableCell align="right">
        <IconButton edge="end" aria-label="edit" onClick={() => handleEdit(transaction)}>
          <EditIcon />
        </IconButton>
        <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(transaction.id)}>
          <DeleteIcon />
        </IconButton>
      </TableCell>
    </TableRow>
  );
});

// New Component: Modal for importing transactions from a broker
function BrokerTransactionImportModal({ open, onClose, portfolioId, assets, onImportSuccess }) {
  const [brokerTransactions, setBrokerTransactions] = useState([]);
  const [selected, setSelected] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Dates state
  const today = new Date().toISOString().slice(0, 10);
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState(sevenDaysAgo);
  const [endDate, setEndDate] = useState(today);

  const handleFetchBrokerTransactions = async () => {
    if (!portfolioId) {
      setError("Please select a portfolio first.");
      return;
    }
    setIsLoading(true);
    setError('');
    setBrokerTransactions([]);
    try {
      const formattedStartDate = startDate.replace(/-/g, '');
      const formattedEndDate = endDate.replace(/-/g, '');
      const data = await fetchApi(`/api/transactions/fetch-broker-transactions/${portfolioId}?start_date=${formattedStartDate}&end_date=${formattedEndDate}`);
      setBrokerTransactions(data || []);
    } catch (error) {
      console.error("Error fetching broker transactions:", error);
      setError(error.message || "Failed to fetch transactions.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (orderNumber) => {
    const selectedIndex = selected.indexOf(orderNumber);
    let newSelected = [];
    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, orderNumber);
    } else {
      newSelected = selected.filter(id => id !== orderNumber);
    }
    setSelected(newSelected);
  };

  const handleSelectAll = (event) => {
    if (event.target.checked) {
      const newSelecteds = brokerTransactions.map((t) => t.order_number);
      setSelected(newSelecteds);
      return;
    }
    setSelected([]);
  };

  // This is the function that will save the selections.
  const handleSaveSelected = async () => {
    setIsLoading(true);
    setError('');

    const selectedTransactions = brokerTransactions.filter(t => selected.includes(t.order_number));

    const transactionsToCreate = [];
    for (const t of selectedTransactions) {
      const asset = assets.find(a => a.symbol === t.symbol);
      if (!asset) {
        setError(`Asset with symbol ${t.symbol} not found in the database. Please add it before importing transactions.`);
        setIsLoading(false);
        return;
      }

      // Convert YYYYMMDD to a Date object and then to ISO string
      const year = parseInt(t.date.substring(0, 4), 10);
      const month = parseInt(t.date.substring(4, 6), 10) - 1; // Month is 0-indexed
      const day = parseInt(t.date.substring(6, 8), 10);
      const transactionDate = new Date(year, month, day).toISOString();

      transactionsToCreate.push({
        portfolio_id: portfolioId,
        asset_id: asset.id,
        transaction_type: t.side.toLowerCase(), // 'buy' or 'sell'
        quantity: parseFloat(t.quantity),
        price: parseFloat(t.price),
        transaction_date: transactionDate,
        fee: 0, // Broker API does not provide fee in this call, default to 0
        tax: 0, // Broker API does not provide tax in this call, default to 0
      });
    }

    try {
      await fetchApi('/api/transactions/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transactionsToCreate),
      });
      alert('Successfully imported transactions!');
      onImportSuccess(); // This will refetch transactions and close the modal
    } catch (error) {
      console.error("Error saving selected transactions:", error);
      setError(error.message || "Failed to save transactions.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Import Transactions from Broker</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
          <TextField label="Start Date" type="date" value={startDate} onChange={e => setStartDate(e.target.value)} InputLabelProps={{ shrink: true }} />
          <TextField label="End Date" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} InputLabelProps={{ shrink: true }} />
          <Button onClick={handleFetchBrokerTransactions} variant="contained">Fetch Transactions</Button>
        </Box>
        {isLoading && <CircularProgress />}
        {error && <Typography color="error">{error}</Typography>}
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selected.length > 0 && selected.length < brokerTransactions.length}
                    checked={brokerTransactions.length > 0 && selected.length === brokerTransactions.length}
                    onChange={handleSelectAll}
                  />
                </TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Side</TableCell>
                <TableCell align="right">Quantity</TableCell>
                <TableCell align="right">Price</TableCell>
                <TableCell align="right">Total Amount</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {brokerTransactions.map((t) => (
                <TableRow key={t.order_number} hover onClick={() => handleSelect(t.order_number)} role="checkbox" tabIndex={-1} selected={selected.includes(t.order_number)}>
                  <TableCell padding="checkbox">
                    <Checkbox checked={selected.includes(t.order_number)} />
                  </TableCell>
                  <TableCell>{t.date}</TableCell>
                  <TableCell>{t.symbol}</TableCell>
                  <TableCell>{t.name}</TableCell>
                  <TableCell>{t.side}</TableCell>
                  <TableCell align="right">{parseInt(t.quantity).toLocaleString()}</TableCell>
                  <TableCell align="right">{parseFloat(t.price).toLocaleString()}</TableCell>
                  <TableCell align="right">{parseInt(t.total_amount).toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSaveSelected} variant="contained" disabled={selected.length === 0}>
          Save Selected ({selected.length})
        </Button>
      </DialogActions>
    </Dialog>
  );
}


function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [assets, setAssets] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [editingTransactionId, setEditingTransactionId] = useState(null);
  const [editedTransaction, setEditedTransaction] = useState(null);
  const [isAdding, setIsAdding] = useState(false);
  const [filters, setFilters] = useState({ portfolio: '', asset: '' });
  
  // New state for the import modal
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const emptyTransaction = {
    asset_id: '',
    portfolio_id: '',
    transaction_type: '',
    quantity: '',
    price: '',
    transaction_date: new Date().toISOString().slice(0, 10),
    fee: '',
    tax: '',
  };

  const fetchTransactions = useCallback(async () => {
    try {
      let url = '/api/transactions/';
      if (filters.portfolio) {
        url = `/api/transactions/?portfolio_id=${filters.portfolio}`;
      }
      const data = await fetchApi(url);
      const sortedData = data.sort((a, b) => new Date(b.transaction_date) - new Date(a.transaction_date));
      setTransactions(sortedData);
    } catch (error) {
      console.error("Error fetching transactions:", error);
    }
  }, [filters.portfolio]);

  const fetchAssets = useCallback(async () => {
    try {
      const data = await fetchApi('/api/assets/');
      setAssets(data);
    } catch (error) {
      console.error("Error fetching assets:", error);
    }
  }, []);

  const fetchPortfolios = useCallback(async () => {
    try {
      const data = await fetchApi('/api/portfolios/');
      setPortfolios(data);
    } catch (error) {
      console.error("Error fetching portfolios:", error);
    }
  }, []);
  
  // Fetch all necessary data on component mount
  useEffect(() => {
    fetchPortfolios();
    fetchAssets();
  }, [fetchPortfolios, fetchAssets]);

  // Refetch transactions when the main portfolio filter changes
  useEffect(() => {
    if (filters.portfolio) {
      fetchTransactions();
    }
  }, [filters.portfolio, fetchTransactions]);


  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setEditedTransaction(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleAddClick = () => {
    // Set the portfolio_id in the new transaction if a filter is selected
    setEditedTransaction({ ...emptyTransaction, portfolio_id: filters.portfolio });
    setIsAdding(true);
    setEditingTransactionId(null);
  };

  const handleCancel = () => {
    setIsAdding(false);
    setEditingTransactionId(null);
    setEditedTransaction(null);
  };

  const handleSave = async (id) => {
    const isCreating = !id;
    const method = isCreating ? 'POST' : 'PUT';
    const url = isCreating ? '/api/transactions/' : `/api/transactions/${id}`;

    const isCash = getAssetName(editedTransaction.asset_id).toLowerCase().startsWith('cash');
    const isSell = editedTransaction.transaction_type === 'sell';
    const isBuy = editedTransaction.transaction_type === 'buy';
    const isDividend = editedTransaction.transaction_type === 'dividend';

    if (
      !editedTransaction.portfolio_id ||
      !editedTransaction.asset_id ||
      !editedTransaction.transaction_type ||
      !editedTransaction.quantity ||
      !editedTransaction.transaction_date ||
      (!isCash && !isDividend && !editedTransaction.price)
    ) {
      alert('Please fill in all required transaction fields.');
      return;
    }

    const requestBody = {
      ...editedTransaction,
      quantity: parseFloat(editedTransaction.quantity),
      price: isCash || isDividend ? 1 : parseFloat(editedTransaction.price),
      fee: isBuy || isSell ? parseFloat(editedTransaction.fee || 0) : 0,
      tax: isSell || isDividend ? parseFloat(editedTransaction.tax || 0) : 0,
      transaction_date: new Date(editedTransaction.transaction_date).toISOString(),
    };

    try {
      await fetchApi(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      handleCancel();
      fetchTransactions();
      alert(`Transaction ${isCreating ? 'added' : 'updated'} successfully!`);
    } catch (error) {
      console.error(`Error ${isCreating ? 'adding' : 'updating'} transaction:`, error);
      alert(`Error ${isCreating ? 'adding' : 'updating'} transaction:\n${error.message}`);
    }
  };

  const handleDelete = useCallback(async (id) => {
    if (window.confirm("Are you sure you want to delete this transaction?")) {
      try {
        await fetchApi(`/api/transactions/${id}`, { method: 'DELETE' });
        fetchTransactions();
        alert("Transaction deleted successfully!");
      } catch (error) {
        console.error("Error deleting transaction:", error);
        alert(`Error deleting transaction: ${error.message}`);
      }
    }
  }, [fetchTransactions]);

  const handleEdit = useCallback((transaction) => {
    setEditingTransactionId(transaction.id);
    setEditedTransaction({
      ...transaction,
      transaction_date: transaction.transaction_date.slice(0, 10),
      fee: transaction.fee || '',
      tax: transaction.tax || '',
    });
    setIsAdding(false);
  }, []);

  const getAssetName = useCallback((assetId) => {
    if (!assetId) return 'Unknown';
    const asset = assets.find(a => a.id === assetId);
    if (asset) {
      if (asset.asset_type && asset.asset_type.toLowerCase() === 'cash') return `Cash (${asset.symbol})`;
      return asset.name ? `${asset.symbol} - ${asset.name}` : asset.symbol;
    }
    return 'Unknown';
  }, [assets]);

  const getPortfolioName = useCallback((portfolioId) => {
    const portfolio = portfolios.find(p => p.id === portfolioId);
    return portfolio ? portfolio.name : 'Unknown';
  }, [portfolios]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };
  
  const handleImportSuccess = () => {
    fetchTransactions();
    setIsImportModalOpen(false);
  }

  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      // If portfolio filter is set, transaction must match.
      const portfolioMatch = filters.portfolio ? t.portfolio_id === filters.portfolio : true;
      // Asset filter is text-based search.
      const assetMatch = filters.asset ? getAssetName(t.asset_id).toLowerCase().includes(filters.asset.toLowerCase()) : true;
      return portfolioMatch && assetMatch;
    });
  }, [transactions, filters, getAssetName]);

  return (
    <div>
      <Typography variant="h5" gutterBottom>Manage Transactions</Typography>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        {/* Filtering UI */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Portfolio</InputLabel>
            <Select name="portfolio" value={filters.portfolio} onChange={handleFilterChange} label="Filter by Portfolio">
              <MenuItem value="">All Portfolios</MenuItem>
              {portfolios
                .filter(p => p.environment === 'live')
                .map(p => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField
            name="asset"
            label="Filter by Asset Name"
            value={filters.asset}
            onChange={handleFilterChange}
            variant="outlined"
            size="small"
          />
          <Button variant="outlined" onClick={fetchTransactions}>Search</Button>
        </Box>
        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<SystemUpdateAltIcon />}
              onClick={() => setIsImportModalOpen(true)}
              disabled={!filters.portfolio} // Only enable if a portfolio is selected
            >
              Import from Broker
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddClick}
              disabled={isAdding || editingTransactionId !== null}
            >
              Add Transaction
            </Button>
        </Box>
      </Box>

      {/* Main transactions table */}
      <TableContainer component={Paper}>
        <Table sx={{ minWidth: 650 }} aria-label="simple table">
          <TableHead>
            <TableRow>
              <TableCell>Portfolio</TableCell>
              <TableCell>Asset</TableCell>
              <TableCell align="right">Type</TableCell>
              <TableCell align="right">Quantity</TableCell>
              <TableCell align="right">Price</TableCell>
              <TableCell align="right">Fee</TableCell>
              <TableCell align="right">Tax</TableCell>
              <TableCell align="right">Date</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isAdding && (
              <EditableTransactionRow
                isAdding={true}
                editedTransaction={editedTransaction}
                portfolios={portfolios}
                assets={assets}
                handleSave={handleSave}
                handleCancel={handleCancel}
                handleInputChange={handleInputChange}
                getAssetName={getAssetName}
              />
            )}
            {filteredTransactions.map((transaction) => (
              <EditableTransactionRow
                key={transaction.id}
                transaction={transaction}
                isEditing={editingTransactionId === transaction.id}
                editedTransaction={editedTransaction}
                getPortfolioName={getPortfolioName}
                getAssetName={getAssetName}
                portfolios={portfolios}
                assets={assets}
                handleEdit={handleEdit}
                handleDelete={handleDelete}
                handleSave={handleSave}
                handleCancel={handleCancel}
                handleInputChange={handleInputChange}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Broker Import Modal */}
      {isImportModalOpen && (
        <BrokerTransactionImportModal
            open={isImportModalOpen}
            onClose={() => setIsImportModalOpen(false)}
            portfolioId={filters.portfolio}
            assets={assets}
            onImportSuccess={handleImportSuccess}
        />
      )}
    </div>
  );
}

export default Transactions;