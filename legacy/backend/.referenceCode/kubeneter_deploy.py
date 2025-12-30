from flask import request
from pass_infra.app.config import config
from pass_infra.app.config.environment import ENV ,ConfigLoader
from pass_infra.app.data.data_access_layer import CustomError
from pass_infra.app.schemas.abstract_class import DFPreprocessStrategy
from pass_infra.app.data.resource_manager_queries import (
    get_server_capacity,
    insert_pod_details,
    update_pod_details,
)
from pass_infra.app.utils.logging import LoggerUtils
from kubernetes import client,config as configs
from azure.containerregistry import ContainerRegistryClient
from pass_infra.app.services.resource_manager.pre_resources_allocation import ResourceAllocation
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
from azure.core.credentials import AzureNamedKeyCredential
 
 
 
class kubeneter_resource_deploy(DFPreprocessStrategy):
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
        super().__init__()
        self.config_loader = ConfigLoader()
        self.config = self.config_loader.settings
        self.kubeconfig_path = None
        self.k8s_core_v1 = None
        self.k8s_apps_v1 = None
        self.k8s_networking_v1 = None
        self.namespace = None

          
    def validate_input_data(self, data: Dict[str, Any]) -> None:

        if 'replicas' not in data or data['replicas'] is None:
            data['replicas'] = 1 # Default to 1 replica if not specified

        required_fields = ["server_name", "vcpu", "storage", "gpu","pod_name","image_url","replicas","username","password"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise CustomError(f"Missing fields: {', '.join(missing)}",400)
        if not isinstance(data["pod_name"], str) or not data["pod_name"].islower() or "_" in data["pod_name"]:
            raise ValueError("Invalid  pod name format. It should be in lowercase and should not contain underscores.")
        if not isinstance(data["image_url"], str) or not (data["image_url"].startswith("https://") ) or ":" not in data["image_url"]:
            raise ValueError("Invalid image URL format. It should start with 'https://'and end with a version tag (e.g., ':v1').")
        # Parse image_url to extract registry_url, image_name, and image_tag
        try:
            image_url = data.get("image_url", "")
            if not image_url:
                raise ValueError("image_url is required.")

            # Remove protocol if present
            if image_url.startswith("https://"):
                image_url = image_url[len("https://"):]

            # Split into registry and image info
            if "/" not in image_url or ":" not in image_url:
                raise ValueError("Invalid image_url format. Expected format: <registry>/<image_name>:<tag>")

            registry_and_image, image_tag = image_url.rsplit(":", 1)
            registry_url, image_name = registry_and_image.split("/", 1)

            data["registery_url"] = registry_url
            data["image_name"] = image_name
            data["image_tag"] = image_tag
            # Extract acr_name (first part of registry_url)
            data["acr_name"] = registry_url.split(".")[0]
        except Exception as e:
            raise CustomError(f"Failed to parse image_url: {str(e)}", 400)
    
    def get_cluster_resource_summary(self, data,kubeconfig_path):
        """Fetches the resource summary of the Kubernetes cluster."""
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
        try:
            nodes = k8s_core_v1.list_node().items
            resource_summary = {
                "total_nodes": len(nodes),
                "total_cpu": 0,
                "total_memory": 0,
                "total_gpu": 0,
            }
            for node in nodes:
                capacity = node.status.capacity
                resource_summary["total_cpu"] += int(capacity.get("cpu", 0))
                resource_summary["total_memory"] += int(capacity.get("memory", 0).replace("Ki", ""))
                resource_summary["total_gpu"] += int(capacity.get("nvidia.com/gpu", 0))
            LoggerUtils.info(f"Cluster resource summary: {resource_summary}")
            if resource_summary["total_cpu"] == 0 or resource_summary["total_memory"] == 0:
                raise CustomError("Cluster has no available resources", 500)
            LoggerUtils.info("Cluster resource summary fetched successfully")
            # Return the resource summary
            resource_summary["total_memory"] = resource_summary["total_memory"] // 1024  # Convert Ki to Mi
            # Convert CPU to integer (cores) if it's a string or resource quantity
            cpu_value = resource_summary["total_cpu"]
            if isinstance(cpu_value, str):
                # Handle cases like "4", "4000m", etc.
                if cpu_value.endswith("m"):
                    resource_summary["total_cpu"] = int(int(cpu_value.rstrip("m")) / 1000)
                else:
                    resource_summary["total_cpu"] = int(cpu_value)
            else:
                resource_summary["total_cpu"] = int(cpu_value)
            resource_summary["total_gpu"] = resource_summary["total_gpu"] or 0  # Ensure GPU is at least 0
            resource_summary["total_memory"] = str(resource_summary["total_memory"]) + "Mi"
            resource_summary["total_cpu"] = str(resource_summary["total_cpu"]) + " cores"
            resource_summary["total_gpu"] = str(resource_summary["total_gpu"]) + " GPUs"
            resource_summary["total_nodes"] = str(resource_summary["total_nodes"]) + " nodes"
            LoggerUtils.info(f"Final resource summary: {resource_summary}")
            # Return the resource summary
            LoggerUtils.info(f"Cluster resource summary: {resource_summary}")
           
            self.compare_resources(data, resource_summary)
            self.fetch_and_validate_master_db_details(data)
            if not resource_summary:
                raise CustomError("Cluster resource summary is empty", 500)
            return resource_summary
        except ApiException as e:
            LoggerUtils.error(f"Failed to fetch cluster resource summary: {str(e)}")
            raise CustomError(f"Failed to fetch cluster resource summary: {str(e)}", 500)
        

    def compare_resources(self, data, resource_summary):
        """Compares the requested resources with the cluster's available resources."""
        LoggerUtils.info(f"Comparing requested resources with cluster resource summary: {resource_summary}")
        if data["vcpu"] > resource_summary["total_cpu"]:
            raise CustomError("Requested vCPU exceeds cluster's total CPU capacity", 400)
        if data["storage"] > resource_summary["total_memory"]:
            raise CustomError("Requested storage exceeds cluster's total memory capacity", 400)
        if data["gpu"] > resource_summary["total_gpu"]:
            raise CustomError("Requested GPU exceeds cluster's total GPU capacity", 400)
        LoggerUtils.info("Resource comparison with cluster summary successful")

    
    def fetch_and_validate_master_db_details(self, data):
        check_resources = ResourceAllocation()
        response = check_resources.execute(payload=data)
        LoggerUtils.info("Master DB details fetched and validated successfully")
        # Fetch server details from the database
        if response.get("status_code") == 200 or response.get("message") == "Quota check complete , allocation possible.":
            LoggerUtils.info("Server details fetched successfully")
            return response.get("data", {}).get("available", {})
        elif response.get("status_code") == 404:
            LoggerUtils.error("Server not found or inactive")
            raise CustomError("Server not found or inactive", 404)
        elif response.get("status_code") == 500:
            LoggerUtils.error("Internal server error while fetching server details")
            raise CustomError("Internal server error while fetching server details", 500)
        else:
            LoggerUtils.error(f"Failed to fetch server details: {response.get('message', 'Unknown error')}")
            raise CustomError(response.get("message", "Failed to fetch server details"), response.get("status_code", 500))
            
    def fetch_server_details(self,data):
        server_details = get_server_capacity(data["server_name"])
        if not server_details or "is_active" not in server_details:
            raise CustomError("Server not found or inactive",404)
        return server_details
    
    def insert_pod_details(self, data):
        pods_details = insert_pod_details({
            "server_id": data["server_id"],
            "vcpu": data["vcpu"],
            "storage": data["storage"],
            "is_active": "Y",
            "pod_status": "Pending",
            "gpu": data["gpu"],
            "pod_name": data["pod_name"],
        })
        LoggerUtils.info(f"Pod details inserted: {pods_details}")
        if not pods_details:
            raise CustomError("Failed to insert pod details", 500)
        return pods_details
    
    def update_pod_details(self, pod_id, pod_ip=None):
        updated_pod_details = update_pod_details(pod_id, pod_ip,)
        LoggerUtils.info(f"Pod details updated: {updated_pod_details}")
        if not updated_pod_details:
            raise CustomError("Failed to update pod details", 500)
        return True
    
    # Function to get kubeconfig from the VM
    # This function connects to the VM via SSH and retrieves the kubeconfig file
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
    
        
    # def check_image_exists(self, data):
    #     image_tag = data["image_tag"]
    #     image_name = data["image_name"]
    #     """Checks if the image tag exists in the specified Azure Container Registry."""
    #     LoggerUtils.info(f"Checking image existence: {image_tag}")
    #     try:
    #         # Get the ACR login server (e.g., myregistry.azurecr.io)"
    #         registry_url = data["registery_url"]
    #         username = data["username"]
    #         password = data["password"]

    #         # Support both Azure Container Registry (ACR) and other registries (e.g., Docker Hub)
    #         if "azurecr.io" in registry_url:
    #             # Ensure registry_url includes the full domain (e.g., myregistry.azurecr.io)
    #             client = ContainerRegistryClient(
    #                 endpoint=f"https://{registry_url}",
    #                 credential=AzureNamedKeyCredential(username, password)
    #             )
    #             acr_name = data["acr_name"]
    #             # List tags in the specified repository
    #             tags = client.list_tag_properties(image_name)
    #             for tag in tags:
    #                 if tag.name == image_tag:
    #                     LoggerUtils.info(f"Image tag '{image_tag}' exists in repository '{image_name}' on ACR '{acr_name}'.")
    #                     return True
    #             raise CustomError(f"Image tag '{image_tag}' does not exist in repository '{image_name}' on ACR '{acr_name}'.")
    #         else:
    #             # For other registries, use Docker Registry HTTP API v2
    #             acr_name = registry_url
    #             repo_url = f"https://{registry_url}/v2/{image_name}/tags/list"
    #             response = requests.get(repo_url, auth=(username, password))
    #             if response.status_code == 200:
    #                 tags = response.json().get("tags", [])
    #                 if image_tag in tags:
    #                     LoggerUtils.info(f"Image tag '{image_tag}' exists in repository '{image_name}' on registry '{registry_url}'.")
    #                     return True
    #                 else:
    #                     raise CustomError(f"Image tag '{image_tag}' does not exist in repository '{image_name}' on registry '{registry_url}'.")
    #             else:
    #                 raise CustomError(f"Failed to access registry '{registry_url}': {response.text}")
    #     except Exception as e:
    #         LoggerUtils.error(f"Error checking image existence: {str(e)}")
    #         raise CustomError(f"Error checking image existence: {str(e)}", 500)
   
    def ensure_namespace_exists(self, k8s_core_v1, namespace_name):
        """Ensures the namespace exists in Kubernetes."""
        try:
            k8s_core_v1.read_namespace(namespace_name)
            LoggerUtils.info(f"Namespace {namespace_name} already exists.")
            raise ValueError(f"Namespace {namespace_name}already exists.")
        except ApiException as e:
            if e.status == 404:
                LoggerUtils.info(f"Creating namespace: {namespace_name}")
                namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace_name))
                k8s_core_v1.create_namespace(namespace)
                LoggerUtils.info(f"Namespace {namespace_name} created successfully.")
            else:
                LoggerUtils.error(f"Error ensuring namespace exists: {str(e)}")
                raise CustomError(f"Failed to ensure namespace exists: {str(e)}")
    
    def create_image_pull_secret(self, kubeconfig_path, data):
        """Creates an image pull secret for ACR."""
        LoggerUtils.info(f"Creating image pull secret for ACR: {data['acr_name']}")
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
        namespace = data["aiservice_name"]
 
        self.ensure_namespace_exists(k8s_core_v1, namespace)
 
        # Obtain ACR credentials
        try:
            username = data["username"]
            password = data["password"]
 
            docker_config_json = {
                "auths": {
                    f"{data['acr_name']}.azurecr.io": {
                        "username": username,
                        "password": password,
                        "auth": base64.b64encode(f"{username}:{password}".encode()).decode(),
                    }
                }
            }
 
            secret_body = client.V1Secret(
                metadata=client.V1ObjectMeta(name="acr-image-pull-secret", namespace=namespace),
                data={".dockerconfigjson": base64.b64encode(json.dumps(docker_config_json).encode()).decode()},
                type="kubernetes.io/dockerconfigjson"
            )
 
            # Check if the secret already exists, else create it
            try:
                k8s_core_v1.read_namespaced_secret(name="acr-image-pull-secret", namespace=namespace)
                LoggerUtils.info("Image pull secret already exists.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.info("Creating a new image pull secret.")
                    k8s_core_v1.create_namespaced_secret(namespace=namespace, body=secret_body)
                    LoggerUtils.info("Image pull secret created successfully.")
                else:
                    LoggerUtils.error(f"Failed to create image pull secret: {str(e)}")
                    raise CustomError(f"Failed to create image pull secret: {str(e)}")
 
        except Exception as e:
            LoggerUtils.error(f"Error creating image pull secret: {str(e)}")
            raise CustomError(f"Error creating image pull secret: {str(e)}")
        
    
    
    # Function to ensure the namespace exists in Kubernetes
    def ensure_namespace_exists(self, k8s_core_v1, namespace_name):
        """Ensures the namespace exists in Kubernetes."""
        try:
            k8s_core_v1.read_namespace(namespace_name)
            LoggerUtils.info(f"Namespace {namespace_name} already exists.")
            raise ValueError(f"Namespace {namespace_name}already exists.")
        except ApiException as e:
            if e.status == 404:
                LoggerUtils.info(f"Creating namespace: {namespace_name}")
                namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace_name))
                k8s_core_v1.create_namespace(namespace)
                LoggerUtils.info(f"Namespace {namespace_name} created successfully.")
            else:
                LoggerUtils.error(f"Error ensuring namespace exists: {str(e)}")
                raise CustomError(f"Failed to ensure namespace exists: {str(e)}")
            
    def create_kubernetes_resources(self, kubeconfig_path, data):
        """Creates Kubernetes resources for the AI service."""
        LoggerUtils.info(f"Creating Kubernetes resources for {data['aiservice_name']}")
       
        # Load Kubernetes configuration
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
        k8s_apps_v1 = client.AppsV1Api()
        k8s_networking_v1 = client.NetworkingV1Api()
        namespace = data["aiservice_name"]
        # existing_node_pools = set()
        # for node in k8s_core_v1.list_node().items:
        #     for label_key, label_value in node.metadata.labels.items():
        #         if any(node_name in label_value.lower() for node_name in data['node_name']) or \
        #            any(node_name in label_key.lower() for node_name in data['node_name']):  
        #             existing_node_pools.add(label_value)
        # LoggerUtils.info(f"Available node pools: {existing_node_pools}")

        # # Find matching node pools from the payload
        # matching_node_pools = [pool for pool in data["node_name"] if pool in existing_node_pools]

        # # If valid node pools exist, use the first one; otherwise, allow auto-scheduling
        # if matching_node_pools:
        #     LoggerUtils.info(f"Using node pool: {matching_node_pools[0]} for scheduling.")
        #     node_selector = {"agentpool": matching_node_pools[0]}  # Adjust key if needed
        # else:
        #     LoggerUtils.info("None of the specified node pools exist. Using default scheduler.")
        #     node_selector = {}  # Let Kubernetes auto-schedule the pod


        # Create a ConfigMap for environment variables
        config_map_name = f"{data['aiservice_name']}-env-config"
        config_map_data = {
            "AZURE_APPCONFIG_CONNECTION_STRING": os.environ.get("AZURE_APPCONFIG_CONNECTION_STRING", ""),
            "AZURE_CLIENT_ID": config.ARM_CLIENT_ID,
            "AZURE_CLIENT_SECRET": config.ARM_CLIENT_SECRET,
            "AZURE_TENANT_ID": config.ARM_TENANT_ID,
            "AZURE_SUBSCRIPTION_ID": config.ARM_SUBSCRIPTION_ID,
            "ENVIRONMENT": ENV,
            "COMMON_UTILIS_URL": config.COMMON_UTILIS_URL,
            "COMMON_UTILIS_PACKAGE": config.COMMON_UTILIS_PACKAGE,
        }
        config_map = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=config_map_name, namespace=namespace),
            data=config_map_data
        )
        # Create or update the ConfigMap
        try:
            k8s_core_v1.read_namespaced_config_map(name=config_map_name, namespace=namespace)
            k8s_core_v1.patch_namespaced_config_map(name=config_map_name, namespace=namespace, body=config_map)
            LoggerUtils.info(f"ConfigMap {config_map_name} updated successfully.")
        except ApiException as e:
            if e.status == 404:
                k8s_core_v1.create_namespaced_config_map(namespace=namespace, body=config_map)
                LoggerUtils.info(f"ConfigMap {config_map_name} created successfully.")
            else:
                LoggerUtils.error(f"Failed to create/update ConfigMap: {str(e)}")
                raise CustomError(f"Failed to create/update ConfigMap: {str(e)}")

        # Define resource requests
        # Convert storage (GB) to memory (Mi)
        try:
            # Accept memory/storage as GB and convert to Mi for Kubernetes
            memory_gb = float(data["storage"])
            memory_mi = int(memory_gb * 1024)
        except (ValueError, TypeError):
            raise CustomError("Invalid value for storage. Must be a number representing GB.", 400)

        # Convert vCPU to millicores (Kubernetes expects CPU in millicores)
        try:
            cpu_cores = float(data["vcpu"])
            cpu_millicores = int(cpu_cores * 1000)
        except (ValueError, TypeError):
            raise CustomError("Invalid value for vcpu. Must be a number.", 400)

        # Convert memory to Mi (Mebibytes) and cpu to millicores (m)
        # If user provides memory as "1Gi", convert to Mi
        memory_value = data["storage"]
        if isinstance(memory_value, str) and memory_value.lower().endswith("gi"):
            try:
                memory_gi = float(memory_value[:-2])
                memory_mi = int(memory_gi * 1024)
            except Exception:
                raise CustomError("Invalid memory format. Use a number or 'Gi' suffix.", 400)
        else:
            try:
                memory_mi = int(float(memory_value) * 1024)  # Convert GB to Mi
            except Exception:
                raise CustomError("Invalid memory format. Use a number or 'Gi' suffix.", 400)

        cpu_value = data["vcpu"]
        try:
            cpu_millicores = int(float(cpu_value) * 1000)
        except Exception:
            raise CustomError("Invalid cpu format. Use a number.", 400)

        resources = client.V1ResourceRequirements(
            limits={
            "cpu": f"{cpu_millicores}m",
            "memory": f"{memory_mi}Mi",
            "nvidia.com/gpu": str(data["gpu"]) if data["gpu"] else "0"
            }
        )
        # Create or update the namespace
        data["vcpu"] = cpu_millicores
        data["storage"] = memory_mi
        
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=data["aiservice_name"], namespace=namespace),
            spec=client.V1DeploymentSpec(
            replicas=data["replicas"],
            selector={"matchLabels": {"app": data["aiservice_name"]}},
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": data["aiservice_name"]}),
                spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                    name=data["aiservice_name"],
                    image=f"{data['acr_name']}.azurecr.io/{data['image_name']}:{data['image_tag']}",
                    ports=[client.V1ContainerPort(container_port=8002)],
                    image_pull_policy="Always",
                    env=[
                        client.V1EnvVar(
                        name=key,
                        value_from=client.V1EnvVarSource(
                            config_map_key_ref=client.V1ConfigMapKeySelector(
                            name=config_map_name,
                            key=key
                            )
                        )
                        ) for key in config_map_data.keys()
                    ],
                    resources=resources
                    )
                ],
                image_pull_secrets=[client.V1LocalObjectReference(name="acr-image-pull-secret")],
                # node_selector=node_selector,  # Use the selected node
                # tolerations=[
                #     client.V1Toleration(
                #     key="CriticalAddonsOnly",
                #     operator="Exists",
                #     effect="NoSchedule"
                #     )
                # ]
                ),
            )
            ),
        )
        try:
            k8s_apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
            LoggerUtils.info(f"Deployment {data['aiservice_name']} created successfully.")
        except ApiException as e:
            if e.status == 409:
                LoggerUtils.info(f"Deployment {data['aiservice_name']} already exists, updating it.")
                k8s_apps_v1.patch_namespaced_deployment(name=data["aiservice_name"], namespace=namespace, body=deployment)
            else:
                raise CustomError(f"Failed to create/update deployment: {str(e)}")
 
        # Create or update service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=data["aiservice_name"], namespace=namespace),
            spec=client.V1ServiceSpec(
                selector={"app": data["aiservice_name"]},
                ports=[client.V1ServicePort(port=80, target_port=8002)],
                type="ClusterIP",
            ),
        )
 
        try:
            k8s_core_v1.create_namespaced_service(namespace=namespace, body=service)
            LoggerUtils.info(f"Service {data['aiservice_name']} created successfully.")
        except ApiException as e:
            if e.status == 409:
                LoggerUtils.info(f"Service {data['aiservice_name']} already exists, updating it.")
                k8s_core_v1.patch_namespaced_service(name=data["aiservice_name"], namespace=namespace, body=service)
            else:
                raise CustomError(f"Failed to create/update service: {str(e)}")
 
        # Create or update Ingress for path-based routing
        self.create_or_update_ingress(k8s_networking_v1,data)
        LoggerUtils.info(f"Kubernetes resources created successfully for {data['aiservice_name']}")
        return True
   
 
 
    def create_or_update_ingress(self,k8s_networking_v1,data):
        """Creates or updates the shared ingress for path-based routing."""
        ingress_name = data["aiservice_name"]
 
        try:
            # Check if the Ingress already exists
            existing_ingress = k8s_networking_v1.read_namespaced_ingress(name=ingress_name, namespace=data["aiservice_name"])
            LoggerUtils.info(f"Ingress {ingress_name} exists, updating it...")
 
            # Extract existing paths
            existing_paths = existing_ingress.spec.rules[0].http.paths if existing_ingress.spec.rules else []
 
            # Define new path
            new_path = client.V1HTTPIngressPath(
                path=f"/{data['aiservice_name']}".replace("//", "/"),  # Ensure no double slashes
                path_type="Prefix",
                backend=client.V1IngressBackend(
                    service=client.V1IngressServiceBackend(
                        name=data['aiservice_name'].replace("/", "-"),  # Ensure valid DNS-1035 label
                        port=client.V1ServiceBackendPort(number=80)  # Removed target port
                    )
                )
            )
            # Only add the path if it's not already there
            if not any(p.path == new_path.path for p in existing_paths):
                existing_paths.append(new_path)
 
                # **Update the spec with modified paths**
                existing_ingress.spec.rules[0].http.paths = existing_paths
 
                # Patch the Ingress with new paths
                k8s_networking_v1.patch_namespaced_ingress(
                    name=ingress_name, namespace=data["aiservice_name"], body=existing_ingress
                )
                LoggerUtils.info(f"Ingress {ingress_name} updated with new route /{data['route_name']}")
            else:
                LoggerUtils.info(f"Ingress {ingress_name} already has route /{data['route_name']}, no update needed.")
                return True          
        except ApiException as e:
            if e.status == 404:
                # Ingress does not exist, create a new one
                LoggerUtils.info(f"Ingress {ingress_name} not found, creating a new one.")
                ingress = client.V1Ingress(
                    metadata=client.V1ObjectMeta(
                        name=ingress_name,
                        namespace=data["aiservice_name"],
                        annotations= config.INGRESS_ANNOTATIONS
                    ),
                    spec=client.V1IngressSpec(
                        ingress_class_name="nginx",  # Corrected placement
                        rules=[client.V1IngressRule(
                            http=client.V1HTTPIngressRuleValue(
                                paths=[
                                    client.V1HTTPIngressPath(
                                        path=f"/{data['route_name']}".replace("//", "/"),
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=data["aiservice_name"],  # Removed replace logic
                                                port=client.V1ServiceBackendPort(number=80)  # Corrected port
                                            )
                                        )
                                    )
                                ]
                            )
                        )]
                    ),
                )
                k8s_networking_v1.create_namespaced_ingress(namespace=data["aiservice_name"], body=ingress)
                LoggerUtils.info(f"Ingress {ingress_name} created successfully with route /{data['route_name']}")
            else:
                LoggerUtils.error(f"Failed to create or update ingress: {e}")
                raise CustomError(f"Failed to create or update ingress: {e}")
    def cleanup_kubernetes_resources(self, kubeconfig_path, data):
        """Cleans up Kubernetes resources."""
        LoggerUtils.info("Cleaning up Kubernetes resources")
        # Load Kubernetes configuration
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
        k8s_apps_v1 = client.AppsV1Api()
        k8s_networking_v1 = client.NetworkingV1Api()

        try:
            # Delete the ingress if it exists
            failed_cleanup_msg = "Failed to clean up Kubernetes resources."
            try:

                k8s_networking_v1.delete_namespaced_ingress(
                    name=data["aiservice_name"], namespace=data["aiservice_name"]
                )
                LoggerUtils.info(f"Ingress {data['aiservice_name']} deleted successfully.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.info(f"Ingress {data['aiservice_name']} not found, skipping deletion.")
                else:
                    raise CustomError(failed_cleanup_msg)

            # Delete the service if it exists
            try:
                k8s_core_v1.delete_namespaced_service(
                    name=data["aiservice_name"], namespace=data["aiservice_name"]
                )
                LoggerUtils.info(f"Service {data['aiservice_name']} deleted successfully.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.info(f"Service {data['aiservice_name']} not found, skipping deletion.")
                else:
                    raise CustomError(failed_cleanup_msg)

            # Delete the deployment if it exists
            try:

                k8s_apps_v1.delete_namespaced_deployment(
                    name=data["aiservice_name"], namespace=data["aiservice_name"]
                )
                k8s_core_v1.delete_namespace(
                    name=data["aiservice_name"]
                )
                LoggerUtils.info(f"Deployment {data['aiservice_name']} deleted successfully.")
            except ApiException as e:
                if e.status == 404:
                    LoggerUtils.info(f"Deployment {data['aiservice_name']} not found, skipping deletion.")
                else:
                    LoggerUtils.error(f"{failed_cleanup_msg}: {str(e)}")
                    raise CustomError(failed_cleanup_msg)

            # Delete any pods if necessary
            for pod in k8s_core_v1.list_namespaced_pod(
                namespace=data["aiservice_name"], label_selector=f"app={data['aiservice_name']}"
            ).items:
                try:
                    k8s_core_v1.delete_namespaced_pod(
                        name=pod.metadata.name, namespace=data["aiservice_name"]
                    )
                    LoggerUtils.info(f"Pod {pod.metadata.name} deleted successfully.")
                except ApiException as e:
                    if e.status == 404:
                        LoggerUtils.info(f"Pod {pod.metadata.name} not found, skipping deletion.")
                    else:
                        LoggerUtils.error(f"{failed_cleanup_msg}: {str(e)}")
                        raise CustomError(failed_cleanup_msg)

        except Exception as e:
            failed_cleanup_msg = "Failed to clean up Kubernetes resources."
            LoggerUtils.error(f"{failed_cleanup_msg}: {str(e)}")
            raise CustomError(failed_cleanup_msg)

    def check_pod_status(
        self,
        k8s_core_v1,
        aiservice_name,
        data,
        kubeconfig_path,
        timeout=500,
    ):
        """Checks the status of the pod."""
        LoggerUtils.info("Checking pod status")
        start_time = time.time()
        while time.time() - start_time < timeout:
            pods = k8s_core_v1.list_namespaced_pod(
                namespace=data["aiservice_name"], label_selector=f"app={aiservice_name}"
            )
            LoggerUtils.info(f"Pods for deployment {data['aiservice_name']} found")
            for pod in pods.items:
                pod_status = pod.status.phase
                if pod_status == "Running":
                    LoggerUtils.info(f"Pod {pod.metadata.name} is running")
                    return True  # Pod is running, no issues
                elif pod_status in [
                    "Failed",
                    "Unknown",
                    "Pending",
                    "Error",
                    "ImagePullBackOff",
                    "crashloopbackoff",
                    "ErrImagePull",
                    "createcontainerconfigerror",
                ]:
                    pod_logs = k8s_core_v1.read_namespaced_pod_log(
                        name=pod.metadata.name, namespace=data["aiservice_name"]
                    )
 
                    # If the pod fails, clean up the resources and raise an error
                    self.cleanup_kubernetes_resources(kubeconfig_path, data)
                    LoggerUtils.error(f"Pod {pod.metadata.name} failed. Logs: {pod_logs}")
                    raise CustomError(f"Pod {pod.metadata.name} failed. Logs: {pod_logs}")
            time.sleep(100)  # Wait for 50 seconds before retrying
 
        # If timeout is reached and pod hasn't started running, clean up resources
        self.cleanup_kubernetes_resources(kubeconfig_path, data)
        LoggerUtils.error(
            f"Timeout: Pods for deployment {data['aiservice_name']} failed to start within {timeout} seconds."
        )
        raise CustomError(
            f"Timeout: Pods for deployment {data['aiservice_name']} failed to start within {timeout} seconds."
        )
    def check_container_status(self, data, kubeconfig_path):
        """Checks the status of the containers within the pod."""
        # Load the kubeconfig file to connect to the Kubernetes cluster
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
 
        pod_logs = []
        try:
            # List pods in the specified namespace with the label selector for the deployment
            LoggerUtils.info(f"Checking container status for deployment {data['aiservice_name']}")
            pods = k8s_core_v1.list_namespaced_pod(
                namespace=data["aiservice_name"],
                label_selector=f"app={data['aiservice_name']}",
            )
            cleanup_msg = "Cleanup completed"
            # Check if there are any pods
            if not pods.items:
                LoggerUtils.error(f"No pods found for deployment {data['aiservice_name']}.")
                raise CustomError(f"No pods found for deployment {data['aiservice_name']}.")
 
            # Iterate over the pods and check the status of containers in each pod
            for pod in pods.items:
                pod_status = pod.status.phase
                if pod_status == "Running":
                    LoggerUtils.info(f"Pod {pod.metadata.name} is running")
                    # Fetch the last 2 minutes of logs from the running pod
                    pod_logs = k8s_core_v1.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=data["aiservice_name"],
                        since_seconds=120  # Last 2 minutes
                    )
                    LoggerUtils.info(f"pod running logs for {pod.metadata.name}:\n{pod_logs}")
                    # Check the container status within the running pod
                    for container_status in pod.status.container_statuses:
                        if container_status.state.waiting:
                            # If the container is waiting or has failed, log the reason and retrieve logs
                            waiting_reason = container_status.state.waiting.reason
                            LoggerUtils.error(f"Container {container_status.name} in pod {pod.metadata.name} is waiting. Reason: {waiting_reason}.")
                            pod_logs = k8s_core_v1.read_namespaced_pod_log(
                                name=pod.metadata.name,
                                namespace=data["aiservice_name"],
                                follow=True,  # Enable live streaming
                            )
                            LoggerUtils.error(f"Live logs for {pod.metadata.name}:\n{pod_logs}")
                            self.cleanup_kubernetes_resources(kubeconfig_path, data)
                            LoggerUtils.info(cleanup_msg)
                            raise CustomError(f"Container {container_status.name} in pod {pod.metadata.name} is waiting. Logs:\n{pod_logs}")
                       
                        elif container_status.state.terminated:
                            # If the container is terminated, check the reason for termination and retrieve logs
                            termination_reason = container_status.state.terminated.reason
                            if termination_reason in ["Error", "OOMKilled", "CrashLoopBackOff","ImagePullBackOff","CrashLoopBackOff"]:
                                LoggerUtils.error(f"Container {container_status.name} in pod {pod.metadata.name} terminated. Reason: {termination_reason}.")
                                pod_logs = k8s_core_v1.read_namespaced_pod_log(
                                    name=pod.metadata.name,
                                    namespace=data["aiservice_name"],
                                    follow=True,  # Enable live streaming
                                )
                                LoggerUtils.error(f"Live logs for {pod.metadata.name}:\n{pod_logs}")
                                self.cleanup_kubernetes_resources(kubeconfig_path, data)
                                LoggerUtils.info(cleanup_msg)
                                raise CustomError(f"Container {container_status.name} in pod {pod.metadata.name} failed. Logs:\n{pod_logs}")
                    # If the pod's containers are running fine, return the pod
                    return pod
 
                elif pod_status in ["Failed", "Unknown", "Pending", "Error",]:
                    # If the pod itself is in a bad state, log details, retrieve logs, and clean up
                    LoggerUtils.error(f"Pod {pod.metadata.name} is in a failed state. Pod status is {pod_status}.")
                    pod_logs = k8s_core_v1.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=data["aiservice_name"],
                        follow=True,  # Enable live streaming
                    )
                    LoggerUtils.error(f"Live logs for {pod.metadata.name}:\n{pod_logs}")
                    self.cleanup_kubernetes_resources(kubeconfig_path, data)
                    LoggerUtils.info(cleanup_msg)
                    raise CustomError(f"Pod {pod.metadata.name} is in a failed state. Logs:\n{pod_logs}")
 
            # If no issues, return the list of pods
            return pods
        except Exception:
            LoggerUtils.error(f"image has been crashed or corrupted Logs:\n{pod_logs}")
            # In case of any error, clean up the resources and return the error
            self.cleanup_kubernetes_resources(kubeconfig_path, data)
            LoggerUtils.info("Cleanup completed successfully")
            if not pod_logs:
                LoggerUtils.error("Pod logs are empty. No logs available during this time.")
                raise CustomError("Image has been crashed. No logs available during this time.")
            raise CustomError(f"Image has been crashed or corrupted. Reason: Logs:\n{pod_logs}")
        
    def get_external_ip_and_host(self, data, kubeconfig_path):
        """Gets the external IP and host for the nginx load balancer."""
        LoggerUtils.debug("get External IP and Host")
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
 
        # Wait for the nginx load balancer to get an external IP
        external_ip = None
        for _ in range(60):
            LoggerUtils.info("Checking external IP for service ingress-nginx-controller")
            services = k8s_core_v1.list_namespaced_service(namespace = "ingress-nginx")
            for service in services.items:
                if service.metadata.name == "ingress-nginx-controller" and service.status.load_balancer.ingress:
                    external_ip = service.status.load_balancer.ingress[0].ip
                    return {"external_ip": external_ip, "route": f"{data['route_name']}"}
            time.sleep(5)
 
        if not external_ip:
            LoggerUtils.error("Failed to retrieve external IP for the nginx load balancer and initiated cleaning the resources")
            self.cleanup_kubernetes_resources(kubeconfig_path, data)
            raise CustomError("Failed to retrieve external IP for the nginx load balancer and resources have been cleaned successfully.")
   

    # Main execution method
    def execute(self):
        data = request.get_json()
        self.validate_input_data(data)
        # self.check_image_exists(data)
        server_details = self.fetch_server_details(data)
        server_config = server_details.get("server_config", {})
        machine_ip = server_config.get("machine_ip")
        username = server_config.get("username")
        password = server_config.get("password")
        data["server_id"] = server_details.get("server_id")
        if not machine_ip or not username or not password:
            raise CustomError("Server configuration is incomplete", 400)
        pod_id_row = self.insert_pod_details(data)
        kubeconfig_path = self.get_kubeconfig(machine_ip, username, password)
        self.get_cluster_resource_summary(data,kubeconfig_path)
        data["aiservice_name"] = data["pod_name"]
        self.create_image_pull_secret(kubeconfig_path, data)
        self.create_kubernetes_resources(kubeconfig_path, data)
        configs.load_kube_config(config_file=kubeconfig_path)
        k8s_core_v1 = client.CoreV1Api()
        client.AppsV1Api()
        client.NetworkingV1Api()
        LoggerUtils.info("Waiting for the pods to start running")
        time.sleep(200)
        self.check_container_status(data, kubeconfig_path).status.phase
        LoggerUtils.info("Container status checked successfully")
        self.check_pod_status(
            k8s_core_v1,
            data["aiservice_name"],
            data,
            kubeconfig_path,
        )
        LoggerUtils.info("Pods are running successfully")
        message = f"{machine_ip}/{data['route_name']}"
        LoggerUtils.info(f"Machine IP: {machine_ip}")
        try:
            # result = self.get_external_ip_and_host(data, kubeconfig_path)
            # message = f"{result['external_ip']}{result['route']}"
           # Extract pod_id from the returned row (adjust key as needed)
            pod_id = pod_id_row["pod_id"] if isinstance(pod_id_row, dict) and "pod_id" in pod_id_row else pod_id_row[0] if hasattr(pod_id_row, "__getitem__") else pod_id_row
            self.update_pod_details(pod_ip = message,pod_id = pod_id)
            LoggerUtils.info("External IP and Host retrieved successfully")
            return {"message": message, "status": "success","data": data}
        except Exception as e:
            LoggerUtils.error(f"Error in kubeneter_resource_deploy: {str(e)}")
            self.update_pod_details(pod_id)
            self.cleanup_kubernetes_resources(kubeconfig_path, data)
            raise CustomError(f"Error in kubeneter_resource_deploy: {str(e)}")
        finally:
            os.remove(kubeconfig_path)
            LoggerUtils.info("Kubeconfig removed successfully.")
      


        
        

    
       