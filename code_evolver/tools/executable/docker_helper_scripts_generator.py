#!/usr/bin/env python3
"""
Docker Helper Scripts Generator
Generates build.sh, run.sh, and test.sh scripts for Docker packages
"""
import json
import sys
from typing import Dict, Any


def generate_build_script(service_name: str) -> str:
    """Generate build.sh script"""
    return f'''#!/bin/bash
# Build script for {service_name}

set -e

echo "Building Docker image for {service_name}..."

docker build -t {service_name}:latest .

echo "Build complete!"
echo "Image: {service_name}:latest"
'''


def generate_run_script(service_name: str, port: int) -> str:
    """Generate run.sh script"""
    return f'''#!/bin/bash
# Run script for {service_name}

set -e

echo "Starting {service_name}..."

# Stop any existing container
docker stop {service_name} 2>/dev/null || true
docker rm {service_name} 2>/dev/null || true

# Run the container
docker run -d \\
  --name {service_name} \\
  -p {port}:{port} \\
  --restart unless-stopped \\
  {service_name}:latest

echo "{service_name} is running!"
echo "API available at: http://localhost:{port}"
echo ""
echo "To view logs: docker logs -f {service_name}"
echo "To stop: docker stop {service_name}"
'''


def generate_test_script(service_name: str, port: int) -> str:
    """Generate test.sh script"""
    return f'''#!/bin/bash
# Test script for {service_name}

set -e

BASE_URL="http://localhost:{port}"

echo "Testing {service_name} API..."
echo ""

# Wait for service to be ready
echo "Waiting for service to start..."
for i in {{1..30}}; do
    if curl -sf $BASE_URL/api/health > /dev/null 2>&1; then
        echo "Service is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Service failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s $BASE_URL/api/health | python3 -m json.tool
echo ""

# Test info endpoint
echo "2. Testing info endpoint..."
curl -s $BASE_URL/api/info | python3 -m json.tool
echo ""

# Test invoke endpoint (example)
echo "3. Testing invoke endpoint..."
echo "   (Sending example request - modify as needed for your tool)"
curl -s -X POST $BASE_URL/api/invoke \\
  -H "Content-Type: application/json" \\
  -d '{{"prompt": "test"}}' | python3 -m json.tool
echo ""

echo "All tests passed!"
'''


def generate_stop_script(service_name: str) -> str:
    """Generate stop.sh script"""
    return f'''#!/bin/bash
# Stop script for {service_name}

echo "Stopping {service_name}..."

docker stop {service_name} 2>/dev/null || echo "Container not running"
docker rm {service_name} 2>/dev/null || echo "Container already removed"

echo "{service_name} stopped and removed."
'''


def generate_docker_compose_up_script(service_name: str, port: int) -> str:
    """Generate docker-compose-up.sh script"""
    return f'''#!/bin/bash
# Docker Compose script for {service_name}

set -e

echo "Starting {service_name} with docker-compose..."

docker-compose up -d

echo "{service_name} is running!"
echo "API available at: http://localhost:{port}"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
'''


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'Missing configuration JSON argument'
        }))
        sys.exit(1)

    try:
        # Parse configuration
        config = json.loads(sys.argv[1])
        service_name = config.get('service_name', 'tool-api')
        port = config.get('port', 8080)

        # Generate all scripts
        scripts = {
            'build.sh': generate_build_script(service_name),
            'run.sh': generate_run_script(service_name, port),
            'test.sh': generate_test_script(service_name, port),
            'stop.sh': generate_stop_script(service_name),
            'docker-compose-up.sh': generate_docker_compose_up_script(service_name, port)
        }

        # Output result
        print(json.dumps({
            'success': True,
            'scripts': scripts
        }))

    except Exception as e:
        print(json.dumps({
            'error': f'Error generating helper scripts: {e}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
