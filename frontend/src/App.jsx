import React, { useState } from 'react';
import { Container, AppBar, Toolbar, Typography, Tabs, Tab, Card, CardContent, Button, Box } from '@mui/material';
import Transactions from './components/Transactions';
import Backtest from './components/Backtest';
import Portfolios from './components/Portfolios';
import PortfolioReturns from './components/PortfolioReturns';
import Assets from './components/Assets';
import LoginPopup from './components/LoginPopup';
import StrategyManager from './components/StrategyManager';
import './App.css';

function App() {
  const [selectedTab, setSelectedTab] = useState(0); // 0 for Portfolio Management, 1 for Backtesting & Strategies
  const [selectedPortfolioSubTab, setSelectedPortfolioSubTab] = useState(0); // 0: Portfolios, 1: Transactions, 2: Portfolio Returns, 3: Assets
  const [selectedBacktestSubTab, setSelectedBacktestSubTab] = useState(0); // 0: Backtest, 1: Strategies

  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(null);

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
    // Reset sub-tabs when main tab changes
    if (newValue === 0) {
      setSelectedPortfolioSubTab(0);
    } else {
      setSelectedBacktestSubTab(0);
    }
  };

  const handlePortfolioSubTabChange = (event, newValue) => {
    setSelectedPortfolioSubTab(newValue);
  };

  const handleBacktestSubTabChange = (event, newValue) => {
    setSelectedBacktestSubTab(newValue);
  };

  const handleLogin = async (appKey, appSecret) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/auth/token`, {
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
          <Tabs value={selectedTab} onChange={handleTabChange} textColor="inherit" indicatorColor="white" sx={{ marginLeft: -2 }}>
            <Tab label="Portfolio Management" />
            <Tab label="Backtesting & Strategies" />
          </Tabs>
          <Box sx={{ flexGrow: 1 }} /> {/* Spacer to push login button to the right */}
          {isAuthenticated ? (
            <Button color="inherit" onClick={handleLogout}>Logout</Button>
          ) : (
            <Button color="inherit" onClick={handleOpenLogin}>Login</Button>
          )}
        </Toolbar>
      </AppBar>
      <LoginPopup open={isLoginOpen} onClose={handleCloseLogin} onLogin={handleLogin} />
      {authError && <Typography color="error">{authError}</Typography>}


      <Card sx={{ marginTop: 0 }}>
        <CardContent>
          {selectedTab === 0 && ( // Portfolio Management
            <>
              <Tabs value={selectedPortfolioSubTab} onChange={handlePortfolioSubTabChange} sx={{ mb: 2 }}>
                <Tab label="Portfolios" />
                <Tab label="Transactions" />
                <Tab label="Portfolio Returns" />
                <Tab label="Assets" />
              </Tabs>
              {selectedPortfolioSubTab === 0 && <Portfolios />}
              {selectedPortfolioSubTab === 1 && <Transactions />}
              {selectedPortfolioSubTab === 2 && <PortfolioReturns />}
              {selectedPortfolioSubTab === 3 && <Assets />}
            </>
          )}

          {selectedTab === 1 && ( // Backtesting & Strategies
            <>
              <Tabs value={selectedBacktestSubTab} onChange={handleBacktestSubTabChange} sx={{ mb: 2 }}>
                <Tab label="Backtest" />
                <Tab label="Strategies" />
              </Tabs>
              {selectedBacktestSubTab === 0 && <Backtest />}
              {selectedBacktestSubTab === 1 && <StrategyManager />}
            </>
          )}
        </CardContent>
      </Card>
    </Container>
  );
}

export default App;