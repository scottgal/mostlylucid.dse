#!/usr/bin/env python3
"""
Smart API Parser
Parses OpenAPI specs, generates test data, and tests all endpoints
"""
import json
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add parent directory to path for node_runtime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def parse_openapi_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse OpenAPI specification

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        Parsed endpoint information
    """
    endpoints = []
    base_path = spec.get('basePath', '')
    servers = spec.get('servers', [])
    base_url = servers[0].get('url', 'http://localhost') if servers else 'http://localhost'

    paths = spec.get('paths', {})

    for path, path_item in paths.items():
        for method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
            if method not in path_item:
                continue

            operation = path_item[method]

            endpoint_info = {
                'path': base_path + path,
                'method': method.upper(),
                'operation_id': operation.get('operationId', f"{method}_{path.replace('/', '_')}"),
                'summary': operation.get('summary', ''),
                'description': operation.get('description', ''),
                'parameters': operation.get('parameters', []),
                'request_body': operation.get('requestBody', {}),
                'responses': operation.get('responses', {}),
                'tags': operation.get('tags', [])
            }

            endpoints.append(endpoint_info)

    return {
        'base_url': base_url,
        'endpoints': endpoints,
        'info': spec.get('info', {}),
        'total_endpoints': len(endpoints)
    }


def extract_schema_from_request_body(request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract JSON schema from request body

    Args:
        request_body: OpenAPI request body object

    Returns:
        JSON schema or None
    """
    if not request_body:
        return None

    content = request_body.get('content', {})

    # Try application/json first
    if 'application/json' in content:
        schema = content['application/json'].get('schema', {})
        return schema

    # Try other content types
    for content_type, content_schema in content.items():
        if 'json' in content_type.lower():
            return content_schema.get('schema', {})

    return None


def generate_fake_data_for_schema(schema: Dict[str, Any], use_llm: bool = False, context: str = "") -> Any:
    """
    Generate fake data for a schema using faker or LLM

    Args:
        schema: JSON schema
        use_llm: Whether to use LLM generator (slower but smarter)
        context: Additional context for LLM

    Returns:
        Generated fake data
    """
    try:
        from node_runtime import call_tool

        if use_llm:
            # Use LLM-based generator for contextual data
            result = call_tool('llm_fake_data_generator', json.dumps({
                'schema_json': json.dumps(schema),
                'additional_context': context
            }))

            # Parse JSON response
            try:
                data = json.loads(result)
                return data
            except json.JSONDecodeError:
                # LLM might return just the data without wrapper
                return json.loads(result)

        else:
            # Use faker-based generator for simple data
            result = call_tool('fake_data_generator', json.dumps({
                'schema': schema,
                'count': 1
            }))

            data = json.loads(result)
            return data.get('data')

    except Exception as e:
        print(f"Warning: Could not generate fake data: {e}", file=sys.stderr)
        # Fallback to minimal data
        return generate_minimal_data(schema)


def generate_minimal_data(schema: Dict[str, Any]) -> Any:
    """
    Generate minimal data when tools are unavailable

    Args:
        schema: JSON schema

    Returns:
        Minimal fake data
    """
    schema_type = schema.get('type', 'string')

    if schema_type == 'string':
        return "test_value"
    elif schema_type == 'integer':
        return 42
    elif schema_type == 'number':
        return 42.0
    elif schema_type == 'boolean':
        return True
    elif schema_type == 'array':
        return []
    elif schema_type == 'object':
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        result = {}
        for prop in required:
            if prop in properties:
                result[prop] = generate_minimal_data(properties[prop])
        return result
    else:
        return None


