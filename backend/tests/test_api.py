import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5006"

def print_status(text, status="INFO"):
    print(f"[{status}] {text}")

def test_workflow():
    print_status("Starting API Test Sequence...")
    
    # 1. Get All Servers
    print_status("Testing GET /servers")
    try:
        response = requests.get(f"{BASE_URL}/servers")
        if response.status_code == 200:
            servers = response.json()
            print_status(f"Success! Found {len(servers)} servers.", "SUCCESS")
            # print(json.dumps(servers, indent=2))
            
            if not servers:
                print_status("No servers found. Cannot proceed.", "ERROR")
                return
            
            target_server_id = servers[0]['id']
            print_status(f"Targeting Server: {target_server_id} ({servers[0]['name']})")
        else:
            print_status(f"Failed with {response.status_code}: {response.text}", "ERROR")
            return
    except Exception as e:
        print_status(f"Connection Failed: {e}", "ERROR")
        return

    # 2. Create Pod
    print_status("Testing POST /create")
    payload = {
        "server_id": target_server_id,
        "pod_id": "test-pod-api",
        "image_url": "nginx:latest",  # Fast starting image
        "requested": {
            "cpus": 0.1,
            "ram_gb": 0.2
        },
        "wait": True  # Explicitly wait
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/create", json=payload)
    duration = time.time() - start_time
    
    if response.status_code == 201 or response.status_code == 200:
        data = response.json()
        print_status(f"Pod Created Successfully in {duration:.2f}s!", "SUCCESS")
        # print(json.dumps(data, indent=2))
        
        # Verify details
        if "details" in data:
            print_status(f"Pod IP: {data['details'].get('pod_ip')}")
            print_status(f"Phase: {data['details'].get('phase')}")
    else:
        print_status(f"Failed to create pod after {duration:.2f}s. Code: {response.status_code}", "ERROR")
        print(response.text)
        return

    # 3. Get Pods
    print_status(f"Testing GET /servers/{target_server_id}/pods")
    response = requests.get(f"{BASE_URL}/servers/{target_server_id}/pods")
    if response.status_code == 200:
        pods = response.json()
        found = False
        for pod in pods:
            if pod['pod_id'] == "test-pod-api":
                found = True
                print_status(f"Verified pod 'test-pod-api' exists in master.json.", "SUCCESS")
                break
        if not found:
            print_status("Pod not found in server list!", "ERROR")
    
    # 4. Delete Pod
    print_status("Testing POST /delete")
    del_payload = {
        "server_id": target_server_id,
        "pod_id": "test-pod-api"
    }
    
    response = requests.post(f"{BASE_URL}/delete", json=del_payload)
    if response.status_code == 200:
        print_status("Pod Deleted Successfully.", "SUCCESS")
    else:
        print_status(f"Failed to delete pod: {response.text}", "ERROR")

if __name__ == "__main__":
    # Wait for server to potentially start
    print_status("Waiting 2s for server warmup...")
    time.sleep(2)
    test_workflow()
