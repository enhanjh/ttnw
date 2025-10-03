#!/bin/bash
echo "Activating 'ttnw' virtual environment and starting scheduler..."

source /opt/ttnw/ttnw/bin/activate

python workers/scheduler.py

# deactivate