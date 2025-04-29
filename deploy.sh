#!/bin/bash
set -e

echo "Starting deployment process..."

# Pull latest changes
git pull origin main

# Activate virtual environment or create if doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Restart the Gunicorn service
echo "Restarting Gunicorn service..."
sudo systemctl restart safe_crossing

echo "Deployment completed successfully!" 