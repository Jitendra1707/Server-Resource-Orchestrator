#!/bin/bash

# Backend Deployment Script
# This script deploys the Flask backend service

set -e  # Exit on any error

echo "🚀 Deploying Resource Manager Backend"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the backend directory
if [ ! -f "app.py" ]; then
    print_error "app.py not found. Please run this script from the backend directory."
    exit 1
fi

# Stop existing backend if running
print_status "Stopping existing backend service..."
if [ -f "logs/backend.pid" ]; then
    ./stop.sh
fi

# Install/update dependencies
print_status "Installing/updating Python dependencies..."
pip install -r requirements.txt

# Create logs directory if it doesn't exist
mkdir -p logs

# Start backend
print_status "Starting backend service..."
./start.sh

print_success "Backend deployment complete! 🎉"
print_status "Backend API: http://localhost:5005"
print_status "Health Check: http://localhost:5005/health"
print_status "API Docs: http://localhost:5005/apidocs" 