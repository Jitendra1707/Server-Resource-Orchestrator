"""
Kubernetes health monitoring module.
Provides comprehensive cluster health checking and status monitoring.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from kubernetes import client
from kubernetes.client.rest import ApiException

from config.config import Config
from config.constants import (
    ClusterStatus, HealthStatus, HealthCheckType, HealthCheckConfig,
    ErrorMessages, SuccessMessages, LogLevels
)
from providers.cloud_kubernetes_provider import CloudKubernetesProvider


class HealthCheckResult:
    """Result of a health check."""
    
    def __init__(self, check_type: str, status: str, details: str = "", 
                 timestamp: Optional[datetime] = None, latency_ms: Optional[int] = None):
        self.check_type = check_type
        self.status = status
        self.details = details
        self.timestamp = timestamp or datetime.now()
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'check_type': self.check_type,
            'status': self.status,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'latency_ms': self.latency_ms
        }


class ClusterHealthMonitor:
    """Monitors Kubernetes cluster health continuously."""
    
    def __init__(self):
        self._monitoring = False
        self._monitor_thread = None
        self._last_health_check = None
        self._cluster_status = ClusterStatus.UNKNOWN
        self._health_results: Dict[str, HealthCheckResult] = {}
        self._last_check_time = None
        self._error_count = 0
        self._consecutive_failures = 0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Kubernetes health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Kubernetes health monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._perform_health_checks()
                time.sleep(HealthCheckConfig.CLUSTER_HEALTH_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(HealthCheckConfig.RETRY_DELAY)
    
    def _perform_health_checks(self) -> None:
        """Perform all health checks."""
        start_time = time.time()
        
        # Check cluster connectivity
        connectivity_result = self._check_cluster_connectivity()
        self._health_results[HealthCheckType.CLUSTER_CONNECTIVITY.value] = connectivity_result
        
        if connectivity_result.status == HealthStatus.FAIL.value:
            self._cluster_status = ClusterStatus.CONNECTION_FAILED
            self._consecutive_failures += 1
            return
        
        # Check API server
        api_result = self._check_api_server()
        self._health_results[HealthCheckType.API_SERVER.value] = api_result
        
        # Check node status
        node_result = self._check_node_status()
        self._health_results[HealthCheckType.NODE_STATUS.value] = node_result
        
        # Check pod status
        pod_result = self._check_pod_status()
        self._health_results[HealthCheckType.POD_STATUS.value] = pod_result
        
        # Determine overall cluster status
        self._determine_cluster_status()
        
        # Update timing
        self._last_check_time = datetime.now()
        self._last_health_check = time.time() - start_time
        
        # Reset error count if healthy
        if self._cluster_status == ClusterStatus.HEALTHY:
            self._consecutive_failures = 0
    
    def _check_cluster_connectivity(self) -> HealthCheckResult:
        """Check if we can connect to the Kubernetes cluster using the same client as pod operations."""
        start_time = time.time()
        
        try:
            # Create a temporary provider to test connection
            # This uses the same configuration as the pod operations
            import json
            import os
            
            # Load master.json to get server configuration
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                master_config = json.load(f)
            
            # Find the first Kubernetes server
            kubernetes_servers = [s for s in master_config.get('servers', []) 
                                if s.get('type') == 'kubernetes' and 
                                not s.get('connection_coordinates', {}).get('is_dummy', False)]
            
            if not kubernetes_servers:
                return HealthCheckResult(
                    check_type=HealthCheckType.CLUSTER_CONNECTIVITY.value,
                    status=HealthStatus.FAIL.value,
                    details="No Kubernetes servers configured",
                    latency_ms=0
                )
            
            # Use the first Kubernetes server for health check
            server = kubernetes_servers[0]
            
            # Create a temporary provider with the same configuration
            provider = CloudKubernetesProvider(server)
            provider._ensure_initialized()
            provider.core_v1.list_namespace()
            
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                check_type=HealthCheckType.CLUSTER_CONNECTIVITY.value,
                status=HealthStatus.PASS.value,
                details=SuccessMessages.CLUSTER_HEALTHY,
                latency_ms=latency
            )
            
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            error_details = f"{ErrorMessages.K8S_CONNECTION_ERROR}: {str(e)}"
            
            return HealthCheckResult(
                check_type=HealthCheckType.CLUSTER_CONNECTIVITY.value,
                status=HealthStatus.FAIL.value,
                details=error_details,
                latency_ms=latency
            )
    
    def _check_api_server(self) -> HealthCheckResult:
        """Check API server responsiveness."""
        start_time = time.time()
        
        try:
            # Create a temporary provider to test connection
            # This uses the same configuration as the pod operations
            import json
            import os
            
            # Load master.json to get server configuration
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                master_config = json.load(f)
            
            # Find the first Kubernetes server
            kubernetes_servers = [s for s in master_config.get('servers', []) 
                                if s.get('type') == 'kubernetes' and 
                                not s.get('connection_coordinates', {}).get('is_dummy', False)]
            
            if not kubernetes_servers:
                return HealthCheckResult(
                    check_type=HealthCheckType.API_SERVER.value,
                    status=HealthStatus.FAIL.value,
                    details="No Kubernetes servers configured",
                    latency_ms=0
                )
            
            # Use the first Kubernetes server for health check
            server = kubernetes_servers[0]
            
            # Create a temporary provider with the same configuration
            provider = CloudKubernetesProvider(server)
            provider._ensure_initialized()
            api_resources = provider.core_v1.get_api_resources()
            
            latency = int((time.time() - start_time) * 1000)
            
            if latency > HealthCheckConfig.MAX_API_LATENCY_MS:
                return HealthCheckResult(
                    check_type=HealthCheckType.API_SERVER.value,
                    status=HealthStatus.WARN.value,
                    details=f"API server responding slowly ({latency}ms)",
                    latency_ms=latency
                )
            
            return HealthCheckResult(
                check_type=HealthCheckType.API_SERVER.value,
                status=HealthStatus.PASS.value,
                details="API server responding normally",
                latency_ms=latency
            )
            
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                check_type=HealthCheckType.API_SERVER.value,
                status=HealthStatus.FAIL.value,
                details=f"{ErrorMessages.K8S_API_SERVER_ERROR}: {str(e)}",
                latency_ms=latency
            )
    
    def _check_node_status(self) -> HealthCheckResult:
        """Check the status of all nodes in the cluster."""
        start_time = time.time()
        
        try:
            # Create a temporary provider to test connection
            # This uses the same configuration as the pod operations
            import json
            import os
            
            # Load master.json to get server configuration
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                master_config = json.load(f)
            
            # Find the first Kubernetes server
            kubernetes_servers = [s for s in master_config.get('servers', []) 
                                if s.get('type') == 'kubernetes' and 
                                not s.get('connection_coordinates', {}).get('is_dummy', False)]
            
            if not kubernetes_servers:
                return HealthCheckResult(
                    check_type=HealthCheckType.NODE_STATUS.value,
                    status=HealthStatus.FAIL.value,
                    details="No Kubernetes servers configured",
                    latency_ms=0
                )
            
            # Use the first Kubernetes server for health check
            server = kubernetes_servers[0]
            
            # Create a temporary provider with the same configuration
            provider = CloudKubernetesProvider(server)
            provider._ensure_initialized()
            nodes = provider.core_v1.list_node()
            
            total_nodes = len(nodes.items)
            ready_nodes = 0
            failed_nodes = []
            
            for node in nodes.items:
                for condition in node.status.conditions:
                    if condition.type == "Ready":
                        if condition.status == "True":
                            ready_nodes += 1
                        else:
                            failed_nodes.append(node.metadata.name)
                        break
            
            latency = int((time.time() - start_time) * 1000)
            
            if failed_nodes:
                if len(failed_nodes) > HealthCheckConfig.MAX_FAILED_NODES:
                    return HealthCheckResult(
                        check_type=HealthCheckType.NODE_STATUS.value,
                        status=HealthStatus.FAIL.value,
                        details=f"{ErrorMessages.K8S_NODE_NOT_READY}: {', '.join(failed_nodes)}",
                        latency_ms=latency
                    )
                else:
                    return HealthCheckResult(
                        check_type=HealthCheckType.NODE_STATUS.value,
                        status=HealthStatus.WARN.value,
                        details=f"Some nodes not ready: {', '.join(failed_nodes)}",
                        latency_ms=latency
                    )
            
            return HealthCheckResult(
                check_type=HealthCheckType.NODE_STATUS.value,
                status=HealthStatus.PASS.value,
                details=f"All {ready_nodes}/{total_nodes} nodes ready",
                latency_ms=latency
            )
            
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                check_type=HealthCheckType.NODE_STATUS.value,
                status=HealthStatus.FAIL.value,
                details=f"Failed to check node status: {str(e)}",
                latency_ms=latency
            )
    
    def _check_pod_status(self) -> HealthCheckResult:
        """Check the status of pods in the cluster."""
        start_time = time.time()
        
        try:
            # Create a temporary provider to test connection
            # This uses the same configuration as the pod operations
            import json
            import os
            
            # Load master.json to get server configuration
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
            with open(config_path, 'r') as f:
                master_config = json.load(f)
            
            # Find the first Kubernetes server
            kubernetes_servers = [s for s in master_config.get('servers', []) 
                                if s.get('type') == 'kubernetes' and 
                                not s.get('connection_coordinates', {}).get('is_dummy', False)]
            
            if not kubernetes_servers:
                return HealthCheckResult(
                    check_type=HealthCheckType.POD_STATUS.value,
                    status=HealthStatus.FAIL.value,
                    details="No Kubernetes servers configured",
                    latency_ms=0
                )
            
            # Use the first Kubernetes server for health check
            server = kubernetes_servers[0]
            
            # Create a temporary provider with the same configuration
            provider = CloudKubernetesProvider(server)
            provider._ensure_initialized()
            
            # Get pods from all namespaces
            pods = provider.core_v1.list_pod_for_all_namespaces()
            
            total_pods = len(pods.items)
            failed_pods = []
            pending_pods = []
            
            for pod in pods.items:
                if pod.status.phase == "Failed":
                    failed_pods.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
                elif pod.status.phase == "Pending":
                    pending_pods.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
            
            latency = int((time.time() - start_time) * 1000)
            
            failed_percentage = (len(failed_pods) / total_pods * 100) if total_pods > 0 else 0
            
            if failed_percentage > HealthCheckConfig.MAX_FAILED_PODS_PERCENT:
                return HealthCheckResult(
                    check_type=HealthCheckType.POD_STATUS.value,
                    status=HealthStatus.FAIL.value,
                    details=f"{ErrorMessages.K8S_POD_FAILED}: {failed_percentage:.1f}% failed",
                    latency_ms=latency
                )
            elif failed_pods or pending_pods:
                details = []
                if failed_pods:
                    details.append(f"{len(failed_pods)} failed")
                if pending_pods:
                    details.append(f"{len(pending_pods)} pending")
                
                return HealthCheckResult(
                    check_type=HealthCheckType.POD_STATUS.value,
                    status=HealthStatus.WARN.value,
                    details=f"Some pods have issues: {', '.join(details)}",
                    latency_ms=latency
                )
            
            return HealthCheckResult(
                check_type=HealthCheckType.POD_STATUS.value,
                status=HealthStatus.PASS.value,
                details=f"All {total_pods} pods healthy",
                latency_ms=latency
            )
            
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                check_type=HealthCheckType.POD_STATUS.value,
                status=HealthStatus.FAIL.value,
                details=f"Failed to check pod status: {str(e)}",
                latency_ms=latency
            )
    
    def _determine_cluster_status(self) -> None:
        """Determine overall cluster status based on health check results."""
        failed_checks = 0
        warning_checks = 0
        
        for result in self._health_results.values():
            if result.status == HealthStatus.FAIL.value:
                failed_checks += 1
            elif result.status == HealthStatus.WARN.value:
                warning_checks += 1
        
        if failed_checks > 0:
            self._cluster_status = ClusterStatus.UNHEALTHY
        elif warning_checks > 0:
            self._cluster_status = ClusterStatus.DEGRADED
        else:
            self._cluster_status = ClusterStatus.HEALTHY
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster status."""
        return {
            'status': self._cluster_status.value,
            'last_check': self._last_check_time.isoformat() if self._last_check_time else None,
            'check_duration_ms': int(self._last_health_check * 1000) if self._last_health_check else None,
            'consecutive_failures': self._consecutive_failures,
            'monitoring_active': self._monitoring
        }
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health check results."""
        return {
            'cluster_status': self.get_cluster_status(),
            'health_checks': {
                check_type: result.to_dict() 
                for check_type, result in self._health_results.items()
            }
        }
    
    def is_healthy(self) -> bool:
        """Check if cluster is healthy."""
        return self._cluster_status in [ClusterStatus.HEALTHY, ClusterStatus.DEGRADED]
    
    def force_health_check(self) -> Dict[str, Any]:
        """Force an immediate health check."""
        self._perform_health_checks()
        return self.get_detailed_health()


# Global health monitor instance
health_monitor = ClusterHealthMonitor() 