# HTTP Content Fetcher

A comprehensive, flexible HTTP client tool for the Code Evolver DSE (Domain Specific Engine) system.

## Overview

The HTTP Content Fetcher is a production-ready tool that provides complete HTTP/REST API capabilities with seamless integration into the DSE workflow system. It supports all HTTP methods, all body types, various authentication methods, and flexible response handling.

## Features

### 🌐 All HTTP Methods
- **GET** - Retrieve resources
- **POST** - Create resources
- **PUT** - Update resources
- **DELETE** - Remove resources
- **PATCH** - Partial updates
- **HEAD** - Get headers only
- **OPTIONS** - Check available methods
- **TRACE** - Debug/diagnostic requests

### 📦 All Body Types
- **JSON** (`application/json`) - Automatic serialization
- **Form-encoded** (`application/x-www-form-urlencoded`) - URL-encoded forms
- **Multipart** (`multipart/form-data`) - File uploads with form data
- **XML** (`application/xml`) - XML documents
- **Text** (`text/plain`) - Plain text content
- **Binary** (`application/octet-stream`) - Binary data
- **Custom** - Any custom content type

### 🔐 Authentication Methods
- **Bearer Token** - OAuth 2.0 / JWT tokens
- **API Key** - Custom API key headers
- **Basic Auth** - HTTP Basic Authentication
- **Digest Auth** - HTTP Digest Authentication
- **Custom Headers** - Any custom authentication scheme

### 📊 Response Formats
- **Auto-detect** - Automatically parse based on Content-Type
- **JSON** - Parse JSON responses
- **Text** - Get response as text
- **Binary** - Get response as base64-encoded binary

### ⚡ Advanced Features
- **Retry Logic** - Automatic retry with exponential backoff
- **Timeout Control** - Configurable request timeouts
- **Streaming** - Support for large file downloads
- **File Upload** - Simple file upload interface
- **Cookie Handling** - Automatic cookie management
- **SSL/TLS** - Configurable SSL verification
- **Proxy Support** - HTTP/HTTPS proxy configuration
- **Redirect Control** - Enable/disable redirect following
- **Response Timing** - Measure request elapsed time
- **Session Persistence** - Maintain session across requests

## Installation

The HTTP Content Fetcher is already integrated into the Code Evolver system. No additional installation required.

### Dependencies

```bash
pip install requests
```

## Usage

### Basic Usage

```python
from http_content_fetcher import create_http_fetcher

# Create fetcher instance
fetcher = create_http_fetcher()

# Simple GET request
result = fetcher.get('https://api.example.com/data')

if result['success']:
    print(result['data'])
else:
    print(f"Error: {result['error']}")
```

### POST with JSON Body

```python
# POST request with JSON
payload = {
    'name': 'John Doe',
    'email': 'john@example.com'
}

result = fetcher.post(
    'https://api.example.com/users',
    body=payload,
    body_type='json'
)

print(f"Created user ID: {result['data']['id']}")
```

### Authentication

```python
# Bearer token
result = fetcher.get(
    'https://api.example.com/protected',
    auth={
        'type': 'bearer',
        'token': 'your_access_token_here'
    }
)

# API Key
result = fetcher.get(
    'https://api.example.com/data',
    auth={
        'type': 'api_key',
        'key': 'your_api_key',
        'header': 'X-API-Key'
    }
)

# Basic Auth
result = fetcher.get(
    'https://api.example.com/data',
    auth={
        'type': 'basic',
        'username': 'user',
        'password': 'pass'
    }
)
```

### Query Parameters

```python
result = fetcher.get(
    'https://api.example.com/search',
    params={
        'q': 'python',
        'page': 1,
        'limit': 10
    }
)
```

### Custom Headers

```python
result = fetcher.get(
    'https://api.example.com/data',
    headers={
        'User-Agent': 'MyApp/1.0',
        'Accept': 'application/json',
        'X-Custom-Header': 'value'
    }
)
```

### Different Body Types

```python
# Form-encoded
result = fetcher.post(
    'https://api.example.com/form',
    body={'field1': 'value1', 'field2': 'value2'},
    body_type='form'
)

# XML
xml_data = '<?xml version="1.0"?><root><item>test</item></root>'
result = fetcher.post(
    'https://api.example.com/xml',
    body=xml_data,
    body_type='xml'
)

# Plain text
result = fetcher.post(
    'https://api.example.com/text',
    body='This is plain text',
    body_type='text'
)
```

