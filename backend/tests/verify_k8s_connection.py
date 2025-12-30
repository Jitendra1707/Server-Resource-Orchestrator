import json
import os
import sys
from kubernetes import client, config as k8s_config

# Add current directory to path so we can import local modules if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.k8s_provider import K8sProvider

def print_color(text, color="reset"):
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def verify_connection():
    print_color("🚀 Starting Kubernetes Connection Verification...", "cyan")

    # 1. Load master.json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'master.json')
    print(f"📂 Loading config from: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            master_config = json.load(f)
    except Exception as e:
        print_color(f"❌ Failed to load master.json: {e}", "red")
        return

    # 2. Extract Kubeconfig
    servers = master_config.get('servers', [])
    if not servers:
        print_color("⚠️  No servers found in master.json", "red")
        return

    # Assuming we create a provider for the first server that has kubeconfig data
    target_server = None
    for server in servers:
        if server.get('connection_coordinates', {}).get('kubeconfig_data'):
            target_server = server
            break
    
    if not target_server:
        print_color("⚠️  No server found with 'kubeconfig_data'.", "red")
        return

    print_color(f"✅ Found server with kubeconfig: {target_server.get('id')}", "green")
    kubeconfig_data = target_server['connection_coordinates']['kubeconfig_data']

    # 3. Initialize Provider and Test Connectivity
    print("\n🔌 Initializing K8sProvider and testing connectivity...")
    try:
        # This uses the same logic as our backend
        provider = K8sProvider(kubeconfig_data)
        
        # Test 1: List Nodes (Basic connectivity check)
        print("   Attempting to list nodes...")
        nodes = provider.core_v1.list_node()
        print_color(f"✅ Connectivity Successful! Found {len(nodes.items)} nodes.", "green")
        for node in nodes.items:
            print(f"   - Node: {node.metadata.name} ({node.status.node_info.os_image})")

    except Exception as e:
        print_color(f"❌ Connectivity Failed: {e}", "red")
        return

    # 4. Test Pod Creation
    print("\n📦 Testing Pod Creation...")
    namespace = "default" # Use default for test check or extract from valid namespaces
    pod_name = "connectivity-check-pod"
    image = "nginx:alpine"
    resources = {"cpus": 0.1, "ram_gb": 0.1}

    try:
        print(f"   Creating deployment '{pod_name}' in namespace '{namespace}'...")
        
        pod_data = {
            "pod_id": pod_name,
            "namespace": namespace,
            "image_url": image,
            "requested": resources # {"cpus": ..., "ram_gb": ...}
        }
        
        provider.create_pod(pod_data)
        print_color("✅ Creation request sent successfully.", "green")
        
        # Optional: Wait a moment or check status (using simple sleep here for script simplicity)
        print("   Waiting 5 seconds for creation...")
        import time
        time.sleep(5)
        
        # Verify it exists
        deployments = provider.apps_v1.list_namespaced_deployment(namespace)
        found = False
        for d in deployments.items:
            if d.metadata.name == pod_name:
                found = True
                print_color(f"✅ Verified: Deployment '{pod_name}' exists in cluster.", "green")
                break
        
        if not found:
            print_color(f"⚠️  Warning: Deployment '{pod_name}' not found in list after creation.", "yellow")

    except Exception as e:
        print_color(f"❌ Creation Failed: {e}", "red")
        return

    # 5. Clean Up
    print("\n🧹 Cleaning Up...")
    try:
        print(f"   Deleting deployment '{pod_name}'...")
        provider.delete_pod(namespace, pod_name)
        print_color("✅ Deletion Successful.", "green")
    except Exception as e:
        print_color(f"❌ Deletion Failed: {e}", "red")

    print_color("\n✨ Verification Complete.", "cyan")

if __name__ == "__main__":
    verify_connection()
