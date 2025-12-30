from flask import request
from pass_infra.app.config import config
from pass_infra.app.config.environment import ENV ,ConfigLoader
from pass_infra.app.data.data_access_layer import CustomError
from pass_infra.app.schemas.abstract_class import DFPreprocessStrategy
from pass_infra.app.data.resource_manager_queries import (
  get_server_details_with_pod_id,
  delete_pod_status,
)
from pass_infra.app.utils.logging import LoggerUtils
from kubernetes import client,config as configs
from azure.containerregistry import ContainerRegistryClient
from azure.identity import ClientSecretCredential
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.resource import ResourceManagementClient
from urllib.parse import urlparse
import time
import paramiko
import json
import requests
import os
import tempfile
import uuid
import base64
import socket
import yaml
from kubernetes.client.rest import ApiException
from typing import Dict, Any
 
 
 
class kubeneter_resource_delete(DFPreprocessStrategy):
    def load_config(self, config_file): #  pragma: no cover
        pass
 
    def load_database_config(self, json_file):#  pragma: no cover
        pass
 

    def get_json(self, json_file: str): #  pragma: no cover
        pass
 
    def on_error(self, errordata): #  pragma: no cover
        pass
 
    def connection_db(self):# pragma: no cover
        pass
 
    def adaptive_adjustments(self) -> None: # pragma: no cover
        pass
 
    def alert_system(self, alert_message, severity) -> None: # pragma: no cover
        pass
 
    def connection_validation(self, config: str) -> dict: # pragma: no cover
        pass
 
    def explainability_monitor(self) -> Dict[str, Any]: # pragma: no cover
        pass
 
    def log_feedback(self, feedback) -> None: # pragma: no cover
        pass
 
    def log_processing_data(self, data, result): # pragma: no cover
        pass
 
    def monitor_performance(self) -> None: # pragma: no cover
        pass
 
    def store_user_preprocess_info(self, user_data: Dict[str, Any]) -> bool: # pragma: no cover
        pass
 
    def user_component(self, connection, inputval) -> bool: # pragma: no cover
        pass
 
    def on_start(self): # pragma: no cover
        return time.time()
 
    def on_finish(self): # pragma: no cover
        return time.time()
    
    def __init__(self):
        pass

    def validate_input_data(self, data):
        required_fields = ["pod_id"]

        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            LoggerUtils.error(f"Missing fields: {', '.join(missing_fields)}")
            raise CustomError(f"Missing fields: {', '.join(missing_fields)}")
        if not isinstance(data["pod_id"], int):
            LoggerUtils.error("pod_id must be an integer")
            raise CustomError("pod_id must be an integer", 400)
        
    def server_details_with_pod_id(self, pod_id: int) -> Dict[str, Any]:
        get_pod_details = get_server_details_with_pod_id(pod_id)
        if not get_pod_details:
            LoggerUtils.error(f"No server details found for pod_id: {pod_id}")
            raise CustomError(f"No server details found for pod_id: {pod_id}", 404)
        return get_pod_details
    
    def update_pod_status_as_delete(self, pod_id: int):
        try:
            delete_pod_status(pod_id)
            LoggerUtils.info(f"Pod status deleted for pod_id: {pod_id}")
        except Exception as e:
            LoggerUtils.error(f"Failed to delete pod status for pod_id: {pod_id}, Error: {str(e)}")
            raise CustomError(f"Failed to delete pod status for pod_id: {pod_id}", 500)
        return True
       

    def get_kubeconfig(self,machine_ip, username, password) -> str:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname= machine_ip,  
            username= username,
            password= password, 
            timeout=60,  # Set a timeout for the SSH connection
        )
        # Check if SSH connection was successful
        transport = ssh.get_transport()
        if transport is None or not transport.is_active():
            LoggerUtils.error("SSH connection failed")
            raise CustomError("SSH connection failed", 500)
        

        stdin, stdout, _ = ssh.exec_command("sudo microk8s config")
        config_data = stdout.read().decode()
        ssh.close()

        # Load YAML
        config_dict = yaml.safe_load(config_data)

        public_ip = machine_ip  # Replace with dynamic IP if needed

        if not config_dict or not isinstance(config_dict, dict):
            raise CustomError("Failed to load kubeconfig YAML or Kubeneters not installed", 500)

        for cluster in config_dict.get("clusters", []):
            server_url = cluster["cluster"]["server"]
            parsed = urlparse(server_url)

            # Replace host (private IP) with public IP
            updated_server_url = f"{parsed.scheme}://{public_ip}:{parsed.port or 16443}"
            cluster["cluster"]["server"] = updated_server_url

            # Insecure skip TLS verification (optional for dev)
            cluster["cluster"]["insecure-skip-tls-verify"] = True
            cluster["cluster"].pop("certificate-authority-data", None)

        config_data_modified = yaml.dump(config_dict)

        kubeconfig_path = os.path.join(tempfile.gettempdir(), f"kubeconfig_{uuid.uuid4()}.yaml")
        with open(kubeconfig_path, "w") as f:
            f.write(config_data_modified)
        LoggerUtils.info(f"Kubeconfig saved to {kubeconfig_path}")
        # Return the path to the kubeconfig file
        if not os.path.exists(kubeconfig_path):
            raise CustomError("Failed to create kubeconfig file", 500)

        return kubeconfig_path
    
    def cleanup_kubernetes_resources(self, kubeconfig_path, data):
        """Deletes Kubernetes resources and waits for namespace deletion."""
        LoggerUtils.info(f"Starting cleanup of Kubernetes resources for {data['aiservice_name']}")

        # Load Kubernetes configuration
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
        k8s_apps_v1 = client.AppsV1Api()
        k8s_networking_v1 = client.NetworkingV1Api()

        missing_resources = []  # Track missing resources

        try:
            # Delete ingress
            try:
                LoggerUtils.info(f"Deleting ingress: {data['aiservice_name']}")
                k8s_networking_v1.delete_namespaced_ingress(
                    name=data["aiservice_name"], namespace=data["aiservice_name"]
                )
                LoggerUtils.info(f"Ingress '{data['aiservice_name']}' deleted successfully.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.warning(f"Ingress '{data['aiservice_name']}' not found, skipping deletion.")
                    missing_resources.append("Ingress")

            # Delete service
            try:
                LoggerUtils.info(f"Deleting service: {data['aiservice_name']}")
                k8s_core_v1.delete_namespaced_service(
                    name=data["aiservice_name"], namespace=data["aiservice_name"]
                )
                LoggerUtils.info(f"Service '{data['aiservice_name']}' deleted successfully.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.warning(f"Service '{data['aiservice_name']}' not found, skipping deletion.")
                    missing_resources.append("Service")

            # Delete deployment
            try:
                LoggerUtils.info(f"Deleting deployment: {data['aiservice_name']}")
                k8s_apps_v1.delete_namespaced_deployment(
                    name=data["aiservice_name"], namespace=data["aiservice_name"]
                )
                LoggerUtils.info(f"Deployment '{data['aiservice_name']}' deleted successfully.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.warning(f"Deployment '{data['aiservice_name']}' not found, skipping deletion.")
                    missing_resources.append("Deployment")

            # Delete namespace and wait until deletion is complete
            try:
                LoggerUtils.info(f"Deleting namespace: {data['aiservice_name']}")
                k8s_core_v1.delete_namespace(name=data["aiservice_name"])

                # Polling for namespace deletion
                timeout = 120  # Maximum wait time in seconds
                interval = 5  # Check every 5 seconds
                elapsed_time = 0

                while elapsed_time < timeout:
                    time.sleep(interval)
                    elapsed_time += interval
                    try:
                        k8s_core_v1.read_namespace(name=data["aiservice_name"])
                        LoggerUtils.info(f"Waiting for namespace '{data['aiservice_name']}' to be deleted...")
                    except ApiException as e:
                        if e.status == 404:
                            LoggerUtils.info(f"Namespace '{data['aiservice_name']}' deleted successfully.")
                            break
                        else:
                            raise CustomError(f"Unexpected error while checking namespace deletion: {e}")

                if elapsed_time >= timeout:
                    raise CustomError(f"Timeout: Namespace '{data['aiservice_name']}' deletion took too long.")

            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.warning(f"Namespace '{data['aiservice_name']}' not found, skipping deletion.")
                    missing_resources.append("Namespace")

            if missing_resources:
                raise CustomError(
                    f"Cleanup incomplete. Missing resources: {', '.join(missing_resources)}"
                )
        except Exception:
            LoggerUtils.error("Failed to clean up Kubernetes resources or resources not found")
            raise CustomError("Failed to clean up Kubernetes resources or resources not found")


    def execute(self) -> Dict[str, Any]:
        try:
            data = request.get_json()
            self.validate_input_data(data)
            get_pod_details = self.server_details_with_pod_id(data["pod_id"])
            if get_pod_details is None:
                LoggerUtils.error(f"No server details found for pod_id: {data['pod_id']}")
                raise CustomError(f"No server details found for pod_id: {data['pod_id']}", 404)
            if get_pod_details["pod_status"] == "Deleted":
                LoggerUtils.info(f"Pod with pod_id: {data['pod_id']} is already deleted.")
                return {"message": "Pod is already deleted", "pod_id": data["pod_id"]}
            if get_pod_details["pod_status"] != "Running":
                LoggerUtils.error(f"Pod with pod_id: {data['pod_id']} is not in a valid state for deletion.")
                raise CustomError(f"Pod with pod_id: {data['pod_id']} is not in a valid state for deletion.", 400)
            data["aiservice_name"] = get_pod_details.get("pod_name", "")
            server_config = get_pod_details.get("server_config", {})
            machine_ip = server_config["machine_ip"]
            username = server_config["username"]
            password = server_config["password"]
            kubeconfig_path = self.get_kubeconfig(machine_ip, username, password)
            self.cleanup_kubernetes_resources(kubeconfig_path, data)
            self.update_pod_status_as_delete(data["pod_id"])
            LoggerUtils.info(f"Successfully deleted Kubernetes resources for pod_id: {data['pod_id']}")
            return {"message": "Kubernetes resources deleted successfully", "pod_id": data["pod_id"]}
        except CustomError as e:
            LoggerUtils.error(f"Validation error: {e}")
            raise CustomError(f"Validation error: {e}")

        
    
      


     


