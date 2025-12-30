# Azure VM Integration Setup Guide

This guide explains how to set up the Resource Manager to work with Kubernetes clusters running on Azure VMs.

## Overview

The Resource Manager can now connect to Kubernetes clusters running on Azure VMs using the `cloud-k8s` mode. The backend and frontend run locally on your machine, but they manage resources on the Azure VM's Kubernetes cluster.

## Prerequisites

1. **Azure VM with Kubernetes**: Your Azure VM must have a Kubernetes cluster running (k3s, k0s, or standard Kubernetes)
2. **SSH Access**: You need SSH access to the Azure VM
3. **SSH Key**: SSH key-based authentication is recommended
4. **Network Access**: The Azure VM must be accessible from your local machine

## Quick Setup

### 1. Run the Setup Script

```bash
cd backend
python setup_azure_vm.py
```

The script will prompt you for:
- Azure VM IP address
- VM username (default: azureuser)
- Path to SSH private key (optional)

### 2. Set Environment Variables

```bash
# Option 1: Export directly
export AZURE_VM_IP=your-vm-ip
export AZURE_VM_USERNAME=azureuser
export AZURE_VM_SSH_KEY_PATH=/path/to/your/private/key
export ENVIRONMENT=production

# Option 2: Source the .env file
source .env
```

### 3. Test Connection

```bash
python setup_azure_vm.py test
```

This will test both SSH connectivity and Kubernetes access.

### 4. Start the Backend

```bash
python app.py
```

The backend will automatically:
1. Connect to your Azure VM via SSH
2. Retrieve the kubeconfig from the VM
3. Update the kubeconfig to use the VM's IP address
4. Connect to the Kubernetes cluster

## Manual Setup

If you prefer to set up manually:

### 1. Environment Variables

Set these environment variables:

```bash
# Required
AZURE_VM_IP=your-vm-ip-address
AZURE_VM_USERNAME=azureuser

# Optional
AZURE_VM_SSH_KEY_PATH=/path/to/ssh/private/key
AZURE_VM_KUBECONFIG=/path/to/kubeconfig  # If you have the kubeconfig file directly

# Backend configuration
ENVIRONMENT=production
BACKEND_PORT=5005
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

### 2. SSH Key Setup

If using SSH key authentication:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure_vm_key

# Copy public key to Azure VM
ssh-copy-id -i ~/.ssh/azure_vm_key.pub azureuser@your-vm-ip

# Set environment variable
export AZURE_VM_SSH_KEY_PATH=~/.ssh/azure_vm_key
```

### 3. Test SSH Connection

```bash
ssh -i ~/.ssh/azure_vm_key azureuser@your-vm-ip
```

### 4. Verify Kubernetes on VM

On the Azure VM, verify Kubernetes is running:

```bash
# For k3s
sudo k3s kubectl get nodes

# For k0s
sudo k0s kubectl get nodes

# For standard Kubernetes
kubectl get nodes
```

## How It Works

### Connection Flow

1. **Detection**: The backend detects `AZURE_VM_IP` environment variable
2. **SSH Connection**: Connects to Azure VM via SSH
3. **Kubeconfig Retrieval**: Gets kubeconfig from `~/.kube/config` on the VM
4. **Server Address Update**: Updates kubeconfig to use VM's IP instead of localhost
5. **Kubernetes Connection**: Connects to Kubernetes API server on the VM

### Architecture

```
Local Machine                    Azure VM
┌─────────────────┐    SSH     ┌─────────────────┐
│                 │ ────────── │                 │
│  Backend        │            │  Kubernetes     │
│  (Port 5005)    │            │  Cluster        │
│                 │            │                 │
│  Frontend       │            │  (k3s/k0s/k8s)  │
│  (Port 4200)    │            │                 │
└─────────────────┘            └─────────────────┘
```

## Troubleshooting

### Common Issues

#### 1. SSH Connection Failed

**Error**: `Failed to connect to Azure VM`

**Solutions**:
- Verify VM IP address is correct
- Check if VM is running and accessible
- Verify SSH key path and permissions
- Check firewall rules on Azure VM

#### 2. Kubernetes Access Failed

**Error**: `Kubernetes access failed`

**Solutions**:
- Verify Kubernetes is running on the VM
- Check if kubeconfig exists at `~/.kube/config`
- Ensure you have proper permissions on the VM

#### 3. Permission Denied

**Error**: `Permission denied (publickey)`

**Solutions**:
- Verify SSH key is correct
- Check SSH key permissions: `chmod 600 /path/to/key`
- Ensure public key is in `~/.ssh/authorized_keys` on VM

#### 4. Timeout Errors

**Error**: `Timeout connecting to Azure VM`

**Solutions**:
- Check network connectivity
- Verify VM is not overloaded
- Increase timeout in the code if needed

### Debug Mode

Enable debug logging by setting:

```bash
export DEBUG=true
```

### Manual Kubeconfig

If SSH connection fails, you can manually provide the kubeconfig:

1. Copy kubeconfig from VM to local machine
2. Update server addresses in kubeconfig to use VM IP
3. Set `AZURE_VM_KUBECONFIG=/path/to/kubeconfig`

## Security Considerations

1. **SSH Keys**: Use strong SSH keys and keep them secure
2. **Network Security**: Ensure Azure VM has proper firewall rules
3. **Kubernetes RBAC**: Configure proper RBAC on the Kubernetes cluster
4. **Environment Variables**: Don't commit sensitive environment variables to version control

## Advanced Configuration

### Custom SSH Options

You can modify SSH options in the code:

```python
ssh_cmd.extend(['-o', 'StrictHostKeyChecking=no'])
ssh_cmd.extend(['-o', 'ConnectTimeout=10'])
```

### Custom Kubernetes Paths

If your Kubernetes is installed in a custom location:

```bash
# On the Azure VM, create a symlink
sudo ln -s /usr/local/bin/k3s /usr/local/bin/kubectl
```

### Load Balancer Configuration

For production use, consider setting up a load balancer:

```bash
# On Azure VM, expose Kubernetes API
sudo k3s server --bind-address 0.0.0.0 --advertise-address YOUR_VM_IP
```

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Enable debug logging
3. Check the backend logs for detailed error messages
4. Verify all prerequisites are met

## Next Steps

Once the Azure VM integration is working:

1. Start the frontend: `cd frontend && npm start`
2. Access the Resource Manager UI at `http://localhost:4200`
3. Switch to "Cloud Kubernetes" mode
4. Start managing your Azure VM Kubernetes resources! 