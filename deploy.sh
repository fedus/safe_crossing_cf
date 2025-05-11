#!/bin/bash
set -e

echo "Starting deployment process..."

# Pull latest changes from the feature branch
git fetch origin
git checkout feature/city-completion-v2
git pull origin feature/city-completion-v2

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

# Follow the logs
echo "Following service logs..."
sudo journalctl -u safe_crossing -f 