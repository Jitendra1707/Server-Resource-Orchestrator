# Type Definitions for Resource Manager

This document explains the type definitions used in the Resource Manager application for better type safety and maintainability.

## Overview

Instead of hardcoding object structures, we now use Python's `TypedDict` to define the structure of our data. This provides:

- **Type Safety**: IDE support and runtime type checking
- **Documentation**: Self-documenting code structure
- **Maintainability**: Easy to update and extend
- **Validation**: Built-in validation functions

## Core Types

### MasterConfig
The complete structure of `master.json`:

```python
class MasterConfig(TypedDict):
    servers: List[ServerConfig]
    config: GlobalConfig
```

### ServerConfig
Individual server configuration:

```python
class ServerConfig(TypedDict):
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
```

### Input Types

#### ServerConfigurationInput
For API requests to configure a server:

```python
class ServerConfigurationInput(TypedDict):
    name: str
    host: str
    username: str
    password: str
    type: Optional[str]  # Auto-set to 'kubernetes'
    environment: Optional[str]  # Auto-set to 'live'
```

#### PodCreationInput
For API requests to create a pod:

```python
class PodCreationInput(TypedDict):
    PodName: str
    image_url: str
    Resources: ResourceInfo
    Owner: str
    container_port: Optional[int]
    service_port: Optional[int]
    expose_service: Optional[bool]
```

## Usage Examples

### Creating a Default Configuration

```python
from config.types import create_default_master_config, create_default_server_config

# Create empty master config
master_config = create_default_master_config()

# Create server config
server_config = create_default_server_config(
    server_id="my-server",
    name="My Kubernetes Server",
    host="192.168.1.100",
    username="admin",
    password="password123"
)
```

### Validation

```python
from config.types import validate_master_config, validate_server_config

# Validate loaded data
try:
    validated_config = validate_master_config(loaded_data)
except ValueError as e:
    print(f"Invalid config: {e}")
```

### API Usage

```python
from config.types import ServerConfigurationInput

# In your API endpoint
def configure_server():
    data: ServerConfigurationInput = request.json
    
    # Type checking ensures required fields exist
    server_id = f"kubernetes-{data['host'].replace('.', '-')}"
    
    # Create typed server config
    server_config = create_default_server_config(
        server_id=server_id,
        name=data['name'],
        host=data['host'],
        username=data['username'],
        password=data['password']
    )
```

## Benefits

1. **IDE Support**: Autocomplete and type hints
2. **Runtime Safety**: Validation prevents invalid data
3. **Documentation**: Types serve as living documentation
4. **Refactoring**: Easy to update structures across the codebase
5. **Testing**: Type-safe test data creation

## Migration from Hardcoded Objects

### Before (Hardcoded)
```python
server_config = {
    "id": server_id,
    "name": data['name'],
    "type": "kubernetes",
    # ... many more fields
}
```

### After (Typed)
```python
server_config = create_default_server_config(
    server_id=server_id,
    name=data['name'],
    host=data['host'],
    username=data['username'],
    password=data['password']
)
```

## Testing

Run the type tests to verify everything works:

```bash
cd backend
PYTHONPATH=. python tests/test_types.py
```

## Future Enhancements

- Add more comprehensive validation rules
- Create Pydantic models for even better validation
- Add schema generation for API documentation
- Implement automatic migration from old formats 