#!/usr/bin/env python3
"""
Locust Load Test Generator and Runner
Generates Locust performance tests from API specs with plausible data
"""
import json
import sys
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional


def parse_openapi_spec(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse OpenAPI spec to extract endpoints

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        List of endpoint definitions
    """
    endpoints = []
    paths = spec.get('paths', {})

    # Validate that paths is a dictionary
    if not isinstance(paths, dict):
        return endpoints

    for path, methods in paths.items():
        # Ensure path is a string and methods is a dict
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue

        for method, details in methods.items():
            # Ensure method is a string before calling .lower()
            if not isinstance(method, str):
                continue

            if method.lower() in ['get', 'post', 'put', 'patch', 'delete']:
                # Ensure details is a dict
                if not isinstance(details, dict):
                    continue

                endpoint = {
                    'path': path,
                    'method': method.upper(),
                    'operation_id': details.get('operationId', f"{method}_{path}"),
                    'summary': details.get('summary', ''),
                    'parameters': details.get('parameters', []),
                    'request_body': details.get('requestBody', {}),
                    'responses': details.get('responses', {})
                }
                endpoints.append(endpoint)

    return endpoints


def load_static_analysis(path: Optional[str]) -> Dict[str, Any]:
    """
    Load static analysis results for data generation hints

    Args:
        path: Path to static analysis JSON file

    Returns:
        Static analysis data or empty dict
    """
    if not path or not os.path.exists(path):
        return {}

    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def generate_plausible_data(schema: Dict[str, Any], static_analysis: Dict[str, Any]) -> str:
    """
    Generate plausible test data based on schema and static analysis

    Args:
        schema: JSON schema for the data
        static_analysis: Static analysis results for hints

    Returns:
        Python code string to generate the data
    """
    try:
        from faker import Faker
        has_faker = True
    except ImportError:
        has_faker = False

    schema_type = schema.get('type', 'string')

    if schema_type == 'object':
        properties = schema.get('properties', {})
        code_parts = ['{']
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get('type', 'string')
            prop_format = prop_schema.get('format', '')

            if has_faker:
                if prop_format == 'email':
                    code_parts.append(f'    "{prop_name}": fake.email(),')
                elif prop_format == 'uuid':
                    code_parts.append(f'    "{prop_name}": fake.uuid4(),')
                elif prop_type == 'string':
                    code_parts.append(f'    "{prop_name}": fake.word(),')
                elif prop_type == 'integer':
                    code_parts.append(f'    "{prop_name}": fake.random_int(1, 100),')
                elif prop_type == 'boolean':
                    code_parts.append(f'    "{prop_name}": fake.boolean(),')
                else:
                    code_parts.append(f'    "{prop_name}": "test_value",')
            else:
                code_parts.append(f'    "{prop_name}": "test_value",')

        code_parts.append('}')
        return '\n'.join(code_parts)

    elif schema_type == 'string':
        return '"test_string"' if not has_faker else 'fake.word()'
    elif schema_type == 'integer':
        return '42' if not has_faker else 'fake.random_int(1, 100)'
    elif schema_type == 'boolean':
        return 'True' if not has_faker else 'fake.boolean()'
    else:
        return '{}'


def generate_locustfile(endpoints: List[Dict[str, Any]],
                       host: str,
                       static_analysis: Dict[str, Any]) -> str:
    """
    Generate Locust test file from endpoints

    Args:
        endpoints: List of API endpoint definitions
        host: Base URL for the API
        static_analysis: Static analysis results

    Returns:
        Generated locustfile content
    """
    lines = [
        '"""',
        'Generated Locust Load Test',
        'Auto-generated performance test with plausible data',
        '"""',
        'from locust import HttpUser, task, between',
        'import json',
        '',
        'try:',
        '    from faker import Faker',
        '    fake = Faker()',
        'except ImportError:',
        '    fake = None',
        '',
        '',
        'class APIUser(HttpUser):',
        '    """Simulated API user for load testing"""',
        '    wait_time = between(1, 3)  # Wait 1-3 seconds between requests',
        '    ',
    ]

    # Generate task methods for each endpoint
    for i, endpoint in enumerate(endpoints):
        method = endpoint['method'].lower()
        path = endpoint['path']
        operation_id = endpoint['operation_id']

        # Replace path parameters with fake data
        path_with_params = path
        if '{' in path:
            # Simple parameter replacement
            path_with_params = path.replace('{id}', '1').replace('{uuid}', 'test-uuid')

        lines.append(f'    @task({i+1})')
        lines.append(f'    def {operation_id.replace("-", "_")}(self):')
        lines.append(f'        """Test {endpoint.get("summary", operation_id)}"""')

        # Generate request body if needed
        if method in ['post', 'put', 'patch'] and endpoint.get('request_body'):
            request_body_schema = endpoint['request_body'].get('content', {}).get('application/json', {}).get('schema', {})
            data_code = generate_plausible_data(request_body_schema, static_analysis)

            lines.append(f'        data = {data_code}')
            lines.append(f'        self.client.{method}(')
            lines.append(f'            "{path_with_params}",')
            lines.append(f'            json=data,')
            lines.append(f'            headers={{"Content-Type": "application/json"}}')
            lines.append(f'        )')
        else:
            lines.append(f'        self.client.{method}("{path_with_params}")')

        lines.append('')

    return '\n'.join(lines)


