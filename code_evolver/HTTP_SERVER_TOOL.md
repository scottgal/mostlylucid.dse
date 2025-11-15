# HTTP Server Tool

The HTTP Server Tool enables DSE workflows to serve content via HTTP, making workflows accessible as web services and REST APIs.

## Features

- **Start/stop HTTP server** on configurable host/port
- **Register routes dynamically** for both HTML and JSON responses
- **Support for multiple HTTP methods** (GET, POST, PUT, DELETE)
- **CORS support** for cross-origin requests
- **Workflow integration** - expose workflows as API endpoints
- **Error handling** and comprehensive logging
- **Non-blocking operation** - runs in background thread

## Installation

Install required dependency:

```bash
pip install flask
```

## Basic Usage

### 1. Creating a Simple HTTP Server

```python
from src.http_server_tool import HTTPServerTool

# Create server
server = HTTPServerTool(host="0.0.0.0", port=8080)

# Add a JSON API endpoint
def hello_handler(request_data):
    return {
        "message": "Hello from DSE!",
        "timestamp": time.time()
    }

server.add_route(
    path="/api/hello",
    methods=["GET", "POST"],
    handler=hello_handler,
    response_type="json",
    description="Simple hello endpoint"
)

# Start server (non-blocking)
server.start(blocking=False)

# Server is now running at http://0.0.0.0:8080
```

### 2. Adding HTML Endpoints

```python
def homepage_handler(request_data):
    return """
    <!DOCTYPE html>
    <html>
    <head><title>My API</title></head>
    <body>
        <h1>Welcome to DSE Workflow API</h1>
        <p>Available endpoints:</p>
        <ul>
            <li>GET /api/hello - Simple hello endpoint</li>
            <li>POST /api/process - Process data</li>
        </ul>
    </body>
    </html>
    """

server.add_route(
    path="/",
    methods=["GET"],
    handler=homepage_handler,
    response_type="html",
    description="Homepage"
)
```

### 3. Exposing Workflows as APIs

```python
from src.http_server_tool import WorkflowHTTPAdapter

# Create adapter
adapter = WorkflowHTTPAdapter(workflow_manager, tools_manager)

# Create server
server = adapter.create_server(
    server_id="api_server",
    host="0.0.0.0",
    port=8080
)

# Register workflow as endpoint
adapter.register_workflow_endpoint(
    server_id="api_server",
    workflow_id="text_summarizer",
    path="/api/summarize",
    methods=["POST"],
    response_type="json"
)

# Start server
adapter.start_server("api_server")
```

## API Reference

### HTTPServerTool

#### Constructor

```python
HTTPServerTool(
    host: str = "0.0.0.0",
    port: int = 8080,
    enable_cors: bool = True,
    debug: bool = False
)
```

**Parameters:**
- `host`: Host to bind to (default: "0.0.0.0")
- `port`: Port to listen on (default: 8080)
- `enable_cors`: Enable CORS headers (default: True)
- `debug`: Enable Flask debug mode (default: False)

#### Methods

##### `add_route()`

Add a route to the HTTP server.

```python
server.add_route(
    path: str,
    methods: List[str],
    handler: Callable,
    response_type: str = "json",
    description: str = ""
)
```

**Parameters:**
- `path`: URL path (e.g., "/api/process")
- `methods`: HTTP methods (e.g., ["GET", "POST"])
- `handler`: Function to handle requests
  - For JSON: `handler(request_data) -> dict`
  - For HTML: `handler(request_data) -> str`
- `response_type`: "json" or "html"
- `description`: Human-readable description

**Handler Input Format:**

```python
request_data = {
    "method": "POST",
    "path": "/api/process",
    "headers": {"Content-Type": "application/json", ...},
    "data": {  # Request body or query params
        "key": "value"
    }
}
```

##### `start()`

Start the HTTP server.

```python
server.start(blocking: bool = False)
```

**Parameters:**
- `blocking`: If True, blocks until server stops. If False, runs in background thread.

##### `stop()`

Stop the HTTP server.

```python
server.stop()
```

##### `list_routes()`

List all registered routes.

```python
routes = server.list_routes()
# Returns: List[Dict[str, Any]]
```

##### `get_server_info()`

Get server information and status.

```python
info = server.get_server_info()
# Returns: {
#     "host": "0.0.0.0",
#     "port": 8080,
#     "is_running": True,
#     "enable_cors": True,
#     "routes_count": 5,
#     "routes": [...],
#     "url": "http://0.0.0.0:8080"
# }
```

### WorkflowHTTPAdapter

Adapter that connects HTTP server to DSE workflow system.

#### Constructor

```python
WorkflowHTTPAdapter(workflow_manager, tools_manager)
```

**Parameters:**
- `workflow_manager`: WorkflowManager instance
- `tools_manager`: ToolsManager instance

#### Methods

##### `create_server()`

Create a new HTTP server instance.

```python
server = adapter.create_server(
    server_id: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    enable_cors: bool = True
)
```

##### `register_workflow_endpoint()`

Register a workflow as an HTTP endpoint.

```python
adapter.register_workflow_endpoint(
    server_id: str,
    workflow_id: str,
    path: str,
    methods: List[str] = ["POST"],
    response_type: str = "json"
)
```

##### `start_server()` / `stop_server()`

