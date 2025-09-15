#!/bin/bash
echo "Starting backend server..."
cd /Users/Amy/ttnw/portfolio_manager
source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
echo "Backend server started in background."
