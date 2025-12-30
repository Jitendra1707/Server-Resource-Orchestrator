"""
Server Configuration API Module
Handles server configuration endpoints.
"""

import os
import json
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Dict, Optional

from config.types import (
    MasterConfig, ServerConfig, ServerConfigurationInput,
    create_default_server_config, validate_master_config,
    validate_server_config
)

# Create blueprint
server_config_bp = Blueprint('server_config', __name__, url_prefix='/api/server-config')

def _load_master_config() -> MasterConfig:
    """Load master configuration from file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            return validate_master_config(config_data)
    except Exception as e:
        print(f"Error loading master config: {e}")
        return create_default_master_config()

def _save_master_config(config: MasterConfig):
    """Save master configuration to file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print("✅ Master configuration updated successfully")
    except Exception as e:
        print(f"Error saving master config: {e}")
        raise

def _update_server_kubeconfig(server_id: str, username: str, password: str) -> Dict:
    """Update server kubeconfig with provided credentials."""
    try:
        # Load current config
        config = _load_master_config()
        
        # Find the server
        server_found = False
        for server in config.get('servers', []):
            if server.get('id') == server_id:
                server_found = True
                
                # Generate kubeconfig with credentials
                kubeconfig_data = _generate_kubeconfig_with_credentials(
                    server.get('connection_coordinates', {}).get('host'),
                    server.get('connection_coordinates', {}).get('port', 16443),
                    username,
                    password
                )
                
                # Update the server's kubeconfig
                if 'connection_coordinates' not in server:
                    server['connection_coordinates'] = {}
                
                server['connection_coordinates']['kubeconfig_data'] = kubeconfig_data
                server['connection_coordinates']['username'] = username
                server['connection_coordinates']['password'] = password  # Store for future reference
                
                break
        
        if not server_found:
            return {
                "type": "error",
                "code": "SERVER_NOT_FOUND",
                "message": f"Server with ID '{server_id}' not found"
            }
        
        # Save updated config
        _save_master_config(config)
        
        return {
            "type": "success",
            "code": "KUBECONFIG_UPDATED",
            "message": f"Kubeconfig updated successfully for server '{server_id}'"
        }
        
    except Exception as e:
        return {
            "type": "error",
            "code": "UPDATE_FAILED",
            "message": f"Failed to update kubeconfig: {str(e)}"
        }

def _generate_kubeconfig_with_credentials(host: str, port: int, username: str, password: str) -> Dict:
    """Generate kubeconfig with username/password authentication."""
    # This is a simplified version - in production you'd want to actually
    # connect to the cluster and get proper certificates
    return {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "server": f"https://{host}:{port}",
                    "insecure-skip-tls-verify": True
                },
                "name": "microk8s-cluster"
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "microk8s-cluster",
                    "user": "admin"
                },
                "name": "microk8s"
            }
        ],
        "current-context": "microk8s",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "admin",
                "user": {
                    "username": username,
                    "password": password
                }
            }
        ]
    }

