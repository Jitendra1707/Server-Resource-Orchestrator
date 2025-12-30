#!/usr/bin/env python3
"""
Simple kubeconfig fix using insecure mode
"""

import json

def simple_kubeconfig_fix():
    """Create a simple kubeconfig with insecure mode"""
    
    # Load master.json
    with open('data/master.json', 'r') as f:
        data = json.load(f)
    
    server = data['servers'][0]
    
    # Create a simple kubeconfig with insecure mode
    kubeconfig_data = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "server": "https://4.246.178.26:16443",
                    "insecure-skip-tls-verify": True
                },
                "name": "azure-vm-cluster"
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "azure-vm-cluster",
                    "user": "admin"
                },
                "name": "azure-vm-context"
            }
        ],
        "current-context": "azure-vm-context",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "admin",
                "user": {
                    "token": ""  # Empty token for now
                }
            }
        ]
    }
    
    # Update the kubeconfig data
    server['connection_coordinates']['kubeconfig_data'] = kubeconfig_data
    
    # Write back to master.json
    with open('data/master.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("✅ Updated kubeconfig with simple insecure configuration")
    return True

def test_simple_connection():
    """Test connection with simple kubeconfig"""
    print("\nTesting simple connection...")
    
    try:
        import tempfile
        import yaml
        from kubernetes import client, config as k8s_config
        
        # Load master.json
        with open('data/master.json', 'r') as f:
            data = json.load(f)
        
        server = data['servers'][0]
        kubeconfig_data = server['connection_coordinates']['kubeconfig_data']
        
        # Create temporary kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as temp_file:
            yaml.dump(kubeconfig_data, temp_file)
            temp_file_path = temp_file.name
        
        # Load the kubeconfig
        k8s_config.load_kube_config(config_file=temp_file_path)
        
        # Create API client
        core_v1 = client.CoreV1Api()
        
        # Test connection
        nodes = core_v1.list_node()
        print(f"✅ Connection successful! Found {len(nodes.items)} nodes")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Simple Kubernetes Connection Fix ===\n")
    
    # Step 1: Update kubeconfig
    if simple_kubeconfig_fix():
        # Step 2: Test connection
        if test_simple_connection():
            print("\n🎉 SUCCESS! Simple connection is working!")
            print("The backend should now show CONNECTED status.")
        else:
            print("\n⚠️  Simple kubeconfig updated but connection test failed.")
            print("This might require additional authentication setup.")
    else:
        print("\n❌ Failed to update kubeconfig.") 