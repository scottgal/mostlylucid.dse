# LLMApi Integration - Test Data Simulator

## Overview

The system now integrates with **LLMApi** (http://localhost:5000) as an intelligent test data simulator for API testing and code generation. LLMApi uses LLMs to generate realistic mock API responses, eliminating the need to call real external APIs during development and testing.

## Quick Start

### 1. Start LLMApi

```bash
# LLMApi should be running on http://localhost:5000
# Health endpoint: http://localhost:5000/health
# Swagger spec: http://localhost:5000/swagger/v1/swagger.json
```

### 2. Verify Integration

```bash
cd code_evolver
python chat_cli.py

> use the api simulator to test a users endpoint
```

The system will:
1. Auto-detect LLMApi is running
2. Generate code using LLMApi for mock data
3. Include health checks in generated code

## Features

### 1. Auto-Detection

LLMApi integration activates automatically when:
- User says "use the api simulator", "use llmapi", "mock api", etc.
- Task involves "check an api", "test endpoint", or "call http"
- Generating code that needs HTTP endpoint testing

### 2. Health Check Tool

New tool: `llmapi_health_check` verifies LLMApi availability:

```python
from node_runtime import call_tool
import json

health = call_tool("llmapi_health_check", json.dumps({
    "base_url": "http://localhost:5000"
}))

result = json.loads(health)
if result["success"]:
    print(f"✓ LLMApi available (v{result['details']['version']})")
    print(f"  Features: {result['details']['features']}")
else:
    print(f"✗ LLMApi unavailable: {result['details']['error']}")
```

### 3. LLMApi Skill

New skill: `.claude/skills/llmapi_simulator.md` provides:
- Complete LLMApi API reference
- Python usage patterns
- Common response shapes
- Error simulation examples
- Best practices

### 4. Configuration

New section in `config.yaml`:

```yaml
llmapi:
  enabled: true
  base_url: "http://localhost:5000"
  port: 5000
  health_check_timeout: 2

  auto_detect:
    enabled: true
    cache_ttl: 300
    keywords:
      - "api simulator"
      - "use llmapi"
      - "mock api"
      - "test data"
      - "check an api"
      - "test endpoint"

  defaults:
    timeout: 10
    include_schema: true
    cache_variants: 3
    accept: "application/json"

  shapes:
    user_list: '{"users":[{"id":0,"name":"string","email":"string"}]}'
    product: '{"id":"string","sku":"string","name":"string","price":0.0}'
    order: '{"orderId":"string","status":"string","total":0.0}'
    generic_list: '[{"id":"string","name":"string","value":"string"}]'

  features:
    streaming: true
    graphql: true
    error_simulation: true
```

## Usage Examples

### Example 1: Test a Users API

```
> create a function that fetches user data from an API endpoint
```

Generated code will:
1. Check LLMApi health
2. Call `http://localhost:5000/api/mock/users`
3. Use appropriate response shape
4. Include error handling

### Example 2: Test with Custom Shape

```
> test a products endpoint with sku, name, and price fields
```

Generated code will use:
```python
shape = {"products": [{"sku": "string", "name": "string", "price": 0.0}]}
```

### Example 3: Error Simulation

```
> test API error handling for 404 and 500 errors
```

Generated code will test multiple scenarios:
- Success case: Normal response
- 404 case: `?error=404&errorMessage=Not%20found`
- 500 case: `?error=500&errorMessage=Server%20error`

## LLMApi Capabilities

### 1. Mock REST Endpoints

Any HTTP method (GET, POST, PUT, DELETE):
```bash
GET http://localhost:5000/api/mock/users?limit=10
POST http://localhost:5000/api/mock/orders
PUT http://localhost:5000/api/mock/users/123
DELETE http://localhost:5000/api/mock/orders/456
```

### 2. Custom Response Shapes

Three ways to specify exact JSON structure:

**Via Header (recommended)**:
```
X-Response-Shape: {"orderId":"string","total":0.0}
```

**Via Query Param (URL-encoded)**:
```
?shape=%7B%22orderId%22%3A%22string%22%7D
```

**Via Body Field**:
```json
{
  "shape": {"orderId": "string", "total": 0.0},
  "customerId": "cus_123"
}
```

### 3. Response Caching

Pre-generate N variants for fast testing:
```json
{"$cache": 5, "users": [{"id": 0, "name": "string"}]}
```

### 4. Error Simulation

**Query Param**:
```
?error=404&errorMessage=Not%20found&errorDetails=User%20does%20not%20exist
```

**Header**:
```
X-Error-Code: 403
X-Error-Message: Insufficient permissions
```

**Shape**:
```json
{"$error": {"code": 422, "message": "Validation failed"}}
```

### 5. Streaming (SSE)

Server-Sent Events for real-time data:
```bash
GET http://localhost:5000/api/mock/stream/stock-prices
Accept: text/event-stream
```

### 6. GraphQL

```bash
POST http://localhost:5000/api/mock/graphql
Content-Type: application/json

{"query": "{ users { id name email } }"}
```

### 7. OpenAPI Loading

Load entire API specs:
```bash
POST http://localhost:5000/api/openapi/specs
{
  "name": "petstore",
  "source": "https://petstore3.swagger.io/api/v3/openapi.json",
  "basePath": "/petstore"
}
```

### 8. Rate Limiting & N-Completions

Test multiple variants with simulated delays:
```
?n=3&rateLimit=500-1000&strategy=parallel
```

## Integration Points

### Code Generation

When generating HTTP client code:
1. Task evaluator detects API-related keywords
2. LLMApi skill is activated
3. Generated code includes:
   - Health check
   - LLMApi endpoints
   - Response shape definitions
   - Error handling

### Testing

When testing generated API clients:
1. Pre-flight health check runs
2. Multiple test scenarios generated (success + errors)
3. Realistic mock data returned
4. No external API calls made

### Workflow Steps

LLMApi can be used in workflow steps:
```yaml
- step: test_api_client
  tool: llmapi_simulator
  inputs:
    endpoint: /api/mock/users
    method: GET
    shape: {"users": [{"id": 0, "name": "string"}]}
```

## Python Helper Pattern

Standard pattern for generated code:

```python
import urllib.request
import json

def call_mock_api(endpoint: str, shape: dict = None):
    """Call LLMApi mock endpoint."""
    base_url = "http://localhost:5000"
    url = f"{base_url}{endpoint}"

    headers = {"Accept": "application/json"}
    if shape:
        headers["X-Response-Shape"] = json.dumps(shape)

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = json.loads(e.read().decode('utf-8'))
        return {"error": e.code, "message": error_body}

# Usage
users = call_mock_api(
    "/api/mock/users",
    shape={"users": [{"id": 0, "name": "string", "email": "string"}]}
)
```

## Benefits

1. **No External Dependencies**: Test without real API access
2. **Realistic Data**: LLM-generated responses match expected structure
3. **Fast Testing**: Cached responses for repeated tests
4. **Error Testing**: Easy simulation of error conditions
5. **Flexible Shapes**: Define exact response structure
6. **Zero Configuration**: Auto-detects when available
7. **Safe Development**: Never calls production APIs during testing

## Troubleshooting

### LLMApi Not Running

```
✗ LLMApi unavailable: Connection failed
```

**Solution**: Start LLMApi on http://localhost:5000

### Wrong Response Structure

**Problem**: Response doesn't match expected shape

**Solution**: Provide explicit shape via X-Response-Shape header:
```python
headers["X-Response-Shape"] = json.dumps({
    "users": [{"id": 0, "name": "string", "email": "string"}]
})
```

### URL Encoding Errors

**Problem**: Special characters in query params cause errors

**Solution**: Use `urllib.parse.quote()`:
```python
import urllib.parse
encoded_shape = urllib.parse.quote(json.dumps(shape))
url = f"{base_url}/api/mock/users?shape={encoded_shape}"
```

### Slow Responses

**Problem**: Each request takes time for LLM generation

**Solution**: Use caching:
```python
shape = {
    "$cache": 10,  # Pre-generate 10 variants
    "users": [{"id": 0, "name": "string"}]
}
```

## Files Added

1. **tools/executable/llmapi_health_check.py** - Health check tool
2. **tools/executable/llmapi_health_check.yaml** - Tool specification
3. **.claude/skills/llmapi_simulator.md** - LLMApi skill documentation
4. **config.yaml** - New `llmapi:` section with settings
5. **LLMAPI_INTEGRATION.md** - This documentation

## References

- **LLMApi Examples**: `D:\Source\LLMApi\LLMApi\LLMApi.http` (1250 lines of samples)
- **Swagger Spec**: http://localhost:5000/swagger/v1/swagger.json
- **Health Endpoint**: http://localhost:5000/health
- **Base URL**: http://localhost:5000

## Future Enhancements

- [ ] Automatic OpenAPI spec loading from generated code
- [ ] Context management for stateful API testing
- [ ] gRPC proto file integration
- [ ] Tool chaining for multi-step API workflows
- [ ] Performance testing with rate limiting
- [ ] WebSocket/SignalR support
