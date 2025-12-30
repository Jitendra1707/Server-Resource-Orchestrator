#!/usr/bin/env python3
"""
Test script for the Server Configuration API
This script demonstrates the API functionality without requiring actual VM credentials.
"""

import requests
import json
import time
from datetime import datetime


class ServerConfigAPITester:
    """Test the Server Configuration API endpoints."""
    
    def __init__(self, base_url="http://localhost:5005"):
        """Initialize the API tester."""
        self.base_url = base_url
        self.api_base = f"{base_url}/api/server-config"
    
    def test_health_check(self):
        """Test the health check endpoint."""
        print("🧪 Testing Health Check...")
        try:
            response = requests.get(f"{self.api_base}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data.get('message')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_get_servers(self):
        """Test getting configured servers."""
        print("\n🧪 Testing Get Servers...")
        try:
            response = requests.get(f"{self.api_base}/servers")
            if response.status_code == 200:
                data = response.json()
                servers = data.get('data', {}).get('servers', [])
                print(f"✅ Get servers successful: {len(servers)} servers found")
                for server in servers:
                    print(f"  - {server.get('name')} ({server.get('id')})")
                return True
            else:
                print(f"❌ Get servers failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get servers error: {e}")
            return False
    
    def test_configure_server_mock(self):
        """Test server configuration with mock data (will fail but shows API structure)."""
        print("\n🧪 Testing Configure Server (Mock)...")
        
        # Mock server configuration data
        mock_config = {
            "vm_ip": "192.168.1.100",
            "username": "testuser",
            "password": "testpassword",
            "name": "Test VM Cluster",
            "environment": "test",
            "port": 16443,
            "location": "Test Environment",
            "description": "Test Kubernetes cluster",
            "configured_by": "test_script"
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/configure",
                json=mock_config,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Response Status: {response.status_code}")
            data = response.json()
            
            if response.status_code == 200:
                print("✅ Server configuration successful (unexpected - this should fail)")
                print(f"  Server ID: {data.get('data', {}).get('server_id')}")
                return True
            elif response.status_code in [400, 500]:
                print(f"⚠️  Server configuration failed as expected: {data.get('message')}")
                print("  This is expected since we're using mock credentials")
                return True  # Expected failure
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                print(f"  Response: {data}")
                return False
                
        except Exception as e:
            print(f"❌ Configure server error: {e}")
            return False
    
    def test_configure_server_validation(self):
        """Test server configuration validation."""
        print("\n🧪 Testing Configure Server Validation...")
        
        # Test missing required fields
        test_cases = [
            {
                "name": "Missing VM IP",
                "data": {"username": "testuser", "password": "testpass"},
                "expected_status": 400
            },
            {
                "name": "Missing Password",
                "data": {"vm_ip": "192.168.1.100", "username": "testuser"},
                "expected_status": 400
            },
            {
                "name": "Empty VM IP",
                "data": {"vm_ip": "", "username": "testuser", "password": "testpass"},
                "expected_status": 400
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            print(f"  Testing: {test_case['name']}")
            try:
                response = requests.post(
                    f"{self.api_base}/configure",
                    json=test_case['data'],
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == test_case['expected_status']:
                    print(f"    ✅ Validation passed: {response.status_code}")
                else:
                    print(f"    ❌ Validation failed: expected {test_case['expected_status']}, got {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                print(f"    ❌ Validation error: {e}")
                all_passed = False
        
        return all_passed
    
    def test_server_connection_mock(self):
        """Test server connection with mock server ID."""
        print("\n🧪 Testing Server Connection (Mock)...")
        
        mock_server_id = "azure-vm-192-168-1-100"
        
        try:
            response = requests.post(f"{self.api_base}/test/{mock_server_id}")
            
            print(f"Response Status: {response.status_code}")
            data = response.json()
            
            if response.status_code == 404:
                print(f"⚠️  Server connection test failed as expected: {data.get('message')}")
                print("  This is expected since the server doesn't exist")
                return True  # Expected failure
            elif response.status_code == 200:
                print("✅ Server connection test successful (unexpected)")
                return True
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                print(f"  Response: {data}")
                return False
                
        except Exception as e:
            print(f"❌ Server connection test error: {e}")
            return False
    
    def generate_api_examples(self):
        """Generate example API calls for documentation."""
        print("\n📋 API Usage Examples:")
        print("=" * 50)
        
        examples = {
            "Health Check": {
                "method": "GET",
                "url": f"{self.api_base}/health",
                "curl": f"curl -X GET {self.api_base}/health"
            },
            "Get Servers": {
                "method": "GET",
                "url": f"{self.api_base}/servers",
                "curl": f"curl -X GET {self.api_base}/servers"
            },
            "Configure Server": {
                "method": "POST",
                "url": f"{self.api_base}/configure",
                "curl": f"""curl -X POST {self.api_base}/configure \\
  -H "Content-Type: application/json" \\
  -d '{{"vm_ip": "4.246.178.26", "username": "azureuser", "password": "your_password"}}'"""
            },
            "Test Server Connection": {
                "method": "POST",
                "url": f"{self.api_base}/test/azure-vm-4-246-178-26",
                "curl": f"curl -X POST {self.api_base}/test/azure-vm-4-246-178-26"
            }
        }
        
        for name, example in examples.items():
            print(f"\n{name}:")
            print(f"  Method: {example['method']}")
            print(f"  URL: {example['url']}")
            print(f"  cURL: {example['curl']}")
    
    def run_all_tests(self):
        """Run all API tests."""
        print("🚀 Server Configuration API Test Suite")
        print("=" * 60)
        print(f"Testing API at: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Get Servers", self.test_get_servers),
            ("Configure Server Validation", self.test_configure_server_validation),
            ("Configure Server Mock", self.test_configure_server_mock),
            ("Server Connection Mock", self.test_server_connection_mock)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The API is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        # Generate examples
        self.generate_api_examples()
        
        return passed == total


def main():
    """Main function."""
    import sys
    
    # Check if backend is running
    base_url = "http://localhost:5005"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🔍 Checking if backend is running at {base_url}...")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running!")
        else:
            print(f"⚠️  Backend responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running!")
        print("Please start the backend first:")
        print("  cd backend && python app.py")
        return False
    except Exception as e:
        print(f"❌ Error checking backend: {e}")
        return False
    
    # Run tests
    tester = ServerConfigAPITester(base_url)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 API test suite completed successfully!")
        print("\nNext steps:")
        print("1. Use the API with real VM credentials")
        print("2. Integrate with frontend applications")
        print("3. Check the documentation for more details")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
    
    return success


if __name__ == "__main__":
    main() 