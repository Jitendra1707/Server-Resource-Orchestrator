"""
Cloud Kubernetes Provider
This module handles cloud Kubernetes resource management (Azure AKS, GKE, Azure VM, etc.).
"""

import json
import os
import subprocess
import tempfile
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

# Suppress SSL/TLS warnings for development environments
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")

from config.constants import (
    PodStatus,
    ResourceType,
    DefaultValues,
    ErrorMessages,
    TimeFormats,
    KubernetesConstants,
)
from config.utils import map_kubernetes_status_to_user_friendly


class CloudKubernetesProvider:
    """Manages cloud Kubernetes resources (Azure AKS, GKE, Azure VM, etc.)."""

    def __init__(self, server_config: Dict = None):
        """Initialize cloud Kubernetes client."""
        self.server_config = server_config
        self.core_v1 = None
        self.apps_v1 = None
        self._initialized = False

        # Don't initialize immediately - wait until first use
        # This prevents password prompts during startup

    def _ensure_initialized(self):
        """Ensure Kubernetes client is initialized."""
        if self.core_v1 is None or self.apps_v1 is None:
            print("Initializing Kubernetes client...")
            if self.server_config:
                try:
                    connection_coords = self.server_config.get(
                        "connection_coordinates", {}
                    )
                    if connection_coords.get("is_dummy", False):
                        print(
                            f"⏭️  Skipping initialization for dummy server: {self.server_config.get('id')}"
                        )
                        return
                    kubeconfig_data = connection_coords.get("kubeconfig_data")
                    k8s_config.load_kube_config_from_dict(kubeconfig_data)
                    self.core_v1 = client.CoreV1Api()
                    self.apps_v1 = client.AppsV1Api()
                    print("✅ Kubeconfig loaded from dict using load_kube_config_from_dict")
                except Exception as e:
                    print(f"Failed to initialize with server config: {e}")

    def get_servers_with_pods(self) -> List[Dict]:
        """
        Get cloud Kubernetes nodes and their pods.

        Returns:
            List of cloud Kubernetes nodes with pods
        """
        try:
            # Check if this is a dummy server
            if self.server_config and self.server_config.get(
                "connection_coordinates", {}
            ).get("is_dummy", False):
                print(
                    f"⏭️  Returning static data for dummy server: {self.server_config.get('id')}"
                )
                # Return static data from server config
                return [
                    {
                        "id": self.server_config.get("id"),
                        "name": self.server_config.get("name", "Dummy Server"),
                        "ip": self.server_config.get("connection_coordinates", {}).get(
                            "host", "0.0.0.0"
                        ),
                        "status": "Offline",  # Dummy servers are offline
                        "resources": self.server_config.get(
                            "resources",
                            {
                                "total": {},
                                "allocated": {},
                                "available": {},
                                "actual_usage": {},
                            },
                        ),
                        "pods": self.server_config.get("pods", []),
                    }
                ]

            # Initialize client on first use
            self._ensure_initialized()

            nodes = self.core_v1.list_node()
            pods = self.core_v1.list_pod_for_all_namespaces()

            # Create node list
            node_list = []
            for i, node in enumerate(nodes.items):
                node_info = {
                    "id": f"cloud-node-{i+1:02d}",
                    "name": node.metadata.name,
                    "ip": (
                        node.status.addresses[0].address
                        if node.status.addresses
                        else "N/A"
                    ),
                    "status": (
                        "Online"
                        if node.status.conditions[-1].type == "Ready"
                        else "Offline"
                    ),
                    "resources": self._extract_node_resources(node),
                    "pods": [],
                }
                node_list.append(node_info)

            # Assign pods to nodes
            for pod in pods.items:
                pod_info = self._extract_pod_info(pod)
                if pod_info:
                    # Find the node this pod is running on
                    node_name = pod.spec.node_name
                    if node_name:
                        node_index = self._get_node_index(node_name, node_list)
                        if node_index is not None:
                            node_list[node_index]["pods"].append(pod_info)

            # Update available resources and get actual usage for each node
            for node in node_list:
                self._update_available_resources(node)

                # Get actual resource usage
                actual_usage = self._get_actual_resource_usage(node["name"])
                node["resources"]["actual_usage"] = actual_usage

            return node_list

        except ApiException as e:
            print(f"Error getting cloud Kubernetes data: {e}")
            return []

    def _extract_node_resources(self, node) -> Dict:
        """
        Extract resource information from a cloud Kubernetes node.

        Args:
            node: Kubernetes node object

        Returns:
            Dictionary with total, allocated, and actual usage resources
        """
        capacity = node.status.capacity
        allocatable = node.status.allocatable

        # Convert to our format
        total = {
            "cpus": int(capacity.get("cpu", 0)),
            "ram_gb": self._parse_memory(capacity.get("memory", "0")),
            "storage_gb": self._parse_memory(capacity.get("ephemeral-storage", "0")),
            "gpus": int(capacity.get("nvidia.com/gpu", 0)),
        }

        allocated = {
            "cpus": int(allocatable.get("cpu", 0)),
            "ram_gb": self._parse_memory(allocatable.get("memory", "0")),
            "storage_gb": self._parse_memory(allocatable.get("ephemeral-storage", "0")),
            "gpus": int(allocatable.get("nvidia.com/gpu", 0)),
        }

        return {
            "total": total,
            "allocated": allocated,
            "available": allocated.copy(),  # Will be updated by _update_available_resources
        }

    def _parse_memory(self, memory_str: str) -> int:
        """
        Parse Kubernetes memory string to GB.

        Args:
            memory_str: Memory string (e.g., "8Gi", "1024Mi", "100u")

        Returns:
            Memory in GB
        """
        if not memory_str:
            return 0

        memory_str = memory_str.upper()

        # Handle various suffixes
        if memory_str.endswith("GI"):
            return int(memory_str[:-2])
        elif memory_str.endswith("MI"):
            return int(memory_str[:-2]) // 1024
        elif memory_str.endswith("KI"):
            return int(memory_str[:-2]) // (1024 * 1024)
        elif memory_str.endswith("U"):
            # Handle micro units (e.g., "100u" = 100 microseconds)
            try:
                return int(memory_str[:-1]) // (
                    1024 * 1024 * 1024 * 1024
                )  # Convert to GB
            except ValueError:
                return 0
        else:
            try:
                return int(memory_str) // (1024 * 1024 * 1024)
            except ValueError:
                return 0

    def _extract_pod_info(self, pod) -> Optional[Dict]:
        """
        Extract pod information from Kubernetes pod object.

        Args:
            pod: Kubernetes pod object

        Returns:
            Pod information dictionary or None if invalid
        """
        try:
            # Skip system pods
            if pod.metadata.namespace in ["kube-system", "default"]:
                return None

            # Extract resources
            resources = self._extract_pod_resources(pod)

            # Get status
            status = self._get_pod_status(pod)

            return {
                "pod_id": pod.metadata.name,
                "name": pod.metadata.name,  # Add name field for UI compatibility
                "namespace": pod.metadata.namespace,  # Add namespace information
                "server_id": (
                    f"cloud-node-{(self._get_node_index(pod.spec.node_name, []) or 0) + 1:02d}"
                    if pod.spec.node_name
                    else "unknown"
                ),
                "image_url": (
                    pod.spec.containers[0].image if pod.spec.containers else "unknown"
                ),
                "requested": resources,
                "owner": pod.metadata.labels.get("owner", "unknown"),
                "status": status,
                "timestamp": (
                    pod.metadata.creation_timestamp.isoformat()
                    if pod.metadata.creation_timestamp
                    else datetime.now().isoformat()
                ),
                "pod_ip": (
                    pod.status.pod_ip if pod.status and pod.status.pod_ip else None
                ),
            }
        except Exception as e:
            print(f"Error extracting pod info: {e}")
            return None

    def _extract_pod_resources(self, pod) -> Dict:
        """
        Extract resource requests and limits from pod.

        Args:
            pod: Kubernetes pod object

        Returns:
            Resource dictionary
        """
        resources = {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0}

        for container in pod.spec.containers:
            if container.resources:
                # Check resource requests first
                if container.resources.requests:
                    requests = container.resources.requests

                    # CPU
                    if requests.get("cpu"):
                        cpu_str = requests["cpu"]
                        if cpu_str.endswith("m"):
                            resources["cpus"] += int(cpu_str[:-1]) // 1000
                        else:
                            resources["cpus"] += int(float(cpu_str))

                    # Memory
                    if requests.get("memory"):
                        memory_str = requests["memory"]
                        resources["ram_gb"] += self._parse_memory(memory_str)

                    # Storage
                    if requests.get("ephemeral-storage"):
                        storage_str = requests["ephemeral-storage"]
                        resources["storage_gb"] += self._parse_memory(storage_str)

                    # GPUs
                    if requests.get("nvidia.com/gpu"):
                        resources["gpus"] += int(requests["nvidia.com/gpu"])

                # If no requests, check limits
                elif container.resources.limits:
                    limits = container.resources.limits

                    # CPU
                    if limits.get("cpu"):
                        cpu_str = limits["cpu"]
                        if cpu_str.endswith("m"):
                            resources["cpus"] += int(cpu_str[:-1]) // 1000
                        else:
                            resources["cpus"] += int(float(cpu_str))

                    # Memory
                    if limits.get("memory"):
                        memory_str = limits["memory"]
                        resources["ram_gb"] += self._parse_memory(memory_str)

                    # Storage
                    if limits.get("ephemeral-storage"):
                        storage_str = limits["ephemeral-storage"]
                        resources["storage_gb"] += self._parse_memory(storage_str)

                    # GPUs
                    if limits.get("nvidia.com/gpu"):
                        resources["gpus"] += int(limits["nvidia.com/gpu"])

                # If no requests or limits, use default estimates based on container type
                else:
                    # Default estimates for common container types
                    image = container.image.lower()
                    if any(
                        keyword in image for keyword in ["nginx", "httpd", "apache"]
                    ):
                        resources["cpus"] += 0.1
                        resources["ram_gb"] += 0.1
                    elif any(
                        keyword in image
                        for keyword in ["python", "node", "java", "golang"]
                    ):
                        resources["cpus"] += 0.5
                        resources["ram_gb"] += 0.5
                    elif any(
                        keyword in image
                        for keyword in ["database", "mysql", "postgres", "redis"]
                    ):
                        resources["cpus"] += 1.0
                        resources["ram_gb"] += 1.0
                    else:
                        # Generic default for unknown containers
                        resources["cpus"] += 0.25
                        resources["ram_gb"] += 0.25

        return resources

    def _get_actual_resource_usage(self, node_name: str) -> Dict:
        """
        Get actual resource usage from Kubernetes metrics API.

        Args:
            node_name: Name of the node

        Returns:
            Dictionary with actual resource usage
        """
        try:
            # Try to get metrics from metrics.k8s.io API
            # Note: This requires metrics-server to be installed
            from kubernetes.client import CustomObjectsApi

            custom_api = CustomObjectsApi()

            # Get pod metrics
            metrics = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1", namespace="", plural="pods"
            )

            total_usage = {"cpus": 0.0, "ram_gb": 0.0, "storage_gb": 0.0, "gpus": 0}

            for pod_metric in metrics.get("items", []):
                pod_name = pod_metric["metadata"]["name"]
                namespace = pod_metric["metadata"]["namespace"]

                # Check if this pod is on our target node
                try:
                    pod = self.core_v1.read_namespaced_pod(pod_name, namespace)
                    if pod.spec.node_name == node_name:
                        for container in pod_metric.get("containers", []):
                            # CPU usage (convert from nanocores to cores)
                            cpu_usage = container.get("usage", {}).get("cpu", "0")
                            if cpu_usage.endswith("n"):
                                total_usage["cpus"] += int(cpu_usage[:-1]) / 1000000000
                            else:
                                total_usage["cpus"] += float(cpu_usage)

                            # Memory usage (convert to GB)
                            memory_usage = container.get("usage", {}).get("memory", "0")
                            total_usage["ram_gb"] += self._parse_memory(memory_usage)

                except Exception as e:
                    print(f"Warning: Could not get pod info for {pod_name}: {e}")
                    continue

            return total_usage

        except Exception as e:
            print(f"Warning: Could not get metrics from Kubernetes API: {e}")
            # Return empty usage if metrics API is not available
            return {"cpus": 0.0, "ram_gb": 0.0, "storage_gb": 0.0, "gpus": 0}

    def _get_pod_status(self, pod) -> str:
        """
        Get user-friendly pod status.

        Args:
            pod: Kubernetes pod object

        Returns:
            User-friendly status string
        """
        if not pod.status:
            return PodStatus.UNKNOWN.value

        phase = pod.status.phase

        if phase == "Running":
            return PodStatus.ONLINE.value
        elif phase == "Pending":
            return PodStatus.PENDING.value
        elif phase == "Failed":
            return PodStatus.FAILED.value
        elif phase == "Succeeded":
            return PodStatus.ONLINE.value
        else:
            return PodStatus.UNKNOWN.value

    def _get_node_index(self, node_name: str, node_list: List[Dict]) -> Optional[int]:
        """
        Get node index by name.

        Args:
            node_name: Name of the node
            node_list: List of nodes

        Returns:
            Node index or None if not found
        """
        for i, node in enumerate(node_list):
            if node.get("name") == node_name:
                return i
        return None

    def _update_available_resources(self, node: Dict):
        """
        Update available resources based on running pods.

        Args:
            node: Node dictionary to update
        """
        total = node["resources"]["total"]
        available = node["resources"]["available"].copy()

        # Subtract pod resources
        for pod in node.get("pods", []):
            requested = pod.get("requested", {})
            for key in ["cpus", "ram_gb", "storage_gb", "gpus"]:
                available[key] = max(0, available[key] - requested.get(key, 0))

        node["resources"]["available"] = available

    def create_pod(self, pod_data: Dict) -> Dict:
        """Create multiple pod replicas in a dynamic namespace (from payload or default to 'default')."""
        self._ensure_initialized()
        print(f"Creating pod with data: {pod_data}")
        try:
            import uuid
            import time

            base_name = pod_data.get("pod_id") or f"deployment-{uuid.uuid4().hex[:8]}"
            resources = pod_data.get("requested", {}) or {}
            image_url = pod_data.get("image_url", "nginx:latest")
            namespace = pod_data.get("namespace") or "default"
            replicas = pod_data.get("replicas", 1)

            # Ensure namespace exists (skip default)
            if namespace != "default":
                try:
                    self.core_v1.read_namespace(namespace)
                except Exception:
                    ns_body = client.V1Namespace(
                        metadata=client.V1ObjectMeta(name=namespace)
                    )
                    self.core_v1.create_namespace(ns_body)

            # Build resource requests
            resource_requests = {}
            if resources.get("cpus", 0):
                resource_requests["cpu"] = str(resources.get("cpus", 1))
            if resources.get("ram_gb", 0):
                resource_requests["memory"] = f"{resources.get('ram_gb', 1)}Gi"
            if resources.get("storage_gb", 0):
                resource_requests["ephemeral-storage"] = (
                    f"{resources.get('storage_gb', 1)}Gi"
                )

            resource_requirements = None
            if resource_requests:
                resource_requirements = client.V1ResourceRequirements(
                    requests=resource_requests
                )

            # Define container
            container = client.V1Container(name=base_name, image=image_url)
            if resource_requirements:
                container.resources = resource_requirements

            # Pod template
            pod_template_spec = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": base_name}),
                spec=client.V1PodSpec(containers=[container]),
            )

            # Deployment spec & metadata
            deployment_spec = client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": base_name}),
                template=pod_template_spec,
            )
            deployment_metadata = client.V1ObjectMeta(
                name=base_name, labels={"app": base_name}
            )
            deployment = client.V1Deployment(
                metadata=deployment_metadata, spec=deployment_spec
            )

            # Create deployment
            self.apps_v1.create_namespaced_deployment(
                namespace=namespace, body=deployment
            )

            # Wait for at least one pod to become ready
            timeout = 60  # seconds
            start = time.time()
            ready_pod = None
            label_selector = f"app={base_name}"
            while time.time() - start < timeout:
                try:
                    pods_resp = self.core_v1.list_namespaced_pod(
                        namespace=namespace, label_selector=label_selector
                    )
                except Exception:
                    pods_resp = None

                if pods_resp and pods_resp.items:
                    for pod in pods_resp.items:
                        if pod.status and pod.status.phase == "Running":
                            container_statuses = pod.status.container_statuses or []
                            if container_statuses and all(
                                cs.ready for cs in container_statuses
                            ):
                                ready_pod = pod
                                break
                    if ready_pod:
                        break
                time.sleep(2)

            if not ready_pod:
                return {
                    "status": "error",
                    "message": f"Deployment {base_name} created but no pod became ready within {timeout}s",
                    "deployment_name": base_name,
                    "replicas": replicas,
                }

            # Resolve pod_ip and external_ip (prefer node ExternalIP if available)
            pod_ip = (
                ready_pod.status.pod_ip
                if ready_pod.status and ready_pod.status.pod_ip
                else None
            )
            external_ip = pod_ip  # fallback

            node_name = ready_pod.spec.node_name
            if node_name:
                try:
                    node_obj = self.core_v1.read_node(node_name)
                    for addr in node_obj.status.addresses or []:
                        if addr.type == "ExternalIP":
                            external_ip = addr.address
                            break
                except Exception:
                    pass  # ignore, keep fallback

            return {
                "status": "success",
                "message": f"Deployment {base_name} created with {replicas} replicas in namespace {namespace}",
                "deployment_name": base_name,
                "replicas": replicas,
                "pod_ip": pod_ip,
                "external_ip": external_ip,
            }

        except ApiException as e:
            return {"status": "error", "message": f"Kubernetes API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to create pod: {e}"}

    def delete_pod(self, pod_data: Dict) -> Dict:
        """Delete the entire namespace containing the pod (destructive)."""
        try:
            self._ensure_initialized()

            namespace = pod_data.get("namespace")
            pod_name = pod_data.get("PodName") or pod_data.get("pod_id")

            if not namespace:
                return {"status": "error", "message": "Namespace is required to delete."}

            # Safety: don't allow deleting critical built-in namespaces
            if namespace in ("default", "kube-system", "kube-public"):
                return {
                    "status": "error",
                    "message": f"Refusing to delete protected namespace '{namespace}'"
                }

            print(f"Attempting to delete namespace {namespace} (origin pod: {pod_name})")

            if not self.core_v1:
                return {"status": "error", "message": "Kubernetes client not initialized"}

            # Check if namespace exists
            try:
                self.core_v1.read_namespace(name=namespace)
            except ApiException as e:
                if e.status == 404:
                    print(f"Namespace {namespace} not found, already deleted")
                    return {
                        "status": "success",
                        "message": f"Namespace {namespace} was already deleted"
                    }
                else:
                    print(f"Error reading namespace {namespace}: {e}")
                    return {"status": "error", "message": f"Error reading namespace: {e}"}

            # Delete namespace with foreground propagation to ensure contained resources are cleaned up
            try:
                delete_options = client.V1DeleteOptions(propagation_policy="Foreground")
                self.core_v1.delete_namespace(name=namespace, body=delete_options)
            except ApiException as e:
                print(f"Error initiating namespace deletion: {e}")
                return {"status": "error", "message": f"Failed to delete namespace: {e}"}

            # Wait for namespace to actually disappear
            import time

            timeout = 60  # seconds
            start = time.time()
            while time.time() - start < timeout:
                try:
                    self.core_v1.read_namespace(name=namespace)
                    # Still exists
                    time.sleep(2)
                except ApiException as e:
                    if e.status == 404:
                        print(f"Namespace {namespace} successfully deleted")
                        return {
                            "status": "success",
                            "message": f"Namespace {namespace} deleted"
                        }
                    else:
                        print(f"Error checking namespace deletion status: {e}")
                        return {
                            "status": "error",
                            "message": f"Error verifying namespace deletion: {e}"
                        }

            return {
                "status": "error",
                "message": f"Namespace {namespace} deletion did not complete within {timeout}s"
            }

        except ApiException as e:
            print(f"Kubernetes API error during namespace deletion: {e}")
            if e.status == 404:
                return {
                    "status": "success",
                    "message": f"Namespace {namespace} was already deleted"
                }
            else:
                return {"status": "error", "message": f"Kubernetes API error: {e}"}
        except Exception as e:
            print(f"Unexpected error during namespace deletion: {e}")
            return {"status": "error", "message": f"Failed to delete namespace: {e}"}

    def get_cluster_available_resources_raw(self) -> dict:
        """
        Aggregate available cluster-level resources by summing allocatable across all nodes
        and subtracting pod requests. Returns raw values with keys: cpus, ram_gb, storage_gb, gpus.
        Does not depend on any other internal helper.
        """
        def _parse_cpu(cpu_str: str) -> float:
            if not cpu_str:
                return 0.0
            s = cpu_str.strip().lower()
            try:
                if s.endswith("m"):  # millicores
                    return int(s[:-1]) / 1000.0
                return float(s)
            except Exception:
                return 0.0

        def _parse_mem_to_gb(mem_str: str) -> int:
            if not mem_str:
                return 0
            s = mem_str.upper()
            try:
                if s.endswith("GI"):
                    return int(float(s[:-2]))
                elif s.endswith("MI"):
                    return int(float(s[:-2])) // 1024
                elif s.endswith("KI"):
                    return int(float(s[:-2])) // (1024 * 1024)
                else:
                    # assume bytes if numeric
                    val = int(s)
                    return val // (1024 ** 3)
            except Exception:
                return 0

        self._ensure_initialized()
        try:
            nodes = self.core_v1.list_node()
            pods = self.core_v1.list_pod_for_all_namespaces()

            # Start with total allocatable (cluster-level)
            available_cpus = 0.0
            available_ram = 0
            available_storage = 0
            available_gpus = 0

            for node in nodes.items:
                alloc = getattr(node.status, "allocatable", {}) or {}
                cpu_alloc = alloc.get("cpu", "0")
                mem_alloc = alloc.get("memory", "")
                storage_alloc = alloc.get("ephemeral-storage", "")
                gpu_alloc = alloc.get("nvidia.com/gpu", 0)

                available_cpus += _parse_cpu(cpu_alloc)
                available_ram += _parse_mem_to_gb(mem_alloc)
                available_storage += _parse_mem_to_gb(storage_alloc)
                try:
                    available_gpus += int(gpu_alloc)
                except Exception:
                    pass

            # Subtract pod requests (including system pods)
            for pod in pods.items:
                if not getattr(pod.spec, "containers", None):
                    continue
                for container in pod.spec.containers:
                    if not getattr(container, "resources", None):
                        continue

                    reqs = {}
                    if getattr(container.resources, "requests", None):
                        reqs = container.resources.requests
                    elif getattr(container.resources, "limits", None):
                        reqs = container.resources.limits

                    if reqs.get("cpu"):
                        available_cpus = max(0.0, available_cpus - _parse_cpu(str(reqs["cpu"])))
                    if reqs.get("memory"):
                        available_ram = max(0, available_ram - _parse_mem_to_gb(str(reqs["memory"])))
                    if reqs.get("ephemeral-storage"):
                        available_storage = max(0, available_storage - _parse_mem_to_gb(str(reqs["ephemeral-storage"])))
                    if reqs.get("nvidia.com/gpu"):
                        try:
                            available_gpus = max(0, available_gpus - int(reqs["nvidia.com/gpu"]))
                        except Exception:
                            pass

            return {
                "resources": {
                    "available": {
                        ResourceType.GPUS.value: available_gpus,
                        ResourceType.RAM_GB.value: available_ram,
                        ResourceType.STORAGE_GB.value: available_storage,
                    }
                }
            }
        except Exception as e:
            print(f"Warning: failed to fetch cluster available resources raw: {e}")
            return {
                    "resources": {
                        "available": {
                            ResourceType.GPUS.value: 0,
                            ResourceType.RAM_GB.value: 0,
                            ResourceType.STORAGE_GB.value: 0,
                        }
                    }
                }




# Global instance for cloud Kubernetes
cloud_kubernetes_provider = CloudKubernetesProvider()
