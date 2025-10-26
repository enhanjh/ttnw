#!/bin/bash

# This script starts the backend and frontend development servers for local testing,
# redirecting their output to separate log files.

# Create a log directory if it doesn't exist
mkdir -p logs

# Function to be called when the script is interrupted (Ctrl+C)
cleanup() {
    echo ""
    echo "Shutting down all servers..."
    # Kill all child processes spawned by this script.
    if [ -n "$BACKEND_PID" ]; then kill $BACKEND_PID; fi
    if [ -n "$FRONTEND_PID" ]; then kill $FRONTEND_PID; fi
    echo "Servers stopped."
}

# Register the cleanup function to be called on script exit.
trap cleanup EXIT

# --- Check for required .env files ---
if [ ! -f .env ]; then
    echo "ERROR: Backend .env file not found!"
    exit 1
fi

# --- Start Backend Server ---
echo "Starting backend server... Logs are in logs/backend.log"
(
    # Activate venv from the root directory
    source ttnw/bin/activate && \
    # Run uvicorn from the root, specifying the app as a module path
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --log-level debug
) > logs/backend.log 2>&1 &
BACKEND_PID=$!

# --- Start Frontend Server ---
echo "Starting frontend server... Logs are in logs/frontend.log"
(
    cd frontend && npm start
) > logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "Servers are starting in the background."

echo "To view logs in real-time, use the following commands in a new terminal:"
echo "  Backend:  tail -f logs/backend.log"
echo "  Frontend: tail -f logs/frontend.log"
echo ""
echo "Press Ctrl+C here to shut down all servers."

# Wait for any background process to exit. The trap will handle cleanup.
wait
