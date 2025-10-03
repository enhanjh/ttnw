import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    TextField, Button, List, ListItem, ListItemText, Paper, IconButton, Box, Typography,
    Select, MenuItem, InputLabel, FormControl, Grid, Dialog, DialogTitle, DialogContent, DialogActions,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';

import { fetchApi } from '../api';

const initialPortfolioFormState = {
    name: '',
    manager: '',
    environment: 'live',
    status: 'active',
    broker_provider: '',
    broker_account_no: '',
    strategy_id: '',
    allowed_telegram_ids: '', // Changed to string for comma-separated input
};

function descendingComparator(a, b, orderBy) {
    if (b[orderBy] < a[orderBy]) {
        return -1;
    }
    if (b[orderBy] > a[orderBy]) {
        return 1;
    }
    return 0;
}

function getComparator(order, orderBy) {
    return order === 'desc'
        ? (a, b) => descendingComparator(a, b, orderBy)
        : (a, b) => -descendingComparator(a, b, orderBy);
}

function stableSort(array, comparator) {
    const stabilizedThis = array.map((el, index) => [el, index]);
    stabilizedThis.sort((a, b) => {
        const order = comparator(a[0], b[0]);
        if (order !== 0) {
            return order;
        }
        return a[1] - b[1];
    });
    return stabilizedThis.map((el) => el[0]);
}

