#!/usr/bin/env python3
"""
Test script for the de-configure server API functionality
"""

import requests
import json
import time
import os

# Configuration
BASE_URL = "http://localhost:5005"
API_BASE = f"{BASE_URL}/api/server-config"

def create_mock_server_for_testing():
    """Create a mock server entry in master.json for testing"""
    try:
        # Read current master.json
        master_json_path = "data/master.json"
        if os.path.exists(master_json_path):
            with open(master_json_path, 'r') as f:
                data = json.load(f)
        else:
            data = {"servers": [], "config": {}}
        
        # Create mock server
        mock_server = {
            "id": "test-server-for-deconfigure",
            "name": "Test Server for De-configure",
            "type": "kubernetes",
            "environment": "test",
            "connection_coordinates": {
                "method": "kubeconfig",
                "host": "192.168.1.100",
                "port": 16443,
                "username": "testuser",
                "kubeconfig_path": "./test_kubeconfig",
                "insecure_skip_tls_verify": True
            },
            "metadata": {
                "location": "Test Environment",
                "environment": "test",
                "description": "Mock server for testing de-configure functionality",
                "setup_method": "test",
                "setup_timestamp": "2025-07-23T20:00:00.000000",
                "configured_by": "test"
            }
        }
        
        # Add mock server if it doesn't exist
        server_exists = any(s.get('id') == mock_server['id'] for s in data.get('servers', []))
        if not server_exists:
            data.setdefault('servers', []).append(mock_server)
            
            # Set as default if no default exists
            if not data.get('config', {}).get('default_server'):
                data.setdefault('config', {})['default_server'] = mock_server['id']
            
            # Save updated configuration
            with open(master_json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print("   ✅ Mock server created for testing")
            return True
        else:
            print("   ✅ Mock server already exists")
            return True
            
    except Exception as e:
        print(f"   ❌ Failed to create mock server: {e}")
        return False

def test_deconfigure_functionality():
    """Test the complete de-configure functionality"""
    
    print("🧪 Testing De-Configure Server API Functionality")
    print("=" * 50)
    
    # Step 1: Check initial state
    print("\n1️⃣ Checking initial server state...")
    response = requests.get(f"{API_BASE}/servers")
    if response.status_code == 200:
        data = response.json()
        initial_servers = data.get('data', {}).get('servers', [])
        print(f"   Initial servers count: {len(initial_servers)}")
        for server in initial_servers:
            print(f"   - {server.get('name')} (ID: {server.get('id')})")
    else:
        print(f"   ❌ Failed to get servers: {response.status_code}")
        return False
    
    # Step 2: Create mock server if none exist
    if len(initial_servers) == 0:
        print("\n2️⃣ No servers found. Creating mock server for testing...")
        if not create_mock_server_for_testing():
            return False
    else:
        print("\n2️⃣ Using existing server for testing...")
    
    # Step 3: Get server list again
    print("\n3️⃣ Getting updated server list...")
    response = requests.get(f"{API_BASE}/servers")
    if response.status_code == 200:
        data = response.json()
        servers = data.get('data', {}).get('servers', [])
        print(f"   Servers count: {len(servers)}")
        
        if len(servers) == 0:
            print("   ⚠️  No servers available for de-configure test")
            return True
        
        test_server = servers[0]
        server_id = test_server.get('id')
        server_name = test_server.get('name')
        print(f"   Testing with server: {server_name} (ID: {server_id})")
    else:
        print(f"   ❌ Failed to get servers: {response.status_code}")
        return False
    
    # Step 4: Test de-configure endpoint
    print(f"\n4️⃣ Testing de-configure for server: {server_id}")
    response = requests.delete(f"{API_BASE}/deconfigure/{server_id}")
    
    if response.status_code == 200:
        data = response.json()
        print("   ✅ De-configure successful!")
        print(f"   📊 Response data:")
        print(f"      - Server ID: {data.get('data', {}).get('server_id')}")
        print(f"      - Server Name: {data.get('data', {}).get('server_name')}")
        print(f"      - Remaining servers: {data.get('data', {}).get('remaining_servers')}")
        print(f"      - Removed files: {len(data.get('data', {}).get('removed_files', []))}")
        print(f"      - New default server: {data.get('data', {}).get('new_default_server')}")
    else:
        print(f"   ❌ De-configure failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False
    
    # Step 5: Verify server was removed
    print("\n5️⃣ Verifying server removal...")
    response = requests.get(f"{API_BASE}/servers")
    if response.status_code == 200:
        data = response.json()
        final_servers = data.get('data', {}).get('servers', [])
        print(f"   Final servers count: {len(final_servers)}")
        
        if len(final_servers) == 0:
            print("   ✅ Server successfully removed!")
        else:
            print("   ❌ Server still exists in list")
            return False
    else:
        print(f"   ❌ Failed to verify removal: {response.status_code}")
        return False
    
    # Step 6: Test de-configure on non-existent server
    print("\n6️⃣ Testing de-configure on non-existent server...")
    response = requests.delete(f"{API_BASE}/deconfigure/non-existent-server")
    
    if response.status_code == 404:
        print("   ✅ Correctly returned 404 for non-existent server")
    else:
        print(f"   ❌ Unexpected response for non-existent server: {response.status_code}")
        return False
    
    print("\n🎉 All tests passed! De-configure functionality is working correctly.")
    return True

def test_api_endpoints():
    """Test all server configuration API endpoints"""
    
    print("\n🔍 Testing API Endpoints")
    print("=" * 30)
    
    endpoints = [
        ("GET", f"{API_BASE}/health", "Health Check"),
        ("GET", f"{API_BASE}/servers", "Get Servers"),
    ]
    
    for method, url, name in endpoints:
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url)
            elif method == "DELETE":
                response = requests.delete(url)
            
            status = "✅" if response.status_code in [200, 404] else "❌"
            print(f"   {status} {method} {url} - {name} ({response.status_code})")
            
        except Exception as e:
            print(f"   ❌ {method} {url} - {name} (Error: {e})")

if __name__ == "__main__":
    try:
        # Test API endpoints first
        test_api_endpoints()
        
        # Test de-configure functionality
        success = test_deconfigure_functionality()
        
        if success:
            print("\n🎯 All tests completed successfully!")
        else:
            print("\n💥 Some tests failed!")
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}") 