def _fetch_and_update_live_data(server_id: str) -> Dict:
    """Fetch live pod data from a configured server and update master.json."""
    try:
        # Get the server configuration
        config = _load_master_config()
        server: Optional[ServerConfig] = None
        for s in config.get('servers', []):
            if s.get('id') == server_id:
                server = s
                break
        
        if not server:
            return {
                "type": "error",
                "code": "SERVER_NOT_FOUND",
                "message": f"Server {server_id} not found in configuration"
            }
        
        # Try to get live data from the server manager
        from core.server_manager import server_manager
        server_manager.reload_config()  # Ensure fresh config
        
        live_server_data = server_manager.get_server_with_pods(server_id)
        
        if live_server_data:
            # Update the server with live data
            server.update({
                "pods": live_server_data.get('pods', []),
                "resources": live_server_data.get('resources', {}),
                "status": live_server_data.get('status', 'configured'),
                "metadata": {
                    **server.get('metadata', {}),
                    "last_updated": datetime.now().isoformat(),
                    "live_data_fresh": True
                }
            })
            
            # Save updated config
            _save_master_config(config)
            
            return {
                "type": "success",
                "code": "LIVE_DATA_UPDATED",
                "message": f"Live data updated for server {server_id}",
                "data": {
                    "pods_count": len(live_server_data.get('pods', [])),
                    "status": live_server_data.get('status', 'configured')
                }
            }
        else:
            # No live data available, but preserve existing data if available
            existing_pods = server.get('pods', [])
            existing_resources = server.get('resources', {})
            
            # Only update metadata, preserve existing live data
            server.update({
                "metadata": {
                    **server.get('metadata', {}),
                    "last_updated": datetime.now().isoformat(),
                    "live_data_fresh": False
                }
            })
            
            _save_master_config(config)
            
            return {
                "type": "warning",
                "code": "NO_LIVE_DATA",
                "message": f"Server {server_id} configured but no live data available (preserving existing data)",
                "data": {
                    "pods_count": len(existing_pods),
                    "status": server.get('status', 'configured')
                }
            }
            
    except Exception as e:
        return {
            "type": "error",
            "code": "LIVE_DATA_FAILED",
            "message": f"Failed to fetch live data: {str(e)}"
        }

def _get_refresh_interval() -> int:
    """Get the refresh interval from master.json config."""
    try:
        config = _load_master_config()
        return config.get('config', {}).get('refresh_interval', 30)  # Default 30 seconds
    except Exception:
        return 30  # Fallback default

def _update_last_refresh():
    """Update the last refresh timestamp in master.json."""
    try:
        config = _load_master_config()
        if 'config' not in config:
            config['config'] = {}
        config['config']['last_refresh'] = datetime.now().isoformat()
        _save_master_config(config)
    except Exception as e:
        print(f"Failed to update last refresh timestamp: {e}")

@server_config_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for server configuration API
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Server configuration API health status
        examples:
          application/json:
            type: "success"
            code: "HEALTHY"
            message: "Server configuration API is running"
    """
    return jsonify({
        "type": "success",
        "code": "HEALTHY",
        "message": "Server configuration API is running"
    })

@server_config_bp.route('/reconnect', methods=['POST'])
def reconnect_servers():
    """
    Reconnect servers by reloading server manager config
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Servers reconnected successfully
        examples:
          application/json:
            status: "success"
            message: "Servers reconnected successfully."
      500:
        description: Failed to reconnect servers
        examples:
          application/json:
            status: "error"
            message: "Failed to reconnect servers: <error_details>"
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No server details provided."}), 400
        # Expect full server config in payload
        server_id = data.get('id') or data.get('server_id')
        if not server_id:
            return jsonify({"status": "error", "message": "Server ID is required."}), 400
        from core.server_manager import server_manager
        # Remove existing provider if present
        if server_id in server_manager.server_providers:
            del server_manager.server_providers[server_id]
        # Use the same logic as initial connection
        provider = server_manager._create_provider(data)
        if provider:
            server_manager.server_providers[server_id] = {
                "provider": provider,
                "config": data
            }
            return jsonify({
                "status": "success",
                "message": f"Server {server_id} reconnected successfully."
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to create provider for server {server_id}."
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to reconnect server: {str(e)}"
        }), 500

