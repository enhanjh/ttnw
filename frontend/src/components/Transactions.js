import React, { useState, useEffect, useCallback, memo, useMemo } from 'react';
import { TextField, Button, Select, MenuItem, InputLabel, FormControl, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Box, Typography } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import AddIcon from '@mui/icons-material/Add';
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


function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [assets, setAssets] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [editingTransactionId, setEditingTransactionId] = useState(null);
  const [editedTransaction, setEditedTransaction] = useState(null);
  const [isAdding, setIsAdding] = useState(false);
  const [filters, setFilters] = useState({ portfolio: '', asset: '' });

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

  useEffect(() => {
    fetchPortfolios();
    fetchAssets();
  }, [fetchPortfolios, fetchAssets]);

  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setEditedTransaction(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleAddClick = () => {
    setEditedTransaction(emptyTransaction);
    setIsAdding(true);
    setEditingTransactionId(null); // Ensure not in edit mode
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

      handleCancel(); // Close edit/add row
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
    setIsAdding(false); // Ensure not in add mode
  }, []);

  const getAssetName = useCallback((assetId) => {
    if (!assetId) return 'Unknown';
    const asset = assets.find(a => a.id === assetId);
    if (asset) {
      if (asset.asset_type && asset.asset_type.toLowerCase() === 'cash') return `Cash (${asset.symbol})`;
      return asset.name ? `${asset.symbol} - ${asset.name}` : asset.symbol;
    }
    if (typeof assetId === 'string' && assetId.startsWith('cash_')) {
      const currency = assetId.split('_')[1].toUpperCase();
      return `Cash (${currency})`;
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

  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      const portfolioMatch = filters.portfolio ? t.portfolio_id === filters.portfolio : true;
      const assetMatch = filters.asset ? getAssetName(t.asset_id).toLowerCase().includes(filters.asset.toLowerCase()) : true;
      return portfolioMatch && assetMatch;
    });
  }, [transactions, filters, getAssetName]);

  return (
    <div>
      <Typography variant="h5" gutterBottom>Manage Transactions</Typography>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Portfolio</InputLabel>
            <Select name="portfolio" value={filters.portfolio} onChange={handleFilterChange} label="Filter by Portfolio">
              <MenuItem value="">All Portfolios</MenuItem>
              {portfolios.map(p => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField
            name="asset"
            label="Filter by Asset Name"
            value={filters.asset}
            onChange={handleFilterChange}
            variant="outlined"
          />
          <Button variant="contained" onClick={fetchTransactions}>Search</Button>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAddClick}
          disabled={isAdding || editingTransactionId !== null}
        >
          Add Transaction
        </Button>
      </Box>

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
    </div>
  );
}

export default Transactions;