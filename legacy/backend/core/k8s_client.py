"""
Kubernetes client module with environment-aware authentication.
Supports both development (local kubeconfig) and production (Azure AKS) environments.
"""

import os
import tempfile
import uuid
import yaml
from typing import Optional, Dict, Any
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from config.config import Config
from config.constants import (
    AuthMethod, KubernetesConstants, DefaultValues, ErrorMessages
)


class KubernetesClient:
    """Kubernetes client with environment-aware authentication."""
    
    def __init__(self):
        self.core_v1 = None
        self.apps_v1 = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize Kubernetes client based on environment."""
        if self._initialized:
            return
            
        auth_method = Config.get_kubernetes_config()['auth_method']
        
        if auth_method == AuthMethod.LOCAL_KUBECONFIG.value:
            self._init_local_kubeconfig()
        elif auth_method == AuthMethod.AZURE_AKS.value:
            self._init_azure_aks()
        else:
            raise ValueError(f"Unsupported authentication method: {auth_method}")
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self._initialized = True
    
    def _init_local_kubeconfig(self) -> None:
        """Initialize using local kubeconfig file."""
        try:
            # Try to load from default kubeconfig locations
            k8s_config.load_kube_config()
        except Exception:
            try:
                # Try in-cluster configuration
                k8s_config.load_incluster_config()
            except Exception:
                raise Exception(ErrorMessages.K8S_CONFIG_ERROR)
    
    def _init_azure_aks(self) -> None:
        """Initialize using Azure AKS authentication."""
        try:
            # This will be implemented when Azure SDK is added
            # For now, fall back to local kubeconfig
            self._init_local_kubeconfig()
        except Exception as e:
            raise Exception(f"{ErrorMessages.K8S_AUTH_ERROR}: {str(e)}")
    
    def create_namespace(self, namespace: str) -> None:
        """Create a namespace."""
        if not self._initialized:
            self.initialize()
        
        ns_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
        try:
            self.core_v1.create_namespace(ns_body)
        except ApiException as e:
            if e.status != KubernetesConstants.ALREADY_EXISTS:
                raise
    
    def create_deployment(self, namespace: str, name: str, image: str, resources: Dict[str, Any]) -> None:
        """Create a deployment."""
        if not self._initialized:
            self.initialize()
        
        container = client.V1Container(
            name=name,
            image=image,
            resources=client.V1ResourceRequirements(
                requests={
                    'cpu': str(resources.get('ram_gb', 1)),
                    'memory': f"{resources.get('ram_gb', 1)}Gi",
                    'nvidia.com/gpu': str(resources.get('gpus', 0))
                },
                limits={
                    'cpu': str(resources.get('ram_gb', 1)),
                    'memory': f"{resources.get('ram_gb', 1)}Gi",
                    'nvidia.com/gpu': str(resources.get('gpus', 0))
                }
            )
        )
        
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}),
            spec=client.V1PodSpec(containers=[container])
        )
        
        spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": name}),
            template=template
        )
        
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=spec
        )
        
        try:
            self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        except ApiException as e:
            if e.status != KubernetesConstants.ALREADY_EXISTS:
                raise
    
    def create_service(self, namespace: str, name: str) -> None:
        """Create a service."""
        if not self._initialized:
            self.initialize()
        
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1ServiceSpec(
                selector={"app": name},
                ports=[client.V1ServicePort(port=80, target_port=80)],
                type="ClusterIP"
            )
        )
        
        try:
            self.core_v1.create_namespaced_service(namespace=namespace, body=service)
        except ApiException as e:
            if e.status != 409:  # 409 = AlreadyExists
                raise
    
    def delete_service(self, namespace: str, name: str) -> None:
        """Delete a service."""
        if not self._initialized:
            self.initialize()
        
        try:
            self.core_v1.delete_namespaced_service(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:  # 404 = NotFound
                raise
    
    def delete_deployment(self, namespace: str, name: str) -> None:
        """Delete a deployment."""
        if not self._initialized:
            self.initialize()
        
        try:
            self.apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)
        except ApiException as e:
            if e.status != 404:  # 404 = NotFound
                raise
    
    def delete_namespace(self, namespace: str) -> None:
        """Delete a namespace."""
        if not self._initialized:
            self.initialize()
        
        try:
            self.core_v1.delete_namespace(name=namespace)
        except ApiException as e:
            if e.status != 404:  # 404 = NotFound
                raise


# Global Kubernetes client instance
k8s_client = KubernetesClient() 