@server_config_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get server configuration
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Server configuration retrieved successfully
        examples:
          application/json:
            type: "success"
            code: "CONFIG_RETRIEVED"
            message: "Server configuration retrieved successfully"
            data:
              servers: []
              config:
                ui_refresh_interval: 5
                auto_refresh_enabled: true
      500:
        description: Failed to load configuration
        examples:
          application/json:
            type: "error"
            code: "CONFIG_LOAD_FAILED"
            message: "Failed to load configuration: <error_details>"
    """
    try:
        config = _load_master_config()
        return jsonify({
            "type": "success",
            "code": "CONFIG_RETRIEVED",
            "message": "Server configuration retrieved successfully",
            "data": config
        })
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "CONFIG_LOAD_FAILED",
            "message": f"Failed to load configuration: {str(e)}"
        }), 500

@server_config_bp.route('/config/refresh', methods=['GET'])
def get_refresh_config():
    """
    Get current refresh configuration
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Refresh configuration retrieved successfully
        examples:
          application/json:
            type: "success"
            code: "REFRESH_CONFIG_RETRIEVED"
            message: "Refresh configuration retrieved"
            data:
              ui_refresh_interval: 5
              auto_refresh_enabled: true
              server_refresh_intervals:
                kubernetes-4-246-178-26:
                  name: "Azure VM Kubernetes"
                  live_refresh_interval: 60
      500:
        description: Failed to get refresh configuration
        examples:
          application/json:
            type: "error"
            code: "REFRESH_CONFIG_FAILED"
            message: "Failed to get refresh configuration: <error_details>"
    """
    try:
        config = _load_master_config()
        refresh_config = config.get('config', {})
        
        # Get server-specific live refresh intervals
        servers = config.get('servers', [])
        server_refresh_intervals = {}
        for server in servers:
            server_id = server.get('id')
            if server_id:
                server_refresh_intervals[server_id] = {
                    'name': server.get('name'),
                    'live_refresh_interval': server.get('live_refresh_interval', 60)
                }
        
        return jsonify({
            "type": "success",
            "code": "REFRESH_CONFIG_RETRIEVED",
            "message": "Refresh configuration retrieved",
            "data": {
                "ui_refresh_interval": refresh_config.get('ui_refresh_interval', 5),
                "auto_refresh_enabled": refresh_config.get('auto_refresh_enabled', True),
                "last_refresh": refresh_config.get('last_refresh'),
                "last_live_refresh": refresh_config.get('last_live_refresh'),
                "server_refresh_intervals": server_refresh_intervals
            }
        })
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "REFRESH_CONFIG_FAILED",
            "message": f"Failed to get refresh configuration: {str(e)}"
        }), 500

@server_config_bp.route('/config/refresh', methods=['POST'])
def update_refresh_config():
    """
    Update refresh configuration
    ---
    tags:
      - Server Configuration
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            ui_refresh_interval:
              type: integer
              description: UI refresh interval in seconds
            auto_refresh_enabled:
              type: boolean
              description: Whether auto refresh is enabled
            server_refresh_intervals:
              type: object
              description: Per-server live refresh intervals
    responses:
      200:
        description: Refresh configuration updated successfully
        examples:
          application/json:
            type: "success"
            code: "REFRESH_CONFIG_UPDATED"
            message: "Refresh configuration updated successfully"
      400:
        description: Invalid data provided
        examples:
          application/json:
            type: "error"
            code: "INVALID_DATA"
            message: "No data provided"
      500:
        description: Failed to update refresh configuration
        examples:
          application/json:
            type: "error"
            code: "REFRESH_CONFIG_UPDATE_FAILED"
            message: "Failed to update refresh configuration: <error_details>"
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                "type": "error",
                "code": "INVALID_DATA",
                "message": "No data provided"
            }), 400
        
        config = _load_master_config()
        if 'config' not in config:
            config['config'] = {}
        
        # Update global UI refresh settings
        if 'ui_refresh_interval' in data:
            config['config']['ui_refresh_interval'] = data['ui_refresh_interval']
        if 'auto_refresh_enabled' in data:
            config['config']['auto_refresh_enabled'] = data['auto_refresh_enabled']
        
        # Update server-specific live refresh intervals
        if 'server_refresh_intervals' in data:
            for server_id, server_config in data['server_refresh_intervals'].items():
                for server in config.get('servers', []):
                    if server.get('id') == server_id:
                        if 'live_refresh_interval' in server_config:
                            server['live_refresh_interval'] = server_config['live_refresh_interval']
                        break
        
        _save_master_config(config)
        
        return jsonify({
            "type": "success",
            "code": "REFRESH_CONFIG_UPDATED",
            "message": "Refresh configuration updated successfully",
            "data": {
                "ui_refresh_interval": config['config'].get('ui_refresh_interval', 5),
                "auto_refresh_enabled": config['config'].get('auto_refresh_enabled', True)
            }
        })
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "REFRESH_CONFIG_UPDATE_FAILED",
            "message": f"Failed to update refresh configuration: {str(e)}"
        }), 500

