#!/bin/bash

# Backend Startup Script
# This script starts the Flask backend service

set -e  # Exit on any error

echo "🚀 Starting Resource Manager Backend"
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

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "Service at $url is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Service at $url failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Python is available
if ! command -v python3 >/dev/null 2>&1; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

print_success "Python 3 is available"

# Check if required packages are installed
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found. Please ensure you're in the backend directory."
    exit 1
fi

print_status "Installing/updating Python dependencies..."
pip install -r requirements.txt

print_success "Dependencies are ready"

# Check if backend port is already in use
if port_in_use 5005; then
    print_warning "Port 5005 is already in use. Backend might already be running."
    print_status "Backend should be available at: http://localhost:5005"
    exit 0
fi

# Start backend
print_status "Starting backend on port 5005..."

# Set environment variables
export AZURE_VM_IP=${AZURE_VM_IP:-4.246.178.26}
export AZURE_VM_KUBECONFIG=${AZURE_VM_KUBECONFIG:-./azure_vm_kubeconfig_updated}
export ENVIRONMENT=${ENVIRONMENT:-live}

# Start backend in background
python main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid

# Wait for backend to be ready
if wait_for_service "http://localhost:5005/health"; then
    print_success "Backend started successfully (PID: $BACKEND_PID)"
    print_success "Backend API: http://localhost:5005"
    print_success "Health Check: http://localhost:5005/health"
    print_success "API Docs: http://localhost:5005/apidocs"
else
    print_error "Backend failed to start"
    exit 1
fi

echo ""
print_success "Backend startup complete! 🚀"
print_status "To stop the backend, run: ./stop.sh"
print_status "To view logs: tail -f logs/backend.log" 