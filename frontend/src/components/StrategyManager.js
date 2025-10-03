import React, { useState, useEffect, useCallback } from 'react';
import { TextField, Button, List, ListItem, ListItemText, Paper, IconButton, Box, Typography, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import { fetchApi } from '../api';

function StrategyManager() {
  const [strategies, setStrategies] = useState([]);
  const [newStrategy, setNewStrategy] = useState({
    name: '',
    description: '',
    strategy_type: '',
    parameters: {
      asset_weights: [],
      rebalancing_frequency: 'monthly',
      rebalancing_threshold: null,
      minimum_tradable_quantity: 1.0,
      expected_return: null,
      expected_std_dev: null,
      expected_mdd: null,
      expected_sharpe_ratio: null,
    },
  });
  const [editingStrategyId, setEditingStrategyId] = useState(null);
  const [editedStrategy, setEditedStrategy] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogMode, setDialogMode] = useState('add'); // 'add' or 'edit'
  const [assetWeightsError, setAssetWeightsError] = useState(null); // New state for asset weights error

  const fetchStrategies = useCallback(async () => {
    try {
      const data = await fetchApi('/api/strategies/');
      setStrategies(data);
    } catch (error) {
      console.error("Error fetching strategies:", error);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const handleNewStrategyChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('parameters.')) {
      const paramName = name.split('.')[1];
      setNewStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          [paramName]: value,
        },
      }));
    } else {
      setNewStrategy(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleEditedStrategyChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('parameters.')) {
      const paramName = name.split('.')[1];
      setEditedStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          [paramName]: value,
        },
      }));
    } else {
      setEditedStrategy(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleAddAsset = () => {
    if (dialogMode === 'add') {
      setNewStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          asset_weights: [...prev.parameters.asset_weights, { asset: '', asset_type: '', weight: '' }],
        },
      }));
    } else {
      setEditedStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          asset_weights: [...prev.parameters.asset_weights, { asset: '', weight: '' }],
        },
      }));
    }
  };

  const handleRemoveAsset = (index) => {
    if (dialogMode === 'add') {
      setNewStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          asset_weights: prev.parameters.asset_weights.filter((_, i) => i !== index),
        },
      }));
    } else {
      setEditedStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          asset_weights: prev.parameters.asset_weights.filter((_, i) => i !== index),
        },
      }));
    }
  };

  const handleAssetChange = (index, field, value) => {
    if (dialogMode === 'add') {
      setNewStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          asset_weights: prev.parameters.asset_weights.map((item, i) =>
            i === index ? { ...item, [field]: value } : item
          ),
        },
      }));
    } else {
      setEditedStrategy(prev => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          asset_weights: prev.parameters.asset_weights.map((item, i) =>
            i === index ? { ...item, [field]: value } : item
          ),
        },
      }));
    }
  };

  const handleAddClick = () => {
    setNewStrategy({
      name: '',
      description: '',
      strategy_type: '',
      parameters: {
        asset_weights: [],
        rebalancing_frequency: 'monthly',
        rebalancing_threshold: null,
        expected_return: null,
        expected_std_dev: null,
        expected_mdd: null,
        expected_sharpe_ratio: null,
      },
    });
    setAssetWeightsError(null); // Clear error on add
    setDialogMode('add');
    setOpenDialog(true);
  };

  const handleEditClick = (strategy) => {
    // Convert asset_weights object to an array of { asset, weight } for UI
    const assetWeightsArray = Object.entries(strategy.parameters.asset_weights || {}).map(([asset, weight]) => ({ asset, weight }));
    setEditedStrategy({
      ...strategy,
      parameters: {
        ...strategy.parameters,
        asset_weights: assetWeightsArray,
      },
    });
    setEditingStrategyId(strategy.id);
    setAssetWeightsError(null); // Clear error on edit
    setDialogMode('edit');
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStrategyId(null);
    setEditedStrategy(null);
    setAssetWeightsError(null); // Clear error on close
  };

  const handleSaveStrategy = async () => {
    let currentStrategy = dialogMode === 'add' ? newStrategy : editedStrategy;
    let assetWeightsObject = {};
    let hasAssetWeightsError = false;

    // Validate and convert asset_weights array to object
    if (currentStrategy.parameters.asset_weights && currentStrategy.parameters.asset_weights.length > 0) {
      for (const item of currentStrategy.parameters.asset_weights) {
        if (!item.asset.trim()) {
          setAssetWeightsError("Asset ticker cannot be empty.");
          hasAssetWeightsError = true;
          break;
        }
        const weight = parseFloat(item.weight);
        if (isNaN(weight) || weight < 0) { // Assuming weights cannot be negative
          setAssetWeightsError(`Invalid weight for asset '${item.asset}'. Must be a non-negative number.`);
          hasAssetWeightsError = true;
          break;
        }
        assetWeightsObject[item.asset.trim()] = weight;
      }
    }

    if (hasAssetWeightsError) {
      alert("Please correct the asset weights before saving.");
      return;
    }

    // Prepare the strategy object to send to the API
    const strategyToSave = {
      ...currentStrategy,
      parameters: {
        ...currentStrategy.parameters,
        asset_weights: assetWeightsObject,
      },
    };

    try {
      if (dialogMode === 'add') {
        await fetchApi('/api/strategies/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(strategyToSave),
        });
        alert('Strategy added successfully!');
      } else if (dialogMode === 'edit') {
        await fetchApi(`/api/strategies/${editingStrategyId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(strategyToSave),
        });
        alert('Strategy updated successfully!');
      }
      handleCloseDialog();
      fetchStrategies();
    } catch (error) {
      console.error("Error saving strategy:", error);
      alert(`Error saving strategy: ${error.message}`);
    }
  };

  const handleDeleteStrategy = async (id) => {
    if (window.confirm("Are you sure you want to delete this strategy?")) {
      try {
        await fetchApi(`/api/strategies/${id}`, {
          method: 'DELETE',
        });
        alert('Strategy deleted successfully!');
        fetchStrategies();
      } catch (error) {
        console.error("Error deleting strategy:", error);
        alert(`Error deleting strategy: ${error.message}`);
      }
    }
  };

  return (
    <Box sx={{ padding: 2 }}>
      <Typography variant="h5" gutterBottom>Manage Strategies</Typography>

      <Button
        variant="contained"
        startIcon={<AddIcon />}
        onClick={handleAddClick}
        sx={{ mb: 2 }}
      >
        Add New Strategy
      </Button>

      <List component={Paper} sx={{ width: '100%', bgcolor: 'background.paper' }}>
        {strategies.map((strategy) => (
          <ListItem
            key={strategy.id.toString()}
            secondaryAction={
              <>
                <IconButton edge="end" aria-label="edit" onClick={() => handleEditClick(strategy)}>
                  <EditIcon />
                </IconButton>
                <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteStrategy(strategy.id)}>
                  <DeleteIcon />
                </IconButton>
              </>
            }
          >
            <ListItemText
              primary={strategy.name}
              secondary={`Type: ${strategy.strategy_type} | Description: ${strategy.description || 'N/A'}`}
            />
          </ListItem>
        ))}
      </List>

      <Dialog open={openDialog} onClose={handleCloseDialog} fullWidth={true} maxWidth="md">
        <DialogTitle>{dialogMode === 'add' ? 'Add New Strategy' : 'Edit Strategy'}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            name="name"
            label="Strategy Name"
            type="text"
            fullWidth
            variant="standard"
            value={dialogMode === 'add' ? newStrategy.name : editedStrategy?.name || ''}
            onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            name="description"
            label="Description"
            type="text"
            fullWidth
            multiline
            rows={2}
            variant="standard"
            value={dialogMode === 'add' ? newStrategy.description : editedStrategy?.description || ''}
            onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
            <InputLabel>Strategy Type</InputLabel>
            <Select
              name="strategy_type"
              value={dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type || ''}
              label="Strategy Type"
              onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
            >
              <MenuItem value=""><em>None</em></MenuItem>
              <MenuItem value="buy_and_hold">Buy and Hold</MenuItem>
              <MenuItem value="moving_average_crossover">Moving Average Crossover</MenuItem>
              <MenuItem value="rebalancing">Rebalancing</MenuItem>
              <MenuItem value="momentum">Momentum</MenuItem>
              {/* Add more strategy types here */}
            </Select>
          </FormControl>



                    <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
                      {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) === 'momentum' ? 'Asset Pool' : 'Asset Weights'}
                    </Typography>
                    {(dialogMode === 'add' ? newStrategy.parameters.asset_weights : editedStrategy?.parameters?.asset_weights || []).map((aw, index) => (
                      <Box key={index} sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                        <TextField
                          margin="dense"
                          label="Asset Ticker"
                          type="text"
                          variant="standard"
                          value={aw.asset}
                          onChange={(e) => handleAssetChange(index, 'asset', e.target.value)}
                          sx={{ flex: 2 }}
                        />
                        <FormControl margin="dense" sx={{ flex: 1 }}>
                          <InputLabel>Asset Type</InputLabel>
                          <Select
                            value={aw.asset_type || ''} // Initialize with empty string if undefined
                            label="Asset Type"
                            onChange={(e) => handleAssetChange(index, 'asset_type', e.target.value)}
                          >
                            <MenuItem value="stock_us">Stock (US)</MenuItem>
                            <MenuItem value="stock_kr_kospi">Stock (KR - KOSPI)</MenuItem>
                            <MenuItem value="stock_kr_kosdaq">Stock (KR - KOSDAQ)</MenuItem>
                            <MenuItem value="cash">Cash</MenuItem>
                          </Select>
                        </FormControl>
                        {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) !== 'momentum' && (
                          <TextField
                            margin="dense"
                            label="Weight"
                            type="number"
                            variant="standard"
                            value={aw.weight}
                            onChange={(e) => handleAssetChange(index, 'weight', e.target.value)}
                            sx={{ flex: 1 }}
                          />
                        )}
                        <IconButton edge="end" aria-label="delete" onClick={() => handleRemoveAsset(index)}>
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    ))}          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAddAsset}
            sx={{ mt: 1, mb: 2 }}
          >
            Add Asset
          </Button>
          {assetWeightsError && (
            <Typography color="error" variant="body2" sx={{ mb: 2 }}>
              {assetWeightsError}
            </Typography>
          )}

          {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) === 'rebalancing' && (
            <>
              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel>Rebalancing Frequency</InputLabel>
                <Select
                  name="parameters.rebalancing_frequency"
                  value={dialogMode === 'add' ? newStrategy.parameters.rebalancing_frequency : editedStrategy?.parameters?.rebalancing_frequency || ''}
                  label="Rebalancing Frequency"
                  onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                >
                  <MenuItem value="monthly">Monthly</MenuItem>
                  <MenuItem value="quarterly">Quarterly</MenuItem>
                  <MenuItem value="annual">Annual</MenuItem>
                  <MenuItem value="never">Never</MenuItem>
                </Select>
              </FormControl>

              <TextField
                margin="dense"
                name="parameters.rebalancing_threshold"
                label="Rebalancing Threshold (e.g., 0.05 for 5%)"
                type="number"
                fullWidth
                variant="standard"
                value={dialogMode === 'add' ? (newStrategy.parameters.rebalancing_threshold || '') : (editedStrategy?.parameters?.rebalancing_threshold || '')}
                onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                sx={{ mb: 2 }}
              />
            </>
          )}

          {/* Add fields for strategy-specific parameters based on strategy_type if needed */}
          {/* For example, if strategy_type is 'moving_average_crossover' */}
          {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) === 'moving_average_crossover' && (
            <>
              <TextField
                margin="dense"
                name="parameters.moving_average_period_short"
                label="Short MA Period"
                type="number"
                fullWidth
                variant="standard"
                value={dialogMode === 'add' ? (newStrategy.parameters.moving_average_period_short || '') : (editedStrategy?.parameters?.moving_average_period_short || '')}
                onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                name="parameters.moving_average_period_long"
                label="Long MA Period"
                type="number"
                fullWidth
                variant="standard"
                value={dialogMode === 'add' ? (newStrategy.parameters.moving_average_period_long || '') : (editedStrategy?.parameters?.moving_average_period_long || '')}
                onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                sx={{ mb: 2 }}
              />
            </>
          )}

          {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) === 'momentum' && (
            <>
              <TextField
                margin="dense"
                name="parameters.lookback_period_months"
                label="Lookback Period (Months)"
                type="number"
                fullWidth
                variant="standard"
                value={dialogMode === 'add' ? (newStrategy.parameters.lookback_period_months || '') : (editedStrategy?.parameters?.lookback_period_months || '')}
                onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                name="parameters.top_n_assets"
                label="Number of Assets to Select"
                type="number"
                fullWidth
                variant="standard"
                value={dialogMode === 'add' ? (newStrategy.parameters.top_n_assets || '') : (editedStrategy?.parameters?.top_n_assets || '')}
                onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                name="parameters.risk_free_asset_ticker"
                label="Risk-Free Asset Ticker (e.g., DGS1 for 1-Year Treasury)"
                type="text"
                fullWidth
                variant="standard"
                value={dialogMode === 'add' ? (newStrategy.parameters.risk_free_asset_ticker || 'DGS1') : (editedStrategy?.parameters?.risk_free_asset_ticker || 'DGS1')}
                onChange={dialogMode === 'add' ? handleNewStrategyChange : handleEditedStrategyChange}
                sx={{ mb: 2 }}
              />
            </>
          )}

        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveStrategy}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default StrategyManager;
