import json
import os
import sys
import time
from kubernetes import client

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.k8s_provider import K8sProvider

def debug_pod_status():
    print("Starting Pod Status Debugger...")

    # Load master.json to get kubeconfig
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'master.json')
    with open(config_path, 'r') as f:
        master_config = json.load(f)
    
    server_id = "azure-vm-01" # Target server
    server = next((s for s in master_config.get("servers", []) if s["id"] == server_id), None)
    
    if not server:
        print(f"❌ Server {server_id} not found")
        return

    kubeconfig = server.get('connection_coordinates', {}).get('kubeconfig_data')
    provider = K8sProvider(kubeconfig)
    
    pod_name = "my-app"
    namespace = f"{pod_name}-ns"
    
    print(f"Checking pod '{pod_name}' in namespace '{namespace}'...")
    
    # List pods with label selector
    pods = provider.core_v1.list_namespaced_pod(
        namespace=namespace, 
        label_selector=f"app={pod_name}"
    )
    
    print(f"Found {len(pods.items)} pods.")
    
    if pods.items:
        pod = pods.items[0]
        print(f"Pod Name: {pod.metadata.name}")
        print(f"Phase: {pod.status.phase}")
        print("Container Statuses:")
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                print(f" - {cs.name}: Ready={cs.ready}, State={cs.state}")
    else:
        print("No pods found matching label selector.")

if __name__ == "__main__":
    debug_pod_status()
