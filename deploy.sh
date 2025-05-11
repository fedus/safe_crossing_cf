#!/bin/bash
set -e

echo "Starting deployment process..."

# Pull latest changes from the development branch
git fetch origin
git checkout flask-docker-production
git pull origin flask-docker-production

# Build and restart the Docker containers
echo "Building and restarting Docker containers..."
docker compose down
docker compose build
docker compose up -d

# Run database migrations
echo "Running database migrations..."
docker compose exec web flask db upgrade

echo "Deployment completed successfully!"

# Show the logs
echo "Showing container logs..."
docker compose logs -f 