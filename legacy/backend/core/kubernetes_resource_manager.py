"""
Kubernetes Resource Manager
This module handles real Kubernetes resource management, replacing mock database operations.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from config.constants import (
    PodStatus, ResourceType, DefaultValues, 
    ErrorMessages, TimeFormats, KubernetesConstants
)
from config.utils import map_kubernetes_status_to_user_friendly


class KubernetesResourceManager:
    """Manages Kubernetes resources and provides real-time data."""
    
    def __init__(self):
        """Initialize Kubernetes client."""
        try:
            # Try to load kubeconfig
            k8s_config.load_kube_config()
        except Exception:
            # Fall back to in-cluster config
            k8s_config.load_incluster_config()
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        
    def get_real_nodes(self) -> List[Dict]:
        """
        Get real Kubernetes nodes and their resources.
        
        Returns:
            List of node information dictionaries
        """
        try:
            nodes = self.core_v1.list_node()
            node_list = []
            
            for i, node in enumerate(nodes.items):
                node_info = {
                    "id": f"node-{i+1:02d}",
                    "name": node.metadata.name,
                    "ip": node.status.addresses[0].address if node.status.addresses else "N/A",
                    "status": "Online" if node.status.conditions[-1].type == "Ready" else "Offline",
                    "resources": self._extract_node_resources(node),
                    "pods": []
                }
                node_list.append(node_info)
            
            return node_list
            
        except ApiException as e:
            print(f"Error getting nodes: {e}")
            return []
    
    def _extract_node_resources(self, node) -> Dict:
        """
        Extract resource information from a Kubernetes node.
        
        Args:
            node: Kubernetes node object
            
        Returns:
            Dictionary with total and available resources
        """
        capacity = node.status.capacity
        allocatable = node.status.allocatable
        
        # Convert to our format
        total = {
            "cpus": int(capacity.get("cpu", 0)),
            "ram_gb": self._parse_memory(capacity.get("memory", "0")),
            "storage_gb": self._parse_memory(capacity.get("ephemeral-storage", "0")),
            "gpus": int(capacity.get("nvidia.com/gpu", 0))
        }
        
        available = {
            "cpus": int(allocatable.get("cpu", 0)),
            "ram_gb": self._parse_memory(allocatable.get("memory", "0")),
            "storage_gb": self._parse_memory(allocatable.get("ephemeral-storage", "0")),
            "gpus": int(allocatable.get("nvidia.com/gpu", 0))
        }
        
        return {
            "total": total,
            "available": available
        }
    
    def _parse_memory(self, memory_str: str) -> int:
        """
        Parse Kubernetes memory string to GB.
        
        Args:
            memory_str: Memory string (e.g., "8Gi", "8192Mi", "8589934592")
            
        Returns:
            Memory in GB as integer
        """
        if not memory_str:
            return 0
        
        memory_str = str(memory_str)
        
        try:
            if memory_str.endswith("Ki"):
                return int(int(memory_str[:-2]) / (1024**2))
            elif memory_str.endswith("Mi"):
                return int(int(memory_str[:-2]) / 1024)
            elif memory_str.endswith("Gi"):
                return int(memory_str[:-2])
            elif memory_str.endswith("Ti"):
                return int(int(memory_str[:-2]) * 1024)
            else:
                # Assume bytes
                return int(int(memory_str) / (1024**3))
        except (ValueError, TypeError):
            return 0
    
    def get_real_pods(self) -> List[Dict]:
        """
        Get real Kubernetes pods across all namespaces.
        
        Returns:
            List of pod information dictionaries
        """
        try:
            pods = self.core_v1.list_pod_for_all_namespaces()
            pod_list = []
            
            for pod in pods.items:
                # Skip system pods
                if pod.metadata.namespace in ['kube-system', 'kubernetes-dashboard']:
                    continue
                    
                pod_info = self._extract_pod_info(pod)
                if pod_info:
                    pod_list.append(pod_info)
            
            return pod_list
            
        except ApiException as e:
            print(f"Error getting pods: {e}")
            return []
    
    def _extract_pod_info(self, pod) -> Optional[Dict]:
        """
        Extract pod information from Kubernetes pod object.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            Pod information dictionary or None if invalid
        """
        try:
            # Get resource requests and limits
            resources = self._extract_pod_resources(pod)
            
            # Get pod status
            status = self._get_pod_status(pod)
            
            pod_info = {
                "pod_id": pod.metadata.name,
                "server_id": f"node-{self._get_node_index(pod.spec.node_name) if pod.spec.node_name else 1:02d}",
                "image_url": pod.spec.containers[0].image if pod.spec.containers else "unknown",
                "requested": resources,
                "owner": pod.metadata.labels.get("owner", DefaultValues.DEFAULT_OWNER),
                "status": status,
                "timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else datetime.utcnow().strftime(TimeFormats.ISO_FORMAT),
                "pod_ip": pod.status.pod_ip if pod.status and pod.status.pod_ip else None
            }
            
            return pod_info
            
        except Exception as e:
            print(f"Error extracting pod info: {e}")
            return None
    
    def _extract_pod_resources(self, pod) -> Dict:
        """
        Extract resource requests from pod spec.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            Dictionary with resource requests
        """
        resources = {
            "gpus": 0,
            "ram_gb": 0,
            "storage_gb": 0,
            "cpus": 0
        }
        
        if pod.spec.containers:
            container = pod.spec.containers[0]
            if container.resources and container.resources.requests:
                requests = container.resources.requests
                
                # CPU
                if requests.get("cpu"):
                    cpu_str = str(requests["cpu"])
                    if cpu_str.endswith("m"):
                        resources["cpus"] = int(int(cpu_str[:-1]) / 1000)
                    else:
                        resources["cpus"] = int(cpu_str)
                
                # Memory
                if requests.get("memory"):
                    memory_str = str(requests["memory"])
                    if memory_str.endswith("Ki"):
                        resources["ram_gb"] = int(int(memory_str[:-2]) / (1024**2))
                    elif memory_str.endswith("Mi"):
                        resources["ram_gb"] = int(int(memory_str[:-2]) / 1024)
                    elif memory_str.endswith("Gi"):
                        resources["ram_gb"] = int(memory_str[:-2])
                    else:
                        resources["ram_gb"] = int(int(memory_str) / (1024**3))
                
                # GPUs
                if requests.get("nvidia.com/gpu"):
                    resources["gpus"] = int(requests["nvidia.com/gpu"])
        
        return resources
    
    def _get_pod_status(self, pod) -> str:
        """
        Get user-friendly pod status.
        
        Args:
            pod: Kubernetes pod object
            
        Returns:
            User-friendly status string
        """
        if not pod.status.phase:
            return PodStatus.UNKNOWN.value
        
        # Map Kubernetes status to user-friendly status
        kubernetes_status = pod.status.phase
        return map_kubernetes_status_to_user_friendly(kubernetes_status)
    
    def _get_node_index(self, node_name: str) -> int:
        """
        Get node index from node name.
        
        Args:
            node_name: Kubernetes node name
            
        Returns:
            Node index (1-based)
        """
        try:
            nodes = self.core_v1.list_node()
            for i, node in enumerate(nodes.items):
                if node.metadata.name == node_name:
                    return i + 1
        except Exception:
            pass
        return 1
    
    def get_servers_with_pods(self) -> List[Dict]:
        """
        Get servers (nodes) with their associated pods.
        
        Returns:
            List of servers with pods
        """
        nodes = self.get_real_nodes()
        pods = self.get_real_pods()
        
        # Group pods by server
        for node in nodes:
            node["pods"] = [pod for pod in pods if pod["server_id"] == node["id"]]
            
            # Update available resources based on actual pod usage
            self._update_available_resources(node)
        
        return nodes
    
    def _update_available_resources(self, node: Dict):
        """
        Update available resources based on actual pod usage.
        
        Args:
            node: Node dictionary to update
        """
        total = node["resources"]["total"]
        used = {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0}
        
        for pod in node["pods"]:
            requested = pod.get("requested", {})
            for resource_type in used:
                used[resource_type] += requested.get(resource_type, 0)
        
        # Calculate available
        available = {}
        for resource_type in used:
            available[resource_type] = max(0, total.get(resource_type, 0) - used[resource_type])
        
        node["resources"]["available"] = available


# Global instance
k8s_resource_manager = KubernetesResourceManager() 