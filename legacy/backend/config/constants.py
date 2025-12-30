"""
Constants and enums for Resource Manager backend.
Centralized definition of all constants used throughout the application.
"""

from enum import Enum
from typing import List, Optional
import os
import subprocess
import re


# Application configuration constants
APP_CONFIG = {
    "display_name": "Resource Manager",
    "description": "Live mode managing all real servers via master.json",
    "capabilities": {
        "real_kubernetes": True,
        "port_management": True,
        "service_creation": True,
        "external_access": True,
        "multi_server": True
    }
}


class AuthMethod(Enum):
    """Kubernetes authentication methods."""
    LOCAL_KUBECONFIG = "local_kubeconfig"
    AZURE_AKS = "azure_aks"
    IN_CLUSTER = "in_cluster"
    SERVICE_ACCOUNT = "service_account"


class ResourceType(Enum):
    """Resource types for pods."""
    GPUS = "gpus"
    RAM_GB = "ram_gb"
    STORAGE_GB = "storage_gb"


class PodStatus(Enum):
    """Pod status values - user-friendly and comprehensive."""
    
    # Success states
    ONLINE = "online"           # Pod is running and healthy
    PENDING = "pending"         # Pod is being initialized/starting up
    
    # Progress states  
    IN_PROGRESS = "in-progress" # Pod is being created/deployed
    UPDATING = "updating"       # Pod is being updated/modified
    
    # Failure states
    FAILED = "failed"           # Pod creation/deployment failed
    ERROR = "error"             # Pod encountered an error
    
    # Unknown/Stale states
    UNKNOWN = "unknown"         # Status cannot be determined
    TIMEOUT = "timeout"         # Operation timed out
    
    # Legacy Kubernetes states (for compatibility)
    RUNNING = "Running"         # Kubernetes Running state
    KUBERNETES_PENDING = "Pending"  # Kubernetes Pending state
    TERMINATED = "Terminated"   # Kubernetes Terminated state


