import React, { useState, useEffect, useCallback } from 'react';
import {
    TextField, Button, List, ListItem, ListItemText, Paper, IconButton, Box, Typography,
    Select, MenuItem, InputLabel, FormControl, Grid, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';

import { fetchApi } from '../api';

const initialPortfolioFormState = {
    name: '',
    manager: '',
    environment: 'live',
    status: 'active',
    broker_provider: '',
    broker_account_no: '',
    strategy_id: '',
};

function Portfolios() {
    const [portfolios, setPortfolios] = useState([]);
    const [strategies, setStrategies] = useState([]);
    const [newPortfolio, setNewPortfolio] = useState(initialPortfolioFormState);
    const [editingPortfolio, setEditingPortfolio] = useState(null);
    const [isCreateFormVisible, setIsCreateFormVisible] = useState(false);

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
            strategy_id: portfolio.strategy ? portfolio.strategy.id : ''
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
                <TextField label="Broker Account No" name="broker_account_no" value={portfolio.broker_account_no || ''} onChange={handleChange} fullWidth />
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

            <Typography variant="h6" sx={{mt: 2}}>Existing Portfolios</Typography>
            <List component={Paper}>
                {portfolios.map((portfolio) => (
                    <ListItem key={portfolio.id} divider secondaryAction={
                        <>
                            <IconButton edge="end" aria-label="edit" onClick={() => handleEdit(portfolio)}><EditIcon /></IconButton>
                            <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(portfolio.id)}><DeleteIcon /></IconButton>
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
