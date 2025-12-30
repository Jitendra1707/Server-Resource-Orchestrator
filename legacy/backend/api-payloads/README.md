# Resource Manager API - Postman Payloads

This directory contains comprehensive API payloads for testing the Resource Manager backend. The API manages GPU/CPU servers and their associated pods with resource allocation and validation.

## API Overview

The Resource Manager API provides endpoints for:
- **Server Management**: View all servers and their resource status
- **Pod Operations**: Create, delete, and update pods with resource allocation
- **Data Validation**: Ensure data consistency across the system
- **Kubernetes Integration**: Deploy and manage pods on Kubernetes clusters

## Base Configuration

**Base URL:** `http://localhost:5000`  
**Content-Type:** `application/json` (for POST requests)

## Data Structure

### Server Object
```json
{
  "id": "server-01",
  "name": "gpu-node-h100-a",
  "resources": {
    "total": { "gpus": 8, "ram_gb": 512, "storage_gb": 2048 },
    "available": { "gpus": 2, "ram_gb": 128, "storage_gb": 548 }
  },
  "pods": [...]
}
```

### Pod Object
```json
{
  "pod_id": "pod-101",
  "owner": "team-a",
  "status": "running",
  "timestamp": "2025-06-22T10:00:00Z",
  "requested": { "gpus": 2, "ram_gb": 128, "storage_gb": 500 },
  "image_url": "https://docker.io/library/nginx:latest",
  "registery_url": "docker.io",
  "image_name": "library/nginx",
  "image_tag": "latest"
}
```

## Validation Rules

### Pod Creation Validation
1. **Required Fields**: All fields must be present and non-empty
2. **Pod Name**: Must be lowercase, no underscores, alphanumeric
3. **Image URL**: Must start with `https://` and contain a version tag (`:latest`, `:1.0`, etc.)
4. **Resources**: Must be a valid object with numeric values
5. **Server Existence**: Server must exist in the system
6. **Resource Availability**: Requested resources must not exceed available resources

### Error Handling
- **Multiple Validation**: All validation errors are collected and returned together
- **Comprehensive Feedback**: Error messages indicate specific field issues
- **Type Safety**: Proper type checking for all inputs

## Available Endpoints

1. **GET /** - API documentation
2. **GET /servers** - List all servers and pods
3. **POST /create** - Create a new pod
4. **POST /delete** - Delete an existing pod
5. **POST /update** - Update pod properties
6. **GET /consistency-check** - Validate data consistency

## Testing Strategy

### 1. Happy Path Testing
- Test valid payloads to ensure successful operations
- Verify resource allocation and deallocation
- Check Kubernetes integration

### 2. Validation Testing
- Test each validation rule individually
- Test multiple validation failures simultaneously
- Verify error message clarity and completeness

### 3. Edge Case Testing
- Test with maximum resource values
- Test with minimum resource values
- Test with special characters in names

### 4. Integration Testing
- Test resource consistency across operations
- Verify data persistence
- Test concurrent operations

## File Structure

```
apipayloads/
├── README.md                    # This file
├── 01-get-endpoints/           # GET request payloads
│   ├── root-endpoint.json
│   ├── get-servers.json
│   └── consistency-check.json
├── 02-create-pod/              # POST /create payloads
│   ├── valid-examples/
│   ├── validation-errors/
│   └── edge-cases/
├── 03-delete-pod/              # POST /delete payloads
├── 04-update-pod/              # POST /update payloads
└── postman-collection.json     # Complete Postman collection
```

## Usage Instructions

1. **Import Collection**: Import `postman-collection.json` into Postman
2. **Set Environment**: Create environment with `base_url` variable
3. **Run Tests**: Execute requests in logical order
4. **Verify Results**: Check responses against expected outcomes

## Common Issues and Solutions

### Connection Issues
- Ensure Flask backend is running on port 5000
- Check firewall settings
- Verify network connectivity

### Validation Errors
- Review validation rules in this README
- Check payload format and data types
- Ensure all required fields are present

### Resource Allocation Issues
- Verify server has sufficient available resources
- Check resource units (GB vs MB, etc.)
- Review existing pod allocations

## Development Notes

- **Backend**: Flask application with CORS enabled
- **Data Storage**: JSON file (`mock_db.json`) for persistence
- **Kubernetes**: Integration via SSH and kubectl
- **Validation**: Comprehensive client-side and server-side validation
- **Error Handling**: Graceful error handling with detailed messages

## Contributing

When adding new payloads:
1. Follow the existing naming convention
2. Include comprehensive comments
3. Test the payload before committing
4. Update this README if adding new endpoints 

## /mode Endpoint

- Accepts: 'demo', 'local-k8s', 'cloud-k8s'
- Example: `{ "mode": "local-k8s" }` 