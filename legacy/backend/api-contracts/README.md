# Backend API Contracts

This directory contains the API contracts that define the **backend's responsibility** for implementing the REST API endpoints.

## 🎯 Backend Implementation Contracts

These contracts define what the **backend must implement**:

### **Server Configuration API** (`server-config-api.json`)
**Backend must implement:**
- `GET /api/server-config/servers` - Return list of configured servers
- `POST /api/server-config/configure` - Accept server configuration requests
- `GET /api/server-config/servers/{id}/test` - Test server connections
- `GET /api/server-config/templates` - Return available templates

### **Kubernetes Resource Management API** (`kubernetes-api.json`)
**Backend must implement:**
- `GET /api/k8s/pods` - Return list of all pods across servers
- `POST /api/k8s/pods` - Accept pod creation requests
- `PUT /api/k8s/pods/{id}` - Accept pod update requests
- `DELETE /api/k8s/pods/{id}` - Handle pod deletion
- `GET /api/k8s/pods/{id}` - Return specific pod details

## 🔧 Backend Implementation Guidelines

### **Request Validation**
```python
def validate_create_pod_request(data):
    """Validate incoming pod creation request"""
    required_fields = ['server_id', 'name', 'resources']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate resource requirements
    resources = data.get('resources', {})
    if resources.get('gpus', 0) < 0:
        raise ValueError("GPU count cannot be negative")
```

### **Response Formatting**
```python
def format_pod_response(pod_data):
    """Format pod data according to contract"""
    return {
        "success": True,
        "pod": {
            "id": pod_data['id'],
            "name": pod_data['name'],
            "server_id": pod_data['server_id'],
            "status": pod_data['status'],
            "resources": pod_data['resources'],
            "created_at": pod_data['created_at']
        }
    }
```

### **Error Handling**
```python
def handle_api_error(error, status_code=500):
    """Return standardized error response"""
    return {
        "success": False,
        "error": str(error),
        "status_code": status_code
    }, status_code
```

## 🧪 Backend Testing with Contracts

### **Contract Compliance Testing**
```python
def test_create_pod_contract_compliance():
    """Test that create pod endpoint follows contract"""
    test_data = {
        "server_id": "server-1",
        "name": "test-pod",
        "resources": {
            "gpus": 1,
            "ram_gb": 8,
            "storage_gb": 100
        }
    }
    
    response = client.post('/api/k8s/pods', json=test_data)
    
    # Verify response follows contract
    assert response.status_code == 200
    data = response.json()
    assert 'success' in data
    assert 'pod_id' in data
    assert 'message' in data
```

### **Schema Validation**
```python
import json

def validate_response_schema(response_data, endpoint_name):
    """Validate response against contract schema"""
    with open('api-contracts/kubernetes-api.json') as f:
        contract = json.load(f)
    
    schema = contract['endpoints'][endpoint_name]['response']
    # Validate response_data against schema
    return validate_schema(response_data, schema)
```

## 📋 Backend Responsibilities

### **Server Management**
- ✅ Implement server configuration endpoints
- ✅ Handle Azure VM connections
- ✅ Manage kubeconfig retrieval
- ✅ Validate server credentials
- ✅ Test server connectivity

### **Pod Management**
- ✅ Implement pod CRUD operations
- ✅ Validate resource requirements
- ✅ Handle multi-cluster deployments
- ✅ Manage pod lifecycle
- ✅ Track resource usage

### **Data Persistence**
- ✅ Store server configurations in `data/master.json`
- ✅ Maintain pod state across servers
- ✅ Handle configuration templates
- ✅ Backup and restore data

### **Error Handling**
- ✅ Return standardized error responses
- ✅ Log errors for debugging
- ✅ Provide meaningful error messages
- ✅ Handle network timeouts
- ✅ Validate input data

## 🔍 Contract Validation

### **Automated Testing**
```bash
# Run contract compliance tests
python -m pytest tests/test_contract_compliance.py

# Validate JSON schemas
python scripts/validate_contracts.py
```

### **Manual Testing**
```bash
# Test server configuration API
curl -X GET http://localhost:5005/api/server-config/servers

# Test pod creation API
curl -X POST http://localhost:5005/api/k8s/pods \
  -H "Content-Type: application/json" \
  -d '{"server_id":"server-1","name":"test-pod","resources":{"gpus":1,"ram_gb":8,"storage_gb":100}}'
```

## 📝 Contract Maintenance

### **When Updating Contracts**
1. Update the contract file
2. Update backend implementation
3. Update tests
4. Update documentation
5. Test contract compliance

### **Version Management**
- Keep contract versions in sync with implementation
- Document breaking changes
- Provide migration guides
- Maintain backward compatibility when possible

## 🚀 Deployment Considerations

### **Production Validation**
- Validate all responses against contracts
- Log contract violations
- Monitor API compliance
- Alert on contract mismatches

### **Performance**
- Optimize response generation
- Cache frequently accessed data
- Minimize response payload size
- Use efficient data serialization

This ensures the backend implements exactly what the contracts specify, making it a reliable API provider for the frontend. 