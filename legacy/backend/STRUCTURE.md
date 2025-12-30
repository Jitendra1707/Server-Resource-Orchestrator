# Backend Directory Structure

This document explains the organized structure of the backend directory.

## 📁 Directory Organization

### **🏗️ Core Application Files** (`core/`)
Contains the main application logic:
- `app.py` - Main Flask application and API endpoints
- `server_configuration_api.py` - Server configuration API endpoints
- `server_manager.py` - Server management logic
- `kubernetes_resource_manager.py` - Kubernetes resource management
- `health_monitor.py` - Health monitoring system
- `k8s_client.py` - Kubernetes client wrapper

### **⚙️ Configuration Files** (`config/`)
Contains configuration and utility files:
- `config.py` - Application configuration management
- `constants.py` - Application constants and enums
- `utils.py` - Utility functions and helpers

### **🔑 Kubeconfig Files** (`kubeconfig/`)
Contains Kubernetes configuration files:
- `azure_vm_kubeconfig` - Azure VM kubeconfig file
- `azure_vm_kubeconfig_updated` - Updated kubeconfig
- `azure_vm_kubeconfig_updated.sanitized` - Sanitized kubeconfig

### **📊 Data Storage** (`data/`)
Contains application data:
- `master.json` - Server configurations and templates
- `mock_db_backup_20250720_194719.json` - Backup data

### **🧪 Testing** (`tests/`)
Contains test files and test utilities:
- `test_server_config_api.py` - Server configuration API tests
- `test_deconfigure_api.py` - Deconfiguration API tests
- `test_azure_vm_integration.py` - Azure VM integration tests

### **📚 Documentation** (`docs/`)
Contains backend-specific documentation:
- `SERVER_CONFIGURATION_SOLUTION.md` - Server configuration solution
- `SERVER_CONFIGURATION_API.md` - Server configuration API docs
- `AZURE_VM_KUBECONFIG_README.md` - Azure VM kubeconfig guide
- `AZURE_VM_SETUP.md` - Azure VM setup guide

### **🛠️ Scripts** (`scripts/`)
Contains utility scripts:
- `configure_vms.py` - VM configuration scripts
- `setup_azure_vm.py` - Azure VM setup
- `fix_*.py` - Kubeconfig fix scripts

### **🔧 Development Tools** (`dev/`)
Contains development utilities and tools.

### **📝 Logs** (`logs/`)
Contains application logs.

### **🌐 API Contracts** (`api-contracts/`)
Contains API contract definitions for backend implementation.

### **☁️ Providers** (`providers/`)
Contains cloud provider integrations:
- `kubernetes_provider.py` - Kubernetes provider implementation
- `cloud_kubernetes_provider.py` - Cloud Kubernetes provider

### **📦 API Payloads** (`apipayloads/`)
Contains API test payloads and examples.

## 🚀 Entry Points

### **Main Entry Point** (`main.py`)
- New main entry point for the Flask application
- Imports from the organized structure
- Handles Python path setup

### **Legacy Entry Point** (`core/app.py`)
- Original Flask application
- Still functional but moved to core/

## 🔄 Migration Benefits

### **✅ Better Organization**
- Related files are grouped together
- Clear separation of concerns
- Easier to find specific functionality

### **✅ Improved Maintainability**
- Logical file grouping
- Reduced root directory clutter
- Clear module boundaries

### **✅ Enhanced Development**
- Easier to understand project structure
- Better import organization
- Cleaner development workflow

### **✅ Cleaned Up**
- Removed outdated documentation
- Removed redundant test files
- Removed legacy scripts
- Kept only essential files

## 📋 File Locations

| **Functionality** | **Location** | **Files** |
|-------------------|--------------|-----------|
| **Main Application** | `core/` | `app.py`, `server_configuration_api.py`, etc. |
| **Configuration** | `config/` | `config.py`, `constants.py`, `utils.py` |
| **Kubernetes Config** | `kubeconfig/` | `azure_vm_kubeconfig*` |
| **Data** | `data/` | `master.json`, backup files |
| **Scripts** | `scripts/` | VM setup and kubeconfig fix scripts |
| **API Contracts** | `api-contracts/` | Contract definitions |
| **Documentation** | `docs/` | Backend docs |
| **Tests** | `tests/` | Test files |
| **Providers** | `providers/` | Cloud provider integrations |

## 🔧 Development Workflow

### **Adding New Features**
1. **Core Logic** → `core/` directory
2. **Configuration** → `config/` directory
3. **Data Files** → `data/` directory
4. **Scripts** → `scripts/` directory
5. **Tests** → `tests/` directory

### **Importing Modules**
```python
# From core modules
from core.app import app
from core.server_manager import server_manager

# From config modules
from config.config import Config
from config.constants import ErrorMessages
from config.utils import some_utility_function
```

### **Running the Application**
```bash
# Using the new main entry point
python main.py

# Or using the start script
./start.sh
```

## 🎯 Benefits for Future Split

This organized structure makes the backend even more independent:

- **Clear module boundaries** for easy extraction
- **Self-contained functionality** in logical groups
- **Minimal cross-dependencies** between modules
- **Clean import structure** for external consumption
- **Organized configuration** for easy deployment
- **Cleaned up** - removed outdated and redundant files

The backend can now be easily split into a standalone repository with this clean, organized structure! 