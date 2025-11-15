"""
Script to register the HTTP Content Fetcher tool in the tools index.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Paths
TOOLS_INDEX = Path(__file__).parent.parent / "tools" / "index.json"


def register_http_content_fetcher():
    """Register the HTTP Content Fetcher tool."""

    # Load existing tools
    with open(TOOLS_INDEX, 'r', encoding='utf-8') as f:
        tools = json.load(f)

    # Define the HTTP Content Fetcher tool
    http_fetcher_tool = {
        "tool_id": "http_content_fetcher",
        "name": "HTTP Content Fetcher",
        "tool_type": "api_connector",
        "description": "Comprehensive HTTP client supporting all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS), all body types (JSON, form-data, multipart, XML, text, binary), various authentication methods (Bearer, API Key, Basic, Digest), and flexible response handling. Designed for seamless integration with DSE workflow system. Can fetch content from any URL and return data in multiple formats.",
        "tags": [
            "http",
            "fetch",
            "content-fetching",
            "web",
            "api",
            "rest",
            "api-connector",
            "http-client",
            "download",
            "upload",
            "json",
            "xml",
            "form-data",
            "authentication",
            "bearer",
            "api-key",
            "workflow-integration"
        ],
        "parameters": {
            "url": {
                "type": "string",
                "required": True,
                "description": "Target URL to fetch content from"
            },
            "method": {
                "type": "string",
                "required": False,
                "default": "GET",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"],
                "description": "HTTP method to use"
            },
            "headers": {
                "type": "object",
                "required": False,
                "description": "Custom HTTP headers"
            },
            "body": {
                "type": ["object", "string", "bytes"],
                "required": False,
                "description": "Request body (dict, string, or bytes)"
            },
            "body_type": {
                "type": "string",
                "required": False,
                "default": "json",
                "enum": ["json", "form", "multipart", "xml", "text", "binary", "custom"],
                "description": "Body content type"
            },
            "params": {
                "type": "object",
                "required": False,
                "description": "URL query parameters"
            },
            "auth": {
                "type": "object",
                "required": False,
                "description": "Authentication configuration (bearer, api_key, basic, digest, custom)"
            },
            "timeout": {
                "type": "integer",
                "required": False,
                "description": "Request timeout in seconds"
            },
            "response_format": {
                "type": "string",
                "required": False,
                "default": "auto",
                "enum": ["auto", "json", "text", "binary"],
                "description": "Expected response format"
            }
        },
        "metadata": {
            "implementation_path": "src/http_content_fetcher.py",
            "implementation_class": "HTTPContentFetcher",
            "factory_function": "create_http_fetcher",
            "supports_streaming": True,
            "supports_file_upload": True,
            "supports_file_download": True,
            "max_retries": 3,
            "retry_backoff_factor": 0.3,
            "default_timeout": 30,
            "supported_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"],
            "supported_body_types": ["json", "form", "multipart", "xml", "text", "binary", "custom"],
            "supported_auth_types": ["bearer", "api_key", "basic", "digest", "custom"],
            "supported_response_formats": ["auto", "json", "text", "binary"],
            "cost_tier": "low",
            "speed_tier": "fast",
            "quality_tier": "excellent",
            "reliability": "high",
            "workflow_compatible": True
        },
        "constraints": {
            "max_timeout": 300,
            "max_retries": 10,
            "verify_ssl": True
        },
        "current_usage": {
            "storage_mb": 0.0,
            "memory_mb": 0.0,
            "calls_count": 0,
            "last_reset": datetime.now(timezone.utc).isoformat()
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage_count": 0
    }

    # Add to tools
    tools["http_content_fetcher"] = http_fetcher_tool

    # Save back to file
    with open(TOOLS_INDEX, 'w', encoding='utf-8') as f:
        json.dump(tools, f, indent=2)

    print(f"✓ Successfully registered HTTP Content Fetcher tool in {TOOLS_INDEX}")
    print(f"  Tool ID: {http_fetcher_tool['tool_id']}")
    print(f"  Type: {http_fetcher_tool['tool_type']}")
    print(f"  Tags: {', '.join(http_fetcher_tool['tags'][:5])}...")
    print(f"  Total tools in index: {len(tools)}")


if __name__ == '__main__':
    try:
        register_http_content_fetcher()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error registering tool: {e}", file=sys.stderr)
        sys.exit(1)