class ApiResponse(Enum):
    """API response status."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class HttpStatus(Enum):
    """HTTP status codes."""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


class DefaultValues:
    """Default values used throughout the application."""
    
    # Default container images
    DEFAULT_IMAGE = "nginx:latest"
    DEFAULT_IMAGE_DEV = "nginx:latest"
    DEFAULT_IMAGE_PROD = "nginx:latest"
    
    # Default resource values
    DEFAULT_CPU = 1
    DEFAULT_MEMORY_GB = 1
    DEFAULT_GPUS = 0
    DEFAULT_STORAGE_GB = 1
    
    # Default pod settings
    DEFAULT_OWNER = "unknown"
    DEFAULT_REPLICAS = 1
    DEFAULT_PORT = 80
    DEFAULT_TARGET_PORT = 80
    
    # Port configuration
    DEFAULT_CONTAINER_PORT = 80
    DEFAULT_SERVICE_PORT = 80
    MIN_NODE_PORT = 30000
    MAX_NODE_PORT = 32767
    
    # Common application ports
    COMMON_PORTS = {
        'web': 80,
        'https': 443,
        'api': 8080,
        'nodejs': 3000,
        'python': 5000,
        'mysql': 3306,
        'postgres': 5432,
        'mongodb': 27017,
        'redis': 6379,
        'nginx': 80,
        'apache': 80
    }
    
    # Default namespace prefixes
    NAMESPACE_PREFIX_DEV = "rm-dev"
    NAMESPACE_PREFIX_PROD = "rm-prod"
    NAMESPACE_PREFIX_STAGING = "rm-staging"


class KubernetesConstants:
    """Kubernetes-specific constants."""
    
    # API versions
    CORE_V1_API = "v1"
    APPS_V1_API = "apps/v1"
    
    # Resource kinds
    NAMESPACE = "Namespace"
    DEPLOYMENT = "Deployment"
    SERVICE = "Service"
    POD = "Pod"
    
    # Label keys
    APP_LABEL = "app"
    ENVIRONMENT_LABEL = "environment"
    
    # Service types
    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    
    # Error codes
    ALREADY_EXISTS = 409
    NOT_FOUND = 404
    CONFLICT = 409


class ValidationRules:
    """Validation rules and constraints."""
    
    # Pod name rules
    POD_NAME_MIN_LENGTH = 1
    POD_NAME_MAX_LENGTH = 63
    POD_NAME_PATTERN = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
    
    # Resource limits
    MAX_GPUS = 16
    MAX_RAM_GB = 1024
    MAX_STORAGE_GB = 10000
    
    # Image URL patterns
    FULL_URL_PATTERN = r'^https?://[^\s/$.?#].[^\s]*$'


class ConfigKeys:
    """Configuration keys for environment variables."""
    
    # Environment
    ENVIRONMENT = "ENVIRONMENT"
    DEBUG = "DEBUG"
    
    # Azure
    AZURE_SUBSCRIPTION_ID = "AZURE_SUBSCRIPTION_ID"
    AZURE_RESOURCE_GROUP = "AZURE_RESOURCE_GROUP"
    AZURE_AKS_CLUSTER_NAME = "AZURE_AKS_CLUSTER_NAME"
    AZURE_USE_MANAGED_IDENTITY = "AZURE_USE_MANAGED_IDENTITY"
    
    # Azure VM (for cloud-k8s mode)
    AZURE_VM_IP = "AZURE_VM_IP"
    AZURE_VM_USERNAME = "AZURE_VM_USERNAME"
    AZURE_VM_SSH_KEY_PATH = "AZURE_VM_SSH_KEY_PATH"
    AZURE_VM_KUBECONFIG = "AZURE_VM_KUBECONFIG"
    AZURE_VM_PASSWORD = "AZURE_VM_PASSWORD"
    
    # CORS
    CORS_ORIGINS = "CORS_ORIGINS"
    
    # Kubernetes
    KUBECONFIG = "KUBECONFIG"
    
    # Flask
    FLASK_ENV = "FLASK_ENV"
    FLASK_DEBUG = "FLASK_DEBUG"


class ErrorMessages:
    """Standard error messages."""
    
    # Kubernetes errors
    K8S_CONFIG_ERROR = "Could not load Kubernetes configuration. Please ensure kubeconfig is available."
    K8S_CONNECTION_ERROR = "Failed to connect to Kubernetes cluster."
    K8S_AUTH_ERROR = "Failed to authenticate with Kubernetes cluster."
    K8S_CLUSTER_NOT_RUNNING = "Kubernetes cluster is not running or accessible."
    K8S_API_SERVER_ERROR = "Kubernetes API server is not responding."
    K8S_NODE_NOT_READY = "One or more Kubernetes nodes are not ready."
    K8S_POD_FAILED = "One or more pods are in failed state."
    
    # Health check errors
    HEALTH_CHECK_FAILED = "Health check failed: {details}"
    CLUSTER_HEALTH_DEGRADED = "Cluster health is degraded: {issues}"
    
    # Validation errors
    POD_NAME_REQUIRED = "Pod name is required."
    POD_NAME_LOWERCASE = "Pod name must be lowercase."
    POD_NAME_NO_UNDERSCORE = "Pod name must not contain underscores."
    RESOURCES_REQUIRED = "Resources must be specified."
    IMAGE_URL_REQUIRED = "Image URL is required in production environment."
    
    # Resource errors
    INSUFFICIENT_RESOURCES = "Not enough {resource} available. Requested: {requested}, Available: {available}"
    RESOURCE_VALIDATION_ERROR = "Invalid resource specification."
    
    # API errors
    INVALID_JSON = "Invalid JSON data"
    MISSING_FIELDS = "Missing required field: {fields}"
    SERVER_NOT_FOUND = "Server '{server_id}' not found."
    POD_NOT_FOUND = "Pod '{pod_name}' not found on any server."
    
    # General errors
    SERVER_ERROR = "Server error"
    UNKNOWN_ERROR = "An unknown error occurred"


class SuccessMessages:
    """Standard success messages."""
    
    POD_CREATED = "Pod created successfully"
    POD_DELETED = "Pod deleted successfully"
    OPERATION_SUCCESS = "Operation completed successfully"
    CLUSTER_HEALTHY = "Kubernetes cluster is healthy"
    HEALTH_CHECK_PASSED = "All health checks passed"


class ApiEndpoints:
    """API endpoint paths."""
    
    ROOT = "/"
    SERVERS = "/servers"
    CREATE_POD = "/create"
    DELETE_POD = "/delete"
    RESOURCE_VALIDATION = "/resource-validation"
    HEALTH_CHECK = "/health"

    HEALTH_DETAILED = "/health/detailed"


class ContentTypes:
    """HTTP content types."""
    
    JSON = "application/json"
    TEXT_HTML = "text/html"
    TEXT_PLAIN = "text/plain"


class TimeFormats:
    """Time format constants."""
    
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOG_FORMAT = "%Y-%m-%d %H:%M:%S"


class FilePaths:
    """File path constants."""
    

    CONFIG_FILE = ".env"
    LOG_FILE = "app.log"
    TEMP_DIR = "/tmp"


class LogLevels(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL" 


class ClusterStatus(Enum):
    """Kubernetes cluster status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    CONNECTION_FAILED = "connection_failed"
    AUTH_FAILED = "auth_failed"
    NOT_RUNNING = "not_running"


