#!/usr/bin/env python3
"""
HTTP Raw Client

Raw HTTP client that returns content as string without parsing.
Useful for HTML pages, text files, binary data, or any non-JSON content.
"""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error
import base64
from typing import Dict, Any, Optional


def make_raw_http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: int = 30,
    encoding: str = "utf-8",
    return_binary: bool = False
) -> Dict[str, Any]:
    """
    Make HTTP request and return raw content.

    Args:
        url: Target URL
        method: HTTP method
        headers: HTTP headers
        body: Request body (raw string)
        timeout: Request timeout in seconds
        encoding: Text encoding (default: utf-8)
        return_binary: If True, return base64-encoded binary data

    Returns:
        {
            "success": bool,
            "status_code": int,
            "headers": dict,
            "content": str,  # Raw content (text or base64)
            "content_type": str,
            "content_length": int,
            "is_binary": bool,
            "error": str  # If failed
        }
    """
    try:
        # Prepare headers
        req_headers = {
            'User-Agent': 'CodeEvolver-HTTP-Raw-Client/1.0',
        }

        if headers:
            req_headers.update(headers)

        # Prepare body
        req_data = None
        if body is not None:
            if isinstance(body, str):
                req_data = body.encode('utf-8')
            elif isinstance(body, bytes):
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
            response_body_bytes = response.read()
            response_headers = dict(response.headers)
            content_type = response_headers.get('Content-Type', '').lower()
            content_length = len(response_body_bytes)

            # Determine if binary
            is_binary = (
                'image' in content_type or
                'video' in content_type or
                'audio' in content_type or
                'application/octet-stream' in content_type or
                'application/pdf' in content_type or
                'application/zip' in content_type or
                return_binary
            )

            # Convert to string
            if is_binary or return_binary:
                # Base64 encode binary data
                content = base64.b64encode(response_body_bytes).decode('ascii')
            else:
                # Decode as text
                try:
                    content = response_body_bytes.decode(encoding)
                except UnicodeDecodeError:
                    # Fallback to latin-1 if decoding fails
                    try:
                        content = response_body_bytes.decode('latin-1')
                    except:
                        # Last resort: base64 encode
                        content = base64.b64encode(response_body_bytes).decode('ascii')
                        is_binary = True

            return {
                "success": True,
                "status_code": response.status,
                "headers": response_headers,
                "content": content,
                "content_type": content_type,
                "content_length": content_length,
                "is_binary": is_binary,
                "url": url,
                "method": method.upper()
            }

    except urllib.error.HTTPError as e:
        # HTTP error (4xx, 5xx)
        error_body = ""
        try:
            error_body = e.read().decode('utf-8') if e.fp else ""
        except:
            error_body = str(e)

        return {
            "success": False,
            "status_code": e.code,
            "headers": dict(e.headers) if e.headers else {},
            "content": error_body,
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
        "url": "https://example.com/page.html",
        "method": "GET",  // Optional, default: GET
        "headers": {...},  // Optional
        "body": "raw text",  // Optional (raw string only)
        "timeout": 30,  // Optional, default: 30
        "encoding": "utf-8",  // Optional, default: utf-8
        "return_binary": false  // Optional, force base64 encoding
    }

    Output JSON:
    {
        "success": true,
        "status_code": 200,
        "headers": {...},
        "content": "raw content...",  // Raw string or base64
        "content_type": "text/html",
        "content_length": 1234,
        "is_binary": false
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
                    "url": "https://example.com",
                    "method": "GET"
                }
            }))
            sys.exit(1)

        method = input_data.get("method", "GET")
        headers = input_data.get("headers", {})
        body = input_data.get("body", None)
        timeout = input_data.get("timeout", 30)
        encoding = input_data.get("encoding", "utf-8")
        return_binary = input_data.get("return_binary", False)

        # Make request
        result = make_raw_http_request(
            url, method, headers, body, timeout, encoding, return_binary
        )

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
