"""
HTTP Content Fetcher Tool for mostlylucid DiSE.

A comprehensive, flexible HTTP client that supports:
- All HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, etc.)
- All body types (JSON, form-data, multipart, XML, text, binary, custom)
- Various authentication methods
- Flexible response handling (JSON, text, binary, auto-detect)
- Retry logic and error handling
- Integration with DSE workflow system
"""

import json
import logging
import time
import base64
from typing import Dict, Any, Optional, Union, List, Tuple
from urllib.parse import urlencode, urlparse
from io import BytesIO

try:
    import requests
    from requests.auth import HTTPBasicAuth, HTTPDigestAuth
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    raise ImportError("requests library required: pip install requests")

logger = logging.getLogger(__name__)


class HTTPContentFetcher:
    """
    Comprehensive HTTP content fetcher supporting all methods, body types, and response formats.

    This tool is designed to integrate seamlessly with the DSE workflow system and can be
    called by other tools or workflow steps.

    Features:
    - All HTTP methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, TRACE
    - All body types: JSON, form-data, multipart, XML, text, binary, custom
    - Authentication: Bearer, API Key, Basic, Digest, Custom Headers
    - Response formats: JSON, text, binary, auto-detect
    - Retry logic with exponential backoff
    - Timeout configuration
    - Proxy support
    - Cookie handling
    - SSL/TLS configuration
    - Custom headers
    - Stream support for large files
    """

    SUPPORTED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE']

    CONTENT_TYPES = {
        'json': 'application/json',
        'form': 'application/x-www-form-urlencoded',
        'multipart': 'multipart/form-data',
        'xml': 'application/xml',
        'text': 'text/plain',
        'html': 'text/html',
        'binary': 'application/octet-stream',
    }

    def __init__(
        self,
        tool_id: str = "http_content_fetcher",
        name: str = "HTTP Content Fetcher",
        default_timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.3,
        verify_ssl: bool = True,
        proxies: Optional[Dict[str, str]] = None
    ):
        """
        Initialize HTTP Content Fetcher.

        Args:
            tool_id: Unique tool identifier
            name: Human-readable name
            default_timeout: Default request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Backoff factor for retries (exponential)
            verify_ssl: Whether to verify SSL certificates
            proxies: Proxy configuration dict {'http': '...', 'https': '...'}
        """
        self.tool_id = tool_id
        self.name = name
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.verify_ssl = verify_ssl
        self.proxies = proxies or {}

        # Create session with retry logic
        self.session = self._create_session()

        logger.info(f"Initialized {self.name} with timeout={default_timeout}s, max_retries={max_retries}")

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST", "PATCH"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def fetch(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[Dict, str, bytes]] = None,
        body_type: str = 'json',
        params: Optional[Dict[str, Any]] = None,
        auth: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        response_format: str = 'auto',
        stream: bool = False,
        allow_redirects: bool = True,
        cookies: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch content from a URL with comprehensive configuration options.

        Args:
            url: Target URL
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, TRACE)
            headers: Custom headers dict
            body: Request body (dict, str, or bytes)
            body_type: Body content type ('json', 'form', 'multipart', 'xml', 'text', 'binary', 'custom')
            params: URL query parameters
            auth: Authentication config
                Examples:
                - {'type': 'bearer', 'token': '...'}
                - {'type': 'api_key', 'key': '...', 'header': 'X-API-Key'}
                - {'type': 'basic', 'username': '...', 'password': '...'}
                - {'type': 'digest', 'username': '...', 'password': '...'}
                - {'type': 'custom', 'headers': {'Authorization': '...'}}
            timeout: Request timeout in seconds (overrides default)
            response_format: Expected response format ('auto', 'json', 'text', 'binary')
            stream: Whether to stream the response (for large files)
            allow_redirects: Whether to follow redirects
            cookies: Cookies dict
            files: Files for multipart upload {'field_name': file_path or file_object}

        Returns:
            Dict with response data:
            {
                'success': bool,
                'status_code': int,
                'headers': dict,
                'data': Any (parsed based on response_format),
                'content_type': str,
                'encoding': str,
                'url': str (final URL after redirects),
                'elapsed_ms': float,
                'error': str or None
            }
        """
        method = method.upper()

        # Validate method
        if method not in self.SUPPORTED_METHODS:
            return self._error_response(f"Unsupported HTTP method: {method}")

        # Validate URL
        if not url or not self._is_valid_url(url):
            return self._error_response(f"Invalid URL: {url}")

        # Prepare request
        timeout = timeout or self.default_timeout
        headers = headers or {}
        auth_obj = None

        # Handle authentication
        if auth:
            auth_obj, auth_headers = self._prepare_auth(auth)
            headers.update(auth_headers)

        # Prepare body and content-type
        prepared_body, content_type_header = self._prepare_body(body, body_type, files)

        # Set content-type header if not already set
        if content_type_header and 'Content-Type' not in headers and 'content-type' not in headers:
            headers['Content-Type'] = content_type_header

        # Make request
        start_time = time.time()

        try:
            logger.info(f"Fetching {method} {url}")

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=prepared_body if body_type != 'json' and not files else None,
                json=prepared_body if body_type == 'json' and not files else None,
                params=params,
                auth=auth_obj,
                timeout=timeout,
                verify=self.verify_ssl,
                proxies=self.proxies,
                stream=stream,
                allow_redirects=allow_redirects,
                cookies=cookies,
                files=files
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Parse response
            result = self._parse_response(response, response_format, stream)
            result['elapsed_ms'] = elapsed_ms

            logger.info(f"Request completed: {method} {url} -> {response.status_code} ({elapsed_ms:.2f}ms)")

            return result

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {url} ({timeout}s)")
            return self._error_response(f"Request timeout after {timeout}s", exception=e)

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {url}")
            return self._error_response("Connection error", exception=e)

        except requests.exceptions.TooManyRedirects as e:
            logger.error(f"Too many redirects: {url}")
            return self._error_response("Too many redirects", exception=e)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {e}")
            return self._error_response("Request failed", exception=e)

        except Exception as e:
            logger.error(f"Unexpected error: {url} - {e}")
            return self._error_response("Unexpected error", exception=e)

    def _prepare_auth(self, auth_config: Dict[str, Any]) -> Tuple[Optional[Any], Dict[str, str]]:
        """
        Prepare authentication object and headers.

        Returns:
            Tuple of (auth_object, headers_dict)
        """
        auth_type = auth_config.get('type', '').lower()
        headers = {}
        auth_obj = None

        if auth_type == 'bearer':
            token = auth_config.get('token', '')
            headers['Authorization'] = f'Bearer {token}'

        elif auth_type == 'api_key':
            key = auth_config.get('key', '')
            header_name = auth_config.get('header', 'X-API-Key')
            headers[header_name] = key

        elif auth_type == 'basic':
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            auth_obj = HTTPBasicAuth(username, password)

        elif auth_type == 'digest':
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            auth_obj = HTTPDigestAuth(username, password)

        elif auth_type == 'custom':
            custom_headers = auth_config.get('headers', {})
            headers.update(custom_headers)

        return auth_obj, headers

    def _prepare_body(
        self,
        body: Optional[Union[Dict, str, bytes]],
        body_type: str,
        files: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Union[Dict, str, bytes]], Optional[str]]:
        """
        Prepare request body based on content type.

        Returns:
            Tuple of (prepared_body, content_type_header)
        """
        if body is None and not files:
            return None, None

        body_type = body_type.lower()

        # Handle multipart with files
        if files:
            # Don't set content-type for multipart - requests will set it with boundary
            return body, None

        # JSON
        if body_type == 'json':
            if isinstance(body, (dict, list)):
                return body, self.CONTENT_TYPES['json']
            elif isinstance(body, str):
                # Validate JSON string
                try:
                    json.loads(body)
                    return body, self.CONTENT_TYPES['json']
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON string, sending as-is")
                    return body, self.CONTENT_TYPES['json']

        # Form-encoded
        elif body_type == 'form':
            if isinstance(body, dict):
                return urlencode(body), self.CONTENT_TYPES['form']
            elif isinstance(body, str):
                return body, self.CONTENT_TYPES['form']

        # XML
        elif body_type == 'xml':
            if isinstance(body, str):
                return body, self.CONTENT_TYPES['xml']
            elif isinstance(body, bytes):
                return body, self.CONTENT_TYPES['xml']

        # Text
        elif body_type == 'text':
            if isinstance(body, str):
                return body, self.CONTENT_TYPES['text']
            elif isinstance(body, bytes):
                return body.decode('utf-8'), self.CONTENT_TYPES['text']

        # Binary
        elif body_type == 'binary':
            if isinstance(body, bytes):
                return body, self.CONTENT_TYPES['binary']
            elif isinstance(body, str):
                return body.encode('utf-8'), self.CONTENT_TYPES['binary']

        # Custom - use as-is
        elif body_type == 'custom':
            return body, None

        # Default - try to be smart
        if isinstance(body, dict):
            return body, self.CONTENT_TYPES['json']
        elif isinstance(body, bytes):
            return body, self.CONTENT_TYPES['binary']
        else:
            return str(body), self.CONTENT_TYPES['text']

    def _parse_response(
        self,
        response: requests.Response,
        response_format: str,
        stream: bool
    ) -> Dict[str, Any]:
        """Parse HTTP response into standardized format."""
        result = {
            'success': response.ok,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content_type': response.headers.get('Content-Type', ''),
            'encoding': response.encoding,
            'url': response.url,
            'data': None,
            'error': None
        }

        # For HEAD requests, no body
        if response.request.method == 'HEAD':
            return result

        # Handle streaming responses
        if stream:
            result['data'] = {
                'stream': True,
                'message': 'Response is being streamed. Use response.iter_content() to read.'
            }
            result['stream_response'] = response
            return result

        # Parse based on response format
        response_format = response_format.lower()

        try:
            # Auto-detect format
            if response_format == 'auto':
                content_type = result['content_type'].lower()

                if 'application/json' in content_type or 'application/javascript' in content_type:
                    result['data'] = response.json()
                elif 'text/' in content_type or 'application/xml' in content_type or 'application/xhtml' in content_type:
                    result['data'] = response.text
                else:
                    # Binary data - encode as base64 for JSON serialization
                    result['data'] = base64.b64encode(response.content).decode('utf-8')
                    result['data_encoding'] = 'base64'

            # Explicit JSON
            elif response_format == 'json':
                result['data'] = response.json()

            # Explicit text
            elif response_format == 'text':
                result['data'] = response.text

            # Explicit binary (base64 encoded)
            elif response_format == 'binary':
                result['data'] = base64.b64encode(response.content).decode('utf-8')
                result['data_encoding'] = 'base64'

            else:
                result['data'] = response.text

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            result['data'] = response.text
            result['error'] = f"JSON parse error: {e}"

        except Exception as e:
            logger.warning(f"Failed to parse response: {e}")
            result['data'] = response.text
            result['error'] = f"Parse error: {e}"

        # Add error message for failed requests
        if not result['success'] and not result['error']:
            result['error'] = f"HTTP {response.status_code}: {response.reason}"

        return result

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _error_response(self, message: str, exception: Optional[Exception] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        error_msg = message
        if exception:
            error_msg = f"{message}: {str(exception)}"

        return {
            'success': False,
            'status_code': 0,
            'headers': {},
            'content_type': '',
            'encoding': None,
            'url': '',
            'data': None,
            'error': error_msg,
            'elapsed_ms': 0
        }

    # Convenience methods for common operations

    def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for GET requests."""
        return self.fetch(url, method='GET', **kwargs)

    def post(self, url: str, body: Optional[Union[Dict, str, bytes]] = None, **kwargs) -> Dict[str, Any]:
        """Convenience method for POST requests."""
        return self.fetch(url, method='POST', body=body, **kwargs)

    def put(self, url: str, body: Optional[Union[Dict, str, bytes]] = None, **kwargs) -> Dict[str, Any]:
        """Convenience method for PUT requests."""
        return self.fetch(url, method='PUT', body=body, **kwargs)

    def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for DELETE requests."""
        return self.fetch(url, method='DELETE', **kwargs)

    def patch(self, url: str, body: Optional[Union[Dict, str, bytes]] = None, **kwargs) -> Dict[str, Any]:
        """Convenience method for PATCH requests."""
        return self.fetch(url, method='PATCH', body=body, **kwargs)

    def head(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for HEAD requests."""
        return self.fetch(url, method='HEAD', **kwargs)

    def download_file(
        self,
        url: str,
        save_path: Optional[str] = None,
        chunk_size: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download a file from URL.

        Args:
            url: URL to download from
            save_path: Path to save file (optional, returns bytes if not provided)
            chunk_size: Chunk size for streaming download
            **kwargs: Additional arguments for fetch()

        Returns:
            Dict with download result
        """
        result = self.fetch(url, method='GET', stream=True, **kwargs)

        if not result['success']:
            return result

        try:
            response = result.get('stream_response')

            if save_path:
                # Save to file
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)

                result['data'] = {
                    'saved': True,
                    'path': save_path,
                    'size_bytes': response.headers.get('Content-Length', 'unknown')
                }
                logger.info(f"File downloaded to {save_path}")

            else:
                # Return bytes
                content = b''.join([chunk for chunk in response.iter_content(chunk_size=chunk_size)])
                result['data'] = base64.b64encode(content).decode('utf-8')
                result['data_encoding'] = 'base64'
                result['size_bytes'] = len(content)

        except Exception as e:
            result['success'] = False
            result['error'] = f"Download failed: {e}"
            logger.error(f"Download failed: {e}")

        return result

    def upload_file(
        self,
        url: str,
        file_path: str,
        field_name: str = 'file',
        additional_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upload a file to URL.

        Args:
            url: URL to upload to
            file_path: Path to file to upload
            field_name: Form field name for file
            additional_data: Additional form data to send
            **kwargs: Additional arguments for fetch()

        Returns:
            Dict with upload result
        """
        try:
            with open(file_path, 'rb') as f:
                files = {field_name: f}
                return self.fetch(
                    url,
                    method='POST',
                    body=additional_data,
                    files=files,
                    **kwargs
                )
        except Exception as e:
            return self._error_response(f"File upload failed", exception=e)

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("HTTP session closed")


# Factory function for easy instantiation
def create_http_fetcher(**kwargs) -> HTTPContentFetcher:
    """
    Factory function to create HTTPContentFetcher instance.

    Args:
        **kwargs: Arguments to pass to HTTPContentFetcher constructor

    Returns:
        HTTPContentFetcher instance
    """
    return HTTPContentFetcher(**kwargs)
