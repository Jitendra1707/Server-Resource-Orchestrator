# Server Configuration API Documentation

This document describes the REST API endpoints for configuring Azure VM servers automatically.

## Overview

The Server Configuration API provides endpoints to:
- Configure new Azure VM servers using username/password authentication
- List configured servers
- Test server connections
- Health check for the API

## Base URL

All endpoints are prefixed with `/api/server-config`

## Authentication

Currently, the API doesn't require authentication. In production, consider adding API key or JWT authentication.

## Endpoints

### 1. Configure Server

**Endpoint:** `POST /api/server-config/configure`

**Description:** Configure a new Azure VM server by fetching kubeconfig and updating configuration files.

**Request Body:**
```json
{
  "vm_ip": "4.246.178.26",
  "username": "azureuser",
  "password": "your_password",
  "name": "My Azure VM Cluster",
  "environment": "live",
  "port": 16443,
  "location": "Azure East US",
  "description": "Production Kubernetes cluster",
  "configured_by": "admin"
}
```

**Required Fields:**
- `vm_ip`: Azure VM IP address
- `password`: VM password

**Optional Fields:**
- `username`: VM username (default: azureuser)
- `name`: Server name (default: "Azure VM Kubernetes ({vm_ip})")
- `environment`: Environment (default: live)
- `port`: Kubernetes port (default: 16443)
- `location`: Server location (default: "Azure VM")
- `description`: Server description
- `configured_by`: Who configured this server

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Server configured successfully",
  "data": {
    "server_id": "azure-vm-4-246-178-26",
    "vm_ip": "4.246.178.26",
    "username": "azureuser",
    "kubeconfig_path": "azure_vm_kubeconfig_updated",
    "connection_test": {
      "success": true,
      "message": "Connection test successful",
      "nodes": "NAME     STATUS   ROLES                  AGE   VERSION\nvm-node  Ready    control-plane,master   2d    v1.24.0+k3s1"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "code": 200
}
```

**Error Response (400):**
```json
{
  "status": "error",
  "message": "VM IP address is required",
  "code": 400
}
```

**Error Response (500):**
```json
{
  "status": "error",
  "message": "Server configuration failed: SSH connection failed",
  "code": 500
}
```

### 2. Get Configured Servers

**Endpoint:** `GET /api/server-config/servers`

**Description:** Get list of all configured servers with their status.

**Request:** No request body required.

**Success Response (200):**
```json
{
  "status": "success",
  "data": {
    "servers": [
      {
        "id": "azure-vm-4-246-178-26",
        "name": "Azure VM Kubernetes (4.246.178.26)",
        "type": "kubernetes",
        "environment": "live",
        "connection_coordinates": {
          "method": "kubeconfig",
          "host": "4.246.178.26",
          "port": 16443,
          "username": "azureuser",
          "kubeconfig_path": "azure_vm_kubeconfig_updated",
          "insecure_skip_tls_verify": true
        },
        "metadata": {
          "location": "Azure VM",
          "environment": "production",
          "description": "Azure VM Kubernetes cluster at 4.246.178.26",
          "setup_method": "api_automated",
          "setup_timestamp": "2024-01-15T10:30:00Z",
          "configured_by": "api"
        },
        "kubeconfig_exists": true
      }
    ],
    "total_count": 1,
    "default_server": "azure-vm-4-246-178-26"
  },
  "code": 200
}
```

### 3. Test Server Connection

**Endpoint:** `POST /api/server-config/test/{server_id}`

**Description:** Test connection to a specific configured server.

**Path Parameters:**
- `server_id`: ID of the server to test

**Request:** No request body required.

**Success Response (200):**
```json
{
  "status": "success",
  "data": {
    "server_id": "azure-vm-4-246-178-26",
    "server_name": "Azure VM Kubernetes (4.246.178.26)",
    "connection_test": {
      "success": true,
      "message": "Connection test successful",
      "nodes": "NAME     STATUS   ROLES                  AGE   VERSION\nvm-node  Ready    control-plane,master   2d    v1.24.0+k3s1"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "code": 200
}
```

**Error Response (404):**
```json
{
  "status": "error",
  "message": "Server azure-vm-4-246-178-26 not found",
  "code": 404
}
```

### 4. Health Check

**Endpoint:** `GET /api/server-config/health`

**Description:** Health check for the server configuration API.

**Request:** No request body required.

**Success Response (200):**
```json
{
  "status": "success",
  "message": "Server Configuration API is healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "code": 200
}
```

## Usage Examples

### Using curl

#### Configure a new server:
```bash
curl -X POST http://localhost:5005/api/server-config/configure \
  -H "Content-Type: application/json" \
  -d '{
    "vm_ip": "4.246.178.26",
    "username": "azureuser",
    "password": "your_password",
    "name": "Production Cluster",
    "environment": "live"
  }'
```

#### Get configured servers:
```bash
curl -X GET http://localhost:5005/api/server-config/servers
```

#### Test server connection:
```bash
curl -X POST http://localhost:5005/api/server-config/test/azure-vm-4-246-178-26
```

#### Health check:
```bash
curl -X GET http://localhost:5005/api/server-config/health
```

### Using Python requests

```python
import requests
import json

# Configure a new server
def configure_server(vm_ip, username, password, name=None):
    url = "http://localhost:5005/api/server-config/configure"
    data = {
        "vm_ip": vm_ip,
        "username": username,
        "password": password
    }
    if name:
        data["name"] = name
    
    response = requests.post(url, json=data)
    return response.json()

# Get configured servers
def get_servers():
    url = "http://localhost:5005/api/server-config/servers"
    response = requests.get(url)
    return response.json()

# Test server connection
def test_server(server_id):
    url = f"http://localhost:5005/api/server-config/test/{server_id}"
    response = requests.post(url)
    return response.json()

# Example usage
if __name__ == "__main__":
    # Configure a server
    result = configure_server(
        vm_ip="4.246.178.26",
        username="azureuser",
        password="your_password",
        name="My Production Cluster"
    )
    print("Configuration result:", json.dumps(result, indent=2))
    
    # Get all servers
    servers = get_servers()
    print("Configured servers:", json.dumps(servers, indent=2))
    
    # Test connection
    if result.get('status') == 'success':
        server_id = result['data']['server_id']
        test_result = test_server(server_id)
        print("Connection test:", json.dumps(test_result, indent=2))
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

// Configure a new server
async function configureServer(vmIp, username, password, name = null) {
    try {
        const data = {
            vm_ip: vmIp,
            username: username,
            password: password
        };
        if (name) data.name = name;
        
        const response = await axios.post('http://localhost:5005/api/server-config/configure', data);
        return response.data;
    } catch (error) {
        console.error('Configuration failed:', error.response?.data || error.message);
        throw error;
    }
}

// Get configured servers
async function getServers() {
    try {
        const response = await axios.get('http://localhost:5005/api/server-config/servers');
        return response.data;
    } catch (error) {
        console.error('Failed to get servers:', error.response?.data || error.message);
        throw error;
    }
}

// Test server connection
async function testServer(serverId) {
    try {
        const response = await axios.post(`http://localhost:5005/api/server-config/test/${serverId}`);
        return response.data;
    } catch (error) {
        console.error('Connection test failed:', error.response?.data || error.message);
        throw error;
    }
}

// Example usage
async function main() {
    try {
        // Configure a server
        const result = await configureServer(
            '4.246.178.26',
            'azureuser',
            'your_password',
            'My Production Cluster'
        );
        console.log('Configuration result:', JSON.stringify(result, null, 2));
        
        // Get all servers
        const servers = await getServers();
        console.log('Configured servers:', JSON.stringify(servers, null, 2));
        
        // Test connection
        if (result.status === 'success') {
            const serverId = result.data.server_id;
            const testResult = await testServer(serverId);
            console.log('Connection test:', JSON.stringify(testResult, null, 2));
        }
    } catch (error) {
        console.error('Error:', error.message);
    }
}

main();
```

## Error Handling

### Common Error Codes

- **400 Bad Request**: Missing required fields or invalid data
- **404 Not Found**: Server not found
- **500 Internal Server Error**: Server configuration failed

### Error Response Format

All error responses follow this format:
```json
{
  "status": "error",
  "message": "Error description",
  "code": 400
}
```

## Prerequisites

### System Requirements
- Python 3.6 or higher
- kubectl installed
- sshpass installed (for password authentication)
- Network access to Azure VM

### VM Requirements
- SSH access enabled
- Password authentication enabled
- Kubernetes cluster running
- kubeconfig file accessible via SSH

## Security Considerations

### Password Security
- Passwords are sent in plain text over HTTPS
- Consider using SSH keys for production environments
- Passwords are not stored in files (only in environment variables if needed)

### Network Security
- Ensure Azure VM has proper firewall rules
- Use VPN or private networks when possible
- Consider using Azure Bastion for secure access

### File Permissions
- Kubeconfig files are set to 600 (user read/write only)
- Sanitized files are set to 644 (user read/write, others read)

## Integration with Frontend

This API is designed to be easily integrated with frontend applications. The endpoints return structured JSON responses that can be consumed by:

- React applications
- Angular applications
- Vue.js applications
- Any other JavaScript framework

### Frontend Integration Example

```javascript
// React component example
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ServerConfiguration() {
    const [servers, setServers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const configureServer = async (serverData) => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await axios.post('/api/server-config/configure', serverData);
            if (response.data.status === 'success') {
                // Refresh servers list
                fetchServers();
                return response.data;
            } else {
                setError(response.data.message);
            }
        } catch (err) {
            setError(err.response?.data?.message || 'Configuration failed');
        } finally {
            setLoading(false);
        }
    };

    const fetchServers = async () => {
        try {
            const response = await axios.get('/api/server-config/servers');
            setServers(response.data.data.servers);
        } catch (err) {
            setError('Failed to fetch servers');
        }
    };

    useEffect(() => {
        fetchServers();
    }, []);

    return (
        <div>
            {/* Server configuration form */}
            {/* Servers list */}
            {/* Error handling */}
        </div>
    );
}
```

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify VM IP address is correct
   - Check if VM is running and accessible
   - Ensure password authentication is enabled on VM

2. **sshpass Not Available**
   - Install sshpass: `brew install sshpass` (macOS) or `sudo apt-get install sshpass` (Ubuntu)

3. **Kubeconfig Not Found**
   - Verify Kubernetes is running on the VM
   - Check if kubeconfig exists in standard locations

4. **Connection Test Failed**
   - Check if the VM IP and port are correct
   - Verify the kubeconfig was processed correctly

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export DEBUG=true
```

### Manual Verification

```bash
# Test SSH connection manually
sshpass -p 'your_password' ssh -o StrictHostKeyChecking=no azureuser@4.246.178.26

# Check kubeconfig on VM
sshpass -p 'your_password' ssh azureuser@4.246.178.26 "cat ~/.kube/config"

# Test kubectl on VM
sshpass -p 'your_password' ssh azureuser@4.246.178.26 "kubectl get nodes"
```

This API provides a robust, secure, and user-friendly way to configure Azure VM Kubernetes connections programmatically, making it easy to integrate with frontend applications and automation workflows. 