function Portfolios() {
    const [portfolios, setPortfolios] = useState([]);
    const [strategies, setStrategies] = useState([]);
    const [newPortfolio, setNewPortfolio] = useState(initialPortfolioFormState);
    const [editingPortfolio, setEditingPortfolio] = useState(null);
    const [isCreateFormVisible, setIsCreateFormVisible] = useState(false);
    
    // Holdings Modal State
    const [holdings, setHoldings] = useState([]);
    const [isHoldingsDialogVisible, setIsHoldingsDialogVisible] = useState(false);
    const [selectedPortfolioName, setSelectedPortfolioName] = useState('');
    
    // Sorting State
    const [order, setOrder] = useState('desc'); // Default desc for better view of returns/value
    const [orderBy, setOrderBy] = useState('current_value');

    const fetchPortfolios = useCallback(async () => {
        try {
            const data = await fetchApi('/api/portfolios/');
            setPortfolios(data);
        } catch (error) {
            console.error("Error fetching portfolios:", error);
        }
    }, []);

    const fetchStrategies = useCallback(async () => {
        try {
            const data = await fetchApi('/api/strategies/');
            setStrategies(data);
        } catch (error) {
            console.error("Error fetching strategies:", error);
        }
    }, []);

    const fetchHoldings = async (portfolioId, portfolioName) => {
        try {
            const data = await fetchApi(`/api/portfolios/${portfolioId}/holdings`);
            setHoldings(data);
            setSelectedPortfolioName(portfolioName);
            setIsHoldingsDialogVisible(true);
        } catch (error) {
            console.error("Error fetching holdings:", error);
            alert(`Error fetching holdings: ${error.message}`);
        }
    };

    const handleRequestSort = (property) => {
        const isAsc = orderBy === property && order === 'asc';
        setOrder(isAsc ? 'desc' : 'asc');
        setOrderBy(property);
    };

    const createSortHandler = (property) => (event) => {
        handleRequestSort(property);
    };

    // Calculate Totals
    const totalSummary = useMemo(() => {
        if (!holdings.length) return { totalInvestment: 0, totalValue: 0, totalProfitLoss: 0, totalReturnPct: 0 };
        
        let totalInvestment = 0;
        let totalValue = 0;

        holdings.forEach(h => {
            totalInvestment += (h.quantity * h.average_price);
            totalValue += h.current_value;
        });

        const totalProfitLoss = totalValue - totalInvestment;

        const totalReturnPct = totalInvestment > 0 
            ? (totalProfitLoss / totalInvestment) * 100 
            : 0;

        return { totalInvestment, totalValue, totalProfitLoss, totalReturnPct };
    }, [holdings]);


    useEffect(() => {
        fetchPortfolios();
        fetchStrategies();
    }, [fetchPortfolios, fetchStrategies]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setNewPortfolio(prev => ({ ...prev, [name]: value }));
    };
    
    const handleEditingChange = (e) => {
        const { name, value } = e.target;
        setEditingPortfolio(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!newPortfolio.name) return;

        const payload = { ...newPortfolio };
        if (!payload.strategy_id) {
            delete payload.strategy_id;
        }

        // Process allowed_telegram_ids string to array of integers
        if (typeof payload.allowed_telegram_ids === 'string') {
            payload.allowed_telegram_ids = payload.allowed_telegram_ids
                .split(',')
                .map(id => id.trim())
                .filter(id => id !== '' && !isNaN(id))
                .map(id => parseInt(id, 10));
        } else {
             payload.allowed_telegram_ids = [];
        }

        try {
            await fetchApi('/api/portfolios/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            setNewPortfolio(initialPortfolioFormState);
            fetchPortfolios();
            setIsCreateFormVisible(false);
            alert("Portfolio added successfully!");
        } catch (error) {
            console.error("Error adding portfolio:", error);
            alert(`Error adding portfolio: ${error.message}`);
        }
    };

    const handleDelete = async (id) => {
        if (window.confirm("Are you sure you want to delete this portfolio?")) {
            try {
                await fetchApi(`/api/portfolios/${id}`, { method: 'DELETE' });
                fetchPortfolios();
                alert("Portfolio deleted successfully!");
            } catch (error) {
                console.error("Error deleting portfolio:", error);
                alert(`Error deleting portfolio: ${error.message}`);
            }
        }
    };

    const handleEdit = (portfolio) => {
        setEditingPortfolio({
            ...portfolio,
            strategy_id: portfolio.strategy ? portfolio.strategy.id : '',
            allowed_telegram_ids: portfolio.allowed_telegram_ids ? portfolio.allowed_telegram_ids.join(', ') : ''
        });
    };

    const handleSave = async (id) => {
        if (!editingPortfolio) return;
        try {
            const updatePayload = { ...editingPortfolio };
            delete updatePayload.id;
            delete updatePayload.created_at;
            delete updatePayload.strategy; 
            
            if (!updatePayload.strategy_id) {
                updatePayload.strategy_id = null;
            }

            // Process allowed_telegram_ids string to array of integers
            if (typeof updatePayload.allowed_telegram_ids === 'string') {
                updatePayload.allowed_telegram_ids = updatePayload.allowed_telegram_ids
                    .split(',')
                    .map(id => id.trim())
                    .filter(id => id !== '' && !isNaN(id))
                    .map(id => parseInt(id, 10));
            } else if (Array.isArray(updatePayload.allowed_telegram_ids)) {
                 // Already an array (maybe didn't change), ensure it's integers if needed, 
                 // but typically input changes it to string. 
                 // If untouched, it might still be array if we initialized it that way, 
                 // but handleEdit converts to string.
                 // Just in case it comes as array:
                 updatePayload.allowed_telegram_ids = updatePayload.allowed_telegram_ids.map(id => parseInt(id, 10));
            }

            await fetchApi(`/api/portfolios/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatePayload),
            });
            setEditingPortfolio(null);
            fetchPortfolios();
            alert("Portfolio updated successfully!");
        } catch (error) {
            console.error("Error updating portfolio:", error);
            alert(`Error updating portfolio: ${error.message}`);
        }
    };

    const handleCancelEdit = () => {
        setEditingPortfolio(null);
    };

    const renderPortfolioForm = (portfolio, handleChange) => (
        <Grid container spacing={2} sx={{mt: 1}}>
            <Grid item xs={12} sm={6}>
                <TextField label="Portfolio Name" name="name" value={portfolio.name} onChange={handleChange} required fullWidth />
            </Grid>
            <Grid item xs={12} sm={6}>
                <TextField label="Manager" name="manager" value={portfolio.manager} onChange={handleChange} fullWidth />
            </Grid>
            <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                    <InputLabel>Environment</InputLabel>
                    <Select name="environment" value={portfolio.environment} label="Environment" onChange={handleChange}>
                        <MenuItem value="live">Live</MenuItem>
                        <MenuItem value="backtest">Backtest</MenuItem>
                    </Select>
                </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                    <InputLabel>Status</InputLabel>
                    <Select name="status" value={portfolio.status} label="Status" onChange={handleChange}>
                        <MenuItem value="active">Active</MenuItem>
                        <MenuItem value="inactive">Inactive</MenuItem>
                    </Select>
                </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
                <TextField label="Broker Provider" name="broker_provider" value={portfolio.broker_provider || ''} onChange={handleChange} fullWidth />
            </Grid>
            <Grid item xs={12} sm={6}>
                <TextField label="Broker Account No (or Alias)" name="broker_account_no" value={portfolio.broker_account_no || ''} onChange={handleChange} fullWidth />
            </Grid>
            <Grid item xs={12}>
                <TextField 
                    label="Allowed Telegram IDs (comma separated)" 
                    name="allowed_telegram_ids" 
                    value={portfolio.allowed_telegram_ids || ''} 
                    onChange={handleChange} 
                    fullWidth 
                    helperText="Enter Telegram IDs separated by commas (e.g., 123456, 987654)"
                />
            </Grid>
            <Grid item xs={12}>
                <FormControl fullWidth>
                    <InputLabel>Strategy</InputLabel>
                    <Select name="strategy_id" value={portfolio.strategy_id || ''} label="Strategy" onChange={handleChange}>
                        <MenuItem value=""><em>None</em></MenuItem>
                        {strategies.map(s => <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>)}
                    </Select>
                </FormControl>
            </Grid>
        </Grid>
    );

    return (
        <Box>
            <Typography variant="h5" gutterBottom>Manage Portfolios</Typography>
            
            <Button variant="contained" color="primary" onClick={() => setIsCreateFormVisible(true)} sx={{ mb: 2 }}>
                Create New Portfolio
            </Button>

            {/* Create Portfolio Dialog */}
            <Dialog open={isCreateFormVisible} onClose={() => setIsCreateFormVisible(false)} maxWidth="md" fullWidth>
                <DialogTitle>Create New Portfolio</DialogTitle>
                <form onSubmit={handleSubmit}>
                    <DialogContent>
                        {renderPortfolioForm(newPortfolio, handleInputChange)}
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setIsCreateFormVisible(false)}>Cancel</Button>
                        <Button type="submit" color="primary">Create</Button>
                    </DialogActions>
                </form>
            </Dialog>

            {/* Edit Portfolio Dialog */}
            <Dialog open={!!editingPortfolio} onClose={handleCancelEdit} maxWidth="md" fullWidth>
                <DialogTitle>Edit Portfolio</DialogTitle>
                {editingPortfolio && (
                    <>
                        <DialogContent>
                            {renderPortfolioForm(editingPortfolio, handleEditingChange)}
                        </DialogContent>
                        <DialogActions>
                            <Button onClick={handleCancelEdit}>Cancel</Button>
                            <Button onClick={() => handleSave(editingPortfolio.id)} color="primary">Save</Button>
                        </DialogActions>
                    </>
                )}
            </Dialog>

            {/* Holdings Dialog */}
            <Dialog open={isHoldingsDialogVisible} onClose={() => setIsHoldingsDialogVisible(false)} maxWidth="lg" fullWidth>
                <DialogTitle>Holdings: {selectedPortfolioName}</DialogTitle>
                <DialogContent>
                    {holdings.length === 0 ? (
                        <Typography>No holdings found or no transactions yet.</Typography>
                    ) : (
                        <>
                            {/* Summary Section */}
                            <Box sx={{ mb: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                                <Grid container spacing={2}>
                                    <Grid item xs={3}>
                                        <Typography variant="subtitle2" color="text.secondary">Total Investment</Typography>
                                        <Typography variant="h6">{totalSummary.totalInvestment.toLocaleString(undefined, { maximumFractionDigits: 0 })}</Typography>
                                    </Grid>
                                    <Grid item xs={3}>
                                        <Typography variant="subtitle2" color="text.secondary">Total Value</Typography>
                                        <Typography variant="h6">{totalSummary.totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</Typography>
                                    </Grid>
                                    <Grid item xs={3}>
                                        <Typography variant="subtitle2" color="text.secondary">Total P/L</Typography>
                                        <Typography variant="h6" sx={{ 
                                            color: totalSummary.totalProfitLoss > 0 ? 'red' : totalSummary.totalProfitLoss < 0 ? 'blue' : 'inherit',
                                            fontWeight: 'bold'
                                        }}>
                                            {totalSummary.totalProfitLoss.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                        </Typography>
                                    </Grid>
                                    <Grid item xs={3}>
                                        <Typography variant="subtitle2" color="text.secondary">Total Return</Typography>
                                        <Typography variant="h6" sx={{ 
                                            color: totalSummary.totalReturnPct > 0 ? 'red' : totalSummary.totalReturnPct < 0 ? 'blue' : 'inherit',
                                            fontWeight: 'bold'
                                        }}>
                                            {totalSummary.totalReturnPct.toFixed(2)}%
                                        </Typography>
                                    </Grid>
                                </Grid>
                            </Box>

                            {/* Sortable Table */}
                            <TableContainer component={Paper}>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell sortDirection={orderBy === 'symbol' ? order : false}>
                                                <TableSortLabel active={orderBy === 'symbol'} direction={orderBy === 'symbol' ? order : 'asc'} onClick={createSortHandler('symbol')}>
                                                    Symbol
                                                </TableSortLabel>
                                            </TableCell>
                                            <TableCell sortDirection={orderBy === 'name' ? order : false}>
                                                <TableSortLabel active={orderBy === 'name'} direction={orderBy === 'name' ? order : 'asc'} onClick={createSortHandler('name')}>
                                                    Name
                                                </TableSortLabel>
                                            </TableCell>
                                            <TableCell align="right" sortDirection={orderBy === 'quantity' ? order : false}>
                                                <TableSortLabel active={orderBy === 'quantity'} direction={orderBy === 'quantity' ? order : 'asc'} onClick={createSortHandler('quantity')}>
                                                    Qty
                                                </TableSortLabel>
                                            </TableCell>
                                            <TableCell align="right" sortDirection={orderBy === 'average_price' ? order : false}>
                                                <TableSortLabel active={orderBy === 'average_price'} direction={orderBy === 'average_price' ? order : 'asc'} onClick={createSortHandler('average_price')}>
                                                    Avg Price
                                                </TableSortLabel>
                                            </TableCell>
                                            <TableCell align="right" sortDirection={orderBy === 'current_price' ? order : false}>
                                                <TableSortLabel active={orderBy === 'current_price'} direction={orderBy === 'current_price' ? order : 'asc'} onClick={createSortHandler('current_price')}>
                                                    Cur Price
                                                </TableSortLabel>
                                            </TableCell>
                                            <TableCell align="right" sortDirection={orderBy === 'current_value' ? order : false}>
                                                <TableSortLabel active={orderBy === 'current_value'} direction={orderBy === 'current_value' ? order : 'asc'} onClick={createSortHandler('current_value')}>
                                                    Value
                                                </TableSortLabel>
                                            </TableCell>
                                            <TableCell align="right" sortDirection={orderBy === 'return_percentage' ? order : false}>
                                                <TableSortLabel active={orderBy === 'return_percentage'} direction={orderBy === 'return_percentage' ? order : 'asc'} onClick={createSortHandler('return_percentage')}>
                                                    Return %
                                                </TableSortLabel>
                                            </TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {stableSort(holdings, getComparator(order, orderBy)).map((row) => (
                                            <TableRow key={row.asset_id}>
                                                <TableCell>{row.symbol}</TableCell>
                                                <TableCell>{row.name}</TableCell>
                                                <TableCell align="right">{row.quantity.toLocaleString()}</TableCell>
                                                <TableCell align="right">{row.average_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</TableCell>
                                                <TableCell align="right">{row.current_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</TableCell>
                                                <TableCell align="right">{row.current_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</TableCell>
                                                <TableCell align="right" sx={{ 
                                                    color: row.return_percentage > 0 ? 'red' : row.return_percentage < 0 ? 'blue' : 'inherit',
                                                    fontWeight: 'bold'
                                                }}>
                                                    {row.return_percentage.toFixed(2)}%
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setIsHoldingsDialogVisible(false)}>Close</Button>
                </DialogActions>
            </Dialog>

            <Typography variant="h6" sx={{mt: 2}}>Existing Portfolios</Typography>
            <List component={Paper}>
                {portfolios.map((portfolio) => (
                    <ListItem key={portfolio.id} divider secondaryAction={
                        <>
                            <IconButton edge="end" aria-label="view holdings" onClick={() => fetchHoldings(portfolio.id, portfolio.name)} title="View Holdings">
                                <VisibilityIcon />
                            </IconButton>
                            <IconButton edge="end" aria-label="edit" onClick={() => handleEdit(portfolio)}>
                                <EditIcon />
                            </IconButton>
                            <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(portfolio.id)}>
                                <DeleteIcon />
                            </IconButton>
                        </>
                    }>
                        <ListItemText 
                            primary={portfolio.name}
                            secondary={
                                <React.Fragment>
                                    <Typography component="span" variant="body2" color="text.primary" sx={{ display: 'block' }}>
                                        Manager: {portfolio.manager || 'N/A'} | Status: {portfolio.status} | Env: {portfolio.environment}
                                    </Typography>
                                    <Typography component="span" variant="body2" color="text.secondary" sx={{ display: 'block' }}>
                                        Strategy: {portfolio.strategy ? portfolio.strategy.name : 'None'}
                                    </Typography>
                                    <Typography component="span" variant="body2" color="text.secondary" sx={{ display: 'block' }}>
                                        Broker: {portfolio.broker_provider || 'N/A'} - {portfolio.broker_account_no || 'N/A'}
                                    </Typography>
                                    <Typography component="span" variant="body2" color="text.secondary" sx={{ display: 'block' }}>
                                        Telegram IDs: {portfolio.allowed_telegram_ids && portfolio.allowed_telegram_ids.length > 0 ? portfolio.allowed_telegram_ids.join(', ') : 'None'}
                                    </Typography>
                                </React.Fragment>
                            }
                        />
                    </ListItem>
                ))}
            </List>
        </Box>
    );
}

export default Portfolios;