#!/bin/bash

# Build the Docker images
echo "Building Docker images..."
docker-compose build

# Run the Docker Compose service
echo "Running 'sermon-processor' Docker service..."
docker-compose run --rm --name sermon-processor sermon-processor 

echo ""
echo "---"
echo "Cleaning up dangling Docker images..."
docker image prune -f

echo "Operation completed."