@server_config_bp.route('/configure', methods=['POST'])
def configure_new_server():
    """
    Configure a new server with provided credentials
    ---
    tags:
      - Server Configuration
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - host
            - username
            - password
          properties:
            name:
              type: string
              description: Server display name
            host:
              type: string
              description: Server host/IP address
            username:
              type: string
              description: Username for authentication
            password:
              type: string
              description: Password for authentication
            type:
              type: string
              description: Server type (auto-set to 'kubernetes')
            environment:
              type: string
              description: Environment (auto-set to 'live')
    responses:
      200:
        description: Server configured successfully
        examples:
          application/json:
            type: "success"
            code: "SERVER_CONFIGURED"
            message: "Server configured successfully"
            data:
              server_id: "kubernetes-4-246-178-26"
              pods_count: 1
              status: "Online"
      400:
        description: Invalid configuration data
        examples:
          application/json:
            type: "error"
            code: "INVALID_CONFIG"
            message: "Invalid configuration data: <details>"
      500:
        description: Failed to configure server
        examples:
          application/json:
            type: "error"
            code: "CONFIG_FAILED"
            message: "Failed to configure server: <error_details>"
    """
    try:
        data: ServerConfigurationInput = request.json
        if not data:
            return jsonify({
                "type": "error",
                "code": "INVALID_DATA",
                "message": "No data provided"
            }), 400
        
        # Validate required fields (type and environment are auto-set)
        required_fields = ['name', 'host', 'username', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "type": "error",
                    "code": "MISSING_FIELD",
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Auto-set type to 'kubernetes' and environment to 'live' since we only handle Kubernetes
        data['type'] = 'kubernetes'
        data['environment'] = 'live'
        
        # Generate server ID from host
        server_id = f"{data['type']}-{data['host'].replace('.', '-')}"
        
        # Create server configuration using typed function
        server_config = create_default_server_config(
            server_id=server_id,
            name=data['name'],
            host=data['host'],
            username=data['username'],
            password=data['password']
        )
        
        # Update kubeconfig data
        server_config['connection_coordinates']['kubeconfig_data'] = _generate_kubeconfig_with_credentials(
            data['host'], 
            16443,  # Default port
            data['username'], 
            data['password']
        )
        
        # Load current config and add new server
        config = _load_master_config()
        config['servers'].append(server_config)
        _save_master_config(config)
        
        # Reload the server manager configuration
        from core.server_manager import server_manager
        server_manager.reload_config()
        
        # Fetch live data and update master.json
        live_data_result = _fetch_and_update_live_data(server_id)
        
        # Prepare response based on live data result
        if live_data_result["type"] == "success":
            return jsonify({
                "type": "success",
                "code": "SERVER_CONFIGURED",
                "message": f"Server '{data['name']}' has been configured successfully with live data",
                "data": {
                    "server_id": server_id,
                    "server_name": data['name'],
                    "total_servers": len(config['servers']),
                    "pods_count": live_data_result["data"]["pods_count"],
                    "status": live_data_result["data"]["status"]
                }
            })
        elif live_data_result["type"] == "warning":
            return jsonify({
                "type": "success",
                "code": "SERVER_CONFIGURED",
                "message": f"Server '{data['name']}' has been configured successfully (no live data available)",
                "data": {
                    "server_id": server_id,
                    "server_name": data['name'],
                    "total_servers": len(config['servers']),
                    "pods_count": 0,
                    "status": "configured"
                }
            })
        else:
            # Live data failed, but server was configured
            return jsonify({
                "type": "success",
                "code": "SERVER_CONFIGURED",
                "message": f"Server '{data['name']}' has been configured successfully (live data fetch failed)",
                "data": {
                    "server_id": server_id,
                    "server_name": data['name'],
                    "total_servers": len(config['servers']),
                    "pods_count": 0,
                    "status": "configured"
                }
            })
        
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "CONFIGURE_FAILED",
            "message": f"Failed to configure server: {str(e)}"
        }), 500

