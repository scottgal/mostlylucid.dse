# Docker Packaging Guide

Complete guide for packaging tools and workflows as containerized API services.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Features](#features)
4. [Using the CLI Command](#using-the-cli-command)
5. [Generated Files](#generated-files)
6. [Configuration](#configuration)
7. [Building and Running](#building-and-running)
8. [API Endpoints](#api-endpoints)
9. [Standalone Executables](#standalone-executables)
10. [Package Recovery](#package-recovery)
11. [Troubleshooting](#troubleshooting)
12. [Advanced Usage](#advanced-usage)

---

## Overview

The Docker Packaging system allows you to wrap any tool or workflow into a containerized REST API service. This enables:

- **Microservices Architecture**: Convert tools into independent services
- **Easy Deployment**: Deploy anywhere Docker runs
- **API Access**: Access tools via HTTP REST API
- **Isolation**: Each tool runs in its own container
- **Scalability**: Scale services independently

### Architecture

```
┌─────────────────────────────────────────┐
│  Docker Container                        │
│  ┌───────────────────────────────────┐  │
│  │  Flask REST API                   │  │
│  │  Endpoints:                       │  │
│  │  - POST /api/invoke              │  │
│  │  - GET /api/health               │  │
│  │  - GET /api/info                 │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Tool/Workflow Runtime            │  │
│  │  - ToolsManager                   │  │
│  │  - LLM Integration                │  │
│  │  - Vector DB                      │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Quick Start

### Option 1: Using the CLI Command

```bash
# Package a tool as Docker API
/tool-compile basic_calculator ./my-calculator-api docker

# Navigate to output directory
cd ./my-calculator-api

# Build and run
chmod +x *.sh
./build.sh
./run.sh

# Test the API
./test.sh
```

### Option 2: Natural Language

Simply ask:
```
"Make a Docker container for the basic_calculator tool"
"Dockerize the code_review workflow"
"Create an API for the general_code_generator tool"
```

---

## Features

### 1. Automatic Generation

- ✅ **Dockerfile** - Optimized multi-stage build
- ✅ **docker-compose.yml** - Full orchestration
- ✅ **Flask API Server** - REST endpoints
- ✅ **.env Files** - Complete configuration
- ✅ **Helper Scripts** - build.sh, run.sh, test.sh, stop.sh
- ✅ **README** - Full documentation
- ✅ **.gitignore** - Git-ready

### 2. Security Hardening

- Non-root user execution
- Minimal base images (Python slim)
- Layer caching optimization
- Health checks
- Environment variable configuration

### 3. Self-Healing

- Automatic package recovery
- Missing dependency detection
- Auto-installation of Python packages
- Error recovery workflows

---

## Using the CLI Command

### Basic Syntax

```bash
/tool-compile <tool_id> <output_path> [format]
```

### Parameters

- `<tool_id>` (required): ID of the tool or workflow to package
- `<output_path>` (optional): Output directory, default: `./docker-package`
- `[format]` (optional): Package format - `docker`, `exe`, or `both`, default: `docker`

### Examples

#### Package as Docker API
```bash
/tool-compile basic_calculator ./calc-api docker
```

#### Package as Standalone Executable
```bash
/tool-compile my_tool ./my-tool-exe exe
```

#### Package Both Formats
```bash
/tool-compile data_processor ./processor both
```

#### Custom Port
```bash
# The system will ask for configuration
# or you can specify in natural language:
"Package basic_calculator as Docker on port 9000"
```

---

## Generated Files

When you package a tool, the following structure is created:

```
my-tool-api/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Orchestration config
├── api_server.py          # Flask API wrapper
├── .env                   # Environment variables (DO NOT COMMIT)
├── .env.example           # Environment template with docs
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
├── build.sh               # Build Docker image
├── run.sh                 # Run container
├── test.sh                # Test API endpoints
├── stop.sh                # Stop container
├── docker-compose-up.sh   # Start with docker-compose
└── code_evolver/          # Application code
    ├── src/
    ├── tools/
    ├── workflows/
    └── config.yaml
```

### File Descriptions

#### **Dockerfile**
Multi-stage Docker build with:
- Python 3.11 slim base
- Non-root user
- Optimized layer caching
- Security hardening

#### **docker-compose.yml**
Orchestration file including:
- Service definition
- Port mapping
- Environment variables
- Health checks
- Restart policies

#### **api_server.py**
Flask REST API with endpoints:
- `GET /` - API documentation
- `GET /api/health` - Health check
- `GET /api/info` - Tool information
- `POST /api/invoke` - Invoke the tool

#### **.env**
Environment configuration:
```env
TOOL_ID=your_tool
API_PORT=8080
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:3b
VECTOR_DB_TYPE=chromadb
```

#### **Helper Scripts**
- `build.sh` - Build Docker image
- `run.sh` - Run container in detached mode
- `test.sh` - Test all API endpoints
- `stop.sh` - Stop and remove container
- `docker-compose-up.sh` - Start with compose

---

## Configuration

### Environment Variables

Edit the `.env` file to configure your service:

#### Application Settings
```env
TOOL_ID=basic_calculator
API_PORT=8080
API_HOST=0.0.0.0
```

#### LLM Configuration

**Using Ollama (Local)**
```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:3b
LLM_BASE_URL=http://localhost:11434
```

**Using OpenAI**
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=your-api-key
```

**Using Anthropic**
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your-api-key
```

#### Vector Database

**ChromaDB (Local)**
```env
VECTOR_DB_TYPE=chromadb
VECTOR_DB_PATH=./rag_memory
```

**Qdrant (Scalable)**
```env
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://localhost:6333
```

### Port Configuration

Change the API port:
```env
API_PORT=9000
```

Update `docker-compose.yml`:
```yaml
ports:
  - "9000:9000"
```

---

## Building and Running

### Method 1: Helper Scripts (Recommended)

```bash
# Make scripts executable
chmod +x *.sh

# Build the image
./build.sh

# Run the container
./run.sh

# Test the API
./test.sh

# View logs
docker logs -f <service-name>

# Stop the service
./stop.sh
```

### Method 2: Docker Compose

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### Method 3: Manual Docker Commands

```bash
# Build
docker build -t my-tool-api:latest .

# Run
docker run -d \
  --name my-tool-api \
  -p 8080:8080 \
  --env-file .env \
  my-tool-api:latest

# Stop
docker stop my-tool-api
docker rm my-tool-api
```

---

## API Endpoints

### GET /

API documentation and endpoint list.

**Example:**
```bash
curl http://localhost:8080/
```

**Response:**
```json
{
  "service": "Tool API Wrapper",
  "tool_id": "basic_calculator",
  "endpoints": {
    "GET /": "API documentation",
    "GET /api/health": "Health check",
    "GET /api/info": "Tool information",
    "POST /api/invoke": "Invoke the tool"
  }
}
```

### GET /api/health

Health check endpoint.

**Example:**
```bash
curl http://localhost:8080/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "tool_id": "basic_calculator",
  "version": "1.0.0"
}
```

### GET /api/info

Get tool information including schema.

**Example:**
```bash
curl http://localhost:8080/api/info
```

**Response:**
```json
{
  "tool_id": "basic_calculator",
  "name": "Basic Calculator",
  "type": "executable",
  "description": "Fast arithmetic operations",
  "input_schema": {
    "operation": "str - Operation: 'add', 'subtract', 'multiply'",
    "a": "number - First operand",
    "b": "number - Second operand"
  },
  "output_schema": {
    "result": "number - Result of the operation"
  }
}
```

### POST /api/invoke

Invoke the tool with JSON input.

**For Executable Tools:**
```bash
curl -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "add",
    "a": 5,
    "b": 3
  }'
```

**For LLM Tools:**
```bash
curl -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate a hello world function",
    "temperature": 0.7
  }'
```

**For Workflows:**
```bash
curl -X POST http://localhost:8080/api/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "param1": "value1",
      "param2": "value2"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "tool_id": "basic_calculator",
  "result": {
    "result": 8
  }
}
```

---

## Standalone Executables

Create standalone executables (.exe, .app) that bundle everything into a single file.

### Generate Standalone Executable

```bash
/tool-compile my_tool ./my-tool-exe exe
```

Or via natural language:
```
"Compile the data_processor tool to an executable"
"Make a standalone exe for my_workflow"
```

### Generated Files

```
my-tool-exe/
├── my_tool_standalone.py    # Standalone wrapper script
├── my_tool_standalone.spec  # PyInstaller spec file
├── BUILD_INSTRUCTIONS.md    # Build guide
└── requirements.txt         # Python dependencies
```

### Building the Executable

#### Prerequisites
```bash
pip install pyinstaller
```

#### Build Steps

**Quick Build:**
```bash
pyinstaller --onefile --name my_tool my_tool_standalone.py
```

**Using Spec File (Recommended):**
```bash
pyinstaller my_tool_standalone.spec
```

**Optimized Build:**
```bash
pyinstaller --onefile \
  --name my_tool \
  --strip \
  --clean \
  --noconfirm \
  my_tool_standalone.py
```

#### Output

The executable will be in:
- `dist/my_tool` (Linux/Mac)
- `dist/my_tool.exe` (Windows)

### Running Standalone Executable

**CLI Mode:**
```bash
# Direct prompt
./dist/my_tool --prompt "your input here"

# JSON input
./dist/my_tool --input '{"param": "value"}'

# From file
./dist/my_tool --file input.json
```

**API Mode:**
```bash
# Start API server
./dist/my_tool

# API runs on http://localhost:8080
```

### Distribution

The executable is standalone and can be distributed without Python installed.

**Size Optimization:**
- Use UPX compression: `--upx-dir=/path/to/upx`
- Exclude modules: `--exclude-module tkinter`
- One-file mode: `--onefile`

---

## Package Recovery

Automatic detection and installation of missing dependencies.

### How It Works

1. **Error Detection**: Scans error messages for missing packages
2. **Package Identification**: Maps import names to package names
3. **Auto-Installation**: Installs missing packages automatically
4. **Retry**: Re-runs the operation after installation

### Supported Error Types

#### Python Imports
```python
ModuleNotFoundError: No module named 'flask'
ImportError: cannot import name 'CORS' from 'flask_cors'
```

#### System Commands
```bash
curl: command not found
docker: command not found
```

### Manual Usage

```python
from tools_manager import ToolsManager

# Configure recovery tool
config = {
    "error_output": error_message,
    "auto_install": True,
    "install_system": False  # Requires sudo
}

# Run recovery
result = tools_manager.invoke_executable_tool(
    tool_id="package_recovery_tool",
    input_json=json.dumps(config)
)
```

### Package Mappings

The recovery tool includes mappings for common packages:

```python
{
    'yaml': 'pyyaml',
    'PIL': 'pillow',
    'cv2': 'opencv-python',
    'sklearn': 'scikit-learn',
    'flask_cors': 'flask-cors',
}
```

### Integration with Workflows

Add recovery step to workflows:

```json
{
  "step_id": "error_recovery",
  "tool": "package_recovery_tool",
  "description": "Recover from missing packages",
  "on_error": {
    "retry": true,
    "max_retries": 1
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:**
```
Error: bind: address already in use
```

**Solution:**
```bash
# Change port in .env
API_PORT=9000

# Update docker-compose.yml
ports:
  - "9000:9000"
```

#### 2. LLM Connection Failed

**Error:**
```
Error connecting to LLM service
```

**Solutions:**

**For Ollama:**
```bash
# Check Ollama is running
ollama serve

# Pull model
ollama pull qwen2.5-coder:3b

# Update .env
LLM_BASE_URL=http://host.docker.internal:11434  # For Docker on Mac/Windows
LLM_BASE_URL=http://172.17.0.1:11434           # For Docker on Linux
```

**For OpenAI/Anthropic:**
```bash
# Check API key in .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```

#### 3. Permission Denied

**Error:**
```
Permission denied: ./build.sh
```

**Solution:**
```bash
chmod +x *.sh
```

#### 4. Container Won't Start

**Debug:**
```bash
# Check logs
docker logs <container-name>

# Run interactively
docker run -it --rm my-tool-api:latest /bin/bash

# Check environment
docker exec <container-name> env
```

#### 5. Module Not Found in Container

**Solution:**

Add to `requirements.txt` or Dockerfile:
```dockerfile
RUN pip install missing-package
```

Rebuild:
```bash
./build.sh
```

### Debugging

#### Enable Debug Mode

```env
FLASK_DEBUG=true
LOG_LEVEL=DEBUG
```

#### View Logs

```bash
# Docker logs
docker logs -f <container-name>

# Docker compose logs
docker-compose logs -f

# Specific service
docker-compose logs -f <service-name>
```

#### Test Locally

```bash
# Run API server locally (outside Docker)
cd code_evolver
python ../api_server.py
```

---

## Advanced Usage

### Custom Base Images

Specify a different base image:

```bash
# Using Python 3.12
/tool-compile my_tool ./output docker --base-image python:3.12-slim

# Using Alpine
/tool-compile my_tool ./output docker --base-image python:3.11-alpine
```

### Multi-Service Deployment

Package multiple tools and deploy together:

```yaml
# docker-compose.yml
version: '3.8'
services:
  calculator:
    build: ./calculator-api
    ports:
      - "8080:8080"

  code-gen:
    build: ./codegen-api
    ports:
      - "8081:8080"

  data-processor:
    build: ./processor-api
    ports:
      - "8082:8080"
    depends_on:
      - calculator
```

### Production Deployment

#### Use Production-Grade WSGI Server

Update `api_server.py` to use Gunicorn:

```python
if __name__ == '__main__':
    # Use Gunicorn in production
    import os
    if os.getenv('FLASK_ENV') == 'production':
        from gunicorn.app.base import BaseApplication
        # ... Gunicorn setup
    else:
        app.run(host='0.0.0.0', port=PORT)
```

#### Add to Dockerfile:
```dockerfile
RUN pip install gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "api_server:app"]
```

#### Security Hardening

1. **Use secrets management:**
```bash
# Use Docker secrets instead of .env
docker secret create openai_key ./openai_key.txt
```

2. **Restrict CORS:**
```env
CORS_ORIGINS=https://yourdomain.com
```

3. **Add rate limiting:**
```python
from flask_limiter import Limiter
limiter = Limiter(app)

@app.route('/api/invoke')
@limiter.limit("10 per minute")
def invoke():
    ...
```

4. **Enable HTTPS:**
```bash
# Use reverse proxy (nginx, traefik)
# or add SSL to Flask app
```

### Monitoring

Add health check endpoints:

```python
@app.route('/metrics')
def metrics():
    return {
        'requests_total': request_count,
        'errors_total': error_count,
        'uptime_seconds': time.time() - start_time
    }
```

Integrate with monitoring tools:
- Prometheus
- Grafana
- DataDog
- New Relic

### CI/CD Integration

#### GitHub Actions

```.github/workflows/build-and-deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build Docker image
        run: docker build -t my-tool-api:${{ github.sha }} .

      - name: Push to registry
        run: docker push my-tool-api:${{ github.sha }}

      - name: Deploy
        run: kubectl apply -f k8s/deployment.yaml
```

---

## Next Steps

1. **Explore Examples**: Check `examples/` directory
2. **Read Tool Documentation**: See `docs/TOOLS.md`
3. **Learn Workflows**: Read `docs/WORKFLOWS.md`
4. **Contribute**: See `CONTRIBUTING.md`

## Support

- Documentation: `docs/`
- Issues: GitHub Issues
- Examples: `examples/`
- Community: Discussions

---

**Happy Packaging! 🚀**
