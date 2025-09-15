import React, { useState, useEffect } from 'react';
import { TextField, Button, List, ListItem, ListItemText, Paper, IconButton, Box, Typography } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import Assets from './Assets'; // Import Assets component

function Portfolios() {
  const [portfolios, setPortfolios] = useState([]);
  const [newPortfolioName, setNewPortfolioName] = useState('');
  const [editingPortfolioId, setEditingPortfolioId] = useState(null);
  const [editedPortfolioName, setEditedPortfolioName] = useState('');
  const [selectedPortfolioId, setSelectedPortfolioId] = useState(null); // New state for selected portfolio

  useEffect(() => {
    fetchPortfolios();
  }, []);

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

  const handleInputChange = (e) => {
    setNewPortfolioName(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newPortfolioName) return;

    try {
      const response = await fetch('/portfolios/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newPortfolioName }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setNewPortfolioName('');
      fetchPortfolios(); // Refresh the list
      alert("Portfolio added successfully!");
    } catch (error) {
      console.error("Error adding portfolio:", error);
      alert(`Error adding portfolio: ${error.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this portfolio?")) {
      try {
        const response = await fetch(`/portfolios/${id}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        fetchPortfolios(); // Refresh the list
        alert("Portfolio deleted successfully!");
        if (selectedPortfolioId === id) {
          setSelectedPortfolioId(null); // Deselect if the deleted portfolio was selected
        }
      } catch (error) {
        console.error("Error deleting portfolio:", error);
        alert(`Error deleting portfolio: ${error.message}`);
      }
    }
  };

  const handleEdit = (portfolio) => {
    setEditingPortfolioId(portfolio.id);
    setEditedPortfolioName(portfolio.name);
  };

  const handleSave = async (id) => {
    try {
      const response = await fetch(`/portfolios/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: editedPortfolioName }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setEditingPortfolioId(null);
      setEditedPortfolioName('');
      fetchPortfolios(); // Refresh the list
      alert("Portfolio updated successfully!");
    } catch (error) {
      console.error("Error updating portfolio:", error);
      alert(`Error updating portfolio: ${error.message}`);
    }
  };

  const handleCancelEdit = () => {
    setEditingPortfolioId(null);
    setEditedPortfolioName('');
  };

  const handlePortfolioClick = (portfolioId) => {
    setSelectedPortfolioId(portfolioId);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Manage Portfolios</Typography>

      {!selectedPortfolioId ? (
        <Box>
          <Typography variant="h6">Create New Portfolio</Typography>
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <TextField
              label="Portfolio Name"
              variant="outlined"
              value={newPortfolioName}
              onChange={handleInputChange}
              required
              fullWidth
            />
            <Button type="submit" variant="contained" color="primary">
              Create Portfolio
            </Button>
          </form>

          <Typography variant="h6">Existing Portfolios</Typography>
          <List component={Paper} sx={{ width: '100%', bgcolor: 'background.paper' }}>
            {portfolios.map((portfolio) => (
              <ListItem
                key={portfolio.id}
                secondaryAction={
                  <>
                    <Button variant="outlined" onClick={() => handlePortfolioClick(portfolio.id)} sx={{ mr: 1 }}>
                      Manage Assets
                    </Button>
                    {editingPortfolioId === portfolio.id ? (
                      <>
                        <IconButton edge="end" aria-label="save" onClick={() => handleSave(portfolio.id)}>
                          <SaveIcon />
                        </IconButton>
                        <IconButton edge="end" aria-label="cancel" onClick={handleCancelEdit}>
                          <CancelIcon />
                        </IconButton>
                      </>
                    ) : (
                      <>
                        <IconButton edge="end" aria-label="edit" onClick={() => handleEdit(portfolio)}>
                          <EditIcon />
                        </IconButton>
                        <IconButton edge="end" aria-label="delete" onClick={() => handleDelete(portfolio.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </>
                    )}
                  </>
                }
              >
                {editingPortfolioId === portfolio.id ? (
                  <TextField
                    value={editedPortfolioName}
                    onChange={(e) => setEditedPortfolioName(e.target.value)}
                    variant="standard"
                    fullWidth
                  />
                ) : (
                  <ListItemText primary={portfolio.name} secondary={`Created: ${new Date(portfolio.created_at).toLocaleDateString()}`} />
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      ) : (
        <Box>
          <Button variant="outlined" onClick={() => setSelectedPortfolioId(null)} sx={{ mb: 2 }}>
            Back to Portfolios
          </Button>
          <Assets portfolioId={selectedPortfolioId} />
        </Box>
      )}
    </Box>
  );
}

export default Portfolios;
