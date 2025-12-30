# Resource Manager Backend

A Flask-based REST API for managing Kubernetes resources across multiple clusters.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip
- Access to Azure VMs with MicroK8s

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your Azure VM details
   ```

3. **Start the backend:**
   ```bash
   ./start.sh
   ```

### Development

- **Start backend:** `./start.sh`
- **Stop backend:** `./stop.sh`
- **Deploy backend:** `./deploy.sh`
- **View logs:** `tail -f logs/backend.log`

## 📋 API Endpoints

### Server Configuration
- `GET /api/server-config/servers` - List all configured servers
- `POST /api/server-config/configure` - Configure a new server
- `DELETE /api/server-config/servers/<server_id>` - Deconfigure a server
- `GET /api/server-config/servers/<server_id>/test` - Test server connection
- `GET /api/server-config/templates` - List available templates
- `GET /api/server-config/templates/<template_id>` - Get specific template
- `POST /api/server-config/templates/<template_id>/apply` - Apply template

### Kubernetes Resources
- `GET /api/k8s/pods` - List all pods across servers
- `POST /api/k8s/pods` - Create a new pod
- `DELETE /api/k8s/pods/<pod_id>` - Delete a pod
- `PUT /api/k8s/pods/<pod_id>` - Update a pod

### Health Monitoring
- `GET /health` - Health check endpoint
- `GET /api/health/servers` - Server health status

## 🔧 Configuration

### Environment Variables
- `AZURE_VM_IP` - Default Azure VM IP
- `AZURE_VM_KUBECONFIG` - Path to kubeconfig file
- `ENVIRONMENT` - Environment (development/production)

### Data Storage
- `data/master.json` - Server configurations and templates
- `logs/` - Application logs

## 🧪 Testing

Run backend tests:
```bash
cd tests
python -m pytest
```

## 📁 Project Structure

```
backend/
├── main.py                  # Main entry point
├── core/                    # Core application files
│   ├── app.py              # Main Flask application
│   ├── server_configuration_api.py # Server configuration endpoints
│   ├── server_manager.py   # Server management logic
│   ├── kubernetes_resource_manager.py # Resource management
│   ├── health_monitor.py   # Health monitoring
│   └── k8s_client.py      # Kubernetes client wrapper
├── config/                  # Configuration files
│   ├── config.py           # Configuration management
│   ├── constants.py        # Application constants
│   └── utils.py            # Utility functions
├── kubeconfig/              # Kubernetes config files
│   └── azure_vm_kubeconfig* # Azure VM kubeconfig files
├── data/                    # Data storage
│   └── master.json         # Server configurations
├── providers/               # Cloud provider integrations
├── apipayloads/            # API test payloads
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── dev/                    # Development tools
├── logs/                   # Application logs
├── api-contracts/          # API contract definitions
├── requirements.txt        # Python dependencies
├── env.example            # Environment template
├── start.sh               # Startup script
├── stop.sh                # Shutdown script
├── deploy.sh              # Deployment script
└── STRUCTURE.md           # Structure documentation
```

## 🔍 Troubleshooting

### Common Issues

1. **Port 5005 already in use:**
   ```bash
   lsof -i :5005
   kill -9 <PID>
   ```

2. **Azure VM connection issues:**
   - Verify VM IP and credentials in `data/master.json`
   - Check SSH connectivity to VM
   - Ensure MicroK8s is running on VM

3. **Kubeconfig issues:**
   - Verify kubeconfig file exists and is valid
   - Check if kubeconfig contains correct cluster IP

### Logs
- **Application logs:** `logs/backend.log`
- **Error logs:** Check console output and logs directory

## 🔗 Integration

### Frontend Integration
- Frontend connects to backend on `http://localhost:5005`
- API endpoints documented at `http://localhost:5005/apidocs`

### External Dependencies
- Azure VMs with MicroK8s
- SSH access for kubeconfig retrieval
- Kubernetes API access

## 📚 Documentation

- [API Documentation](http://localhost:5005/apidocs) (when running)
- [Server Configuration Guide](docs/SERVER_CONFIGURATION.md)
- [Kubernetes Integration Guide](docs/KUBERNETES_INTEGRATION.md)
- [Health Monitoring Guide](docs/HEALTH_MONITORING.md)

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure all scripts are executable

## 📄 License

On-premise application - internal use only. 