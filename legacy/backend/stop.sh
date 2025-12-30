#!/bin/bash

# Backend Shutdown Script
# This script stops the Flask backend service

echo "🛑 Stopping Resource Manager Backend"
echo "===================================="

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

# Function to check if a process is running
process_running() {
    ps -p $1 >/dev/null 2>&1
}

# Stop Backend
print_status "Stopping Backend Service..."
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if process_running $BACKEND_PID; then
        print_status "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
        if process_running $BACKEND_PID; then
            print_warning "Backend didn't stop gracefully, force killing..."
            kill -9 $BACKEND_PID
        fi
        print_success "Backend stopped"
    else
        print_warning "Backend process not running"
    fi
    rm -f logs/backend.pid
else
    print_warning "Backend PID file not found"
fi

# Clean up
print_status "Cleaning up..."
print_success "Cleanup completed"

echo ""
echo "🎉 Backend Shutdown Complete!"
echo "============================="
print_success "Backend service stopped successfully!"
print_status "Note: Azure VM Kubernetes cluster remains running."
print_status "To stop the cluster, you would need to stop the Azure VM itself." 