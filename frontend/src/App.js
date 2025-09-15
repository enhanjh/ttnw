import React, { useState } from 'react';
import { Container, AppBar, Toolbar, Typography, Tabs, Tab, Card, CardContent, Button } from '@mui/material';
import Transactions from './components/Transactions';
import Backtest from './components/Backtest';
import Portfolios from './components/Portfolios';
import PortfolioReturns from './components/PortfolioReturns';
import LoginPopup from './components/LoginPopup';
import './App.css';

function App() {
  const [selectedTab, setSelectedTab] = useState(0);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(null);

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  const handleLogin = async (appKey, appSecret) => {
    try {
      const response = await fetch('/auth/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ appkey: appKey, appsecret: appSecret }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      setIsAuthenticated(true);
      setIsLoginOpen(false);
      setAuthError(null);
    } catch (error) {
      console.error("Authentication error:", error);
      setAuthError(error.message);
      alert(`Authentication failed: ${error.message}`);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
  };

  const handleOpenLogin = () => {
    setIsLoginOpen(true);
  };

  const handleCloseLogin = () => {
    setIsLoginOpen(false);
  };

  return (
    <Container>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Portfolio Manager
          </Typography>
          {isAuthenticated ? (
            <Button color="inherit" onClick={handleLogout}>Logout</Button>
          ) : (
            <Button color="inherit" onClick={handleOpenLogin}>Login</Button>
          )}
        </Toolbar>
      </AppBar>
      <LoginPopup open={isLoginOpen} onClose={handleCloseLogin} onLogin={handleLogin} />
      {authError && <Typography color="error">{authError}</Typography>}
      <Tabs value={selectedTab} onChange={handleTabChange} centered>
        <Tab label="Portfolios" />
        <Tab label="Transactions" />
        <Tab label="Portfolio Returns" />
        <Tab label="Backtest" />
      </Tabs>

      <Card sx={{ marginTop: 2 }}>
        <CardContent>
          {selectedTab === 0 && <Portfolios />}
          {selectedTab === 1 && <Transactions />}
          {selectedTab === 2 && <PortfolioReturns />}
          {selectedTab === 3 && <Backtest />}
        </CardContent>
      </Card>
    </Container>
  );
}

export default App;