class HealthCheckType(Enum):
    """Types of health checks."""
    CLUSTER_CONNECTIVITY = "cluster_connectivity"
    API_SERVER = "api_server"
    NODE_STATUS = "node_status"
    POD_STATUS = "pod_status"
    RESOURCE_AVAILABILITY = "resource_availability"


class HealthStatus(Enum):
    """Health status values."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class HealthCheckConfig:
    """Health check configuration constants."""
    
    # Polling intervals (in seconds)
    CLUSTER_HEALTH_INTERVAL = 30  # Check cluster health every 30 seconds
    NODE_STATUS_INTERVAL = 60     # Check node status every 60 seconds
    POD_STATUS_INTERVAL = 120     # Check pod status every 2 minutes
    
    # Timeout values (in seconds)
    API_SERVER_TIMEOUT = 10       # API server connection timeout
    NODE_READY_TIMEOUT = 30       # Node ready check timeout
    POD_READY_TIMEOUT = 60        # Pod ready check timeout
    
    # Thresholds
    MAX_FAILED_NODES = 1          # Maximum number of failed nodes before cluster is unhealthy
    MAX_FAILED_PODS_PERCENT = 20  # Maximum percentage of failed pods before cluster is degraded
    MAX_API_LATENCY_MS = 1000     # Maximum API server latency in milliseconds
    
    # Retry settings
    MAX_RETRIES = 3               # Maximum number of retries for health checks
    RETRY_DELAY = 5               # Delay between retries in seconds 


# Port Configuration
class Ports:
    """Port configuration with environment-based defaults"""
    
    # Default ports (can be overridden by environment variables)
    BACKEND_DEFAULT = 5005
    KUBERNETES_API_DEFAULT = 8443
    
    # Environment variable names
    BACKEND_PORT_ENV = 'BACKEND_PORT'
    KUBERNETES_API_PORT_ENV = 'KUBERNETES_API_PORT'
    
    @classmethod
    def get_backend_port(cls) -> int:
        """Get backend port from environment or use default"""
        return int(os.getenv(cls.BACKEND_PORT_ENV, cls.BACKEND_DEFAULT))
    
    @classmethod
    def get_kubernetes_api_port(cls) -> int:
        """Get Kubernetes API port from environment or use default"""
        return int(os.getenv(cls.KUBERNETES_API_PORT_ENV, cls.KUBERNETES_API_DEFAULT)) 