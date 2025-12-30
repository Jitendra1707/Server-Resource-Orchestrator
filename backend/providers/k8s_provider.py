from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
import uuid

class K8sProvider:
    """Interacts with Kubernetes clusters."""

    def __init__(self, kubeconfig_data=None):
        if kubeconfig_data:
            # For remote servers, we'd load from dict, but for V2 initial setup
            # we'll assume local kubeconfig if data is None
            k8s_config.load_kube_config_from_dict(kubeconfig_data)
        else:
            try:
                k8s_config.load_kube_config()
            except:
                # Fallback or error handled at higher level
                pass
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.networking_v1 = client.NetworkingV1Api()
    def _ensure_initialized(self):
        if not hasattr(self, 'core_v1') or not self.core_v1:
            try:
                self.core_v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                self.networking_v1 = client.NetworkingV1Api()
            except Exception as e:
                raise Exception(f"K8s client not initialized: {e}")

    def create_service(self, namespace, app_name, port=80):
        """Creates a ClusterIP service for the app."""
        try:
            service = client.V1Service(
                metadata=client.V1ObjectMeta(name=app_name),
                spec=client.V1ServiceSpec(
                    selector={"app": app_name},
                    ports=[client.V1ServicePort(port=port, target_port=80, protocol="TCP")],
                    type="ClusterIP"
                )
            )
            self.core_v1.create_namespaced_service(namespace=namespace, body=service)
            print(f"Service {app_name} created in {namespace}.")
            return True
        except ApiException as e:
            if e.status == 409: # Already exists
                print(f"Service {app_name} already exists.")
                return True
            print(f"Failed to create service: {e}")
            raise

    def create_ingress(self, namespace, app_name, service_name, path):
        """Creates an Ingress resource."""
        try:
            path_obj = client.V1HTTPIngressPath(
                path=path,
                path_type="Prefix",
                backend=client.V1IngressBackend(
                    service=client.V1IngressServiceBackend(
                        name=service_name,
                        port=client.V1ServiceBackendPort(number=80)
                    )
                )
            )
            
            rule = client.V1IngressRule(
                http=client.V1HTTPIngressRuleValue(paths=[path_obj])
            )
            
            ingress = client.V1Ingress(
                metadata=client.V1ObjectMeta(
                    name=app_name, 
                    annotations={"nginx.ingress.kubernetes.io/rewrite-target": "/"}
                ),
                spec=client.V1IngressSpec(
                    ingress_class_name="nginx",
                    rules=[rule]
                )
            )
            
            self.networking_v1.create_namespaced_ingress(namespace=namespace, body=ingress)
            print(f"Ingress {app_name} created for path {path}.")
            return True
        except ApiException as e:
            if e.status == 409:
                print(f"Ingress {app_name} already exists.")
                return True
            print(f"Failed to create ingress: {e}")
            raise

    def create_pod(self, pod_data):
        """Create multiple pod replicas in a dynamic namespace (from payload or default to 'default')."""
        self._ensure_initialized()
        print(f"Creating pod with data: {pod_data}")
        try:
            import uuid
            import time

            base_name = pod_data.get("pod_id") or f"deployment-{uuid.uuid4().hex[:8]}"
            resources = pod_data.get("requested", {}) or {}
            image_url = pod_data.get("image_url", "nginx:latest")
            namespace = pod_data.get("namespace") or "default"
            replicas = pod_data.get("replicas", 1)

            # Ensure namespace exists (skip default)
            if namespace != "default":
                try:
                    self.core_v1.read_namespace(namespace)
                except Exception:
                    ns_body = client.V1Namespace(
                        metadata=client.V1ObjectMeta(name=namespace)
                    )
                    self.core_v1.create_namespace(ns_body)

            # Build resource requests
            resource_requests = {}
            if resources.get("cpus", 0):
                resource_requests["cpu"] = str(resources.get("cpus", 1))
            if resources.get("ram_gb", 0):
                resource_requests["memory"] = f"{resources.get('ram_gb', 1)}Gi"
            if resources.get("storage_gb", 0):
                resource_requests["ephemeral-storage"] = (
                    f"{resources.get('storage_gb', 1)}Gi"
                )

            resource_requirements = None
            if resource_requests:
                resource_requirements = client.V1ResourceRequirements(
                    requests=resource_requests
                )

            # Define container
            container = client.V1Container(name=base_name, image=image_url)
            if resource_requirements:
                container.resources = resource_requirements

            # Pod template
            pod_template_spec = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": base_name}),
                spec=client.V1PodSpec(containers=[container]),
            )

            # Deployment spec & metadata
            deployment_spec = client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels={"app": base_name}),
                template=pod_template_spec,
            )
            deployment_metadata = client.V1ObjectMeta(
                name=base_name, labels={"app": base_name}
            )
            deployment = client.V1Deployment(
                metadata=deployment_metadata, spec=deployment_spec
            )

            # Create deployment
            self.apps_v1.create_namespaced_deployment(
                namespace=namespace, body=deployment
            )

            # Ingress / Route Support
            route_path = pod_data.get("route")
            ingress_details = {"status": "skipped"}
            
            if route_path:
                try:
                    print(f"Debug: Creating service/ingress for {base_name} at {route_path} in {namespace}")
                    self.create_service(namespace, base_name)
                    self.create_ingress(namespace, base_name, base_name, route_path)
                    ingress_details = {"status": "created", "route": route_path}
                except Exception as e:
                    print(f"Warning: Failed to create ingress/service: {e}")
                    ingress_details = {"status": "failed", "error": str(e)}

            # Wait for at least one pod to become ready
            timeout = 60  # seconds
            start = time.time()
            ready_pod = None
            label_selector = f"app={base_name}"
            while time.time() - start < timeout:
                try:
                    pods_resp = self.core_v1.list_namespaced_pod(
                        namespace=namespace, label_selector=label_selector
                    )
                except Exception:
                    pods_resp = None

                if pods_resp and pods_resp.items:
                    for pod in pods_resp.items:
                        if pod.status and pod.status.phase == "Running":
                            container_statuses = pod.status.container_statuses or []
                            if container_statuses and all(
                                cs.ready for cs in container_statuses
                            ):
                                ready_pod = pod
                                break
                    if ready_pod:
                        break
                time.sleep(2)

            if not ready_pod:
                return {
                    "status": "error",
                    "message": f"Deployment {base_name} created but no pod became ready within {timeout}s",
                    "deployment_name": base_name,
                    "replicas": replicas,
                    "ingress": ingress_details
                }

            # Resolve pod_ip and external_ip (prefer node ExternalIP if available)
            pod_ip = (
                ready_pod.status.pod_ip
                if ready_pod.status and ready_pod.status.pod_ip
                else None
            )
            external_ip = pod_ip  # fallback

            node_name = ready_pod.spec.node_name
            if node_name:
                try:
                    node_obj = self.core_v1.read_node(node_name)
                    for addr in node_obj.status.addresses or []:
                        if addr.type == "ExternalIP":
                            external_ip = addr.address
                            break
                except Exception:
                    pass  # ignore, keep fallback

            # If ingress was created, resolve Ingress IP/Hostname
            if route_path and ingress_details.get("status") == "created":
                print(f"Waiting for ingress IP for {base_name}...")
                ingress_timeout = 60
                istart = time.time()
                while time.time() - istart < ingress_timeout:
                    try:
                        ing = self.networking_v1.read_namespaced_ingress(base_name, namespace)
                        if ing.status and ing.status.load_balancer and ing.status.load_balancer.ingress:
                            ing_entry = ing.status.load_balancer.ingress[0]
                            ing_ip = ing_entry.ip or ing_entry.hostname
                            if ing_ip:
                                external_ip = ing_ip
                                ingress_details["ingress_ip"] = ing_ip
                                break
                    except Exception:
                        pass
                    time.sleep(2)

            return {
                "status": "success",
                "message": f"Deployment {base_name} created with {replicas} replicas in namespace {namespace}",
                "deployment_name": base_name,
                "replicas": replicas,
                "pod_ip": pod_ip,
                "external_ip": external_ip,
                "ingress": ingress_details
            }

        except ApiException as e:
            return {"status": "error", "message": f"Kubernetes API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to create pod: {e}"}

    def get_logs(self, namespace, deployment_name, tail_lines=100):
        """Fetches logs for the first pod found in the deployment."""
        self._ensure_initialized()
        try:
            # Find pods for this deployment
            label_selector = f"app={deployment_name}"
            pods = self.core_v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
            
            if not pods.items:
                return f"No pods found for deployment {deployment_name} in {namespace}."

            # Use the first pod (usually only one if replicas=1)
            pod_name = pods.items[0].metadata.name
            return self.core_v1.read_namespaced_pod_log(
                name=pod_name, 
                namespace=namespace, 
                tail_lines=tail_lines
            )
        except Exception as e:
            return f"Error fetching logs: {str(e)}"


    def _get_pod_events(self, namespace, pod_name):
        try:
            events = self.core_v1.list_namespaced_event(
                namespace=namespace, 
                field_selector=f"involvedObject.name={pod_name},involvedObject.kind=Pod"
            )
            event_list = []
            for e in events.items:
                event_list.append(f"[{e.type}] {e.reason}: {e.message}")
            return event_list
        except Exception:
            return []

    def update_deployment_image(self, namespace, deployment_name, new_image, timeout=300):
        """Updates the deployment image and waits for rollout."""
        self._ensure_initialized()
        try:
            # Patch the deployment
            patch_body = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": deployment_name, 
                                    "image": new_image
                                }
                            ]
                        }
                    }
                }
            }
            
            print(f"Patching deployment {deployment_name} in {namespace} with image {new_image}...")
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch_body
            )
            
            # Wait for Rollout
            import time
            start = time.time()
            while time.time() - start < timeout:
                try:
                    dep = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)
                    
                    # specific rollout logic:
                    # 1. observedGeneration >= generation
                    # 2. updatedReplicas == replicas
                    # 3. availableReplicas == replicas
                    
                    replicas = dep.spec.replicas or 1
                    status = dep.status
                    
                    if (status.observed_generation >= dep.metadata.generation and
                        status.updated_replicas == replicas and
                        status.available_replicas == replicas):
                        
                        return {
                            "status": "success",
                            "message": f"Deployment updated to {new_image}",
                            "image": new_image
                        }
                except:
                    pass
                        
                time.sleep(2)
                
            return {"status": "error", "message": f"Timeout waiting for update rollout of {deployment_name}"}

        except ApiException as e:
            return {"status": "error", "message": f"Kubernetes API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to update deployment: {e}"}

    def delete_pod(self, namespace, pod_name):
        """Deletes the deployment and optionally the namespace."""
        try:
            # Delete deployment
            self.apps_v1.delete_namespaced_deployment(name=pod_name, namespace=namespace)
            # Delete namespace (standard V2 isolation strategy)
            self.core_v1.delete_namespace(name=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise
