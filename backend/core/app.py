from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime

from core.server_manager import ServerManager

app = Flask(__name__)
CORS(app)

# Initialize ServerManager
# Go up one level from 'core' to 'backend_v2' to find 'data'
base_dir = os.path.dirname(os.path.dirname(__file__))
data_path = os.path.join(base_dir, 'data', 'master.json')

sm = ServerManager(data_path)

@app.route('/servers', methods=['GET'])
def get_servers():
    """Returns all servers configured in master.json."""
    return jsonify(sm.get_all_servers()), 200

@app.route('/servers/<server_id>/pods', methods=['GET'])
def get_server_pods(server_id):
    """Returns pods for a specific server."""
    pods = sm.get_pods_for_server(server_id)
    return jsonify(pods), 200

@app.route('/create', methods=['POST'])
def create_pod():
    """Creates a pod on a server and updates master.json."""
    data = request.json
    server_id = data.get('server_id')
    
    result = sm.create_pod(server_id, data)
    
    if "error" in result:
        # Determine status code based on error message (simple heuristic)
        if "not found" in result["error"].lower():
            return jsonify(result), 404
        elif "Insufficient" in result["error"]:
            return jsonify(result), 400
        else:
            return jsonify(result), 500
            
    return jsonify(result), 200

@app.route('/update', methods=['POST'])
def update_pod():
    """Updates a pod's image."""
    data = request.json
    server_id = data.get('server_id')
    pod_id = data.get('pod_id')
    image_url = data.get('image_url')
    
    if not all([server_id, pod_id, image_url]):
        return jsonify({"error": "Missing required fields"}), 400

    result = sm.update_pod(server_id, pod_id, image_url)
    
    if "error" in result:
        return jsonify(result), 500
        
    return jsonify(result), 200

@app.route('/delete', methods=['POST'])
def delete_pod():
    """Deletes a pod and updates master.json."""
    data = request.json
    server_id = data.get('server_id')
    pod_id = data.get('pod_id')
    
    result = sm.delete_pod(server_id, pod_id)
    
    if "error" in result:
        return jsonify(result), 500 # Simplified error handling for delete
        
    return jsonify(result), 200
@app.route('/logs', methods=['GET'])
def get_logs():
    """Returns logs for a specific pod."""
    server_id = request.args.get('server_id')
    pod_id = request.args.get('pod_id')
    
    if not server_id or not pod_id:
        return jsonify({"error": "Missing server_id or pod_id"}), 400
        
    logs = sm.get_pod_logs(server_id, pod_id)
    return logs, 200, {'Content-Type': 'text/plain'}

@app.route('/scan', methods=['GET'])
def scan_image():
    """Starts a background security scan."""
    server_id = request.args.get('server_id')
    pod_id = request.args.get('pod_id')
    
    if not server_id or not pod_id:
        return jsonify({"error": "Missing server_id or pod_id"}), 400
        
    result = sm.scan_pod_image(server_id, pod_id)
    return jsonify(result), 200

@app.route('/scan/status', methods=['GET'])
def scan_status():
    """Polls the status of a background scan."""
    scan_id = request.args.get('scan_id')
    if not scan_id:
        return jsonify({"error": "Missing scan_id"}), 400
        
    status = sm.get_scan_status(scan_id)
    if not status:
        return jsonify({"error": "Scan not found"}), 404
        
    return jsonify(status), 200
