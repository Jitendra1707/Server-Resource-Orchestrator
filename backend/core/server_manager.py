import json
import os
import time
import threading
import uuid
import uuid
import subprocess
import json as py_json
from threading import RLock as Lock
from typing import Dict, Optional, List
from providers.k8s_provider import K8sProvider
from datetime import datetime

class ScanManager:
    """Manages background Trivy scans and their logs."""
    def __init__(self):
        self.scans = {}
        self.lock = threading.Lock()

    def create_scan(self, image_url):
        scan_id = str(uuid.uuid4())
        with self.lock:
            self.scans[scan_id] = {
                "id": scan_id,
                "image": image_url,
                "status": "running",
                "logs": [],
                "result": None,
                "start_time": datetime.now().isoformat()
            }
        return scan_id

    def add_log(self, scan_id, log_line):
        with self.lock:
            if scan_id in self.scans:
                self.scans[scan_id]["logs"].append(log_line)

    def complete_scan(self, scan_id, result, status="success"):
        with self.lock:
            if scan_id in self.scans:
                self.scans[scan_id]["status"] = status
                self.scans[scan_id]["result"] = result
                self.scans[scan_id]["end_time"] = datetime.now().isoformat()

    def get_scan(self, scan_id):
        with self.lock:
            return self.scans.get(scan_id)

