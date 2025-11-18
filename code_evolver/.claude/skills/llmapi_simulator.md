# LLMApi Simulator Skill

You are an expert at using LLMApi (http://localhost:5000) as a test data simulator for API testing and code generation.

## When to Use This Skill

This skill should be activated when the user's request includes phrases like:
- "use the api simulator"
- "use llmapi"
- "mock api"
- "test data"
- "simulate endpoint"
- "call http" or "call an api"
- "check an api" or "test endpoint"
- Any task involving testing HTTP endpoints

**CRITICAL**: For ANY task that involves calling an HTTP API endpoint, checking an API, or post-codegen testing of API-calling tools, you MUST use LLMApi as the simulator. Never call real external APIs during testing.

## Pre-Flight Check

ALWAYS start by checking if LLMApi is available using the `llmapi_health_check` tool:

```python
from node_runtime import call_tool
import json

# Check if LLMApi is available (default port: 5000)
health_result = call_tool("llmapi_health_check", json.dumps({"base_url": "http://localhost:5000"}))
health_data = json.loads(health_result)

if not health_data.get("success"):
    print(f"⚠ LLMApi not available: {health_data.get('error')}")
    print("Please start LLMApi on http://localhost:5000")
    exit(1)

print(f"✓ LLMApi is healthy (version: {health_data['details'].get('version', 'unknown')})")
print(f"  Features: {', '.join(health_data['details'].get('features', []))}")
```

## Core LLMApi Capabilities

### 1. Mock REST Endpoints
Generate realistic JSON responses for any REST endpoint:

**Basic GET (returns realistic data based on URL path)**:
```bash
GET http://localhost:5000/api/mock/users?limit=10
Accept: application/json
```

**With Custom Shape (define exact JSON structure)**:
```bash
GET http://localhost:5000/api/mock/products?shape=%7B%22products%22%3A%5B%7B%22id%22%3A%22string%22%2C%22price%22%3A0.0%7D%5D%7D
Accept: application/json
```

**Shape via Header (cleaner approach)**:
```bash
GET http://localhost:5000/api/mock/orders
X-Response-Shape: {"orderId":"string","total":0.0,"items":[{"sku":"string","qty":0}]}
Accept: application/json
```

### 2. POST/PUT/DELETE Support
All HTTP methods work - LLMApi generates appropriate responses:

```bash
POST http://localhost:5000/api/mock/orders
Content-Type: application/json
X-Response-Shape: {"orderId":"string","status":"created","total":0.0}

{
  "customerId": "cus_123",
  "items": [{"sku": "ABC-001", "qty": 2}]
}
```

### 3. Response Caching ($cache)
Pre-generate and cache N response variants for fast testing:

```bash
GET http://localhost:5000/api/mock/users
X-Response-Shape: {"$cache":5,"users":[{"id":0,"name":"string"}]}
```

The `$cache: 5` prefetches 5 different variants and serves them instantly.

### 4. Error Simulation
Test error handling by specifying error codes:

**Via Query Param**:
```bash
GET http://localhost:5000/api/mock/users/999?error=404&errorMessage=User%20not%20found
```

**Via Header**:
```bash
GET http://localhost:5000/api/mock/admin/data
X-Error-Code: 403
X-Error-Message: Insufficient permissions
```

**Via Shape**:
```bash
GET http://localhost:5000/api/mock/data?shape=%7B%22%24error%22%3A500%7D
```

### 5. Streaming Endpoints (SSE)
Server-Sent Events for testing real-time data:

```bash
GET http://localhost:5000/api/mock/stream/stock-prices?symbol=AAPL
Accept: text/event-stream
```

### 6. GraphQL Support
Test GraphQL queries:

```bash
POST http://localhost:5000/api/mock/graphql
Content-Type: application/json

{
  "query": "{ users { id name email } }"
}
```

### 7. OpenAPI Spec Loading
Load and mock entire OpenAPI specifications:

```bash
POST http://localhost:5000/api/openapi/specs
Content-Type: application/json

{
  "name": "petstore",
  "source": "https://petstore3.swagger.io/api/v3/openapi.json",
  "basePath": "/petstore"
}

# Then call: GET http://localhost:5000/petstore/pet/42
```

### 8. Rate Limiting & N-Completions
Generate multiple response variants with rate limiting simulation:

```bash
GET http://localhost:5000/api/mock/users?n=3&rateLimit=500-1000&strategy=parallel
```

## Python Usage Pattern

When generating code that needs to call APIs, use this pattern:

```python
import urllib.request
import urllib.parse
import json

def call_mock_api(endpoint: str, method: str = "GET", shape: dict = None, body: dict = None):
    """
    Call LLMApi mock endpoint for testing.

    Args:
        endpoint: Endpoint path (e.g., "/api/mock/users")
        method: HTTP method
        shape: Optional response shape definition
        body: Optional request body

    Returns:
        Response data as dict
    """
    base_url = "http://localhost:5000"
    url = f"{base_url}{endpoint}"

    headers = {"Accept": "application/json"}

    # Add response shape if specified
    if shape:
        headers["X-Response-Shape"] = json.dumps(shape)

    # Prepare request
    data = None
    if body:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        # Handle error responses
        error_body = json.loads(e.read().decode('utf-8'))
        return {"error": e.code, "message": error_body}

# Example usage
users = call_mock_api(
    "/api/mock/users",
    shape={"users": [{"id": 0, "name": "string", "email": "string"}]}
)
print(json.dumps(users, indent=2))
```

## Common Shapes (from config.yaml)

Use these predefined shapes for common scenarios:

- **user_list**: `{"users":[{"id":0,"name":"string","email":"string","isActive":true}],"meta":{"total":0,"next":"string"}}`
- **product**: `{"id":"string","sku":"string","name":"string","price":0.0,"inStock":true,"tags":["string"]}`
- **order**: `{"orderId":"string","status":"string","total":0.0,"items":[{"sku":"string","qty":0}],"customer":{"id":"string","name":"string"}}`
- **generic_list**: `[{"id":"string","name":"string","value":"string"}]`

## Best Practices

1. **Always check health first** - Use `llmapi_health_check` before making requests
2. **Use shapes for consistency** - Define response structure with X-Response-Shape
3. **Cache for performance** - Use `$cache` for repeated test runs
4. **Test error cases** - Use error simulation to verify error handling
5. **Use realistic paths** - Path influences LLM's understanding (e.g., `/users` vs `/products`)
6. **URL encode query params** - Use `urllib.parse.quote()` for special characters
7. **Never call real APIs** - Always use LLMApi simulator for testing

## Example Workflow: Testing an API Client

```python
# 1. Health check
health = call_tool("llmapi_health_check", "{}")
if not json.loads(health)["success"]:
    print("Start LLMApi first!")
    exit(1)

# 2. Test successful case
response = call_mock_api(
    "/api/mock/orders/123",
    shape={"orderId": "string", "status": "string", "total": 0.0}
)
assert "orderId" in response

# 3. Test error case
error_response = call_mock_api(
    "/api/mock/orders/999?error=404&errorMessage=Order%20not%20found"
)
assert error_response.get("error") == 404

# 4. Test with caching for performance
cached_response = call_mock_api(
    "/api/mock/products",
    shape={"$cache": 10, "products": [{"id": "string", "price": 0.0}]}
)

print("✓ All API tests passed!")
```

## Integration with Code Generation

When generating tools that call HTTP APIs:

1. **Check if task mentions API testing** → Use LLMApi
2. **Generate code with mock calls** → Point to localhost:5000
3. **Include health check** → Verify LLMApi is running
4. **Provide shape definitions** → Document expected response structure
5. **Add error handling** → Test with error simulation

## Troubleshooting

- **Connection refused**: LLMApi not running - start it on port 5000
- **Empty response**: Check shape syntax - must be valid JSON
- **Wrong structure**: Provide more detailed shape with nested objects
- **Slow responses**: Use `$cache` to prefetch variants
- **URL encoding errors**: Use `urllib.parse.quote()` for query params with special chars

## Reference

Full LLMApi documentation: `D:\Source\LLMApi\LLMApi\LLMApi.http`
Swagger spec: `http://localhost:5000/swagger/v1/swagger.json` (OpenAPI 3.0.4, v2.1.0)
Default port: **5000** (configurable via `config.yaml` → `llmapi.base_url`)

**Available API Groups** (from OpenAPI spec):
- **API Contexts**: Manage stateful API contexts with history
- **Code Review**: LLM-powered code review
- **gRPC Proto Management**: Upload and mock gRPC services
- **gRPC Service Calls**: JSON and Protobuf support
- **OpenAPI Management**: Load and mock OpenAPI specs dynamically
- **SignalR Management**: Real-time streaming contexts
- **Tool Fitness**: Test and evolve tools automatically
- **Unit Test Generation**: Pyguin + LLM test generation
- **Mock Endpoints** (`/api/mock/{path}`): Universal mock REST/streaming/GraphQL

## Remember

**ALWAYS use LLMApi for API testing - never call real external APIs during development or testing!**
