#!/usr/bin/env python3
"""
Script to fix VM-2 configuration with correct server address.
"""

import requests
import json

# Backend API configuration
BACKEND_URL = "http://localhost:5005"
CONFIGURE_ENDPOINT = f"{BACKEND_URL}/api/server-config/configure"

# VM-2 configuration with correct external IP
VM2_CONFIG = {
    "vm_ip": "4.246.163.135",
    "username": "azureuser",
    "password": "azureuser@12345",
    "name": "Azure VM-2 Kubernetes",
    "description": "Kubernetes cluster on Azure VM-2"
}

def fix_vm2_config():
    """Fix VM-2 configuration."""
    print("🔧 Fixing VM-2 configuration...")
    
    try:
        response = requests.post(CONFIGURE_ENDPOINT, json=VM2_CONFIG, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ Successfully fixed VM-2 configuration")
                return True
            else:
                print(f"❌ Failed to fix VM-2: {result.get('message')}")
                return False
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing VM-2: {e}")
        return False

if __name__ == "__main__":
    fix_vm2_config() 