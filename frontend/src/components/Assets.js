import React, { useState, useEffect } from 'react';
import { Autocomplete, TextField, Button, List, ListItem, ListItemText, FormControl, InputLabel, Select, MenuItem, IconButton } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

function Assets({ portfolioId }) {
  const [assets, setAssets] = useState([]);
  
  const [portfolios, setPortfolios] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [selectedName, setSelectedName] = useState('');
  const [selectedPortfolio, setSelectedPortfolio] = useState('');
  const [selectedCountry, setSelectedCountry] = useState('US'); // Default to US
  const [editingAssetId, setEditingAssetId] = useState(null);
  const [editedAsset, setEditedAsset] = useState({
    symbol: '',
    name: '',
    asset_type: '',
    portfolio_id: '',
  });

  useEffect(() => {
    fetchAssets();
    
    fetchPortfolios();
  }, [portfolioId]);

  const fetchAssets = async () => {
    try {
      const response = await fetch(`/assets/?portfolio_id=${portfolioId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setAssets(data);
    } catch (error) {
      console.error("Error fetching assets:", error);
    }
  };

  

  const fetchPortfolios = async () => {
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
  };

  const handleSymbolChange = (event) => {
    setSelectedSymbol(event.target.value);
  };

  

  const handleCountryChange = (event) => {
    setSelectedCountry(event.target.value);
    setSelectedSymbol(''); // Reset selected symbol when country changes
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSymbol || selectedSymbol.trim() === '') {
      alert('Please select a symbol and a portfolio.');
      return;
    }

    const newAsset = {
      symbol: selectedSymbol,
      name: selectedName,
      asset_type: selectedCountry === 'US' ? 'stock_us' : (selectedCountry === 'KR' ? 'stock_kr_kospi' : 'stock_kr_kosdaq'),
      portfolio_id: portfolioId,
    };

    try {
      const response = await fetch('/assets/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newAsset),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setSelectedSymbol('');
      setSelectedName('');
      fetchAssets(); // Refresh the list
      alert("Asset added successfully!");
    } catch (error) {
      console.error("Error adding asset:", error);
      alert(`Error adding asset: ${error.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this asset?")) {
      try {
        const response = await fetch(`/assets/${id}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        fetchAssets(); // Refresh the list
        alert("Asset deleted successfully!");
      } catch (error) {
        console.error("Error deleting asset:", error);
        alert(`Error deleting asset: ${error.message}`);
      }
    }
  };

  const handleEdit = (asset) => {
    setEditingAssetId(asset.id);
    setEditedAsset({
      symbol: asset.symbol,
      name: asset.name,
      asset_type: asset.asset_type,
      portfolio_id: asset.portfolio_id,
    });
  };

  const handleSave = async (id) => {
    try {
      const response = await fetch(`/assets/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editedAsset),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setEditingAssetId(null);
      setEditedAsset({
        symbol: '',
        name: '',
        asset_type: '',
        portfolio_id: '',
      });
      fetchAssets(); // Refresh the list
      alert("Asset updated successfully!");
    } catch (error) {
      console.error("Error updating asset:", error);
      alert(`Error updating asset: ${error.message}`);
    }
  };

  const handleCancelEdit = () => {
    setEditingAssetId(null);
    setEditedAsset({
      symbol: '',
      name: '',
      asset_type: '',
      portfolio_id: '',
    });
  };

  const getPortfolioName = (portfolioId) => {
    const portfolio = portfolios.find(p => p.id === portfolioId);
    return portfolio ? portfolio.name : 'Unknown';
  };

  

  return (
    <div>
      <h2>Manage Assets</h2>

      <h3>Add New Asset</h3>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
        <FormControl fullWidth>
          <InputLabel id="country-select-label">Country</InputLabel>
          <Select
            labelId="country-select-label"
            value={selectedCountry}
            onChange={handleCountryChange}
            required
          >
            <MenuItem value="US">US (All)</MenuItem>
            <MenuItem value="KR">KR (KOSPI)</MenuItem>
            <MenuItem value="KOSDAQ">KR (KOSDAQ)</MenuItem>
          </Select>
        </FormControl>
        <TextField
          label="Symbol"
          value={selectedSymbol}
          onChange={handleSymbolChange}
          variant="outlined"
          fullWidth
          sx={{ mb: 2 }}
        />
        <TextField
          label="Name"
          value={selectedName}
          onChange={(e) => setSelectedName(e.target.value)}
          variant="outlined"
          fullWidth
          sx={{ mb: 2 }}
        />
        <Button type="submit" variant="contained" color="primary">
          Add Asset
        </Button>
        
      </form>

      <h3>Existing Assets</h3>
      <List>
        {assets.map((asset) => (
          <ListItem
            key={asset.id}
            secondaryAction={
              editingAssetId === asset.id ? (
                <>
                  <IconButton edge="end" aria-label="save" onClick={() => handleSave(asset.id)}>
                    <SaveIcon />
                  </IconButton>
                  <IconButton edge="end" aria-label="cancel" onClick={handleCancelEdit}>
                    <CancelIcon />
                  </IconButton>
                </>
              ) : (
                <>
                  <IconButton edge="end" aria-label="edit" onClick={() => handleEdit(asset)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(asset.id)}>
                    <DeleteIcon />
                  </IconButton>
                </>
              )
            }
          >
            {editingAssetId === asset.id ? (
              <>
                <TextField
                  label="Symbol"
                  value={editedAsset.symbol}
                  onChange={(e) => setEditedAsset({ ...editedAsset, symbol: e.target.value })}
                  variant="standard"
                  size="small"
                  sx={{ mr: 1 }}
                />
                <TextField
                  label="Name"
                  value={editedAsset.name}
                  onChange={(e) => setEditedAsset({ ...editedAsset, name: e.target.value })}
                  variant="standard"
                  size="small"
                  sx={{ mr: 1 }}
                />
                <TextField
                  label="Type"
                  value={editedAsset.asset_type}
                  onChange={(e) => setEditedAsset({ ...editedAsset, asset_type: e.target.value })}
                  variant="standard"
                  size="small"
                  sx={{ mr: 1 }}
                />
                <FormControl variant="standard" size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>Portfolio</InputLabel>
                  <Select
                    value={editedAsset.portfolio_id}
                    onChange={(e) => setEditedAsset({ ...editedAsset, portfolio_id: e.target.value })}
                    label="Portfolio"
                  >
                    {portfolios.map((portfolio) => (
                      <MenuItem key={portfolio.id} value={portfolio.id}>
                        {portfolio.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            ) : (
              <ListItemText primary={`${asset.symbol} - ${asset.name}`} secondary={asset.asset_type} />
            )}
          </ListItem>
        ))}
      </List>
    </div>
  );
}

export default Assets;
