import React, { useState, useEffect, useCallback, memo } from 'react';
import { TextField, Button, Select, MenuItem, InputLabel, FormControl, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Box } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

// For performance optimization, the row component is wrapped in React.memo
// This prevents the row from re-rendering if its props have not changed.
const TransactionRow = memo(function TransactionRow({
  transaction,
  isEditing,
  editedTransaction,
  getPortfolioName,
  getAssetName,
  handleEdit,
  handleDelete,
  handleSave,
  handleCancelEdit,
  handleEditInputChange
}) {
  const assetName = getAssetName(transaction.asset_id);
  const isCash = assetName.toLowerCase().startsWith('cash');

  return (
    <TableRow sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
      {isEditing ? (
        <>
          <TableCell component="th" scope="row">
            {getPortfolioName(editedTransaction.portfolio_id)}
          </TableCell>
          <TableCell>{getAssetName(editedTransaction.asset_id)}</TableCell>
          <TableCell align="right">{editedTransaction.transaction_type}</TableCell>
          <TableCell align="right">
            <TextField
              type="number"
              name="quantity"
              value={editedTransaction.quantity}
              onChange={handleEditInputChange}
              size="small"
              sx={{ width: '80px' }}
            />
          </TableCell>
          <TableCell align="right">
            <TextField
              type="number"
              name="price"
              value={editedTransaction.price}
              onChange={handleEditInputChange}
              size="small"
              sx={{ width: '100px' }}
            />
          </TableCell>
          <TableCell align="right">
            <TextField
              type="number"
              name="fee"
              value={editedTransaction.fee}
              onChange={handleEditInputChange}
              size="small"
              sx={{ width: '80px' }}
            />
          </TableCell>
          <TableCell align="right">
            <TextField
              type="number"
              name="tax"
              value={editedTransaction.tax}
              onChange={handleEditInputChange}
              size="small"
              sx={{ width: '80px' }}
            />
          </TableCell>
          <TableCell align="right">
            <TextField
              type="date"
              name="transaction_date"
              value={editedTransaction.transaction_date}
              onChange={handleEditInputChange}
              size="small"
              sx={{ width: '140px' }}
              InputLabelProps={{ shrink: true }}
            />
          </TableCell>
          <TableCell align="right">
            <IconButton edge="end" aria-label="save" onClick={() => handleSave(transaction.id)}>
              <SaveIcon />
            </IconButton>
            <IconButton edge="end" aria-label="cancel" onClick={handleCancelEdit}>
              <CancelIcon />
            </IconButton>
          </TableCell>
        </>
      ) : (
        <>
          <TableCell component="th" scope="row">
            {getPortfolioName(transaction.portfolio_id)}
          </TableCell>
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
        </>
      )}
    </TableRow>
  );
});

