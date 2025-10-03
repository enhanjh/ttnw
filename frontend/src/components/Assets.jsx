import React, { useState, useEffect, useCallback } from 'react';
import {
    Box, TextField, Button, Select, MenuItem, InputLabel, FormControl, IconButton,
    List, ListItem, ListItemText
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import { fetchApi } from '../api';

function Assets() {
  const [assets, setAssets] = useState([]);
  
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [selectedName, setSelectedName] = useState('');
  const [selectedCountry, setSelectedCountry] = useState('US'); // Default to US
  const [newMinTradeQty, setNewMinTradeQty] = useState(1.0);
  const [editingAssetId, setEditingAssetId] = useState(null);
  const [editedAsset, setEditedAsset] = useState({
    symbol: '',
    name: '',
    asset_type: '',
    portfolio_id: '',
    minimum_tradable_quantity: 1.0,
  });

  const fetchAssets = useCallback(async () => {
    try {
      const data = await fetchApi(`/api/assets/`);
      setAssets(data);
    } catch (error) {
      console.error("Error fetching assets:", error);
    }
  }, []);



  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

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
      alert('Please select a symbol.');
      return;
    }

    const newAsset = {
      symbol: selectedSymbol,
      name: selectedName,
      asset_type: selectedCountry === 'US' ? 'stock_us' : (selectedCountry === 'KR' ? 'stock_kr_kospi' : 'stock_kr_kosdaq'),
      minimum_tradable_quantity: parseFloat(newMinTradeQty),
    };

    try {
      await fetchApi('/api/assets/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newAsset),
      });
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
        await fetchApi(`/api/assets/${id}`, {
          method: 'DELETE',
        });
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
      minimum_tradable_quantity: asset.minimum_tradable_quantity || 1.0,
    });
  };

  const handleSave = async (id) => {
    try {
      await fetchApi(`/api/assets/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editedAsset),
      });
      setEditingAssetId(null);
      setEditedAsset({
        symbol: '',
        name: '',
        asset_type: '',
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
      minimum_tradable_quantity: 1.0,
    });
  };



  

  return (
    <div>
      <h2>Manage Assets</h2>

      <h3>Add New Asset</h3>
      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
        <FormControl sx={{ minWidth: 150 }}>
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
        />
        <TextField
          label="Name"
          value={selectedName}
          onChange={(e) => setSelectedName(e.target.value)}
          variant="outlined"
        />
        <TextField
          label="Min. Trade Qty"
          type="number"
          value={newMinTradeQty}
          onChange={(e) => setNewMinTradeQty(e.target.value)}
          variant="outlined"
          sx={{ width: 150 }}
        />
        <Button type="submit" variant="contained" color="primary" sx={{ ml: 'auto' }}>
          Add Asset
        </Button>
      </Box>

      <h3>Existing Assets</h3>
      <List>
        {assets.map((asset) => (
          <ListItem
            key={asset.id.toString()}
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

                <TextField
                  label="Min. Trade Qty"
                  type="number"
                  value={editedAsset.minimum_tradable_quantity}
                  onChange={(e) => setEditedAsset({ ...editedAsset, minimum_tradable_quantity: e.target.value })}
                  variant="standard"
                  size="small"
                  sx={{ mr: 1, width: 150 }}
                />
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
