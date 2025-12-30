#!/usr/bin/env python3
"""
Test script for Azure VM integration
This script tests the Azure VM connection and Kubernetes integration.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers.cloud_kubernetes_provider import CloudKubernetesProvider


def test_azure_vm_detection():
    """Test Azure VM environment variable detection."""
    print("🧪 Testing Azure VM Detection")
    print("=" * 30)
    
    # Test without Azure VM IP
    with patch.dict(os.environ, {}, clear=True):
        provider = CloudKubernetesProvider()
        print("✅ Standard cloud connection initialized")
    
    # Test with Azure VM IP
    with patch.dict(os.environ, {'AZURE_VM_IP': '192.168.1.100'}, clear=True):
        try:
            provider = CloudKubernetesProvider()
            print("✅ Azure VM connection initialized")
        except Exception as e:
            print(f"⚠️  Azure VM connection failed (expected if no real VM): {e}")


def test_kubeconfig_generation():
    """Test kubeconfig generation from Azure VM."""
    print("\n🧪 Testing Kubeconfig Generation")
    print("=" * 35)
    
    # Mock kubeconfig content
    mock_kubeconfig = {
        "clusters": [
            {
                "name": "default",
                "cluster": {
                    "server": "https://localhost:6443",
                    "certificate-authority-data": "mock-ca-data"
                }
            }
        ],
        "contexts": [
            {
                "name": "default",
                "context": {
                    "cluster": "default",
                    "user": "default"
                }
            }
        ],
        "users": [
            {
                "name": "default",
                "user": {
                    "client-certificate-data": "mock-cert-data",
                    "client-key-data": "mock-key-data"
                }
            }
        ],
        "current-context": "default"
    }
    
    # Mock SSH command output
    mock_ssh_output = json.dumps(mock_kubeconfig)
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = mock_ssh_output
        
        provider = CloudKubernetesProvider()
        
        # Test kubeconfig generation
        vm_ip = "192.168.1.100"
        username = "azureuser"
        
        try:
            kubeconfig = provider._generate_kubeconfig_from_vm(vm_ip, username)
            kubeconfig_data = json.loads(kubeconfig)
            
            # Check if server address was updated
            server = kubeconfig_data["clusters"][0]["cluster"]["server"]
            if vm_ip in server:
                print("✅ Kubeconfig server address updated correctly")
            else:
                print("❌ Kubeconfig server address not updated")
                
        except Exception as e:
            print(f"❌ Kubeconfig generation failed: {e}")


def test_environment_variables():
    """Test environment variable configuration."""
    print("\n🧪 Testing Environment Variables")
    print("=" * 35)
    
    required_vars = [
        'AZURE_VM_IP',
        'AZURE_VM_USERNAME',
        'AZURE_VM_SSH_KEY_PATH',
        'AZURE_VM_KUBECONFIG'
    ]
    
    print("Required environment variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: Not set")
    
    print("\nTo set these variables:")
    print("export AZURE_VM_IP=your-vm-ip")
    print("export AZURE_VM_USERNAME=azureuser")
    print("export AZURE_VM_SSH_KEY_PATH=/path/to/ssh/key")
    print("export AZURE_VM_KUBECONFIG=/path/to/kubeconfig")


def test_provider_initialization():
    """Test provider initialization with different configurations."""
    print("\n🧪 Testing Provider Initialization")
    print("=" * 40)
    
    # Test 1: No Azure VM configuration
    print("Test 1: Standard cloud connection")
    try:
        with patch.dict(os.environ, {}, clear=True):
            provider = CloudKubernetesProvider()
            print("  ✅ Standard cloud provider initialized")
    except Exception as e:
        print(f"  ❌ Standard cloud provider failed: {e}")
    
    # Test 2: Azure VM configuration
    print("Test 2: Azure VM connection")
    try:
        with patch.dict(os.environ, {
            'AZURE_VM_IP': '192.168.1.100',
            'AZURE_VM_USERNAME': 'azureuser'
        }, clear=True):
            provider = CloudKubernetesProvider()
            print("  ✅ Azure VM provider initialized")
    except Exception as e:
        print(f"  ⚠️  Azure VM provider failed (expected if no real VM): {e}")
    
    # Test 3: Direct kubeconfig
    print("Test 3: Direct kubeconfig")
    try:
        with patch.dict(os.environ, {
            'AZURE_VM_KUBECONFIG': '/tmp/test-kubeconfig'
        }, clear=True):
            provider = CloudKubernetesProvider()
            print("  ✅ Direct kubeconfig provider initialized")
    except Exception as e:
        print(f"  ⚠️  Direct kubeconfig provider failed (expected if no real file): {e}")


def main():
    """Run all tests."""
    print("🚀 Azure VM Integration Tests")
    print("=" * 50)
    
    test_azure_vm_detection()
    test_kubeconfig_generation()
    test_environment_variables()
    test_provider_initialization()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n📋 Next Steps:")
    print("1. Set up your Azure VM with Kubernetes")
    print("2. Configure environment variables")
    print("3. Run: python setup_azure_vm.py")
    print("4. Test connection: python setup_azure_vm.py test")
    print("5. Start the backend: python app.py")


if __name__ == "__main__":
    main() 