class ServerManager:
    """Manages the server state and persistence in master.json."""
    
    def __init__(self, config_path):
        self.config_path = config_path
        self.lock = Lock()
        self.server_providers = {}
        self.scan_manager = ScanManager()
        self.reload_config()

    def reload_config(self):
        """Loads config and initializes providers."""
        with self.lock:
            if not os.path.exists(self.config_path):
                self.config = {"servers": [], "config": {}}
                return
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

            # Initialize providers
            self.server_providers = {}
            for server in self.config.get("servers", []):
                server_id = server.get("id")
                kubeconfig = server.get('connection_coordinates', {}).get('kubeconfig_data')
                
                # Only init provider if we have kubeconfig
                if kubeconfig:
                    try:
                        self.server_providers[server_id] = {
                            "provider": K8sProvider(kubeconfig),
                            "last_updated": datetime.now()
                        }
                    except Exception as e:
                        print(f"Failed to init provider for {server_id}: {e}")

    def _save_config(self):
        with self.lock:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)

    def get_all_servers(self):
        """Returns all configured servers."""
        self.reload_config()
        return self.config.get("servers", [])

    def get_server_by_id(self, server_id):
        """Finds a server by its ID."""
        for server in self.config.get("servers", []):
            if server["id"] == server_id:
                return server
        return None

    def get_pods_for_server(self, server_id):
        """Returns list of pods for a specific server."""
        self.reload_config()
        server = self.get_server_by_id(server_id)
        return server.get("pods", []) if server else []

    def update_server_status(self, server_id, status):
        """Updates the online/offline status of a server."""
        for server in self.config.get("servers", []):
            if server["id"] == server_id:
                server["status"] = status
                self._save_config()
                return True
        return False

    def validation_steps(self, pod_data: Dict) -> Dict:
        """Validates and prepares the pod object."""
        # 1. Basic Fields
        pod_id = pod_data.get('pod_id') or pod_data.get('pod_name')
        if not pod_id:
            pod_id = f"pod-{uuid.uuid4().hex[:8]}"
        
        # 2. Resources
        # Support both 'resources' dict and direct keys if needed, or stick to schema
        # Incoming might be {'resources': {'cpus': 1...}} or flat
        raw_resources = pod_data.get('resources', {})
        if not raw_resources and 'requested' in pod_data: # Handle 'requested' key if passed
             raw_resources = pod_data['requested']

        cpus = float(raw_resources.get('cpus', 0.1))
        ram_gb = float(raw_resources.get('ram_gb', 0.1))
        storage_gb = float(raw_resources.get('storage_gb', 0.1))

        # 3. Image
        image_url = pod_data.get('image_url') or pod_data.get('image') or 'nginx:latest'

        # 4. Construct internal pod object
        pod_object = {
            "pod_id": pod_id,
            "name": pod_id, # Display name same as ID for now
            "namespace": pod_data.get('namespace') or pod_id,
            "image_url": image_url,
            "replicas": pod_data.get('replicas', 1),
            "route": pod_data.get('route'),
            "requested": {
                "cpus": cpus,
                "ram_gb": ram_gb,
                "storage_gb": storage_gb
            },
            "status": "provisioning", # Initial status
            "timestamp": datetime.now().isoformat()
        }
        
        return pod_object

    def create_pod(self, server_id: str, pod_data: Dict) -> Dict:
        """Create a pod on the specified server."""
        try:
            pod_object = self.validation_steps(pod_data)
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}

        # Check server existence in config first
        server = self.get_server_by_id(server_id)
        if not server:
            return {"error": f"Server {server_id} not found in config"}

        # Resource Availability Check (Soft check before trying provider)
        # Note: This checks local 'bookkeeping' availability, K8s might still reject if node full
        available = server.get('resources', {}).get('available', {})
        requested = pod_object['requested']
        if (requested['cpus'] > available.get('cpus', 0) or 
            requested['ram_gb'] > available.get('ram_gb', 0)):
             return {"error": "Insufficient resources (bookkeeping check)"}

        if server_id not in self.server_providers:
            self.reload_config()
            if server_id not in self.server_providers:
                return {"error": f"Server {server_id} provider not initialized (missing kubeconfig?)"}

        try:
            provider_wrapper = self.server_providers[server_id]
            provider = provider_wrapper["provider"]
            
            # Call provider
            # Note: pod_object matches the clean structure expected by K8sProvider.create_pod
            result = provider.create_pod(pod_object)
            
            # Synchonous Pod Sync
            if result.get('status') == 'success':
                 try:
                     time.sleep(2)
                 except: pass # safe sleep
                 
            # Always update master.json, even on timeout/error, so the user sees the pod state
            try:
                self.update_pod_object(server_id, pod_object, creation_result=result)
            except Exception as e:
                print(f"Failed to update pod object: {e}")

            return result
        except Exception as e:
            return {"error": f"Failed to create pod: {e}"}

    def update_pod_object(self, server_id, pod_object, creation_result):
        """Updates master.json with the new pod and deducts resources."""
        with self.lock:
            self.reload_config() # Refresh state (reload_config is safe with RLock)
            for server in self.config.get("servers", []):
                if server["id"] == server_id:
                    # Enrich pod object with result details
                    # If provider explicitly reports error (e.g. timeout), set status to error
                    if creation_result.get('status') == 'error':
                         pod_object['status'] = 'error'
                    else:
                         pod_object['status'] = 'running' if creation_result.get('pod_ip') else 'error'
                    
                    pod_object['pod_ip'] = creation_result.get('pod_ip')
                    pod_object['external_ip'] = creation_result.get('external_ip')
                    # Store error message if present for debugging? (Schema might not have it, but useful to have)
                     # pod_object['error_message'] = creation_result.get('message') # Optional enhancement
                    
                    server["pods"].append(pod_object)
                    
                    # Deduct resources
                    req = pod_object["requested"]
                    avail = server["resources"]["available"]
                    alloc = server["resources"]["allocated"]
                    
                    for k in ["cpus", "ram_gb", "storage_gb"]:
                        val = req.get(k, 0)
                        if k in avail: avail[k] = max(0, avail[k] - val)
                        if k in alloc: alloc[k] += val
            
            self._save_config()

    def update_pod(self, server_id: str, pod_id: str, image_url: str) -> Dict:
        """Updates a pod's image using rolling update strategy."""
        
        server = self.get_server_by_id(server_id)
        if not server:
            return {"error": "Server not found"}

        # Find pod
        target_pod = None
        for pod in server.get('pods', []):
            if pod['pod_id'] == pod_id:
                target_pod = pod
                break
        
        if not target_pod:
            return {"error": "Pod not found on server"}
            
        namespace = target_pod.get('namespace', pod_id) # Default to pod_id if missing in dict

        if server_id not in self.server_providers:
            self.reload_config()
            if server_id not in self.server_providers:
                return {"error": "Provider not initialized for server"}

        try:
            provider = self.server_providers[server_id]["provider"]
            result = provider.update_deployment_image(namespace, pod_id, image_url)
            
            if result.get("status") == "success":
                # Update master.json persistence
                with self.lock:
                    self.reload_config() # Refresh
                    # Need to refetch reference in case config changed
                    for s in self.config.get("servers", []):
                        if s["id"] == server_id:
                            for p in s["pods"]:
                                if p["pod_id"] == pod_id:
                                    p["image_url"] = image_url
                                    p["timestamp"] = datetime.now().isoformat()
                                    p["status"] = "running" # Ensure running
                                    p["last_updated"] = datetime.now().isoformat()
                                    break
                    self._save_config()
                    
            return result
        except Exception as e:
            return {"error": f"Failed to update pod: {e}"}
            
    def delete_pod(self, server_id, pod_id):
        """Deletes a pod from the specified server and updates master.json."""
        
        server = self.get_server_by_id(server_id)
        if not server:
            return {"error": "Server not found"}

        # Find pod namespace
        namespace = pod_id
        pod_found = False
        for pod in server.get('pods', []):
            if pod['pod_id'] == pod_id:
                namespace = pod.get('namespace', 'default')
                pod_found = True
                break
        
        if not pod_found:
            return {"error": "Pod not found in master.json"}

        if server_id not in self.server_providers:
            self.reload_config()
            
        try:
            if server_id in self.server_providers:
                 provider = self.server_providers[server_id]["provider"]
                 # Note: K8sProvider.delete_pod args: (namespace, pod_name)
                 # current pod_id in new logic is the name of deployment
                 provider.delete_pod(namespace, pod_id)
            else:
                 print(f"Warning: No provider for {server_id}, skipping K8s deletion, only cleaning DB.")

            # Update master.json (Remove and Restore resources)
            self._remove_pod_from_server_internal(server_id, pod_id)
            
            return {"message": "Pod deleted successfully"}
        except Exception as e:
             # Even if K8s fails, we might want to clean up our DB? 
             # For now, return error
            return {"error": str(e)}

    def _remove_pod_from_server_internal(self, server_id, pod_id):
        """Internal method to remove a pod and restore resources."""
        with self.lock:
            # Reload config
            self.reload_config() # Uses the reloaded config from 'update_pod_object' logic effectively
            for server in self.config.get("servers", []):
                if server["id"] == server_id:
                    pod_to_remove = None
                    for pod in server["pods"]:
                        if pod["pod_id"] == pod_id:
                            pod_to_remove = pod
                            break
                    
                    if pod_to_remove:
                        server["pods"].remove(pod_to_remove)
                        # Restore resources
                        requested = pod_to_remove.get("requested", {})
                        avail = server["resources"]["available"]
                        alloc = server["resources"]["allocated"]
                        
                        for k in ["cpus", "ram_gb", "storage_gb"]:
                            val = requested.get(k, 0)
                            if k in avail: avail[k] += val
                            if k in alloc: alloc[k] = max(0, alloc[k] - val)

                        self._save_config()
                        return True
            return False

    def get_pod_logs(self, server_id, pod_id):
        """Fetches logs for a pod on a specific server."""
        self.reload_config()
        server = self.get_server_by_id(server_id)
        if not server:
            return "Server not found"

        # Find pod to get namespace
        # Default to pod_id if not found, but we check master.json first
        namespace = pod_id
        for pod in server.get('pods', []):
            if pod['pod_id'] == pod_id:
                namespace = pod.get('namespace', pod_id)
                break

        if server_id not in self.server_providers:
            return "Provider not initialized for this server"

        provider = self.server_providers[server_id]["provider"]
        return provider.get_logs(namespace, pod_id)

    def scan_pod_image(self, server_id, pod_id):
        """Initiates a background security scan on a pod's image."""
        self.reload_config()
        server = self.get_server_by_id(server_id)
        if not server:
            return {"status": "error", "message": "Server not found"}

        image_url = None
        for pod in server.get('pods', []):
            if pod['pod_id'] == pod_id:
                image_url = pod.get('image_url')
                break

        if not image_url:
            return {"status": "error", "message": "Pod or Image URL not found"}

        scan_id = self.scan_manager.create_scan(image_url)
        
        # Start background thread
        thread = threading.Thread(target=self._run_trivy_scan, args=(scan_id, image_url))
        thread.daemon = True
        thread.start()

        return {"status": "accepted", "scan_id": scan_id}

    def _run_trivy_scan(self, scan_id, image_url):
        """Background worker to run Trivy and capture logs."""
        
        try:
            self.scan_manager.add_log(scan_id, f"Scanning {image_url} (this context may take a minute)...")
            
            # Use one Popen call. Remove --quiet to get logs, but use --no-progress to keep logs clean.
            cmd = [
                "trivy", "image", 
                "--format", "json", 
                "--no-progress", 
                "--skip-version-check",
                image_url
            ]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                bufsize=1, # Line buffered
                universal_newlines=True
            )
            
            stderr_lines = []
            stdout_data = []

            # Stream stderr to logs in real-time
            def stream_stderr():
                for line in process.stderr:
                    clean_line = line.strip()
                    if clean_line:
                        self.scan_manager.add_log(scan_id, clean_line)
                        stderr_lines.append(clean_line)

            stderr_thread = threading.Thread(target=stream_stderr)
            stderr_thread.start()
            
            # Read stdout
            stdout_content = process.stdout.read()
            process.wait()
            stderr_thread.join()

            if process.returncode != 0:
                # Capture more context from stderr on failure
                error_details = "\n".join(stderr_lines[-100:])
                self.scan_manager.complete_scan(scan_id, {"error": f"Trivy exited with code {process.returncode}. Details: {error_details}"}, status="error")
                return

            if not stdout_content.strip():
                self.scan_manager.complete_scan(scan_id, {"error": "Trivy returned empty output"}, status="error")
                return

            try:
                # Some versions of trivy might output notices to stdout even with --format json
                # We try to find the start of the JSON object/array
                start_idx = stdout_content.find('{')
                if start_idx == -1:
                    start_idx = stdout_content.find('[')
                
                if start_idx != -1:
                    json_str = stdout_content[start_idx:]
                    scan_data = py_json.loads(json_str)
                else:
                    scan_data = py_json.loads(stdout_content)
            except Exception as e:
                self.scan_manager.complete_scan(scan_id, {"error": f"Failed to parse Trivy output: {str(e)}"}, status="error")
                return
            
            # Aggregate vulnerabilities
            summary = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
            vulnerabilities = []
            
            for res in scan_data.get("Results", []):
                for vuln in res.get("Vulnerabilities", []):
                    # Trivy severities are usually UPPERCASE (e.g., 'LOW', 'MEDIUM')
                    # We normalize to Title case to match our summary keys
                    raw_severity = vuln.get("Severity", "Unknown")
                    severity = raw_severity.title() 
                    
                    if severity in summary:
                        summary[severity] += 1
                    else:
                        summary["Unknown"] += 1
                    
                    if len(vulnerabilities) < 1000:
                        vulnerabilities.append({
                            "id": vuln.get("VulnerabilityID"),
                            "pkg": vuln.get("PkgName"),
                            "severity": severity, # Use normalized severity for consistency
                            "title": vuln.get("Title", "No title")
                        })
            
            report = {
                "image": image_url,
                "summary": summary,
                "vulnerabilities": vulnerabilities,
                "total": sum(summary.values())
            }
            
            self.scan_manager.complete_scan(scan_id, report)
            
        except Exception as e:
            self.scan_manager.complete_scan(scan_id, {"error": str(e)}, status="error")

    def get_scan_status(self, scan_id):
        """Returns the current state of a scan."""
        return self.scan_manager.get_scan(scan_id)
