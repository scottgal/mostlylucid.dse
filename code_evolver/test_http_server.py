#!/usr/bin/env python3
"""
Quick test script for HTTP Server Tool.
Tests basic functionality without requiring full workflow system.
"""

import sys
import time
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.http_server_tool import HTTPServerTool


def test_basic_server():
    """Test basic HTTP server functionality."""
    print("Testing HTTP Server Tool...")
    print("=" * 50)

    # Create server
    print("\n1. Creating server...")
    server = HTTPServerTool(host="127.0.0.1", port=8083)
    print(f"   ✓ Server created")

    # Add JSON endpoint
    print("\n2. Adding JSON endpoint...")

    def json_handler(request_data):
        return {
            "status": "success",
            "message": "Hello from HTTP Server Tool!",
            "request_method": request_data.get("method"),
            "timestamp": time.time()
        }

    server.add_route(
        path="/api/test",
        methods=["GET", "POST"],
        handler=json_handler,
        response_type="json",
        description="Test JSON endpoint"
    )
    print(f"   ✓ Route added: /api/test")

    # Add HTML endpoint
    print("\n3. Adding HTML endpoint...")

    def html_handler(request_data):
        return "<h1>HTTP Server Tool Test</h1><p>Server is working!</p>"

    server.add_route(
        path="/",
        methods=["GET"],
        handler=html_handler,
        response_type="html",
        description="Test HTML endpoint"
    )
    print(f"   ✓ Route added: /")

    # Get server info
    print("\n4. Getting server info...")
    info = server.get_server_info()
    print(f"   ✓ Host: {info['host']}")
    print(f"   ✓ Port: {info['port']}")
    print(f"   ✓ URL: {info['url']}")
    print(f"   ✓ Routes: {info['routes_count']}")

    # List routes
    print("\n5. Listing routes...")
    for route in server.list_routes():
        print(f"   ✓ {route['methods']} {route['path']} ({route['response_type']})")

    # Start server
    print("\n6. Starting server (non-blocking)...")
    server.start(blocking=False)
    print(f"   ✓ Server started")

    # Wait for server to be ready
    time.sleep(1)

    # Test endpoints
    print("\n7. Testing endpoints...")

    try:
        # Test JSON endpoint with GET
        print("\n   a) Testing GET /api/test...")
        response = requests.get("http://127.0.0.1:8083/api/test", timeout=5)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "success", f"Expected success, got {data['status']}"
        print(f"      ✓ Status: {response.status_code}")
        print(f"      ✓ Response: {data}")

        # Test JSON endpoint with POST
        print("\n   b) Testing POST /api/test...")
        response = requests.post(
            "http://127.0.0.1:8083/api/test",
            json={"test": "data"},
            timeout=5
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"      ✓ Status: {response.status_code}")
        print(f"      ✓ Response: {data}")

        # Test HTML endpoint
        print("\n   c) Testing GET /...")
        response = requests.get("http://127.0.0.1:8083/", timeout=5)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "HTTP Server Tool Test" in response.text, "Expected HTML content"
        print(f"      ✓ Status: {response.status_code}")
        print(f"      ✓ Content type: {response.headers.get('Content-Type')}")
        print(f"      ✓ HTML received (length: {len(response.text)})")

        print("\n8. All tests passed! ✓")

    except requests.exceptions.RequestException as e:
        print(f"\n   ✗ Request failed: {e}")
        return False
    except AssertionError as e:
        print(f"\n   ✗ Assertion failed: {e}")
        return False
    finally:
        # Stop server
        print("\n9. Stopping server...")
        server.stop()
        print(f"   ✓ Server stopped")

    print("\n" + "=" * 50)
    print("HTTP Server Tool Test: SUCCESS ✓")
    print("=" * 50)
    return True


def test_error_handling():
    """Test error handling in handlers."""
    print("\n\nTesting Error Handling...")
    print("=" * 50)

    server = HTTPServerTool(host="127.0.0.1", port=8084)

    # Add handler that raises exception
    def error_handler(request_data):
        raise ValueError("Intentional test error")

    server.add_route(
        path="/api/error",
        methods=["GET"],
        handler=error_handler,
        response_type="json",
        description="Error test endpoint"
    )

    server.start(blocking=False)
    time.sleep(1)

    try:
        print("\n1. Testing error handling...")
        response = requests.get("http://127.0.0.1:8084/api/error", timeout=5)

        # Should return 500 error
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        data = response.json()
        assert "error" in data, "Expected error field in response"
        print(f"   ✓ Error handled correctly")
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Error message: {data.get('error')}")

        print("\nError Handling Test: SUCCESS ✓")
        return True

    except Exception as e:
        print(f"\n   ✗ Test failed: {e}")
        return False
    finally:
        server.stop()
        print("   ✓ Server stopped")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 48 + "╗")
    print("║" + " " * 10 + "HTTP Server Tool - Test Suite" + " " * 8 + "║")
    print("╚" + "═" * 48 + "╝")

    # Check if Flask is installed
    try:
        import flask
        print("\n✓ Flask is installed")
    except ImportError:
        print("\n✗ Flask is not installed")
        print("Please install it with: pip install flask")
        return False

    # Check if requests is installed
    try:
        import requests
        print("✓ Requests is installed")
    except ImportError:
        print("\n✗ Requests is not installed")
        print("Please install it with: pip install requests")
        return False

    # Run tests
    all_passed = True

    if not test_basic_server():
        all_passed = False

    if not test_error_handling():
        all_passed = False

    # Summary
    print("\n\n")
    print("╔" + "═" * 48 + "╗")
    if all_passed:
        print("║" + " " * 12 + "ALL TESTS PASSED ✓" + " " * 17 + "║")
    else:
        print("║" + " " * 12 + "SOME TESTS FAILED ✗" + " " * 15 + "║")
    print("╚" + "═" * 48 + "╝")
    print("\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