def generate_fake_parameters(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate fake values for path/query/header parameters

    Args:
        parameters: List of parameter definitions

    Returns:
        Dictionary of parameter values
    """
    result = {
        'path': {},
        'query': {},
        'header': {},
        'cookie': {}
    }

    for param in parameters:
        param_in = param.get('in', 'query')
        param_name = param.get('name', 'unknown')
        param_schema = param.get('schema', {'type': 'string'})

        # Generate fake value based on schema
        if param_schema.get('type') == 'string':
            if param_name.lower() == 'id':
                value = "12345"
            elif param_name.lower() == 'email':
                value = "test@example.com"
            else:
                value = f"test_{param_name}"
        elif param_schema.get('type') == 'integer':
            value = 42
        elif param_schema.get('type') == 'boolean':
            value = True
        else:
            value = "test"

        result[param_in][param_name] = value

    return result


def test_endpoint(
    base_url: str,
    endpoint: Dict[str, Any],
    use_llm: bool = False,
    make_request: bool = True
) -> Dict[str, Any]:
    """
    Test a single API endpoint

    Args:
        base_url: Base URL of API
        endpoint: Endpoint information
        use_llm: Use LLM for data generation
        make_request: Actually make HTTP request (vs dry run)

    Returns:
        Test result
    """
    import urllib.request
    import urllib.parse

    # Build URL
    path = endpoint['path']
    method = endpoint['method']

    # Generate parameters
    params = generate_fake_parameters(endpoint['parameters'])

    # Replace path parameters
    url = base_url + path
    for param_name, param_value in params['path'].items():
        url = url.replace(f'{{{param_name}}}', str(param_value))

    # Add query parameters
    if params['query']:
        query_string = urllib.parse.urlencode(params['query'])
        url = f"{url}?{query_string}"

    # Generate request body
    request_body_schema = extract_schema_from_request_body(endpoint['request_body'])
    request_data = None

    if request_body_schema:
        context = f"{endpoint.get('summary', '')} - {endpoint.get('description', '')}"
        request_data = generate_fake_data_for_schema(
            request_body_schema,
            use_llm=use_llm,
            context=context
        )

    # Prepare result
    result = {
        'endpoint': endpoint['operation_id'],
        'method': method,
        'url': url,
        'path_params': params['path'],
        'query_params': params['query'],
        'headers': params['header'],
        'request_body': request_data,
        'dry_run': not make_request
    }

    # Make actual HTTP request if requested
    if make_request:
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'SmartAPIParser/1.0',
                **params['header']
            }

            data_bytes = None
            if request_data:
                data_bytes = json.dumps(request_data).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers=headers,
                method=method
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                response_body = response.read().decode('utf-8')

                result.update({
                    'success': True,
                    'status_code': response.status,
                    'response_body': response_body,
                    'response_headers': dict(response.headers)
                })

        except urllib.error.HTTPError as e:
            result.update({
                'success': False,
                'status_code': e.code,
                'error': str(e),
                'response_body': e.read().decode('utf-8') if e.fp else None
            })

        except Exception as e:
            result.update({
                'success': False,
                'error': str(e)
            })

    return result


def main():
    """Main entry point"""
    try:
        # Read input
        input_data = json.load(sys.stdin)

        # Get OpenAPI spec
        openapi_spec = input_data.get('openapi_spec')
        if not openapi_spec:
            raise ValueError("Missing 'openapi_spec' in input")

        # Options
        use_llm = input_data.get('use_llm_generator', False)
        make_requests = input_data.get('make_requests', False)  # Dry run by default
        endpoints_to_test = input_data.get('endpoints', None)  # None = all endpoints

        # Parse spec
        parsed = parse_openapi_spec(openapi_spec)

        # Test endpoints
        results = []
        for endpoint in parsed['endpoints']:
            # Filter by endpoint if specified
            if endpoints_to_test and endpoint['operation_id'] not in endpoints_to_test:
                continue

            result = test_endpoint(
                parsed['base_url'],
                endpoint,
                use_llm=use_llm,
                make_request=make_requests
            )
            results.append(result)

        # Output results
        print(json.dumps({
            'success': True,
            'api_info': parsed['info'],
            'base_url': parsed['base_url'],
            'total_endpoints': parsed['total_endpoints'],
            'tested_endpoints': len(results),
            'results': results,
            'options': {
                'use_llm_generator': use_llm,
                'make_requests': make_requests
            }
        }, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
