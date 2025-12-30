"""
Server Manager Module
Handles server and pod management operations.
"""

import warnings
# Suppress SSL/TLS warnings for development environments
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

import os
import json
import time
import uuid
from datetime import datetime
from flask import  jsonify
from typing import Dict, List, Optional
from kubernetes import client, config
from providers.cloud_kubernetes_provider import CloudKubernetesProvider
from config.types import MasterConfig, ServerConfig
from config.utils import (
    get_available_resources,
    validate_resource_request,
    create_pod_k8s,
    delete_pod_k8s
)

class ServerManager:
    """Manages server configurations and Kubernetes providers."""
    
    def __init__(self):
        """Initialize the server manager."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()
    
    def _load_master_config(self) -> MasterConfig:
        """Load master configuration from data/master.json."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                from config.types import validate_master_config
                return validate_master_config(config_data)
        except Exception as e:
            print(f"❌ Failed to load master config: {e}")
            from config.types import create_default_master_config
            return create_default_master_config()
    
    def _initialize_providers(self):
        """Initialize providers for all configured servers."""
        print(f"🔧 Initializing providers for {len(self.master_config.get('servers', []))} servers")
        
        for server in self.master_config.get("servers", []):
            server_id = server.get("id")
            print(f"🔧 Processing server: {server_id}")
            
            if server_id:
                try:
                    provider = self._create_provider(server)
                    if provider:
                        self.server_providers[server_id] = {
                            "provider": provider,
                            "config": server
                        }
                        print(f"✅ Created provider for server: {server_id}")
                    else:
                        print(f"⚠️  No provider created for server: {server_id}")
                except Exception as e:
                    print(f"❌ Failed to create provider for {server_id}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"🔧 Total providers initialized: {len(self.server_providers)}")
        print(f"🔧 Provider IDs: {list(self.server_providers.keys())}")
    
    def _create_provider(self, server_config: Dict):
        """Create appropriate provider based on server type and connection method."""
        server_type = server_config.get("type")
        connection_coords = server_config.get("connection_coordinates", {})
        connection_method = connection_coords.get("method")
        
        print(f"🔧 Creating provider for server {server_config.get('id')}:")
        print(f"   - Type: {server_type}")
        print(f"   - Connection method: {connection_method}")
        print(f"   - Host: {connection_coords.get('host')}")
        
        if server_type == "kubernetes":
            # Use CloudKubernetesProvider for Azure VM or cloud connections
            if connection_method == "kubeconfig" and connection_coords.get("host"):
                print(f"✅ Using CloudKubernetesProvider for {server_config.get('id')} with kubeconfig")
                try:
                    provider = CloudKubernetesProvider(server_config)
                    print(f"✅ CloudKubernetesProvider created successfully")
                    return provider
                except Exception as e:
                    print(f"❌ Failed to create CloudKubernetesProvider: {e}")
                    return None
            else:
                # No local provider support - only cloud/remote connections
                print(f"❌ Unsupported connection method: {connection_method}")
                print(f"   Only 'kubeconfig' with host is supported for Azure VM connections")
                return None
        else:
            print(f"❌ Unknown server type: {server_type}")
            return None
    
    def get_server_ids(self) -> List[str]:
        """Get list of all server IDs."""
        return list(self.server_providers.keys())
    
    def get_server_config(self, server_id: str) -> Optional[Dict]:
        """Get configuration for a specific server."""
        if server_id in self.server_providers:
            return self.server_providers[server_id]["config"]
        return None
    
    def get_server_provider(self, server_id: str):
        """Get provider instance for a specific server."""
        if server_id in self.server_providers:
            return self.server_providers[server_id]["provider"]
        return None
    
    def get_all_servers_static(self) -> List[Dict]:
        """
        Get all servers and pods from master.json only (no live sync).
        This method is optimized for fast API responses.
        
        Returns:
            List of servers with their data from master.json
        """
        all_servers = []
        
        # Read directly from master.json without any provider initialization
        for server_config in self.master_config.get("servers", []):
            server_id = server_config.get("id")
            server_name = server_config.get("name", server_id)
            server_type = server_config.get("type", "unknown")
            environment = server_config.get("environment", "unknown")
            metadata = server_config.get("metadata", {})
            
            # Create server object from master.json data only
            server_data = {
                "id": server_id,  # Add id field for frontend compatibility
                "server_id": server_id,
                "name": server_name,  # Add name field for frontend compatibility
                "server_name": server_name,
                "server_type": server_type,
                "metadata": metadata,
                "environment": environment,
                "status": server_config.get("status", "offline"),
                "pods": server_config.get("pods", []),
                "resources": server_config.get("resources", {
                    "total": {}, 
                    "allocated": {}, 
                    "available": {}, 
                    "actual_usage": {}
                })
            }
            
            all_servers.append(server_data)
        
        return all_servers

    def get_all_servers_with_pods(self) -> List[Dict]:
        """Get all servers with their pods data."""
        all_servers = []
        
        # Get all servers from master config, not just those with providers
        for server_config in self.master_config.get("servers", []):
            server_id = server_config.get("id")
            server_name = server_config.get("name", server_id)
            server_type = server_config.get("type", "unknown")
            environment = server_config.get("environment", "unknown")
            metadata = server_config.get("metadata", {})
            
            # Check if we have a provider for this server
            if server_id in self.server_providers:
                try:
                    provider = self.server_providers[server_id]["provider"]
                    
                    # Get live data from provider
                    servers_data = provider.get_servers_with_pods()
                    
                    # Add server metadata
                    for server_data in servers_data:
                        server_data["server_id"] = server_id
                        server_data["server_name"] = server_name
                        server_data["server_type"] = server_type
                        server_data["metadata"] = metadata
                        server_data["environment"] = environment
                    
                    all_servers.extend(servers_data)
                    
                except Exception as e:
                    print(f"Error getting live data for server {server_id}: {e}")
                    # Add server with error state but include static data
                    error_server = {
                        "server_id": server_id,
                        "server_name": server_name,
                        "server_type": server_type,
                        "metadata": metadata,
                        "environment": environment,
                        "status": "error",
                        "pods": server_config.get("pods", []),
                        "resources": server_config.get("resources", {"total": {}, "allocated": {}, "available": {}, "actual_usage": {}})
                    }
                    all_servers.append(error_server)
            else:
                # Server doesn't have a provider (like dummy servers), use static data
                static_server = {
                    "server_id": server_id,
                    "server_name": server_name,
                    "server_type": server_type,
                    "metadata": metadata,
                    "environment": environment,
                    "status": "offline",  # or "static" to indicate it's not live
                    "pods": server_config.get("pods", []),
                    "resources": server_config.get("resources", {"total": {}, "allocated": {}, "available": {}, "actual_usage": {}})
                }
                all_servers.append(static_server)
        
        return all_servers
    
    def get_server_with_pods(self, server_id: str) -> Optional[Dict]:
        """Get specific server with its pods data."""
        if server_id not in self.server_providers:
            return None
        
        try:
            provider = self.server_providers[server_id]["provider"]
            config = self.server_providers[server_id]["config"]
            
            servers_data = provider.get_servers_with_pods()
            
            if servers_data:
                server_data = servers_data[0]  # Get first server
                server_data["server_id"] = server_id
                server_data["server_name"] = config.get("name", server_id)
                server_data["server_type"] = config.get("type", "unknown")
                server_data["metadata"] = config.get("metadata", {})
                server_data["environment"] = config.get("environment", "unknown")
                return server_data
            
        except Exception as e:
            print(f"Error getting data for server {server_id}: {e}")
        
        return None
    
    def _append_pending_pod_to_master(self, pod_data: Dict) -> Dict:
        """
        Append a pending pod entry for the given server_id into master.json.
        Raises if pod_id already exists or required fields are missing.
        Returns the pod entry that was added.
        """
        pod_id = pod_data.get("pod_name") 
        server_id = pod_data.get("server_id")

        namespace = f"{pod_id}-ns"
        image_url = pod_data.get("image_url") or None

        resources = pod_data.get("Resources") or {}
        requested = {
            "cpus": resources.get("cpus", 0),
            "ram_gb": resources.get("ram_gb", 0),
            "storage_gb": resources.get("storage_gb", 0),
            "gpus": resources.get("gpus", 0)
        }

        owner = pod_data.get("owner", "unknown")
        status = "pending"
        timestamp = datetime.now().isoformat()
        pod_ip = None

        pending_pod = {
            "pod_id": pod_id,
            "name": pod_id,
            "namespace": namespace,
            "server_id": server_id,
            "image_url": image_url,
            "requested": requested,
            "owner": owner,
            "status": status,
            "timestamp": timestamp,
            "pod_ip": pod_ip
        }

        # Locate server
        for server in self.master_config.get("servers", []):
            if server.get("id") == server_id:
                server.setdefault("pods", [])

                # Check for existing pod
                for existing in server["pods"]:
                    if (existing.get("pod_id") and existing.get("pod_id") == pod_id) or \
                    (existing.get("name") and existing.get("name") == pod_id):
                        print(f"❌ Pod '{pod_id}' already exists on server '{server_id}'")
                        raise ValueError(f"Pod '{pod_id}' already exists on server '{server_id}'")

                # Append and persist
                server["pods"].append(pending_pod)
                config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
                temp_path = config_path + ".tmp"
                with open(temp_path, "w") as f:
                    json.dump(self.master_config, f, indent=2)
                os.replace(temp_path, config_path)
                return pending_pod

        # Server not found
        raise ValueError(f"Server '{server_id}' not found in master config")


    def validation_steps(self, pod_data) -> Dict:
        server_id = pod_data.get('server_id')
        pod_id = pod_data.get("pod_name") 

        # Append pending pod; will raise if pod exists or server missing
        pod_object = self._append_pending_pod_to_master(pod_data)
        print(f"✅ Appended pending pod {pod_object.get('pod_id')}")

        # Validate resources against the static/master view
        servers = self.get_all_servers_static()
        server_data = next((s for s in servers if s.get('server_id') == server_id), None)
        if not server_data:
            raise ValueError(f"Server '{server_id}' not found")

        ok, err = validate_resource_request(server_data, pod_data.get('Resources', {}))
        if not ok:
            raise ValueError(err)
        
        provider = self.server_providers[server_id]["provider"]
        
        # Get fresh live data for backend validation
        print(f"🔍 Validating pod creation for {pod_data.get('PodName', '')} on server {server_id}")
        cluster_server = provider.get_cluster_available_resources_raw()
        print(f"✅ Cluster resources: {cluster_server}")
        if cluster_server:
            # Backend validation: Validate against live Kubernetes data
            ok, err = validate_resource_request(cluster_server, pod_data.get("Resources", {}))
            if not ok:
                return jsonify({'error': err}), 400
            
        updated_resources = self.reserve_resources_in_master_simple(
                    self.master_config,
                    server_id,
                    pod_object.get("requested", {})
                )
            
        return pod_object

    def create_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Create a pod on the specified server."""
        try:
            pod_object = self.validation_steps(pod_data)
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}

        if server_id not in self.server_providers:
            self.reload_config()
            if server_id not in self.server_providers:
                return {"error": f"Server {server_id} not found"}
        try:
            provider = self.server_providers[server_id]["provider"]
            result = provider.create_pod(pod_object)
            
            # OPTIMIZATION: Sync pods synchronously after successful creation
            if result.get('status') == 'success':
                try:
                    time.sleep(2)
                    self.update_pod_object(server_id, pod_object, creation_result=result)
                except Exception as e:
                    print(f"Sync failed but pod was created: {e}")
            else:
                self.update_pod_object(server_id, pod_object, creation_result=result)

            return result
        except Exception as e:
            return {"error": f"Failed to create pod: {e}"}
        
    def update_pod_object(self, server_id: str, pod_object: Dict, creation_result: Dict) -> Dict:
        """
        Update the pending pod_object in master.json based on creation_result.
        - If creation succeeded, mark as online and inject pod_ip / external_ip.
        - If it failed, mark as failed and record error.
        """
        pod_id = pod_object.get("pod_id") or pod_object.get("name")
        if not pod_id:
            return pod_object  # nothing to do

        # Update status and fields based solely on creation_result
        if creation_result.get("status") == "success":
            pod_object["status"] = "online"
            # Prefer whatever the result returned, fallback to existing
            if "pod_ip" in creation_result:
                pod_object["pod_ip"] = creation_result.get("pod_ip")
            if "external_ip" in creation_result:
                pod_object["external_ip"] = creation_result.get("external_ip")
        else:
            pod_object["status"] = "failed"

        pod_object["timestamp"] = datetime.now().isoformat()

        # Persist into master.json: replace existing pod entry or append
        for server in self.master_config.get("servers", []):
            if server.get("id") == server_id:
                server.setdefault("pods", [])
                replaced = False
                for idx, existing in enumerate(server["pods"]):
                    if (existing.get("pod_id") and existing.get("pod_id") == pod_id) or \
                    (existing.get("name") and existing.get("name") == pod_id):
                        server["pods"][idx] = pod_object
                        replaced = True
                        break
                if not replaced:
                    server["pods"].append(pod_object)
                break

        # Atomic write back
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            temp_path = config_path + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(self.master_config, f, indent=2)
            os.replace(temp_path, config_path)
        except Exception as e:
            print(f"Failed to persist updated pod_object to master.json: {e}")

        return pod_object

    def delete_pod(self, server_id: str, pod_name: str, pod_data: Dict = None) -> Dict:
        """Delete a pod from the specified server and update master.json only if successful."""
        print(f"ServerManager: Deleting pod {pod_name} from server {server_id}")
        
        self.reload_config()
        if server_id not in self.server_providers:
            print(f"ServerManager: Server {server_id} not found")
            return {"error": f"Server {server_id} not found"}
        
        try:
            # Find the pod in master.json to get its namespace
            pod_namespace = None
            for server in self.master_config.get('servers', []):
                if server.get('id') == server_id:
                    for pod in server.get('pods', []):
                        if pod.get('pod_id') == pod_name or pod.get('name') == pod_name:
                            pod_object = pod
                            pod_namespace = pod.get('namespace', 'default')
                            print(f"ServerManager: Found pod {pod_name} in namespace {pod_namespace}")
                            break
                    break
            
            provider = self.server_providers[server_id]["provider"]
            pod_data = pod_data or {"PodName": pod_name, "namespace": pod_namespace}
            print(f"ServerManager: Calling provider delete_pod with data: {pod_data}")
            
            result = provider.delete_pod(pod_data)
            print(f"ServerManager: Provider delete result: {result}")
            
            if result.get('status') == 'success':
                print(f"ServerManager: Pod deletion successful, syncing pods from Kubernetes")

                try:
                    self.release_resources_in_master_simple(self.master_config, server_id, pod_object.get('requested'))
                    print(f"ServerManager: Released resources for pod {pod_name}")
                except Exception as e:
                    print(f"ServerManager: Failed to release resources for pod {pod_name}: {e}")
                    # Fallback: manually remove from master.json
                self.master_config = self._load_master_config()
                for server in self.master_config.get('servers', []):
                    if server.get('id') == server_id:
                        original_count = len(server.get('pods', []))
                        server['pods'] = [p for p in server.get('pods', []) if p.get('pod_id') != pod_name and p.get('name') != pod_name]
                        new_count = len(server.get('pods', []))
                        print(f"ServerManager: Removed {original_count - new_count} pods from master.json")
                config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
                with open(config_path, 'w') as f:
                    json.dump(self.master_config, f, indent=2)
            else:
                print(f"ServerManager: Pod deletion failed: {result}")
                return {"error": f"Failed to delete pod: {result.get('message', 'Unknown error')}"}
            
            return result
        except Exception as e:
            print(f"ServerManager: Exception during pod deletion: {e}")
            return {"error": f"Failed to delete pod: {e}"}
    
    def reload_config(self):
        """Reload the master configuration."""
        self.master_config = self._load_master_config()
        self.server_providers = {}
        self._initialize_providers()

    def reserve_resources_in_master_simple(self,master_config: dict, server_id: str, pod_requested: dict) -> dict:
        """
        Subtract requested resources from available and add to allocated in master.json for given server_id.
        Persists the change immediately by overwriting master.json (no temp file).
        Returns the updated resources dict.
        """
        # Locate server
        server = next((s for s in master_config.get("servers", []) if s.get("id") == server_id), None)
        if not server:
            raise ValueError(f"Server '{server_id}' not found in master config")

        # Ensure resource structure exists
        server.setdefault("resources", {})
        resources = server["resources"]

        # Adjust each resource
        for key in ["cpus", "ram_gb", "storage_gb", "gpus"]:
            req = pod_requested.get(key, 0) or 0
            # Increase allocated
            prev_alloc = resources["allocated"].get(key, 0)
            resources["allocated"][key] = prev_alloc + req
            # Decrease available, floor at 0
            prev_avail = resources["available"].get(key, 0)
            resources["available"][key] = max(0, prev_avail - req)

        # Persist immediately (overwrite)
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
        with open(config_path, "w") as f:
            json.dump(master_config, f, indent=2)

        return resources
    
    def release_resources_in_master_simple(self, master_config: dict, server_id: str, pod_requested: dict) -> dict:
        """
        Reverse of reserve: add requested resources back to available and subtract from allocated
        for given server_id. Caps available so allocated+available <= total. Persists immediately.
        Returns updated resources dict.
        """
        print(f"ServerManager: Releasing resources for server {server_id} with request: {pod_requested}")
        server = next((s for s in master_config.get("servers", []) if s.get("id") == server_id), None)
        if not server:
            raise ValueError(f"Server '{server_id}' not found in master config")
        
        resources = server["resources"]
        allocated = resources["allocated"]
        available = resources["available"]

        for key in ["cpus", "ram_gb", "storage_gb", "gpus"]:
            req = pod_requested.get(key, 0) or 0

            # Decrease allocated (floor at 0)
            prev_alloc = allocated.get(key, 0)
            allocated[key] = max(0, prev_alloc - req)

            # Increase available by released amount
            prev_avail = available.get(key, 0)
            available[key] = prev_avail + req

            # Persist immediately
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, "w") as f:
                json.dump(master_config, f, indent=2)

        return resources


# Create a global instance
server_manager = ServerManager() 