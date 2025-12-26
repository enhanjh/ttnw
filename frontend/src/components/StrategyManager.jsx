import React, { useState, useEffect, useCallback } from 'react';
import { Tooltip, Autocomplete, TextField, Button, List, ListItem, ListItemText, Paper, IconButton, Box, Typography, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import AddIcon from '@mui/icons-material/Add';
import { fetchApi } from '../api';

const defaultParameters = {
  asset_weights: [],
  rebalancing_frequency: 'monthly',
  rebalancing_threshold: null,
  minimum_tradable_quantity: 1.0,
  fundamental_conditions: [],
  re_evaluation_frequency: 'annual',
  fundamental_data_region: 'KR',
  top_n: 20,
  ranking_metric: 'market_cap',
  ranking_order: 'desc',
  expected_return: null,
  expected_std_dev: null,
  expected_mdd: null,
  expected_sharpe_ratio: null,
};

function StrategyManager() {
  const [strategies, setStrategies] = useState([]);
  const [newStrategy, setNewStrategy] = useState({
    name: '',
    description: '',
    strategy_type: '',
    parameters: defaultParameters,
  });
  const [editingStrategyId, setEditingStrategyId] = useState(null);
  const [editedStrategy, setEditedStrategy] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogMode, setDialogMode] = useState('add'); // 'add' or 'edit'
  const [assetWeightsError, setAssetWeightsError] = useState(null); // New state for asset weights error
  const [globalAssets, setGlobalAssets] = useState([]); // New state for global assets

  useEffect(() => {
    const fetchGlobalAssets = async () => {
      try {
        const data = await fetchApi('/api/assets/');
        setGlobalAssets(data);
      } catch (error) {
        console.error("Error fetching global assets:", error);
      }
    };
    fetchGlobalAssets();
  }, []);

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

  const getStrategyUpdater = () => (dialogMode === 'add' ? setNewStrategy : setEditedStrategy);

  const handleStrategyChange = (e) => {
    const { name, value } = e.target;
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => {
      if (name.startsWith('parameters.')) {
        const paramName = name.split('.')[1];
        return {
          ...prev,
          parameters: {
            ...prev.parameters,
            [paramName]: value,
          },
        };
      }
      return { ...prev, [name]: value };
    });
  };

  const handleAddAsset = () => {
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        asset_weights: [...prev.parameters.asset_weights, { asset: '', asset_type: '', weight: '' }],
      },
    }));
  };

  const handleRemoveAsset = (index) => {
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        asset_weights: prev.parameters.asset_weights.filter((_, i) => i !== index),
      },
    }));
  };

  const handleAssetChange = (index, field, value) => {
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        asset_weights: prev.parameters.asset_weights.map((item, i) =>
          i === index ? { ...item, [field]: value } : item
        ),
      },
    }));
  };

  const handleAddFundamentalCondition = () => {
    const newCondition = {
      value_metric: '',
      comparison_metric: '',
      comparison_operator: '>',
      comparison_multiplier: 1.0,
    };
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        fundamental_conditions: [...(prev.parameters.fundamental_conditions || []), newCondition],
      },
    }));
  };

  const handleRemoveFundamentalCondition = (index) => {
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        fundamental_conditions: prev.parameters.fundamental_conditions.filter((_, i) => i !== index),
      },
    }));
  };

  const handleFundamentalConditionChange = (index, field, value) => {
    const stateSetter = getStrategyUpdater();
    stateSetter(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        fundamental_conditions: prev.parameters.fundamental_conditions.map((item, i) =>
          i === index ? { ...item, [field]: value } : item
        ),
      },
    }));
  };

  const handleAddClick = () => {
    setNewStrategy({
      name: '',
      description: '',
      strategy_type: '',
      parameters: defaultParameters,
    });
    setAssetWeightsError(null); // Clear error on add
    setDialogMode('add');
    setOpenDialog(true);
  };

  const handleDuplicateClick = (strategyToDuplicate) => {
    // Create a deep copy to avoid any nested object reference issues.
    const duplicatedStrategyData = JSON.parse(JSON.stringify(strategyToDuplicate));

    // Modify the name for the new strategy
    duplicatedStrategyData.name = `${duplicatedStrategyData.name} (Copy)`;
    
    // Set the `newStrategy` state with this copied data.
    // The 'id' will be ignored when saving as a new strategy.
    setNewStrategy(duplicatedStrategyData);
    
    // Set the dialog mode to 'add' and open it for the user to confirm/edit.
    setAssetWeightsError(null);
    setDialogMode('add');
    setOpenDialog(true);
  };

  const handleEditClick = (strategy) => {
    // The asset_weights from the backend is now an array of objects, which matches the UI state.
    // We just need to make sure it's an array and handle old data that might not be an array.
    const assetWeightsArray = Array.isArray(strategy.parameters.asset_weights) ? strategy.parameters.asset_weights : [];
    const fundamentalConditionsArray = Array.isArray(strategy.parameters.fundamental_conditions) ? strategy.parameters.fundamental_conditions : [];
    setEditedStrategy({
      ...strategy,
      parameters: {
        ...strategy.parameters,
        asset_weights: assetWeightsArray,
        fundamental_conditions: fundamentalConditionsArray,
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
    let hasAssetWeightsError = false;

    // Create a deep copy to avoid mutating the state directly
    const strategyToSave = JSON.parse(JSON.stringify(currentStrategy));

    // Validate and parse asset_weights array
    if (strategyToSave.parameters.asset_weights && strategyToSave.parameters.asset_weights.length > 0) {
      const isMomentum = strategyToSave.strategy_type === 'momentum';
      for (const item of strategyToSave.parameters.asset_weights) {
        if (!item.asset.trim()) {
          setAssetWeightsError("Asset ticker cannot be empty.");
          hasAssetWeightsError = true;
          break;
        }
        if (!isMomentum) {
            const weight = parseFloat(item.weight);
            if (isNaN(weight) || weight < 0) {
              setAssetWeightsError(`Invalid weight for asset '${item.asset}'. Must be a non-negative number.`);
              hasAssetWeightsError = true;
              break;
            }
            item.weight = weight; // Update item weight to be a number
        } else {
            item.weight = null; // Ensure weight is null for momentum strategy
        }
      }
    }

    if (hasAssetWeightsError) {
      alert("Please correct the asset weights before saving.");
      return;
    }

    // Validate fundamental conditions
    if (strategyToSave.strategy_type === 'fundamental_indicator' && strategyToSave.parameters.fundamental_conditions) {
      for (const condition of strategyToSave.parameters.fundamental_conditions) {
        if (!condition.value_metric) {
          setAssetWeightsError("Value Metric cannot be empty in fundamental conditions.");
          hasAssetWeightsError = true;
          break;
        }
        if (!condition.comparison_metric) {
          setAssetWeightsError("Comparison Metric cannot be empty in fundamental conditions.");
          hasAssetWeightsError = true;
          break;
        }
        if (!condition.comparison_operator) {
          setAssetWeightsError("Comparison Operator cannot be empty in fundamental conditions.");
          hasAssetWeightsError = true;
          break;
        }
        const multiplier = parseFloat(condition.comparison_multiplier); // Parse here as it's stored as string
        if (isNaN(multiplier) && condition.comparison_multiplier !== null) { // Check for NaN only if not null
          setAssetWeightsError("Multiplier must be a valid number in fundamental conditions.");
          hasAssetWeightsError = true;
          break;
        }
        condition.comparison_multiplier = multiplier; // Ensure it's a number
      }
    }

    // Sanitize other numeric parameter fields
    const numericFields = [
      'rebalancing_threshold',
      'moving_average_period_short',
      'moving_average_period_long',
      'lookback_period_months',
      'top_n_assets',
    ];

    for (const field of numericFields) {
        const value = strategyToSave.parameters[field];
        if (value === '' || value === null || value === undefined) {
            strategyToSave.parameters[field] = null;
        } else if (typeof value === 'string') {
            const parsed = parseFloat(value);
            strategyToSave.parameters[field] = isNaN(parsed) ? null : parsed;
        }
    }

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
                <IconButton edge="end" aria-label="duplicate" onClick={() => handleDuplicateClick(strategy)}>
                  <ContentCopyIcon />
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
            onChange={handleStrategyChange}
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
            onChange={handleStrategyChange}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
            <InputLabel>Strategy Type</InputLabel>
            <Select
              name="strategy_type"
              value={dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type || ''}
              label="Strategy Type"
              onChange={handleStrategyChange}
            >
              <MenuItem value=""><em>None</em></MenuItem>
              <MenuItem value="buy_and_hold">Buy and Hold</MenuItem>
              <MenuItem value="moving_average_crossover">Moving Average Crossover</MenuItem>
              <MenuItem value="asset_allocation">Asset Allocation</MenuItem>
              <MenuItem value="momentum">Momentum</MenuItem>
              <MenuItem value="fundamental_indicator">Fundamental Value</MenuItem>
              {/* Add more strategy types here */}
            </Select>
          </FormControl>



          {/* Asset Weights / Asset Pool Section (Hidden for Fundamental Indicator) */}
          {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) !== 'fundamental_indicator' && (
            <>
              {(dialogMode === 'add' ? newStrategy.parameters.asset_weights : editedStrategy?.parameters?.asset_weights || []).map((aw, index) => (
                <Box key={index} sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                  <Autocomplete
                    options={globalAssets}
                    getOptionLabel={(option) => option.symbol ? `${option.symbol} - ${option.name}` : ''}
                    value={globalAssets.find(asset => asset.symbol === aw.asset) || null}
                    onChange={(event, newValue) => {
                      handleAssetChange(index, 'asset', newValue ? newValue.symbol : '');
                      handleAssetChange(index, 'asset_type', newValue ? newValue.asset_type : '');
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        margin="dense"
                        label="Asset Ticker"
                        variant="standard"
                        sx={{ flex: 2 }}
                      />
                    )}
                    sx={{ flex: 2 }}
                  />
                  <TextField
                    margin="dense"
                    label="Asset Type"
                    variant="standard"
                    value={aw.asset_type || ''}
                    InputProps={{ readOnly: true }} // Make it read-only
                    sx={{ flex: 1 }}
                  />
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
              ))}
              <Button
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
            </>
          )}

          {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) === 'asset_allocation' && (
            <>
              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel>Rebalancing Frequency</InputLabel>
                <Select
                  name="parameters.rebalancing_frequency"
                  value={dialogMode === 'add' ? newStrategy.parameters.rebalancing_frequency : editedStrategy?.parameters?.rebalancing_frequency || ''}
                  label="Rebalancing Frequency"
                  onChange={handleStrategyChange}
                >
                  <MenuItem value="always">Always (Debug/Test)</MenuItem>
                  <MenuItem value="daily">Daily</MenuItem>
                  <MenuItem value="weekly">Weekly</MenuItem>
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
                onChange={handleStrategyChange}
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
                onChange={handleStrategyChange}
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
                onChange={handleStrategyChange}
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
                onChange={handleStrategyChange}
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
                onChange={handleStrategyChange}
                sx={{ mb: 2 }}
              />
              <Tooltip title={
                <>
                  <Typography variant="subtitle2" gutterBottom>Available FRED Tickers:</Typography>
                  <ul>
                    <li>DGS1MO (1-Month)</li>
                    <li>DGS3MO (3-Month)</li>
                    <li>DGS6MO (6-Month)</li>
                    <li>DGS1 (1-Year)</li>
                    <li>DGS2 (2-Year)</li>
                    <li>DGS3 (3-Year)</li>
                    <li>DGS5 (5-Year)</li>
                    <li>DGS7 (7-Year)</li>
                    <li>DGS10 (10-Year)</li>
                    <li>DGS20 (20-Year)</li>
                    <li>DGS30 (30-Year)</li>
                  </ul>
                </>
              }>
                <TextField
                  margin="dense"
                  name="parameters.risk_free_asset_ticker"
                  label="Risk-Free Asset Ticker (e.g., DGS1 for 1-Year Treasury)"
                  type="text"
                  fullWidth
                  variant="standard"
                  value={dialogMode === 'add' ? (newStrategy.parameters.risk_free_asset_ticker || 'DGS1') : (editedStrategy?.parameters?.risk_free_asset_ticker || 'DGS1')}
                  onChange={handleStrategyChange}
                  sx={{ mb: 2 }}
                />
              </Tooltip>
            </>
          )}

          {(dialogMode === 'add' ? newStrategy.strategy_type : editedStrategy?.strategy_type) === 'fundamental_indicator' && (
            <>
              <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Fundamental Conditions</Typography>
              {(dialogMode === 'add' ? newStrategy.parameters.fundamental_conditions : editedStrategy?.parameters?.fundamental_conditions || []).map((condition, index) => (
                <Box key={index} sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                  <FormControl sx={{ flex: 2 }}>
                    <InputLabel>Value Metric</InputLabel>
                    <Select
                      name="value_metric"
                      value={condition.value_metric || ''}
                      label="Value Metric"
                      onChange={(e) => handleFundamentalConditionChange(index, 'value_metric', e.target.value)}
                    >
                      <MenuItem value="current_assets">Current Assets</MenuItem>
                      <MenuItem value="total_liabilities">Total Liabilities</MenuItem>
                      <MenuItem value="net_income">Net Income</MenuItem>
                      <MenuItem value="eps">EPS</MenuItem>
                      <MenuItem value="net_current_asset_value">Net Current Asset Value</MenuItem>
                      {/* Add more options as needed */}
                    </Select>
                  </FormControl>
                  <FormControl sx={{ flex: 1 }}>
                    <InputLabel>Operator</InputLabel>
                    <Select
                      name="comparison_operator"
                      value={condition.comparison_operator || ''}
                      label="Operator" 
                      onChange={(e) => handleFundamentalConditionChange(index, 'comparison_operator', e.target.value)}
                    >
                      <MenuItem value=">">&gt;</MenuItem>
                      <MenuItem value="<">&lt;</MenuItem>
                      <MenuItem value=">=">&gt;=</MenuItem>
                      <MenuItem value="<=">&lt;=</MenuItem>
                      <MenuItem value="=">=</MenuItem>
                    </Select>
                  </FormControl>
                  <FormControl sx={{ flex: 2 }}>
                    <InputLabel>Comparison Metric</InputLabel>
                    <Select
                      name="comparison_metric"
                      value={condition.comparison_metric || ''}
                      label="Comparison Metric"
                      onChange={(e) => handleFundamentalConditionChange(index, 'comparison_metric', e.target.value)}
                    >
                      <MenuItem value="market_cap">Market Cap</MenuItem>
                      <MenuItem value="current_assets">Current Assets</MenuItem>
                      <MenuItem value="total_liabilities">Total Liabilities</MenuItem>
                      <MenuItem value="net_income">Net Income</MenuItem>
                      <MenuItem value="eps">EPS</MenuItem>
                      <MenuItem value="constant">Constant</MenuItem>
                      {/* Add more options as needed */}
                    </Select>
                  </FormControl>
                  <TextField
                    margin="dense"
                    label="Multiplier"
                    type="text" // Changed to text to allow more flexible input
                    variant="standard"
                    value={condition.comparison_multiplier === null ? '' : condition.comparison_multiplier}
                    onChange={(e) => handleFundamentalConditionChange(index, 'comparison_multiplier', e.target.value === '' ? null : e.target.value)}
                    sx={{ flex: 1 }}
                  />
                  <IconButton edge="end" aria-label="delete" onClick={() => handleRemoveFundamentalCondition(index)}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
              ))}
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={handleAddFundamentalCondition}
                sx={{ mt: 1, mb: 2 }}
              >
                Add Condition
              </Button>

              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel>Re-evaluation Frequency</InputLabel>
                <Select
                  name="parameters.re_evaluation_frequency"
                  value={dialogMode === 'add' ? newStrategy.parameters.re_evaluation_frequency : editedStrategy?.parameters?.re_evaluation_frequency || ''}
                  label="Re-evaluation Frequency"
                  onChange={handleStrategyChange}
                >
                  <MenuItem value="annual">Annual</MenuItem>
                  <MenuItem value="quarterly">Quarterly</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel>Fundamental Data Region</InputLabel>
                <Select
                  name="parameters.fundamental_data_region"
                  value={dialogMode === 'add' ? newStrategy.parameters.fundamental_data_region : editedStrategy?.parameters?.fundamental_data_region || ''}
                  label="Fundamental Data Region"
                  onChange={handleStrategyChange}
                >
                  <MenuItem value="KR">South Korea (Open DART)</MenuItem>
                  <MenuItem value="US">United States (Placeholder)</MenuItem>
                </Select>
              </FormControl>

              {/* New fields for Top N */}
              <TextField
                margin="dense"
                name="parameters.top_n"
                label="Number of Top Assets (N)"
                type="number"
                fullWidth
                variant="standard"
                onChange={handleStrategyChange}
                sx={{ mb: 2 }}
              />

              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel>Ranking Metric</InputLabel>
                <Select
                  name="parameters.ranking_metric"
                  value={dialogMode === 'add' ? newStrategy.parameters.ranking_metric : editedStrategy?.parameters?.ranking_metric || ''}
                  label="Ranking Metric"
                  onChange={handleStrategyChange}
                >
                  <MenuItem value="market_cap">Market Cap</MenuItem>
                  {/* Add more ranking metrics here */}
                </Select>
              </FormControl>
              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel>Ranking Order</InputLabel>
                <Select
                  name="parameters.ranking_order"
                  value={dialogMode === 'add' ? newStrategy.parameters.ranking_order : editedStrategy?.parameters?.ranking_order || ''}
                  label="Ranking Order"
                  onChange={handleStrategyChange}
                >
                  <MenuItem value="desc">Descending (High to Low)</MenuItem>
                  <MenuItem value="asc">Ascending (Low to High)</MenuItem>
                </Select>
              </FormControl>
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