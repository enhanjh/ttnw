import React, { useState } from 'react';
import { Modal, Box, Typography, TextField, Button } from '@mui/material';

const style = {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: 400,
  bgcolor: 'background.paper',
  border: '2px solid #000',
  boxShadow: 24,
  p: 4,
};

function LoginPopup({ open, onClose, onLogin }) {
  const [appKey, setAppKey] = useState('');
  const [appSecret, setAppSecret] = useState('');

  const handleLogin = () => {
    onLogin(appKey, appSecret);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="login-modal-title"
      aria-describedby="login-modal-description"
    >
      <Box sx={style}>
        <Typography id="login-modal-title" variant="h6" component="h2">
          Enter API Credentials
        </Typography>
        <TextField
          label="App Key"
          variant="outlined"
          value={appKey}
          onChange={(e) => setAppKey(e.target.value)}
          fullWidth
          sx={{ mt: 2 }}
        />
        <TextField
          label="App Secret"
          variant="outlined"
          type="password"
          value={appSecret}
          onChange={(e) => setAppSecret(e.target.value)}
          fullWidth
          sx={{ mt: 2 }}
        />
        <Button variant="contained" onClick={handleLogin} sx={{ mt: 2 }}>
          Login
        </Button>
      </Box>
    </Modal>
  );
}

export default LoginPopup;
