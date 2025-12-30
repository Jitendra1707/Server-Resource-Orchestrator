"""
Type definitions for the Resource Manager application.
Defines the structure of master.json and related data types.
"""

from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class KubeconfigCluster(TypedDict):
    """Kubernetes cluster configuration."""
    cluster: Dict[str, Any]
    name: str


class KubeconfigContext(TypedDict):
    """Kubernetes context configuration."""
    context: Dict[str, Any]
    name: str


class KubeconfigUser(TypedDict):
    """Kubernetes user configuration."""
    name: str
    user: Dict[str, Any]


class KubeconfigData(TypedDict):
    """Complete kubeconfig data structure."""
    apiVersion: str
    clusters: List[KubeconfigCluster]
    contexts: List[KubeconfigContext]
    current_context: str
    kind: str
    preferences: Dict[str, Any]
    users: List[KubeconfigUser]


class ConnectionCoordinates(TypedDict):
    """Server connection configuration."""
    method: str
    host: str
    port: int
    username: str
    kubeconfig_path: str
    kubeconfig_data: KubeconfigData
    insecure_skip_tls_verify: bool
    password: str


class ServerMetadata(TypedDict):
    """Server metadata information."""
    location: str
    environment: str
    description: str
    setup_method: str
    setup_timestamp: str
    configured_by: str
    last_updated: Optional[str]
    live_data_fresh: Optional[bool]


class ResourceInfo(TypedDict):
    """Resource information (CPU, RAM, Storage, GPU)."""
    cpus: int
    ram_gb: int
    storage_gb: int
    gpus: int


class ServerResources(TypedDict):
    """Server resource information."""
    total: ResourceInfo
    allocated: ResourceInfo
    available: ResourceInfo


class PodInfo(TypedDict):
    """Pod information structure."""
    pod_id: str
    namespace: Optional[str]
    server_id: Optional[str]
    image_url: str
    requested: ResourceInfo
    owner: str
    status: str
    timestamp: str


class ServerConfig(TypedDict):
    """Complete server configuration structure."""
    id: str
    name: str
    type: str
    environment: str
    live_refresh_interval: int
    connection_coordinates: ConnectionCoordinates
    resources: ServerResources
    metadata: ServerMetadata
    pods: List[PodInfo]
    status: str


class GlobalConfig(TypedDict):
    """Global configuration settings."""
    ui_refresh_interval: int
    auto_refresh_enabled: bool
    last_refresh: Optional[str]
    last_live_refresh: Optional[str]


class MasterConfig(TypedDict):
    """Complete master.json structure."""
    servers: List[ServerConfig]
    config: GlobalConfig


# Input types for API requests
class ServerConfigurationInput(TypedDict):
    """Input for server configuration."""
    name: str
    host: str
    username: str
    password: str
    type: Optional[str]  # Auto-set to 'kubernetes'
    environment: Optional[str]  # Auto-set to 'live'


class PodCreationInput(TypedDict):
    """Input for pod creation."""
    PodName: str
    image_url: str
    Resources: ResourceInfo
    Owner: str
    container_port: Optional[int]
    service_port: Optional[int]
    expose_service: Optional[bool]


class RefreshConfigInput(TypedDict):
    """Input for refresh configuration."""
    ui_refresh_interval: int
    auto_refresh_enabled: bool


# Response types
class ApiResponse(TypedDict):
    """Standard API response structure."""
    type: str  # 'success', 'error', 'warning'
    code: str
    message: str
    data: Optional[Dict[str, Any]]


class ServerConfigurationResponse(ApiResponse):
    """Response for server configuration."""
    data: Dict[str, Any]  # Contains server_id, server_name, total_servers, etc.


class PodCreationResponse(ApiResponse):
    """Response for pod creation."""
    data: Dict[str, Any]  # Contains pod info, service info, access_url


# Validation functions
def validate_server_config(config: Dict[str, Any]) -> ServerConfig:
    """Validate and convert a dictionary to ServerConfig."""
    # Basic validation - in production you'd want more comprehensive validation
    required_fields = ['id', 'name', 'type', 'environment', 'connection_coordinates']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    return config  # type: ignore


def validate_master_config(config: Dict[str, Any]) -> MasterConfig:
    """Validate and convert a dictionary to MasterConfig."""
    if 'servers' not in config:
        raise ValueError("Missing 'servers' field in master config")
    if 'config' not in config:
        raise ValueError("Missing 'config' field in master config")
    
    return config  # type: ignore


def create_default_server_config(
    server_id: str,
    name: str,
    host: str,
    username: str,
    password: str
) -> ServerConfig:
    """Create a default server configuration with proper typing."""
    return {
        "id": server_id,
        "name": name,
        "type": "kubernetes",
        "environment": "live",
        "live_refresh_interval": 60,
        "connection_coordinates": {
            "method": "kubeconfig",
            "host": host,
            "port": 16443,
            "username": username,
            "kubeconfig_path": f"{server_id}_kubeconfig",
            "kubeconfig_data": {},  # Will be populated by _generate_kubeconfig_with_credentials
            "insecure_skip_tls_verify": True,
            "password": password
        },
        "resources": {
            "total": {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0},
            "allocated": {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0},
            "available": {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0}
        },
        "metadata": {
            "location": "Kubernetes Server",
            "environment": "live",
            "description": f"Kubernetes cluster on {host}",
            "setup_method": "api_automated",
            "setup_timestamp": datetime.now().isoformat(),
            "configured_by": "api",
            "last_updated": None,
            "live_data_fresh": False
        },
        "pods": [],
        "status": "configured"
    }


def create_default_master_config() -> MasterConfig:
    """Create a default master configuration with proper typing."""
    return {
        "servers": [],
        "config": {
            "ui_refresh_interval": 5,
            "auto_refresh_enabled": True,
            "last_refresh": None,
            "last_live_refresh": None
        }
    } 