function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [assets, setAssets] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [newTransaction, setNewTransaction] = useState({
    asset_id: '',
    portfolio_id: '',
    transaction_type: '',
    quantity: '',
    price: '',
    transaction_date: new Date().toISOString().slice(0, 10),
    fee: '',
    tax: '',
  });
  const [editingTransactionId, setEditingTransactionId] = useState(null);
  const [editedTransaction, setEditedTransaction] = useState({
    asset_id: '',
    portfolio_id: '',
    transaction_type: '',
    quantity: '',
    price: '',
    transaction_date: '',
    fee: '',
    tax: '',
  });

  const fetchTransactions = useCallback(async () => {
    try {
      const response = await fetch('/transactions/');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const sortedData = data.sort((a, b) => new Date(b.transaction_date) - new Date(a.transaction_date));
      setTransactions(sortedData);
    } catch (error) {
      console.error("Error fetching transactions:", error);
    }
  }, []);

  const fetchAssets = useCallback(async () => {
    try {
      const response = await fetch('/assets/');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setAssets(data);
    } catch (error) {
      console.error("Error fetching assets:", error);
    }
  }, []);

  const fetchPortfolios = useCallback(async () => {
    try {
      const response = await fetch('/portfolios/');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setPortfolios(data);
    } catch (error) {
      console.error("Error fetching portfolios:", error);
    }
  }, []);

  useEffect(() => {
    fetchPortfolios();
    fetchTransactions();
    fetchAssets();
  }, [fetchPortfolios, fetchTransactions, fetchAssets]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (name === 'asset_id') {
      setNewTransaction({ ...newTransaction, asset_id: value, transaction_type: '' });
    } else {
      setNewTransaction({ ...newTransaction, [name]: value });
    }
  };

  const handleEditInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setEditedTransaction(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isCash = String(newTransaction.asset_id).startsWith('cash_');
    const isSell = newTransaction.transaction_type === 'sell';
    const isBuy = newTransaction.transaction_type === 'buy';
    const isDividend = newTransaction.transaction_type === 'dividend';

    if (
      !newTransaction.portfolio_id ||
      !newTransaction.asset_id ||
      !newTransaction.transaction_type ||
      !newTransaction.quantity ||
      !newTransaction.transaction_date ||
      (!isCash && !isDividend && !newTransaction.price) // Price is required only for non-cash, non-dividend tx
    ) {
      alert('Please fill in all required transaction fields.');
      return;
    }

    const requestBody = {
      ...newTransaction,
      quantity: parseFloat(newTransaction.quantity),
      price: isCash || isDividend ? 1 : parseFloat(newTransaction.price),
      fee: isBuy || isSell ? parseFloat(newTransaction.fee || 0) : 0,
      tax: isSell || isDividend ? parseFloat(newTransaction.tax || 0) : 0,
      transaction_date: new Date(newTransaction.transaction_date).toISOString(),
    };

    try {
      const response = await fetch('/transactions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      setNewTransaction({
        asset_id: '',
        portfolio_id: '',
        transaction_type: '',
        quantity: '',
        price: '',
        transaction_date: new Date().toISOString().slice(0, 10),
        fee: '',
        tax: '',
      });
      fetchTransactions();
      alert("Transaction added successfully!");
    } catch (error) {
      console.error("Error adding transaction:", error);
      alert(`Error adding transaction: ${error.message}`);
    }
  };

  const handleDelete = useCallback(async (id) => {
    if (window.confirm("Are you sure you want to delete this transaction?")) {
      try {
        const response = await fetch(`/transactions/${id}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
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
      asset_id: transaction.asset_id,
      portfolio_id: transaction.portfolio_id,
      transaction_type: transaction.transaction_type,
      quantity: transaction.quantity,
      price: transaction.price,
      transaction_date: transaction.transaction_date.slice(0, 10),
      fee: transaction.fee || '',
      tax: transaction.tax || '',
    });
  }, []);

  const handleSave = useCallback(async (id) => {
    try {
      const response = await fetch(`/transactions/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...editedTransaction,
          quantity: parseFloat(editedTransaction.quantity),
          price: parseFloat(editedTransaction.price),
          fee: parseFloat(editedTransaction.fee || 0),
          tax: parseFloat(editedTransaction.tax || 0),
          transaction_date: new Date(editedTransaction.transaction_date).toISOString(),
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setEditingTransactionId(null);
      fetchTransactions();
      alert("Transaction updated successfully!");
    } catch (error) {
      console.error("Error updating transaction:", error);
      alert(`Error updating transaction: ${error.message}`);
    }
  }, [editedTransaction, fetchTransactions]);

  const handleCancelEdit = useCallback(() => {
    setEditingTransactionId(null);
  }, []);

  const getAssetName = useCallback((assetId) => {
    const asset = assets.find(a => a.id === assetId);
    if (asset) {
      if (asset.asset_type && asset.asset_type.toLowerCase() === 'cash') {
        return `Cash (${asset.symbol})`;
      }
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

  const isCashTransaction = String(newTransaction.asset_id).startsWith('cash_');

  const transactionTypes = isCashTransaction
    ? [
        { value: 'deposit', label: 'Deposit' },
        { value: 'withdrawal', label: 'Withdrawal' },
        { value: 'dividend', label: 'Dividend' },
      ]
    : [
        { value: 'buy', label: 'Buy' },
        { value: 'sell', label: 'Sell' },
      ];

  return (
    <div>
      <h2>Manage Transactions</h2>

      <h3>Add New Transaction</h3>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
        <Box sx={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <FormControl sx={{ flex: 1, minWidth: '150px' }}>
            <InputLabel id="portfolio-select-label">Portfolio</InputLabel>
            <Select
              labelId="portfolio-select-label"
              name="portfolio_id"
              value={newTransaction.portfolio_id}
              onChange={handleInputChange}
              required
            >
              <MenuItem value="">Select Portfolio</MenuItem>
              {portfolios.map((portfolio) => (
                <MenuItem key={portfolio.id} value={portfolio.id}>
                  {portfolio.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl sx={{ flex: 1, minWidth: '150px' }}>
            <InputLabel id="asset-select-label">Asset</InputLabel>
            <Select
              labelId="asset-select-label"
              name="asset_id"
              value={newTransaction.asset_id}
              onChange={handleInputChange}
              required
            >
              <MenuItem value="">Select Asset</MenuItem>
              <MenuItem value="cash_krw">Cash (KRW)</MenuItem>
              <MenuItem value="cash_usd">Cash (USD)</MenuItem>
              {assets.filter(asset => !(asset.asset_type && asset.asset_type.toLowerCase() === 'cash')).map((asset) => (
                <MenuItem key={asset.id} value={asset.id}>
                  {asset.symbol} - {asset.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl sx={{ flex: 1, minWidth: '150px' }}>
            <InputLabel id="type-select-label">Transaction Type</InputLabel>
            <Select
              labelId="type-select-label"
              name="transaction_type"
              value={newTransaction.transaction_type}
              onChange={handleInputChange}
              required
            >
              <MenuItem value="">Select Type</MenuItem>
              {transactionTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <TextField
            type="number"
            name="quantity"
            label={newTransaction.transaction_type === 'dividend' ? "Dividend Amount" : "Quantity"}
            value={newTransaction.quantity}
            onChange={handleInputChange}
            required
            sx={{ flex: 1, minWidth: '150px' }}
          />
          {(newTransaction.transaction_type === 'buy' || newTransaction.transaction_type === 'sell') && (
            <>
              <TextField
                type="number"
                name="price"
                label="Price"
                value={newTransaction.price}
                onChange={handleInputChange}
                required
                sx={{ flex: 1, minWidth: '150px' }}
              />
              <TextField
                type="number"
                name="fee"
                label="Fee"
                value={newTransaction.fee}
                onChange={handleInputChange}
                sx={{ flex: 1, minWidth: '150px' }}
              />
            </>
          )}
          {(newTransaction.transaction_type === 'sell' || newTransaction.transaction_type === 'dividend') && (
            <TextField
              type="number"
              name="tax"
              label="Tax"
              value={newTransaction.tax}
              onChange={handleInputChange}
              sx={{ flex: 1, minWidth: '150px' }}
            />
          )}
          <TextField
            type="date"
            name="transaction_date"
            label="Transaction Date"
            value={newTransaction.transaction_date}
            onChange={handleInputChange}
            required
            sx={{ flex: 1, minWidth: '150px' }}
            InputLabelProps={{
              shrink: true,
            }}
          />
        </Box>
        <Button type="submit" variant="contained" color="primary" sx={{ mt: 1 }}>
          Add Transaction
        </Button>
      </form>

      <h3>Existing Transactions</h3>
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
            {transactions.map((transaction) => (
              <TransactionRow
                key={transaction.id}
                transaction={transaction}
                isEditing={editingTransactionId === transaction.id}
                editedTransaction={editedTransaction}
                getPortfolioName={getPortfolioName}
                getAssetName={getAssetName}
                handleEdit={handleEdit}
                handleDelete={handleDelete}
                handleSave={handleSave}
                handleCancelEdit={handleCancelEdit}
                handleEditInputChange={handleEditInputChange}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
}

export default Transactions;