### File Upload

```python
# Upload a file
result = fetcher.upload_file(
    url='https://api.example.com/upload',
    file_path='/path/to/file.pdf',
    field_name='document',
    additional_data={'description': 'Important document'}
)
```

### File Download

```python
# Download to file
result = fetcher.download_file(
    url='https://example.com/large-file.zip',
    save_path='/path/to/save/file.zip'
)

# Download to memory (base64 encoded)
result = fetcher.download_file(
    url='https://example.com/file.pdf'
)
binary_data = base64.b64decode(result['data'])
```

### Advanced Configuration

```python
# Create fetcher with custom settings
fetcher = create_http_fetcher(
    default_timeout=60,
    max_retries=5,
    retry_backoff_factor=0.5,
    verify_ssl=True,
    proxies={
        'http': 'http://proxy.example.com:8080',
        'https': 'https://proxy.example.com:8080'
    }
)
```

### Workflow Integration

```python
# Use in DSE workflow steps
fetcher = create_http_fetcher(
    tool_id="api_client",
    name="External API Client"
)

# Step 1: Fetch user data
user_result = fetcher.get('https://api.example.com/users/123')

if user_result['success']:
    user = user_result['data']

    # Step 2: Use data from Step 1 in Step 2
    posts_result = fetcher.get(
        'https://api.example.com/posts',
        params={'userId': user['id']}
    )

    if posts_result['success']:
        posts = posts_result['data']

        # Step 3: Process and create new resource
        summary_result = fetcher.post(
            'https://api.example.com/summaries',
            body={
                'user_id': user['id'],
                'post_count': len(posts),
                'summary': f"User {user['name']} has {len(posts)} posts"
            }
        )
```

## Response Format

All methods return a standardized response dictionary:

```python
{
    'success': bool,              # True if request succeeded (status < 400)
    'status_code': int,           # HTTP status code (e.g., 200, 404, 500)
    'headers': dict,              # Response headers
    'content_type': str,          # Content-Type header value
    'encoding': str,              # Response encoding (e.g., 'utf-8')
    'url': str,                   # Final URL (after redirects)
    'data': Any,                  # Parsed response data
    'error': str or None,         # Error message if failed
    'elapsed_ms': float           # Request duration in milliseconds
}
```

## Error Handling

The tool handles errors gracefully and always returns a consistent response format:

```python
result = fetcher.get('https://invalid-url.example.com')

if not result['success']:
    print(f"Request failed: {result['error']}")
    print(f"Status code: {result['status_code']}")
```

Common error scenarios:
- **Invalid URL** - Malformed URL
- **Connection Error** - Cannot connect to server
- **Timeout** - Request exceeded timeout duration
- **HTTP Errors** - 4xx and 5xx status codes
- **SSL Errors** - Certificate verification failures

## Configuration Options

### Fetch Method Parameters

```python
fetcher.fetch(
    url='https://api.example.com/endpoint',
    method='GET',                                    # HTTP method
    headers={'Custom': 'Header'},                    # Custom headers
    body={'key': 'value'},                          # Request body
    body_type='json',                               # Body content type
    params={'query': 'param'},                      # URL parameters
    auth={'type': 'bearer', 'token': '...'},        # Authentication
    timeout=30,                                     # Timeout in seconds
    response_format='auto',                         # Response format
    stream=False,                                   # Stream response
    allow_redirects=True,                           # Follow redirects
    cookies={'session': 'value'},                   # Cookies
    files={'field': '/path/to/file'}                # File upload
)
```

### Timeout Configuration

```python
# Per-request timeout
result = fetcher.get('https://api.example.com/slow', timeout=60)

# Default timeout at creation
fetcher = create_http_fetcher(default_timeout=30)
```

### Retry Configuration

```python
fetcher = create_http_fetcher(
    max_retries=5,              # Number of retry attempts
    retry_backoff_factor=0.5    # Exponential backoff (0.5s, 1s, 2s, 4s, 8s)
)
```

## Convenience Methods

Convenience methods for common HTTP operations:

