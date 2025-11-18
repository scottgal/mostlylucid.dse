#!/usr/bin/env python3
"""
LLMApi Health Check Tool
Checks if LLMApi is running and accessible
"""
import json
import sys
import urllib.request
import urllib.error
from typing import Dict, Any


def check_llmapi_health(base_url: str = "http://localhost:5000") -> Dict[str, Any]:
    """
    Check if LLMApi is running and healthy.

    Args:
        base_url: Base URL of LLMApi instance

    Returns:
        Health check result with status, version, endpoints info
    """
    health_endpoint = f"{base_url}/health"

    result = {
        "available": False,
        "base_url": base_url,
        "health_endpoint": health_endpoint,
        "error": None,
        "version": None,
        "features": []
    }

    try:
        # Try health endpoint
        req = urllib.request.Request(health_endpoint, headers={"Accept": "application/json"})

        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                result["available"] = True

                # Try to get swagger for feature detection
                try:
                    swagger_url = f"{base_url}/swagger/v1/swagger.json"
                    swagger_req = urllib.request.Request(swagger_url, headers={"Accept": "application/json"})

                    with urllib.request.urlopen(swagger_req, timeout=3) as swagger_response:
                        swagger_data = json.loads(swagger_response.read().decode('utf-8'))

                        if 'info' in swagger_data and 'version' in swagger_data['info']:
                            result["version"] = swagger_data['info']['version']

                        # Detect available features from paths
                        if 'paths' in swagger_data:
                            paths = swagger_data['paths']

                            if any('/mock/' in p for p in paths):
                                result["features"].append("mock_endpoints")
                            if any('/stream/' in p for p in paths):
                                result["features"].append("streaming")
                            if '/api/mock/graphql' in paths:
                                result["features"].append("graphql")
                            if any('/openapi/' in p for p in paths):
                                result["features"].append("openapi_specs")
                            if any('/contexts' in p for p in paths):
                                result["features"].append("contexts")
                            if any('/grpc/' in p for p in paths):
                                result["features"].append("grpc")

                except Exception as swagger_error:
                    # Swagger not available, but health endpoint is
                    result["features"] = ["basic"]

    except urllib.error.URLError as e:
        result["error"] = f"Connection failed: {str(e.reason)}"
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"

    return result


def main():
    """Main entry point for standalone execution."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        base_url = input_data.get('base_url', 'http://localhost:5000')

        # Perform health check
        result = check_llmapi_health(base_url)

        # Return result as JSON
        print(json.dumps({
            "success": result["available"],
            "status": "healthy" if result["available"] else "unavailable",
            "details": result
        }, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
