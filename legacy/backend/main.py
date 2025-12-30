#!/usr/bin/env python3
"""
Resource Manager Backend - Main Entry Point
This is the main entry point for the Flask backend application.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app from the core module
from core.app import app

if __name__ == '__main__':
    # Run the Flask application
    app.run(
        host='0.0.0.0',
        port=5005,
        debug=True
    ) 