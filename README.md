# Server Resource Manager

A professional Onprem or cloud server resource management system designed for high scalability and ease of use. This project allows you to manage servers, monitor server health, and orchestrate pod lifecycles through a modern web interface.

## 🚀 Key Features
- **Server Management**: Add any server to the master list and manage it seamlessly.
- **Kubernetes Management**: Create, update, and delete pods across multiple clusters.
- **Health Monitoring**: Real-time status tracking for pods/servers and Kubernetes resources.
- **Resource Allocation**: Fine-grained control over GPU, RAM, and Storage for your workloads.
- **Runtime Security Scanning**: Integrated **Trivy** scanning for container images directly from the management interface.
- **Independent Architecture**: Decoupled Frontend and Backend for independent scaling and deployment.

## 🏗️ Tech Stack

- **Backend**: Python, Flask, Kubernetes Client (Primary Management SDK)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla/Modern JS)
- **Security & Monitoring**: MicroK8s, SSH Integration, **Trivy** (Container Scanning)

## 📁 Project Structure

```text
.
├── backend/            # Python Flask REST API
│   ├── tests/          # Diagnostic and test scripts
├── frontend/           # Modern Web Interface
├── docs/               # Documentation (API docs, etc.)
├── legacy/             # Previous versions and legacy code
├── .gitignore          # Root ignore file
├── LICENSE             # MIT License
└── README.md           # Main documentation (this file)
```

## 🛠️ Getting Started

### Prerequisites

- Python 3.8+
- Modern Web Browser
- Kubernetes Cluster access (or MicroK8s)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:5006`.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Open `index.html` in your browser, or use a simple static server:
   ```bash
   # Using Python's built-in server
   python -m http.server 8000
   ```
   Access the UI at `http://localhost:8000`.

## 📚 API Documentation

For detailed API endpoint documentation, refer to [docs/API_DOCUMENTATION.md](file:///docs/API_DOCUMENTATION.md).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.