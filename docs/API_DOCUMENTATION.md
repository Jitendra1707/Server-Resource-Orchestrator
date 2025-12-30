# Backend V2 API Documentation

Base URL: `http://localhost:5006`

## Endpoints

### 1. Get All Servers
Returns a list of all configured servers and their status.

- **URL**: `/servers`
- **Method**: `GET`
- **Response**: `200 OK`
- **Body**: Array of Server Objects

### 2. Get Server Pods
Returns the list of pods for a specific server.

- **URL**: `/servers/<server_id>/pods`
- **Method**: `GET`
- **Response**: `200 OK`
- **Body**: Array of Pod Objects

### 3. Create Pod
Creates a new pod (Deployment) on the specified server.
- Validates resource availability.
- Creates a Kubernetes Deployment.
- **Waits for Pod to become Running**.
- Updates the internal state (`master.json`).

- **URL**: `/create`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Payload**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `server_id` | string | Yes | - | The ID of the server to target. |
| `pod_id` | string | Yes | - | Unique identifier for the pod/deployment. |
| `image_url` | string | No | `nginx:latest` | Container image to use. |
| `route` | string | No | - | Ingress route path (e.g., `/my-app`). |
| `namespace` | string | No | `pod_id` | Kubernetes namespace. Defaults to `pod_id` if not provided. |
| `wait` | boolean | No | `true` | Wait for pod to be ready. |
| `requested` | object | No | `{"cpus": 0.5, "ram_gb": 1}` | Resource requests. |

**Example Payload**:
```json
{
  "server_id": "server-1",
  "pod_id": "python-worker-01",
  "image_url": "python:3.9-slim",
  "route": "/worker-app",
  "namespace": "worker-space",
  "requested": {
    "cpus": 1.0,
    "ram_gb": 2.0,
    "storage_gb": 10.0
  }
}
```

**Response (Success)**:
```json
{
  "message": "Pod created successfully",
  "pod": {
      "pod_id": "python-worker-01",
      "namespace": "worker-space",
      "status": "running",
      "pod_ip": "10.244.0.5",
      ...
  },
  "details": {
      "status": "success",
      "message": "Deployment is ready",
      "pod_ip": "10.244.0.5",
      "external_ip": "10.244.0.5"
  }
}
```

**Response (Error - CrashLoopBackOff)**:
```json
{
  "status": "error",
  "error": "Pod failed to start: CrashLoopBackOff",
  "details": "Back-off restarting failed container",
  "logs": "Traceback (most recent call last)...",
  "events": ["[Warning] BackOff: Back-off restarting failed container"]
}
```

### 4. Update Pod
Updates a pod's image using a Rolling Update strategy (Blue-Green logic).
- Patches the deployment image.
- **Waits for the rollout to complete** (new pods ready) before returning success.

- **URL**: `/update`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Payload**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `server_id` | string | Yes | The ID of the server. |
| `pod_id` | string | Yes | The ID/Name of the pod to update. |
| `image_url` | string | Yes | The new image URL. |

**Example Payload**:
```json
{
  "server_id": "server-1",
  "pod_id": "python-worker-01",
  "image_url": "python:3.9-slim-v2"
}
```

**Response (Success)**:
```json
{
  "status": "success",
  "message": "Deployment updated to python:3.9-slim-v2",
  "image": "python:3.9-slim-v2"
}
```

### 5. Delete Pod
Deletes a pod (Deployment) from the specified server.

- **URL**: `/delete`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Payload**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `server_id` | string | Yes | The ID of the server. |
| `pod_id` | string | Yes | The ID/Name of the pod to delete. |
