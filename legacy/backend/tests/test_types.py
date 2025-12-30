"""
Test file for type definitions.
"""

import json
import tempfile
import os
from config.types import (
    MasterConfig, ServerConfig, ServerConfigurationInput,
    create_default_server_config, create_default_master_config,
    validate_master_config, validate_server_config
)


def test_create_default_master_config():
    """Test creating a default master config."""
    config = create_default_master_config()
    
    # Verify structure
    assert 'servers' in config
    assert 'config' in config
    assert isinstance(config['servers'], list)
    assert isinstance(config['config'], dict)
    
    # Verify config defaults
    assert config['config']['ui_refresh_interval'] == 5
    assert config['config']['auto_refresh_enabled'] is True
    
    print("✅ Default master config creation works")


def test_create_default_server_config():
    """Test creating a default server config."""
    server_config = create_default_server_config(
        server_id="test-server",
        name="Test Server",
        host="192.168.1.1",
        username="testuser",
        password="testpass"
    )
    
    # Verify structure
    assert server_config['id'] == "test-server"
    assert server_config['name'] == "Test Server"
    assert server_config['type'] == "kubernetes"
    assert server_config['environment'] == "live"
    assert server_config['live_refresh_interval'] == 60
    
    # Verify connection coordinates
    coords = server_config['connection_coordinates']
    assert coords['method'] == "kubeconfig"
    assert coords['host'] == "192.168.1.1"
    assert coords['port'] == 16443
    assert coords['username'] == "testuser"
    assert coords['password'] == "testpass"
    
    # Verify metadata
    metadata = server_config['metadata']
    assert metadata['setup_method'] == "api_automated"
    assert metadata['configured_by'] == "api"
    
    print("✅ Default server config creation works")


def test_validate_master_config():
    """Test master config validation."""
    # Valid config
    valid_config = {
        "servers": [],
        "config": {
            "ui_refresh_interval": 5,
            "auto_refresh_enabled": True,
            "last_refresh": None,
            "last_live_refresh": None
        }
    }
    
    validated = validate_master_config(valid_config)
    assert validated == valid_config
    
    # Invalid config - missing servers
    invalid_config = {
        "config": {"ui_refresh_interval": 5}
    }
    
    try:
        validate_master_config(invalid_config)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Missing 'servers' field" in str(e)
    
    print("✅ Master config validation works")


def test_validate_server_config():
    """Test server config validation."""
    # Valid server config
    valid_server = {
        "id": "test-server",
        "name": "Test Server",
        "type": "kubernetes",
        "environment": "live",
        "connection_coordinates": {
            "method": "kubeconfig",
            "host": "192.168.1.1",
            "port": 16443,
            "username": "testuser",
            "kubeconfig_path": "test_kubeconfig",
            "kubeconfig_data": {},
            "insecure_skip_tls_verify": True,
            "password": "testpass"
        },
        "resources": {
            "total": {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0},
            "allocated": {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0},
            "available": {"cpus": 0, "ram_gb": 0, "storage_gb": 0, "gpus": 0}
        },
        "metadata": {
            "location": "Test Location",
            "environment": "live",
            "description": "Test server",
            "setup_method": "api_automated",
            "setup_timestamp": "2025-01-01T00:00:00",
            "configured_by": "api",
            "last_updated": None,
            "live_data_fresh": False
        },
        "pods": [],
        "status": "configured"
    }
    
    validated = validate_server_config(valid_server)
    assert validated == valid_server
    
    # Invalid server config - missing required field
    invalid_server = {
        "name": "Test Server",
        "type": "kubernetes"
        # Missing 'id' and other required fields
    }
    
    try:
        validate_server_config(invalid_server)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Missing required field" in str(e)
    
    print("✅ Server config validation works")


def test_json_serialization():
    """Test that our types can be serialized to JSON."""
    config = create_default_master_config()
    server_config = create_default_server_config(
        "test-server", "Test Server", "192.168.1.1", "testuser", "testpass"
    )
    
    # Add server to config
    config['servers'].append(server_config)
    
    # Serialize to JSON
    json_str = json.dumps(config, indent=2)
    
    # Deserialize back
    loaded_config = json.loads(json_str)
    
    # Validate the loaded config
    validated_config = validate_master_config(loaded_config)
    assert len(validated_config['servers']) == 1
    assert validated_config['servers'][0]['id'] == "test-server"
    
    print("✅ JSON serialization/deserialization works")


def test_file_operations():
    """Test file operations with typed configs."""
    config = create_default_master_config()
    server_config = create_default_server_config(
        "test-server", "Test Server", "192.168.1.1", "testuser", "testpass"
    )
    config['servers'].append(server_config)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(config, f, indent=2)
        temp_file = f.name
    
    try:
        # Read back from file
        with open(temp_file, 'r') as f:
            loaded_config = json.load(f)
        
        # Validate
        validated_config = validate_master_config(loaded_config)
        assert len(validated_config['servers']) == 1
        assert validated_config['servers'][0]['name'] == "Test Server"
        
        print("✅ File operations work with typed configs")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)


if __name__ == "__main__":
    print("🧪 Running type definition tests...")
    
    test_create_default_master_config()
    test_create_default_server_config()
    test_validate_master_config()
    test_validate_server_config()
    test_json_serialization()
    test_file_operations()
    
    print("🎉 All type definition tests passed!") 