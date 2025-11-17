#!/usr/bin/env python3
"""
Create Locust Specification
Creates a Locust load test specification for RAG storage
"""
import json
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


def create_locust_spec(tool_name: str,
                       endpoints: Optional[List[Dict[str, Any]]],
                       base_url: str) -> Dict[str, Any]:
    """
    Create a Locust test specification

    Args:
        tool_name: Name of the tool
        endpoints: List of endpoint definitions
        base_url: Base URL for the API

    Returns:
        Locust specification dictionary
    """
    spec = {
        'name': f'{tool_name} Load Test Specification',
        'version': '1.0.0',
        'type': 'locust_spec',
        'tool_name': tool_name,
        'base_url': base_url,
        'test_config': {
            'users': 10,
            'spawn_rate': 2,
            'run_time': '30s',
            'wait_time': {
                'min': 1,
                'max': 3
            }
        },
        'endpoints': endpoints or [
            {
                'path': '/health',
                'method': 'GET',
                'weight': 10,
                'description': 'Health check endpoint'
            }
        ],
        'data_generation': {
            'use_faker': True,
            'use_static_analysis': True,
            'randomize': True
        },
        'assertions': [
            {
                'type': 'response_time',
                'threshold_ms': 1000,
                'percentile': 95
            },
            {
                'type': 'success_rate',
                'threshold': 0.99
            }
        ],
        'metadata': {
            'created_by': 'create_locust_spec',
            'purpose': 'Performance characterization and load testing',
            'rag_tags': ['performance', 'load-test', 'characterization', tool_name]
        }
    }

    return spec


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        tool_name = input_data.get('tool_name', 'unknown_tool')
        endpoints = input_data.get('endpoints')
        base_url = input_data.get('base_url', 'http://localhost:8000')
        output_path = input_data.get('output_path', './specs/locust')

        # Create spec
        spec = create_locust_spec(tool_name, endpoints, base_url)

        # Create output directory
        os.makedirs(output_path, exist_ok=True)

        # Save spec file
        spec_filename = f'{tool_name.lower().replace(" ", "_")}_locust_spec.yaml'
        spec_path = os.path.join(output_path, spec_filename)

        with open(spec_path, 'w') as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)

        # Output result
        print(json.dumps({
            'success': True,
            'spec_path': spec_path,
            'spec': spec
        }, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
