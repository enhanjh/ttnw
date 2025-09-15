#!/bin/bash
echo "Stopping backend server..."
lsof -t -i :8000 | xargs kill -9
echo "Backend server stopped."
