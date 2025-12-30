import requests
import time
import sys

BASE_URL = "http://localhost:5006"

def test_async_scan():
    print("--- Testing Async Security Scan ---")
    
    # 1. Get a server and pod
    print("Fetching servers...")
    res = requests.get(f"{BASE_URL}/servers")
    if not res.ok:
        print(f"Failed to fetch servers: {res.text}")
        return
    
    servers = res.json()
    if not servers:
        print("No servers found. Please ensure master.json has data.")
        return
    
    server_id = servers[0]["id"]
    if not servers[0]["pods"]:
        print(f"No pods found on server {server_id}. Please create one first.")
        return
        
    pod_id = servers[0]["pods"][0]["pod_id"]
    print(f"Targeting Pod: {pod_id} on Server: {server_id}")

    # 2. Initiate scan
    print(f"Initiating scan for {pod_id}...")
    res = requests.get(f"{BASE_URL}/scan?server_id={server_id}&pod_id={pod_id}")
    if not res.ok:
        print(f"Failed to initiate scan: {res.text}")
        return
    
    data = res.json()
    if data.get("status") != "accepted":
        print(f"Unexpected status: {data.get('status')}")
        return
        
    scan_id = data.get("scan_id")
    print(f"Scan initiated. Scan ID: {scan_id}")

    # 3. Poll for status and logs
    print("Polling for status and logs...")
    completed = False
    attempts = 0
    max_attempts = 60 # 2 minutes
    
    while not completed and attempts < max_attempts:
        time.sleep(2)
        attempts += 1
        
        status_res = requests.get(f"{BASE_URL}/scan/status?scan_id={scan_id}")
        if not status_res.ok:
            print(f"Error polling status: {status_res.text}")
            break
            
        status_data = status_res.json()
        status = status_data.get("status")
        logs = status_data.get("logs", [])
        
        print(f"[Attempt {attempts}] Status: {status} | Logs: {len(logs)} lines")
        
        if status in ["success", "error"]:
            completed = True
            print(f"Scan completed with status: {status}")
            if status == "success":
                result = status_data.get("result", {})
                print("Vulnerability Summary:")
                print(result.get("summary"))
                print(f"Total: {result.get('total')}")
            else:
                print(f"Error Result: {status_data.get('result')}")
            break
    
    if not completed:
        print("Timed out waiting for scan to complete.")

if __name__ == "__main__":
    test_async_scan()
