#!/usr/bin/env python3
"""
HTTP REST Client

Standard REST API client with JSON communication.
Supports GET, POST, PUT, PATCH, DELETE with automatic JSON parsing.
"""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional


def make_http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Make HTTP request with JSON handling.

    Args:
        url: Target URL
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        headers: HTTP headers
        body: Request body (will be JSON-encoded if dict/list)
        timeout: Request timeout in seconds

    Returns:
        {
            "success": bool,
            "status_code": int,
            "headers": dict,
            "body": dict/list/str,  # Parsed JSON or raw text
            "error": str  # If failed
        }
    """
    try:
        # Prepare headers
        req_headers = {
            'User-Agent': 'DiSE-HTTP-REST-Client/1.0',
            'Accept': 'application/json',
        }

        if headers:
            req_headers.update(headers)

        # Prepare body
        req_data = None
        if body is not None:
            if isinstance(body, (dict, list)):
                # JSON encode
                req_data = json.dumps(body).encode('utf-8')
                req_headers['Content-Type'] = 'application/json'
            elif isinstance(body, str):
                # Raw string
                req_data = body.encode('utf-8')
            elif isinstance(body, bytes):
                # Already bytes
                req_data = body

        # Create request
        request = urllib.request.Request(
            url,
            data=req_data,
            headers=req_headers,
            method=method.upper()
        )

        # Make request
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode('utf-8')
            response_headers = dict(response.headers)

            # Try to parse as JSON
            try:
                parsed_body = json.loads(response_body)
            except json.JSONDecodeError:
                # Not JSON, return as string
                parsed_body = response_body

            return {
                "success": True,
                "status_code": response.status,
                "headers": response_headers,
                "body": parsed_body,
                "url": url,
                "method": method.upper()
            }

    except urllib.error.HTTPError as e:
        # HTTP error (4xx, 5xx)
        error_body = e.read().decode('utf-8') if e.fp else ""

        # Try to parse error body as JSON
        try:
            parsed_error = json.loads(error_body)
        except json.JSONDecodeError:
            parsed_error = error_body

        return {
            "success": False,
            "status_code": e.code,
            "headers": dict(e.headers),
            "body": parsed_error,
            "error": f"HTTP {e.code}: {e.reason}",
            "url": url,
            "method": method.upper()
        }

    except urllib.error.URLError as e:
        # Connection error
        return {
            "success": False,
            "error": f"Connection failed: {str(e.reason)}",
            "url": url,
            "method": method.upper()
        }

    except Exception as e:
        # Other errors
        return {
            "success": False,
            "error": str(e),
            "url": url,
            "method": method.upper()
        }


def main():
    """
    Main entry point.

    Input JSON:
    {
        "url": "https://api.example.com/users",
        "method": "GET",  // Optional, default: GET
        "headers": {...},  // Optional
        "body": {...},  // Optional (dict/list will be JSON-encoded)
        "timeout": 30  // Optional, default: 30
    }

    Output JSON:
    {
        "success": true,
        "status_code": 200,
        "headers": {...},
        "body": {...}  // Parsed JSON or raw string
    }
    """
    try:
        # Read input
        input_data = json.load(sys.stdin)

        # Extract parameters
        url = input_data.get("url", "")
        if not url:
            print(json.dumps({
                "success": False,
                "error": "url is required",
                "example": {
                    "url": "https://api.example.com/endpoint",
                    "method": "GET"
                }
            }))
            sys.exit(1)

        method = input_data.get("method", "GET")
        headers = input_data.get("headers", {})
        body = input_data.get("body", None)
        timeout = input_data.get("timeout", 30)

        # Make request
        result = make_http_request(url, method, headers, body, timeout)

        # Output result
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
