#!/usr/bin/env python3
"""
Script to configure both Azure VMs with stored credentials.
This script will configure both VMs and store their credentials in master.json.
"""

import requests
import json
import time

# Backend API configuration
BACKEND_URL = "http://localhost:5005"
CONFIGURE_ENDPOINT = f"{BACKEND_URL}/api/server-config/configure"

# VM configurations
VMS = [
    {
        "vm_ip": "4.246.178.26",
        "username": "azureuser", 
        "password": "azureuser@12345",
        "name": "Azure VM-1 Kubernetes",
        "description": "Kubernetes cluster on Azure VM-1"
    },
    {
        "vm_ip": "4.246.163.135",
        "username": "azureuser",
        "password": "azureuser@12345", 
        "name": "Azure VM-2 Kubernetes",
        "description": "Kubernetes cluster on Azure VM-2"
    }
]

def configure_vm(vm_config):
    """Configure a single VM."""
    print(f"\n🔧 Configuring {vm_config['name']} ({vm_config['vm_ip']})...")
    
    try:
        response = requests.post(CONFIGURE_ENDPOINT, json=vm_config, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"✅ Successfully configured {vm_config['name']}")
                return True
            else:
                print(f"❌ Failed to configure {vm_config['name']}: {result.get('message')}")
                return False
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error configuring {vm_config['name']}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error configuring {vm_config['name']}: {e}")
        return False

def main():
    """Main function to configure all VMs."""
    print("🚀 Starting VM configuration process...")
    print(f"📡 Backend URL: {BACKEND_URL}")
    
    # Check if backend is running
    try:
        health_response = requests.get(f"{BACKEND_URL}/api/server-config/health", timeout=10)
        if health_response.status_code != 200:
            print("❌ Backend is not responding properly")
            return
        print("✅ Backend is running")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("Please ensure the backend is running on port 5005")
        return
    
    successful_configs = 0
    
    for vm_config in VMS:
        if configure_vm(vm_config):
            successful_configs += 1
        time.sleep(2)  # Small delay between configurations
    
    print(f"\n📊 Configuration Summary:")
    print(f"✅ Successfully configured: {successful_configs}/{len(VMS)} VMs")
    
    if successful_configs == len(VMS):
        print("🎉 All VMs configured successfully!")
        print("\nNext steps:")
        print("1. Check the frontend to see the green LED status")
        print("2. Try creating pods on the configured servers")
    else:
        print("⚠️  Some VMs failed to configure. Check the logs above.")

if __name__ == "__main__":
    main() 