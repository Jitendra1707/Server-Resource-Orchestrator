import json
import os
import sys
import time
from kubernetes import client

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.k8s_provider import K8sProvider

def debug_creation_loop():
    print("Starting Debug Creation Loop Check...")

    # Load master.json to get kubeconfig
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'master.json')
    with open(config_path, 'r') as f:
        master_config = json.load(f)
    
    server_id = "azure-vm-01"
    server = next((s for s in master_config.get("servers", []) if s["id"] == server_id), None)
    
    if not server:
        print(f"Server {server_id} not found")
        return

    kubeconfig = server.get('connection_coordinates', {}).get('kubeconfig_data')
    provider = K8sProvider(kubeconfig)
    
    pod_name = "my-app"
    namespace = f"{pod_name}-ns"
    
    print(f"Analyzing Deployment '{pod_name}' in namespace '{namespace}'...")

    start_time = time.time()
    for i in range(10): # Try 10 checks
        print(f"--- Check {i+1} ---")
        try:
            dep_status = provider.apps_v1.read_namespaced_deployment_status(
                name=pod_name,
                namespace=namespace
            ).status
            
            print(f"Replicas: {dep_status.replicas}")
            print(f"Ready Replicas: {dep_status.ready_replicas}")
            print(f"Unavailable Replicas: {dep_status.unavailable_replicas}")
            print(f"Conditions: {dep_status.conditions}")
            
            if dep_status.ready_replicas and dep_status.ready_replicas >= (dep_status.replicas or 1):
                print("SUCCESS CONDITION MET!")
                return
            else:
                print("Success condition NOT met.")

        except Exception as e:
            print(f"EXCEPTION: {e}")
        
        time.sleep(2)

    print("Finished loop without meeting success condition.")

if __name__ == "__main__":
    debug_creation_loop()
