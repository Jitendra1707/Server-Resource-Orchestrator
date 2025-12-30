#!/usr/bin/env python3
"""
Get fresh kubeconfig from Azure VM with proper authentication
"""

import json
import subprocess
import yaml
import time

def get_fresh_kubeconfig():
    """Get fresh kubeconfig from Azure VM and update master.json"""
    
    print("Getting fresh kubeconfig from Azure VM...")
    
    # Try to get kubeconfig from Azure VM
    try:
        # Use sshpass or expect-like approach to handle password
        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            'azureuser@4.246.178.26', 'sudo microk8s config'
        ]
        
        # Run the command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"SSH failed: {result.stderr}")
            return False
        
        kubeconfig_content = result.stdout
        print("✅ Successfully retrieved kubeconfig from Azure VM")
        
        # Parse the kubeconfig
        kubeconfig_data = yaml.safe_load(kubeconfig_content)
        
        # Update server URL to use external IP
        for cluster in kubeconfig_data.get('clusters', []):
            if 'cluster' in cluster and 'server' in cluster['cluster']:
                old_server = cluster['cluster']['server']
                print(f"Original server: {old_server}")
                
                # Replace internal IP with external IP
                if '10.0.0.5' in old_server:
                    new_server = old_server.replace('10.0.0.5', '4.246.178.26')
                    cluster['cluster']['server'] = new_server
                    print(f"Updated server: {new_server}")
        
        # Load master.json
        with open('data/master.json', 'r') as f:
            data = json.load(f)
        
        # Update the kubeconfig data
        server = data['servers'][0]
        server['connection_coordinates']['kubeconfig_data'] = kubeconfig_data
        
        # Write back to master.json
        with open('data/master.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print("✅ Successfully updated master.json with fresh kubeconfig")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout getting kubeconfig from Azure VM")
        return False
    except Exception as e:
        print(f"❌ Error getting kubeconfig: {e}")
        return False

def test_connection():
    """Test the connection with the new kubeconfig"""
    print("\nTesting connection with new kubeconfig...")
    
    try:
        import tempfile
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
        
        # List first node
        if nodes.items:
            node = nodes.items[0]
            print(f"First node: {node.metadata.name}")
            print(f"Node status: {node.status.conditions[-1].type if node.status.conditions else 'Unknown'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Azure VM Kubernetes Connection Fix ===\n")
    
    # Step 1: Get fresh kubeconfig
    if get_fresh_kubeconfig():
        # Step 2: Test connection
        if test_connection():
            print("\n🎉 SUCCESS! Kubernetes connection is working!")
            print("The backend should now show CONNECTED status.")
        else:
            print("\n⚠️  Kubeconfig updated but connection test failed.")
    else:
        print("\n❌ Failed to get fresh kubeconfig from Azure VM.")
        print("Please check:")
        print("1. Azure VM is running")
        print("2. SSH access is working")
        print("3. MicroK8s is installed and running") 