#!/bin/bash
echo "Stopping frontend server..."
lsof -t -i :3000 | xargs kill -9
echo "Frontend server stopped."
