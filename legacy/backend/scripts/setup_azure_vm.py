#!/usr/bin/env python3
"""
Azure VM Setup Script
This script helps configure the Azure VM connection for the Resource Manager.
"""

import os
import sys
from pathlib import Path


def setup_azure_vm():
    """Setup Azure VM connection configuration."""
    print("🔧 Azure VM Setup for Resource Manager")
    print("=" * 50)
    
    # Get Azure VM details
    vm_ip = input("Enter Azure VM IP address: ").strip()
    if not vm_ip:
        print("❌ VM IP address is required")
        return False
    
    vm_username = input("Enter VM username (default: azureuser): ").strip() or "azureuser"
    
    ssh_key_path = input("Enter path to SSH private key (optional): ").strip()
    if ssh_key_path and not os.path.exists(ssh_key_path):
        print(f"❌ SSH key file not found: {ssh_key_path}")
        return False
    
    # Create environment file
    env_content = f"""# Azure VM Configuration for Resource Manager
# Set these environment variables before running the backend

# Azure VM Connection Details
AZURE_VM_IP={vm_ip}
AZURE_VM_USERNAME={vm_username}
"""
    
    if ssh_key_path:
        env_content += f"AZURE_VM_SSH_KEY_PATH={ssh_key_path}\n"
    
    env_content += """
# Optional: Direct kubeconfig path (if you have the kubeconfig file)
# AZURE_VM_KUBECONFIG=/path/to/kubeconfig

# Backend Configuration
ENVIRONMENT=production
BACKEND_PORT=5005

# CORS Configuration (for frontend)
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
"""
    
    # Write to .env file
    env_file = Path(".env")
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Configuration saved to {env_file}")
    print("\n📋 Next Steps:")
    print("1. Set the environment variables:")
    print(f"   export AZURE_VM_IP={vm_ip}")
    print(f"   export AZURE_VM_USERNAME={vm_username}")
    if ssh_key_path:
        print(f"   export AZURE_VM_SSH_KEY_PATH={ssh_key_path}")
    print("   export ENVIRONMENT=production")
    print("\n2. Or source the .env file:")
    print("   source .env")
    print("\n3. Start the backend in cloud-k8s mode:")
    print("   python app.py")
    print("\n4. The backend will automatically connect to your Azure VM Kubernetes cluster")
    
    return True


def test_connection():
    """Test the Azure VM connection."""
    print("\n🧪 Testing Azure VM Connection")
    print("=" * 30)
    
    vm_ip = os.getenv('AZURE_VM_IP')
    vm_username = os.getenv('AZURE_VM_USERNAME', 'azureuser')
    ssh_key_path = os.getenv('AZURE_VM_SSH_KEY_PATH')
    
    if not vm_ip:
        print("❌ AZURE_VM_IP not set")
        return False
    
    print(f"Testing connection to {vm_username}@{vm_ip}...")
    
    try:
        import subprocess
        
        # Build SSH command
        ssh_cmd = ['ssh']
        if ssh_key_path:
            ssh_cmd.extend(['-i', ssh_key_path])
        ssh_cmd.extend(['-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10'])
        ssh_cmd.extend([f'{vm_username}@{vm_ip}'])
        ssh_cmd.extend(['echo "Connection successful"'])
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ SSH connection successful")
            
            # Test Kubernetes access
            k8s_cmd = ssh_cmd[:-1] + ['kubectl get nodes']
            result = subprocess.run(k8s_cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ Kubernetes access successful")
                print("📊 Cluster nodes:")
                print(result.stdout)
                return True
            else:
                print("❌ Kubernetes access failed")
                print(f"Error: {result.stderr}")
                return False
        else:
            print("❌ SSH connection failed")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Connection timeout")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_connection()
        else:
            print("Usage: python setup_azure_vm.py [test]")
    else:
        setup_azure_vm()


if __name__ == "__main__":
    main() 