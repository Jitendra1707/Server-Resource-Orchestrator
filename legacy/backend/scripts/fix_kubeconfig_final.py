#!/usr/bin/env python3
"""
Fix the final kubeconfig conflict by removing certificate data when using insecure mode
"""

import json

def fix_kubeconfig_final():
    """Remove certificate data when using insecure-skip-tls-verify"""
    
    # Load master.json
    with open('data/master.json', 'r') as f:
        data = json.load(f)
    
    server = data['servers'][0]
    kubeconfig_data = server['connection_coordinates']['kubeconfig_data']
    
    # Check if insecure-skip-tls-verify is true
    clusters = kubeconfig_data.get('clusters', [])
    for cluster in clusters:
        cluster_config = cluster.get('cluster', {})
        if cluster_config.get('insecure-skip-tls-verify'):
            print(f"Found insecure-skip-tls-verify=True for cluster: {cluster.get('name')}")
            
            # Remove certificate data from users
            users = kubeconfig_data.get('users', [])
            for user in users:
                user_config = user.get('user', {})
                if 'client-certificate-data' in user_config:
                    print(f"Removing client-certificate-data from user: {user.get('name')}")
                    del user_config['client-certificate-data']
                if 'client-key-data' in user_config:
                    print(f"Removing client-key-data from user: {user.get('name')}")
                    del user_config['client-key-data']
    
    # Write back the fixed data
    with open('data/master.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("Fixed kubeconfig conflicts in master.json")
    return True

if __name__ == "__main__":
    fix_kubeconfig_final() 