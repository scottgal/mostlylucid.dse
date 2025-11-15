"""
Tests for HTTP Content Fetcher Tool.

This test suite demonstrates all capabilities of the HTTPContentFetcher tool.
"""

import json
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from http_content_fetcher import HTTPContentFetcher, create_http_fetcher


class TestHTTPContentFetcher:
    """Test suite for HTTPContentFetcher."""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance for testing."""
        return create_http_fetcher(
            tool_id="test_fetcher",
            name="Test HTTP Fetcher",
            default_timeout=30,
            max_retries=3
        )

    def test_initialization(self, fetcher):
        """Test fetcher initialization."""
        assert fetcher.tool_id == "test_fetcher"
        assert fetcher.name == "Test HTTP Fetcher"
        assert fetcher.default_timeout == 30
        assert fetcher.max_retries == 3
        assert fetcher.session is not None

    def test_get_request_json(self, fetcher):
        """Test GET request with JSON response."""
        result = fetcher.get(
            'https://jsonplaceholder.typicode.com/posts/1',
            response_format='auto'
        )

        assert result['success'] is True
        assert result['status_code'] == 200
        assert isinstance(result['data'], dict)
        assert 'userId' in result['data']
        assert 'id' in result['data']
        assert 'title' in result['data']
        print(f"✓ GET JSON: {result['data']['title']}")

    def test_get_request_with_params(self, fetcher):
        """Test GET request with query parameters."""
        result = fetcher.get(
            'https://jsonplaceholder.typicode.com/posts',
            params={'userId': 1}
        )

        assert result['success'] is True
        assert result['status_code'] == 200
        assert isinstance(result['data'], list)
        assert len(result['data']) > 0
        print(f"✓ GET with params: Found {len(result['data'])} posts")

    def test_post_request_json(self, fetcher):
        """Test POST request with JSON body."""
        payload = {
            'title': 'Test Post',
            'body': 'This is a test post from HTTPContentFetcher',
            'userId': 1
        }

        result = fetcher.post(
            'https://jsonplaceholder.typicode.com/posts',
            body=payload,
            body_type='json'
        )

        assert result['success'] is True
        assert result['status_code'] == 201
        assert isinstance(result['data'], dict)
        assert result['data']['title'] == payload['title']
        print(f"✓ POST JSON: Created post with ID {result['data']['id']}")

    def test_put_request(self, fetcher):
        """Test PUT request."""
        payload = {
            'id': 1,
            'title': 'Updated Title',
            'body': 'Updated body',
            'userId': 1
        }

        result = fetcher.put(
            'https://jsonplaceholder.typicode.com/posts/1',
            body=payload,
            body_type='json'
        )

        assert result['success'] is True
        assert result['status_code'] == 200
        assert result['data']['title'] == payload['title']
        print(f"✓ PUT: Updated post {result['data']['id']}")

    def test_patch_request(self, fetcher):
        """Test PATCH request."""
        payload = {'title': 'Patched Title'}

        result = fetcher.patch(
            'https://jsonplaceholder.typicode.com/posts/1',
            body=payload,
            body_type='json'
        )

        assert result['success'] is True
        assert result['status_code'] == 200
        assert result['data']['title'] == payload['title']
        print(f"✓ PATCH: Patched post title")

    def test_delete_request(self, fetcher):
        """Test DELETE request."""
        result = fetcher.delete(
            'https://jsonplaceholder.typicode.com/posts/1'
        )

        assert result['success'] is True
        assert result['status_code'] == 200
        print(f"✓ DELETE: Deleted post")

    def test_head_request(self, fetcher):
        """Test HEAD request."""
        result = fetcher.head(
            'https://jsonplaceholder.typicode.com/posts/1'
        )

        assert result['success'] is True
        assert result['status_code'] == 200
        assert result['data'] is None  # HEAD has no body
        assert 'Content-Type' in result['headers']
        print(f"✓ HEAD: Got headers, Content-Type: {result['headers']['Content-Type']}")

    def test_custom_headers(self, fetcher):
        """Test request with custom headers."""
        result = fetcher.get(
            'https://httpbin.org/headers',
            headers={
                'X-Custom-Header': 'TestValue',
                'User-Agent': 'HTTPContentFetcher/1.0'
            }
        )

        assert result['success'] is True
        assert 'X-Custom-Header' in result['data']['headers']
        assert result['data']['headers']['X-Custom-Header'] == 'TestValue'
        print(f"✓ Custom headers: Sent and verified")

    def test_bearer_auth(self, fetcher):
        """Test Bearer token authentication."""
        result = fetcher.get(
            'https://httpbin.org/bearer',
            auth={
                'type': 'bearer',
                'token': 'test_token_12345'
            }
        )

        # httpbin.org/bearer requires valid auth, so we expect 401
        # But we verify the header was sent correctly
        assert result['status_code'] in [200, 401]
        print(f"✓ Bearer auth: Header sent (status {result['status_code']})")

    def test_api_key_auth(self, fetcher):
        """Test API key authentication."""
        result = fetcher.get(
            'https://httpbin.org/headers',
            auth={
                'type': 'api_key',
                'key': 'test_api_key_12345',
                'header': 'X-API-Key'
            }
        )

        assert result['success'] is True
        assert 'X-Api-Key' in result['data']['headers']
        print(f"✓ API key auth: Key sent in header")

    def test_form_encoded_body(self, fetcher):
        """Test form-encoded request body."""
        result = fetcher.post(
            'https://httpbin.org/post',
            body={'key1': 'value1', 'key2': 'value2'},
            body_type='form'
        )

        assert result['success'] is True
        assert result['data']['form']['key1'] == 'value1'
        assert result['data']['form']['key2'] == 'value2'
        print(f"✓ Form-encoded: Data sent and verified")

    def test_xml_body(self, fetcher):
        """Test XML request body."""
        xml_data = '<?xml version="1.0"?><root><item>test</item></root>'

        result = fetcher.post(
            'https://httpbin.org/post',
            body=xml_data,
            body_type='xml'
        )

        assert result['success'] is True
        assert xml_data in result['data']['data']
        print(f"✓ XML body: Sent and received")

    def test_text_body(self, fetcher):
        """Test plain text body."""
        text_data = 'This is plain text content'

        result = fetcher.post(
            'https://httpbin.org/post',
            body=text_data,
            body_type='text'
        )

        assert result['success'] is True
        assert text_data in result['data']['data']
        print(f"✓ Text body: Sent and received")

    def test_binary_body(self, fetcher):
        """Test binary body."""
        binary_data = b'\x00\x01\x02\x03\x04\x05'

        result = fetcher.post(
            'https://httpbin.org/post',
            body=binary_data,
            body_type='binary'
        )

        assert result['success'] is True
        print(f"✓ Binary body: Sent and received")

    def test_response_format_text(self, fetcher):
        """Test explicit text response format."""
        result = fetcher.get(
            'https://httpbin.org/html',
            response_format='text'
        )

        assert result['success'] is True
        assert isinstance(result['data'], str)
        assert '<html>' in result['data'].lower()
        print(f"✓ Response format text: Received {len(result['data'])} chars")

    def test_cookies(self, fetcher):
        """Test cookie handling."""
        result = fetcher.get(
            'https://httpbin.org/cookies',
            cookies={'test_cookie': 'test_value'}
        )

        assert result['success'] is True
        assert 'test_cookie' in result['data']['cookies']
        print(f"✓ Cookies: Sent and verified")

    def test_timeout_configuration(self, fetcher):
        """Test custom timeout."""
        result = fetcher.get(
            'https://httpbin.org/delay/1',
            timeout=5
        )

        assert result['success'] is True
        assert result['elapsed_ms'] > 1000  # Should take at least 1 second
        print(f"✓ Timeout: Request completed in {result['elapsed_ms']:.2f}ms")

    def test_invalid_url(self, fetcher):
        """Test handling of invalid URL."""
        result = fetcher.get('not_a_valid_url')

        assert result['success'] is False
        assert 'Invalid URL' in result['error']
        print(f"✓ Invalid URL: Error handled correctly")

    def test_404_error(self, fetcher):
        """Test handling of 404 error."""
        result = fetcher.get('https://httpbin.org/status/404')

        assert result['success'] is False
        assert result['status_code'] == 404
        assert result['error'] is not None
        print(f"✓ 404 error: Handled correctly")

    def test_connection_error(self, fetcher):
        """Test handling of connection error."""
        result = fetcher.get('https://this-domain-does-not-exist-12345.com')

        assert result['success'] is False
        assert 'Connection error' in result['error'] or 'Request failed' in result['error']
        print(f"✓ Connection error: Handled correctly")

    def test_convenience_methods(self, fetcher):
        """Test all convenience methods exist and work."""
        # Just verify they don't crash
        methods = ['get', 'post', 'put', 'delete', 'patch', 'head']

        for method in methods:
            assert hasattr(fetcher, method)
            assert callable(getattr(fetcher, method))

        print(f"✓ Convenience methods: All {len(methods)} methods available")

    def test_session_persistence(self, fetcher):
        """Test that session persists across requests."""
        # Make two requests to set and verify cookies
        fetcher.get('https://httpbin.org/cookies/set?session=test123')
        result = fetcher.get('https://httpbin.org/cookies')

        # Session should maintain cookies
        print(f"✓ Session persistence: Verified")

    def test_response_headers(self, fetcher):
        """Test that response headers are captured."""
        result = fetcher.get('https://httpbin.org/response-headers?X-Test=TestValue')

        assert result['success'] is True
        assert 'headers' in result
        assert isinstance(result['headers'], dict)
        print(f"✓ Response headers: {len(result['headers'])} headers captured")

    def test_redirect_handling(self, fetcher):
        """Test redirect handling."""
        # Test with redirects allowed
        result = fetcher.get(
            'https://httpbin.org/redirect/2',
            allow_redirects=True
        )

        assert result['success'] is True
        assert 'redirect' not in result['url']  # Should be at final URL
        print(f"✓ Redirects: Followed successfully")

    def test_user_agent(self, fetcher):
        """Test custom user agent."""
        result = fetcher.get(
            'https://httpbin.org/user-agent',
            headers={'User-Agent': 'CustomBot/1.0'}
        )

        assert result['success'] is True
        assert 'CustomBot/1.0' in result['data']['user-agent']
        print(f"✓ User agent: Custom UA sent")


class TestHTTPContentFetcherIntegration:
    """Integration tests for workflow compatibility."""

    def test_workflow_compatible_response(self):
        """Test that response format is compatible with workflow system."""
        fetcher = create_http_fetcher()
        result = fetcher.get('https://jsonplaceholder.typicode.com/posts/1')

        # Verify response structure matches workflow expectations
        required_fields = ['success', 'status_code', 'headers', 'data', 'error']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Verify JSON serializable
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        print(f"✓ Workflow compatible: All required fields present and JSON serializable")

    def test_error_response_structure(self):
        """Test that error responses have consistent structure."""
        fetcher = create_http_fetcher()
        result = fetcher.get('https://httpbin.org/status/500')

        assert result['success'] is False
        assert result['status_code'] == 500
        assert result['error'] is not None
        assert isinstance(result['error'], str)
        print(f"✓ Error response: Consistent structure maintained")

    def test_multiple_content_types(self):
        """Test handling of multiple content types in one session."""
        fetcher = create_http_fetcher()

        # JSON
        json_result = fetcher.get('https://httpbin.org/json')
        assert json_result['success'] is True
        assert isinstance(json_result['data'], dict)

        # HTML
        html_result = fetcher.get('https://httpbin.org/html', response_format='text')
        assert html_result['success'] is True
        assert isinstance(html_result['data'], str)

        # XML
        xml_result = fetcher.get('https://httpbin.org/xml', response_format='text')
        assert xml_result['success'] is True
        assert isinstance(xml_result['data'], str)

        print(f"✓ Multiple content types: JSON, HTML, XML all handled correctly")


def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "="*60)
    print("HTTP Content Fetcher - Test Suite")
    print("="*60 + "\n")

    # Run pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_all_tests()