@server_config_bp.route('/servers', methods=['GET'])
def get_servers():
    """
    Get all configured servers with their complete data (pods, resources, etc.)
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: List of all configured servers with complete data
        examples:
          application/json:
            type: "success"
            code: "SERVERS_RETRIEVED"
            message: "Servers retrieved successfully"
            data:
              - id: "kubernetes-4-246-178-26"
                name: "Azure VM Kubernetes (4.246.178.26)"
                type: "kubernetes"
                environment: "live"
                status: "Online"
                pods:
                  - pod_id: "paas-ai-baseline-engine-784f6c5b76-25n7m"
                    namespace: "aidf-cli-setup"
                    status: "online"
                resources:
                  total:
                    cpus: 6
                    ram_gb: 110
                    storage_gb: 122
                    gpus: 0
                  available:
                    cpus: 6
                    ram_gb: 109
                    storage_gb: 121
                    gpus: 0
      500:
        description: Failed to retrieve servers
        examples:
          application/json:
            type: "error"
            code: "SERVERS_RETRIEVAL_FAILED"
            message: "Failed to retrieve servers: <error_details>"
    """
    try:
        config = _load_master_config()
        servers = config.get('servers', [])
        
        # Return complete server data (including pods and resources)
        server_list = []
        for server in servers:
            server_info = {
                "id": server.get('id'),
                "name": server.get('name'),
                "type": server.get('type'),
                "environment": server.get('environment'),
                "status": server.get('status', 'configured'),
                "pods": server.get('pods', []),
                "resources": server.get('resources', {}),
                "metadata": server.get('metadata', {}),
                "connection_coordinates": {
                    "method": server.get('connection_coordinates', {}).get('method'),
                    "host": server.get('connection_coordinates', {}).get('host'),
                    "port": server.get('connection_coordinates', {}).get('port')
                    # Exclude sensitive data like passwords
                }
            }
            server_list.append(server_info)
        
        return jsonify({
            "type": "success",
            "code": "SERVERS_RETRIEVED",
            "message": f"Found {len(server_list)} servers",
            "data": server_list
        })
        
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "SERVERS_RETRIEVAL_FAILED",
            "message": f"Failed to retrieve servers: {str(e)}"
        }), 500

