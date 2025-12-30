# Azure VM Kubernetes Configuration

This directory contains the Kubernetes configuration file for connecting to the Azure VM microk8s cluster.

## Files

- `azure_vm_kubeconfig_updated` - The actual kubeconfig file with credentials
- `azure_vm_kubeconfig_updated.sanitized` - Sanitized version for documentation (no credentials)

## Connection Details

- **Server**: `4.246.178.26:16443`
- **Cluster Type**: microk8s
- **Authentication**: Certificate-based (admin user)
- **TLS**: Insecure (skip-tls-verify: true)

## Security Notice

⚠️ **IMPORTANT**: The `azure_vm_kubeconfig_updated` file contains sensitive certificate data and should be kept secure:
- Do not commit this file to version control
- Do not share this file publicly
- Keep file permissions restricted (600 or 400)
- Consider using environment variables for sensitive data

## Usage

### 1. Direct kubectl usage

```bash
# Set the kubeconfig file
export KUBECONFIG=./azure_vm_kubeconfig_updated

# Test connection
kubectl get nodes

# List all pods
kubectl get pods --all-namespaces

# Get cluster info
kubectl cluster-info
```

### 2. With Resource Manager Backend

The backend automatically uses this file when configured for the live environment:

```bash
# Set environment to live
export ENVIRONMENT=live

# Start the backend
python app.py
```

The backend will:
- Load the kubeconfig from `./azure_vm_kubeconfig_updated`
- Connect to the Azure VM microk8s cluster
- Provide API endpoints for managing Kubernetes resources

### 3. Environment Variables

You can also set the kubeconfig path via environment variable:

```bash
export AZURE_VM_KUBECONFIG=./azure_vm_kubeconfig_updated
export ENVIRONMENT=live
python app.py
```

## Troubleshooting

### Connection Issues

1. **Check if the Azure VM is running**:
   ```bash
   ping 4.246.178.26
   ```

2. **Verify port accessibility**:
   ```bash
   telnet 4.246.178.26 16443
   ```

3. **Test with kubectl**:
   ```bash
   kubectl --kubeconfig=./azure_vm_kubeconfig_updated get nodes
   ```

### Certificate Issues

If you encounter certificate errors:
- The kubeconfig is configured with `insecure-skip-tls-verify: true`
- This should bypass most TLS verification issues
- If still having problems, check if the certificates have expired

### Permission Issues

Ensure proper file permissions:
```bash
chmod 600 azure_vm_kubeconfig_updated
```

## Backup and Recovery

### Creating a backup
```bash
cp azure_vm_kubeconfig_updated azure_vm_kubeconfig_updated.backup
```

### Restoring from backup
```bash
cp azure_vm_kubeconfig_updated.backup azure_vm_kubeconfig_updated
```

## Related Documentation

- [Azure VM Setup Guide](../AZURE_VM_SETUP.md)
- [Unified Architecture](../UNIFIED_ARCHITECTURE.md)
- [Backend Configuration](config.py)
- [Kubernetes Client](k8s_client.py) 