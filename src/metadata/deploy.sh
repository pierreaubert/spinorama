#!/bin/bash
# Deployment script for Speaker Metadata Manager

set -e

echo "Building Speaker Metadata Manager..."

# Build the application
npm run build

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "Error: Build failed - dist directory not found"
    exit 1
fi

echo "Build completed successfully"

# Define deployment paths
PROD_PATH="./dist"
# PROD_PATH="/var/www/html/spinorama-prod"
METADATA_MANAGER_PATH="$PROD_PATH/metadata-manager"

echo "Deploying to production..."

# Create metadata-manager directory if it doesn't exist
sudo mkdir -p "$METADATA_MANAGER_PATH"

# Copy built files to production
sudo cp -r dist/* "$METADATA_MANAGER_PATH/"

# Set proper permissions
sudo chown -R www-data:www-data "$METADATA_MANAGER_PATH"
sudo chmod -R 644 "$METADATA_MANAGER_PATH"
sudo find "$METADATA_MANAGER_PATH" -type d -exec chmod 755 {} \;

echo "Deployment completed successfully"
echo "Application available at: https://spinorama.org/metadata-manager/"
