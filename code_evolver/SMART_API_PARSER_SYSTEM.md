# Smart API Parser System

## Overview

A comprehensive API testing framework with intelligent data generation capabilities.

## Components Created

### 1. Fake Data Generator (Faker-based)
**Location:** `tools/executable/fake_data_generator.py` + `.yaml`

Generates realistic fake data using the Faker library for testing APIs.

**Features:**
- Supports all JSON Schema types (string, integer, number, boolean, array, object)
- Recognizes common formats (email, uri, date, date-time, uuid, hostname, ipv4, ipv6)
- Context-aware generation based on field descriptions
- Fallback to basic generation if Faker not available
- Fast and free

**Usage:**
```bash
echo '{"schema": {"type": "string", "format": "email"}}' | python tools/executable/fake_data_generator.py
```

**Output:**
```json
{
  "success": true,
  "data": "john.doe@example.com",
  "schema": {"type": "string", "format": "email"}
}
```

### 2. LLM Fake Data Generator
**Location:** `tools/llm/llm_fake_data_generator.yaml`

Uses LLM (gemma3:4b) to generate contextually appropriate fake data.

**Features:**
- Contextual understanding of domain-specific requirements
- Complex nested objects with proper relationships
- Data that "makes sense" together
- Uses fast model (gemma3:4b) for quick generation

**When to use:**
- Domain-specific APIs (healthcare, finance, etc.)
- Complex business logic in data
- When data needs to be contextually coherent

**Example:**
```yaml
Input:
  schema_json: |
    {
      "type": "object",
      "properties": {
        "patient_id": {"type": "string"},
        "diagnosis": {"type": "string"},
        "medications": {"type": "array", "items": {"type": "string"}}
      }
    }
  additional_context: "Medical patient records"

Output:
  {
    "patient_id": "PT-2024-03547",
    "diagnosis": "Type 2 Diabetes",
    "medications": ["Metformin 500mg", "Insulin glargine"]
  }
```

### 3. Smart API Parser
**Location:** `tools/executable/smart_api_parser.py` + `.yaml`

Intelligently parses OpenAPI 3.0 specifications, generates test data, and tests endpoints.

**Features:**
- Parses OpenAPI 3.0 specs
- Extracts all endpoints (GET, POST, PUT, PATCH, DELETE, etc.)
- Generates fake data for request bodies and parameters
- Supports both dry-run and actual HTTP requests
- Can use either Faker or LLM for data generation
- Detailed test results per endpoint

**Modes:**

1. **Dry Run (Default)** - Parse and generate data without requests
2. **Faker Mode** - Fast, free data generation
3. **LLM Mode** - Context-aware, intelligent data
4. **Live Testing** - Actually make HTTP requests

**Usage:**
```python
from node_runtime import call_tool
import json

spec = {
    "openapi": "3.0.0",
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/users": {
            "post": {
                "operationId": "createUser",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# Dry run with Faker
result = call_tool("smart_api_parser", json.dumps({
    "openapi_spec": spec,
    "use_llm_generator": False,
    "make_requests": False
}))
```

## Installation

### Optional: Install Faker for enhanced data generation
```bash
pip install faker
```

The system works without Faker (uses fallback generator), but Faker provides:
- More realistic data
- Better variety
- Context-aware generation

## Testing

### Direct Tool Testing

```bash
# Test fake data generator
cd code_evolver
echo '{"schema": {"type": "string", "format": "email"}}' | python tools/executable/fake_data_generator.py

# Test with user object
echo '{"schema": {"type": "object", "required": ["name", "email"], "properties": {"name": {"type": "string"}, "email": {"type": "string", "format": "email"}}}}' | python tools/executable/fake_data_generator.py
```

### Through node_runtime

```python
from node_runtime import call_tool
import json

# Simple email
result = call_tool('fake_data_generator', json.dumps({
    'schema': {'type': 'string', 'format': 'email'}
}))
print(result)
```

## Performance Comparison

| Feature | Faker Generator | LLM Generator |
|---------|----------------|---------------|
| Speed | Very Fast (~10ms) | Fast (~500ms) |
| Cost | Free | Low (~$0.0001) |
| Quality | Good | Excellent |
| Context Awareness | Basic | High |
| Best For | Standard types | Domain-specific |

## Use Cases

### 1. API Development
- Generate test data for endpoints during development
- Validate OpenAPI specifications
- Quick prototyping with realistic data

### 2. Integration Testing
- Test all API endpoints automatically
- Generate diverse test cases
- Validate request/response schemas

### 3. Load Testing
- Generate large volumes of test data
- Realistic user scenarios
- Performance benchmarking

### 4. API Documentation
- Generate example requests/responses
- Validate documentation accuracy
- Create interactive API explorers

## Examples

### Example 1: E-commerce API Testing

```python
openapi_spec = {
    "openapi": "3.0.0",
    "paths": {
        "/orders": {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "product_id": {"type": "string"},
                                                "quantity": {"type": "integer"},
                                                "price": {"type": "number"}
                                            }
                                        }
                                    },
                                    "total": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# Use LLM for contextual data
result = call_tool("smart_api_parser", json.dumps({
    "openapi_spec": openapi_spec,
    "use_llm_generator": True,  # Smart, context-aware
    "make_requests": False  # Dry run
}))
```

### Example 2: Healthcare API

```python
# LLM generator for medical context
result = call_tool('llm_fake_data_generator', json.dumps({
    'schema_json': json.dumps({
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "symptoms": {"type": "array", "items": {"type": "string"}},
            "diagnosis": {"type": "string"}
        }
    }),
    'additional_context': 'Medical patient intake form'
}))
```

## Architecture

```
User Request
    ↓
[Smart API Parser]
    ├─→ Parse OpenAPI Spec
    ├─→ Extract Endpoints
    ├─→ For each endpoint:
    │   ├─→ Extract request schema
    │   ├─→ Choose generator (Faker vs LLM)
    │   ├─→ [Fake Data Generator] or [LLM Data Generator]
    │   ├─→ Generate test data
    │   └─→ (Optional) Make HTTP request
    └─→ Return results
```

## Future Enhancements

- [ ] Support for more data generators (hypothesis, factory-boy)
- [ ] GraphQL schema support
- [ ] Response validation
- [ ] Performance metrics collection
- [ ] Test report generation
- [ ] CI/CD integration helpers
- [ ] Mock server generation

## Troubleshooting

### Issue: "Tool missing command"
**Solution:** Tools are automatically loaded. Restart the system or ensure YAML files are in `tools/executable/` or `tools/llm/`

### Issue: Basic data instead of realistic
**Solution:** Install Faker: `pip install faker`

### Issue: Slow data generation
**Solution:** Use `use_llm_generator: false` for faster Faker-based generation

## Summary

The Smart API Parser System provides three powerful tools:

1. **Fake Data Generator** - Fast, free, realistic data using Faker
2. **LLM Data Generator** - Context-aware, intelligent data for complex domains
3. **Smart API Parser** - Comprehensive OpenAPI testing with intelligent data generation

All tools work independently or together for a complete API testing workflow.
