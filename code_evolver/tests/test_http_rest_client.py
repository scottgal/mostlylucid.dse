#!/usr/bin/env python3
"""
Unit tests for http_rest_client.py tool.
Tests HTTP REST client functionality.
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from urllib.error import HTTPError, URLError
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.executable.http_rest_client import make_http_request


class TestHTTPRestClient(unittest.TestCase):
    """Test cases for HTTP REST client."""

    @patch('urllib.request.urlopen')
    def test_get_request_success(self, mock_urlopen):
        """Test successful GET request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"result": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://api.example.com/data", method="GET")

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["body"]["result"], "success")

    @patch('urllib.request.urlopen')
    def test_post_request_with_json_body(self, mock_urlopen):
        """Test POST request with JSON body."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"id": 123, "created": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        body = {"name": "Test", "value": 42}
        result = make_http_request(
            "https://api.example.com/create",
            method="POST",
            body=body
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 201)
        self.assertEqual(result["body"]["id"], 123)

    @patch('urllib.request.urlopen')
    def test_put_request(self, mock_urlopen):
        """Test PUT request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"updated": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        body = {"name": "Updated Name"}
        result = make_http_request(
            "https://api.example.com/update/1",
            method="PUT",
            body=body
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)

    @patch('urllib.request.urlopen')
    def test_delete_request(self, mock_urlopen):
        """Test DELETE request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.headers = {}
        mock_response.read.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request(
            "https://api.example.com/delete/1",
            method="DELETE"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 204)

    @patch('urllib.request.urlopen')
    def test_request_with_custom_headers(self, mock_urlopen):
        """Test request with custom headers."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{"result": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        headers = {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value"
        }

        result = make_http_request(
            "https://api.example.com/secure",
            method="GET",
            headers=headers
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)

    @patch('urllib.request.urlopen')
    def test_non_json_response(self, mock_urlopen):
        """Test handling of non-JSON response."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.read.return_value = b'Plain text response'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://api.example.com/text", method="GET")

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["body"], "Plain text response")
        self.assertIsInstance(result["body"], str)

    @patch('urllib.request.urlopen')
    def test_http_error_404(self, mock_urlopen):
        """Test handling of HTTP 404 error."""
        # Mock HTTP error
        mock_error = HTTPError(
            url="https://api.example.com/notfound",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=BytesIO(b'{"error": "Resource not found"}')
        )
        mock_urlopen.side_effect = mock_error

        result = make_http_request("https://api.example.com/notfound", method="GET")

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 404)
        self.assertIn("error", result)

    @patch('urllib.request.urlopen')
    def test_http_error_500(self, mock_urlopen):
        """Test handling of HTTP 500 error."""
        # Mock HTTP error
        mock_error = HTTPError(
            url="https://api.example.com/error",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=BytesIO(b'{"error": "Server error"}')
        )
        mock_urlopen.side_effect = mock_error

        result = make_http_request("https://api.example.com/error", method="GET")

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 500)
        self.assertIn("error", result)

    @patch('urllib.request.urlopen')
    def test_network_error(self, mock_urlopen):
        """Test handling of network error."""
        # Mock network error
        mock_urlopen.side_effect = URLError("Connection refused")

        result = make_http_request("https://api.example.com/unreachable", method="GET")

        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("Connection refused", result["error"])

    @patch('urllib.request.urlopen')
    def test_timeout_error(self, mock_urlopen):
        """Test handling of timeout error."""
        import socket
        mock_urlopen.side_effect = socket.timeout("Request timed out")

        result = make_http_request(
            "https://api.example.com/slow",
            method="GET",
            timeout=1
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch('urllib.request.urlopen')
    def test_request_with_string_body(self, mock_urlopen):
        """Test request with string body."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'OK'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        body = "raw string data"
        result = make_http_request(
            "https://api.example.com/upload",
            method="POST",
            body=body
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)

    @patch('urllib.request.urlopen')
    def test_request_with_bytes_body(self, mock_urlopen):
        """Test request with bytes body."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'OK'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        body = b"binary data"
        result = make_http_request(
            "https://api.example.com/upload",
            method="POST",
            body=body
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)


class TestHTTPRestClientEdgeCases(unittest.TestCase):
    """Test edge cases for HTTP REST client."""

    @patch('urllib.request.urlopen')
    def test_empty_response_body(self, mock_urlopen):
        """Test handling of empty response body."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b''
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://api.example.com/empty", method="GET")

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["body"], "")

    @patch('urllib.request.urlopen')
    def test_malformed_json_response(self, mock_urlopen):
        """Test handling of malformed JSON response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.read.return_value = b'{invalid json'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://api.example.com/malformed", method="GET")

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        # Should return raw string when JSON parsing fails
        self.assertIsInstance(result["body"], str)


if __name__ == "__main__":
    unittest.main()