def run_locust(locustfile_path: str,
               host: str,
               users: int,
               spawn_rate: int,
               run_time: str) -> Dict[str, Any]:
    """
    Execute Locust load test

    Args:
        locustfile_path: Path to locustfile
        host: Base URL for API
        users: Number of concurrent users
        spawn_rate: Users spawned per second
        run_time: Test duration

    Returns:
        Test results and statistics
    """
    try:
        # Create temporary directory for results
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_file = os.path.join(tmpdir, 'stats.json')

            cmd = [
                'locust',
                '-f', locustfile_path,
                '--host', host,
                '--users', str(users),
                '--spawn-rate', str(spawn_rate),
                '--run-time', run_time,
                '--headless',
                '--html', os.path.join(tmpdir, 'report.html'),
                '--json', stats_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Parse stats if available
            stats = {}
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, 'r') as f:
                        stats = json.load(f)
                except Exception:
                    pass

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'stats': stats,
                'exit_code': result.returncode
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Test execution timeout',
            'stats': {}
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'Locust not installed. Run: pip install locust',
            'stats': {}
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        spec_file = input_data.get('spec_file')
        spec_content = input_data.get('spec_content')
        static_analysis_path = input_data.get('static_analysis_path')
        mode = input_data.get('mode', 'both')
        output_path = input_data.get('output_path', './locustfiles')
        users = input_data.get('users', 10)
        spawn_rate = input_data.get('spawn_rate', 2)
        run_time = input_data.get('run_time', '30s')
        host = input_data.get('host', 'http://localhost:8000')

        # Load spec
        spec = {}
        if spec_file and os.path.exists(spec_file):
            with open(spec_file, 'r') as f:
                import yaml
                try:
                    spec = yaml.safe_load(f)
                except:
                    f.seek(0)
                    spec = json.load(f)
        elif spec_content:
            import yaml
            try:
                spec = yaml.safe_load(spec_content)
            except:
                spec = json.loads(spec_content)
        else:
            # Create a basic spec for testing
            spec = {
                'paths': {
                    '/health': {'get': {'operationId': 'health_check', 'summary': 'Health check'}}
                }
            }

        # Load static analysis
        static_analysis = load_static_analysis(static_analysis_path)

        # Parse endpoints
        endpoints = parse_openapi_spec(spec)

        if not endpoints:
            raise ValueError("No endpoints found in spec")

        # Generate locustfile
        locustfile_content = generate_locustfile(endpoints, host, static_analysis)

        # Create output directory
        os.makedirs(output_path, exist_ok=True)
        locustfile_path = os.path.join(output_path, 'locustfile.py')

        # Write locustfile
        with open(locustfile_path, 'w') as f:
            f.write(locustfile_content)

        result = {
            'success': True,
            'locustfile_path': locustfile_path,
            'endpoints_count': len(endpoints),
            'mode': mode
        }

        # Run tests if requested
        if mode in ['run', 'both']:
            test_results = run_locust(locustfile_path, host, users, spawn_rate, run_time)
            result['results'] = test_results
            result['stats'] = test_results.get('stats', {})
            result['success'] = result['success'] and test_results.get('success', False)

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