@server_config_bp.route('/servers/<server_id>/kubeconfig', methods=['POST'])
def update_kubeconfig(server_id: str):
    """Update kubeconfig for a specific server with credentials."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "type": "error",
                "code": "INVALID_REQUEST",
                "message": "Request body is required"
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "type": "error",
                "code": "MISSING_CREDENTIALS",
                "message": "Both username and password are required"
            }), 400
        
        # Update the kubeconfig
        result = _update_server_kubeconfig(server_id, username, password)
        
        if result["type"] == "success":
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "UPDATE_FAILED",
            "message": f"Failed to update kubeconfig: {str(e)}"
        }), 500

@server_config_bp.route('/servers/<server_id>/test-connection', methods=['POST'])
def test_connection(server_id: str):
    """Test connection to a server."""
    try:
        config = _load_master_config()
        
        # Find the server
        server = None
        for s in config.get('servers', []):
            if s.get('id') == server_id:
                server = s
                break
        
        if not server:
            return jsonify({
                "type": "error",
                "code": "SERVER_NOT_FOUND",
                "message": f"Server with ID '{server_id}' not found"
            }), 404
        
        # Test the connection by trying to get nodes
        try:
            from providers.cloud_kubernetes_provider import CloudKubernetesProvider
            provider = CloudKubernetesProvider(server)
            
            # Ensure the provider is initialized
            provider._ensure_initialized()
            
            if not provider.core_v1:
                return jsonify({
                    "type": "error",
                    "code": "PROVIDER_NOT_INITIALIZED",
                    "message": f"Kubernetes provider not initialized for server '{server_id}'"
                }), 500
            
            nodes = provider.core_v1.list_node()
            
            return jsonify({
                "type": "success",
                "code": "CONNECTION_SUCCESS",
                "message": f"Successfully connected to server '{server_id}'",
                "data": {
                    "node_count": len(nodes.items) if nodes.items else 0
                }
            })
        except Exception as e:
            return jsonify({
                "type": "error",
                "code": "CONNECTION_FAILED",
                "message": f"Failed to connect to server '{server_id}': {str(e)}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "TEST_FAILED",
            "message": f"Failed to test connection: {str(e)}"
        }), 500

@server_config_bp.route('/deconfigure/<server_id>', methods=['DELETE', 'OPTIONS'])
def deconfigure_server(server_id: str):
    """
    De-configure (remove) a server from the system
    ---
    tags:
      - Server Configuration
    parameters:
      - in: path
        name: server_id
        required: true
        type: string
        description: ID of the server to deconfigure
    responses:
      200:
        description: Server deconfigured successfully
        examples:
          application/json:
            type: "success"
            code: "SERVER_DECONFIGURED"
            message: "Server deconfigured successfully"
            data:
              server_id: "kubernetes-4-246-178-26"
              remaining_servers: 0
      404:
        description: Server not found
        examples:
          application/json:
            type: "error"
            code: "SERVER_NOT_FOUND"
            message: "Server not found: <server_id>"
      500:
        description: Failed to deconfigure server
        examples:
          application/json:
            type: "error"
            code: "DECONFIG_FAILED"
            message: "Failed to deconfigure server: <error_details>"
    """
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        config = _load_master_config()
        
        # Find the server
        server_found = False
        for i, server in enumerate(config.get('servers', [])):
            if server.get('id') == server_id:
                server_found = True
                server_name = server.get('name', server_id)
                
                # Remove the server
                config['servers'].pop(i)
                
                # Save updated config
                _save_master_config(config)
                
                # Reload the server manager configuration to reflect changes
                from core.server_manager import server_manager
                server_manager.reload_config()
                
                return jsonify({
                    "type": "success",
                    "code": "SERVER_DECONFIGURED",
                    "message": f"Server '{server_name}' has been de-configured successfully",
                    "data": {
                        "removed_server": server_id,
                        "remaining_servers": len(config.get('servers', [])),
                        "removed_files": []  # Could be extended to remove kubeconfig files
                    }
                })
        
        if not server_found:
            return jsonify({
                "type": "error",
                "code": "SERVER_NOT_FOUND",
                "message": f"Server with ID '{server_id}' not found"
            }), 404
            
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "DECONFIGURE_FAILED",
            "message": f"Failed to de-configure server: {str(e)}"
        }), 500

@server_config_bp.route('/servers/<server_id>/refresh', methods=['POST'])
def refresh_server_data(server_id: str):
    """Refresh live data for a specific server."""
    try:
        result = _fetch_and_update_live_data(server_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "REFRESH_FAILED",
            "message": f"Failed to refresh server data: {str(e)}"
        }), 500

@server_config_bp.route('/servers/refresh-all', methods=['POST'])
def refresh_all_servers():
    """Refresh live data for all configured servers."""
    try:
        config = _load_master_config()
        servers = config.get('servers', [])
        
        results = []
        for server in servers:
            server_id = server.get('id')
            if server_id:
                result = _fetch_and_update_live_data(server_id)
                results.append({
                    "server_id": server_id,
                    "server_name": server.get('name'),
                    "result": result
                })
        
        successful = sum(1 for r in results if r["result"]["type"] == "success")
        total = len(results)
        
        return jsonify({
            "type": "success",
            "code": "REFRESH_ALL_COMPLETED",
            "message": f"Refreshed {successful}/{total} servers",
            "data": {
                "total_servers": total,
                "successful_refreshes": successful,
                "results": results
            }
        })
        
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "REFRESH_ALL_FAILED",
            "message": f"Failed to refresh all servers: {str(e)}"
        }), 500

@server_config_bp.route('/background-refresh/status', methods=['GET'])
def get_background_refresh_status():
    """
    Get background refresh service status
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Background refresh service status
        examples:
          application/json:
            type: "success"
            code: "BACKGROUND_STATUS_RETRIEVED"
            message: "Background refresh status retrieved"
            data:
              is_running: true
              refresh_interval: 60
              last_refresh: "2025-07-24T19:11:51.203489"
              total_servers: 1
      500:
        description: Failed to get background refresh status
        examples:
          application/json:
            type: "error"
            code: "BACKGROUND_STATUS_FAILED"
            message: "Failed to get background refresh status: <error_details>"
    """
    try:
        from core.background_refresh_service import background_refresh_service
        
        config = _load_master_config()
        refresh_config = config.get('config', {})
        
        return jsonify({
            "type": "success",
            "code": "BACKGROUND_REFRESH_STATUS",
            "message": "Background refresh service status retrieved",
            "data": {
                "running": background_refresh_service.running,
                "refresh_interval": refresh_config.get('live_refresh_interval', 60),
                "auto_refresh_enabled": refresh_config.get('auto_refresh_enabled', True),
                "last_live_refresh": refresh_config.get('last_live_refresh')
            }
        })
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "BACKGROUND_REFRESH_STATUS_FAILED",
            "message": f"Failed to get background refresh status: {str(e)}"
        }), 500

@server_config_bp.route('/background-refresh/start', methods=['POST'])
def start_background_refresh():
    """
    Start the background refresh service
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Background refresh service started successfully
        examples:
          application/json:
            type: "success"
            code: "BACKGROUND_REFRESH_STARTED"
            message: "Background refresh service started successfully"
            data:
              is_running: true
              refresh_interval: 60
      500:
        description: Failed to start background refresh service
        examples:
          application/json:
            type: "error"
            code: "BACKGROUND_REFRESH_START_FAILED"
            message: "Failed to start background refresh service: <error_details>"
    """
    try:
        from core.background_refresh_service import background_refresh_service
        
        background_refresh_service.start()
        
        return jsonify({
            "type": "success",
            "code": "BACKGROUND_REFRESH_STARTED",
            "message": "Background refresh service started successfully"
        })
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "BACKGROUND_REFRESH_START_FAILED",
            "message": f"Failed to start background refresh service: {str(e)}"
        }), 500

@server_config_bp.route('/background-refresh/stop', methods=['POST'])
def stop_background_refresh():
    """
    Stop the background refresh service
    ---
    tags:
      - Server Configuration
    responses:
      200:
        description: Background refresh service stopped successfully
        examples:
          application/json:
            type: "success"
            code: "BACKGROUND_REFRESH_STOPPED"
            message: "Background refresh service stopped successfully"
            data:
              is_running: false
      500:
        description: Failed to stop background refresh service
        examples:
          application/json:
            type: "error"
            code: "BACKGROUND_REFRESH_STOP_FAILED"
            message: "Failed to stop background refresh service: <error_details>"
    """
    try:
        from core.background_refresh_service import background_refresh_service
        
        background_refresh_service.stop()
        
        return jsonify({
            "type": "success",
            "code": "BACKGROUND_REFRESH_STOPPED",
            "message": "Background refresh service stopped successfully"
        })
    except Exception as e:
        return jsonify({
            "type": "error",
            "code": "BACKGROUND_REFRESH_STOP_FAILED",
            "message": f"Failed to stop background refresh service: {str(e)}"
        }), 500