```python
fetcher.get(url, **kwargs)        # GET request
fetcher.post(url, body, **kwargs) # POST request
fetcher.put(url, body, **kwargs)  # PUT request
fetcher.delete(url, **kwargs)     # DELETE request
fetcher.patch(url, body, **kwargs)# PATCH request
fetcher.head(url, **kwargs)       # HEAD request
```

## Testing

Run the comprehensive test suite:

```bash
cd /home/user/mostlylucid.dse/code_evolver
python -m pytest tests/test_http_content_fetcher.py -v
```

Run example demonstrations:

```bash
python examples/http_content_fetcher_example.py
```

## Integration with DSE Workflow System

The HTTP Content Fetcher is fully integrated with the Code Evolver DSE system:

- **Tool Type**: `api_connector`
- **Tool ID**: `http_content_fetcher`
- **Workflow Compatible**: Yes
- **Tags**: http, fetch, content-fetching, web, api, rest, authentication

### Usage in Workflows

The tool can be referenced in workflow definitions:

```yaml
steps:
  - name: fetch_external_data
    tool: http_content_fetcher
    parameters:
      url: https://api.example.com/data
      method: GET
      auth:
        type: bearer
        token: ${API_TOKEN}
    output: external_data

  - name: process_data
    tool: data_processor
    input: ${external_data.data}
```

## Security Considerations

- **SSL/TLS Verification**: Enabled by default (set `verify_ssl=False` to disable)
- **Sensitive Data**: Never log authentication tokens or sensitive data
- **Timeout Limits**: Maximum timeout is 300 seconds (5 minutes)
- **Retry Limits**: Maximum retries is 10 attempts
- **Input Validation**: URLs are validated before requests

## Performance

- **Speed Tier**: Fast
- **Cost Tier**: Low
- **Quality Tier**: Excellent
- **Reliability**: High

Typical performance metrics:
- Local API: 50-200ms
- Remote API: 200-1000ms
- File downloads: Depends on file size and network speed

## Troubleshooting

### SSL Certificate Errors

```python
# Disable SSL verification (not recommended for production)
fetcher = create_http_fetcher(verify_ssl=False)
```

### Connection Timeouts

```python
# Increase timeout for slow APIs
result = fetcher.get(url, timeout=120)
```

### Proxy Issues

```python
# Configure proxy
fetcher = create_http_fetcher(
    proxies={
        'http': 'http://proxy:8080',
        'https': 'http://proxy:8080'
    }
)
```

## Examples

See the following files for more examples:

- **Basic Examples**: `/home/user/mostlylucid.dse/code_evolver/examples/http_content_fetcher_example.py`
- **Test Suite**: `/home/user/mostlylucid.dse/code_evolver/tests/test_http_content_fetcher.py`

## API Reference

### Class: HTTPContentFetcher

Main class for HTTP content fetching.

**Constructor:**
```python
HTTPContentFetcher(
    tool_id: str = "http_content_fetcher",
    name: str = "HTTP Content Fetcher",
    default_timeout: int = 30,
    max_retries: int = 3,
    retry_backoff_factor: float = 0.3,
    verify_ssl: bool = True,
    proxies: Optional[Dict[str, str]] = None
)
```

**Methods:**
- `fetch(url, **kwargs)` - Main fetch method with full control
- `get(url, **kwargs)` - GET request
- `post(url, body, **kwargs)` - POST request
- `put(url, body, **kwargs)` - PUT request
- `delete(url, **kwargs)` - DELETE request
- `patch(url, body, **kwargs)` - PATCH request
- `head(url, **kwargs)` - HEAD request
- `download_file(url, save_path, **kwargs)` - Download file
- `upload_file(url, file_path, **kwargs)` - Upload file
- `close()` - Close session

### Factory Function

```python
create_http_fetcher(**kwargs) -> HTTPContentFetcher
```

Convenient factory function to create HTTPContentFetcher instances.

## License

Part of the Code Evolver DSE system.

## Support

For issues or questions:
1. Check the examples in `/code_evolver/examples/`
2. Review the test suite in `/code_evolver/tests/`
3. Consult the Code Evolver documentation

## Version

Version: 1.0.0
Created: 2025-11-15
Status: Production Ready