Start or stop a server by ID.

```python
adapter.start_server(server_id: str, blocking: bool = False)
adapter.stop_server(server_id: str)
```

##### `list_servers()`

List all registered servers.

```python
servers = adapter.list_servers()
# Returns: List[Dict[str, Any]]
```

## Configuration

The HTTP server tool is registered in `config.yaml`:

```yaml
tools:
  http_server:
    name: "HTTP Server"
    type: "custom"
    description: "HTTP server that allows workflows to serve content via HTTP"
    cost_tier: "free"
    speed_tier: "very-fast"
    quality_tier: "excellent"
    custom:
      module: "src.http_server_tool"
      class: "HTTPServerTool"
      config:
        host: "0.0.0.0"
        port: 8080
        enable_cors: true
```

## Use Cases

### 1. REST API for Workflows

Expose workflows as REST endpoints:

```python
# Text summarization API
POST /api/summarize
{
  "text": "Long text to summarize..."
}

# Returns:
{
  "summary": "Condensed version...",
  "length": 150
}
```

### 2. Web Dashboard

Serve HTML dashboards for workflow monitoring:

```python
GET /dashboard
# Returns HTML page with workflow status, metrics, etc.
```

### 3. Webhook Receiver

Create endpoints to receive webhooks:

```python
POST /webhooks/github
# Process GitHub webhook events and trigger workflows
```

### 4. Data Processing API

Expose data processing workflows:

```python
POST /api/process-data
{
  "data": [...],
  "operation": "transform"
}

# Returns processed data
```

### 5. Integration Hub

Create integration endpoints for external systems:

```python
POST /integrations/slack/notify
POST /integrations/email/send
POST /integrations/database/query
```

## Examples

See `examples/http_server_demo.py` for complete working examples:

```bash
# Run the demo
cd code_evolver
python examples/http_server_demo.py
```

The demo includes:
1. Basic HTTP server with JSON and HTML endpoints
2. Workflow API endpoints simulation
3. WorkflowHTTPAdapter usage

## Testing

Test your HTTP server with curl:

```bash
# Test JSON endpoint
curl http://localhost:8080/api/hello

# Test with POST data
curl -X POST http://localhost:8080/api/process \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# Test HTML endpoint
curl http://localhost:8080/
```

Or use the Python requests library:

```python
import requests

# JSON API call
response = requests.post(
    "http://localhost:8080/api/process",
    json={"data": "test"}
)
print(response.json())

# HTML page
response = requests.get("http://localhost:8080/")
print(response.text)
```

## Security Considerations

1. **CORS**: Enabled by default for development. Disable for production:
   ```python
   server = HTTPServerTool(enable_cors=False)
   ```

2. **Authentication**: Add authentication handlers:
   ```python
   def authenticated_handler(request_data):
       token = request_data["headers"].get("Authorization")
       if not validate_token(token):
           return {"error": "Unauthorized"}, 401
       # Process request...
   ```

3. **Rate Limiting**: Implement rate limiting in handlers:
   ```python
   from functools import wraps
   from time import time

   def rate_limit(max_per_minute):
       def decorator(f):
           calls = []
           @wraps(f)
           def wrapped(*args, **kwargs):
               now = time()
               calls[:] = [c for c in calls if c > now - 60]
               if len(calls) >= max_per_minute:
                   return {"error": "Rate limit exceeded"}, 429
               calls.append(now)
               return f(*args, **kwargs)
           return wrapped
       return decorator
   ```

4. **Input Validation**: Always validate input data:
   ```python
   def process_handler(request_data):
       data = request_data.get("data", {})

       # Validate required fields
       if "text" not in data:
           return {"error": "Missing required field: text"}

       # Validate data types
       if not isinstance(data["text"], str):
           return {"error": "Invalid type for field: text"}

       # Process valid data...
   ```

## Performance Tips

1. **Non-blocking mode**: Use `blocking=False` to run server in background
2. **Threaded requests**: Flask handles requests in separate threads by default
3. **Keep handlers lightweight**: Move heavy processing to workflows
4. **Use appropriate response types**: JSON for APIs, HTML for pages
5. **Monitor resources**: Track memory and CPU usage for long-running servers

## Troubleshooting

### Port already in use

```python
# Use a different port
server = HTTPServerTool(port=8081)
```

### CORS errors

```python
# Ensure CORS is enabled
server = HTTPServerTool(enable_cors=True)
```

### Server not responding

```python
# Check if server is running
info = server.get_server_info()
print(f"Running: {info['is_running']}")

# Check logs for errors
```

### Handler errors

```python
# Handlers should catch and return errors
def safe_handler(request_data):
    try:
        # Process request
        result = process(request_data)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

## Future Enhancements

Planned features:
- WebSocket support for real-time communication
- Built-in authentication/authorization
- Rate limiting and throttling
- Request/response middleware
- OpenAPI/Swagger documentation generation
- HTTPS/TLS support
- Load balancing across multiple instances
- Metrics and monitoring endpoints

## Contributing

To extend the HTTP server tool:

1. Add new features to `src/http_server_tool.py`
2. Update configuration in `config.yaml`
3. Add examples to `examples/http_server_demo.py`
4. Update this documentation

## License

Part of the DSE (Dynamic Software Evolution) project.
