#!/usr/bin/env python3
"""
Docker Compose Generator
Generates docker-compose.yml for tool API wrappers
"""
import json
import sys
import yaml
from typing import Dict, Any


def generate_docker_compose(config: Dict[str, Any]) -> str:
    """
    Generate a docker-compose.yml for a tool API wrapper

    Args:
        config: Configuration dictionary with:
            - service_name: Name of the service
            - image_name: Docker image name
            - port: Port to expose
            - env_vars: Environment variables (dict)
            - volumes: Volume mappings (list)
            - depends_on: Service dependencies (list)

    Returns:
        Generated docker-compose.yml content
    """
    service_name = config.get('service_name', 'tool-api')
    image_name = config.get('image_name', 'tool-api:latest')
    port = config.get('port', 8080)
    env_vars = config.get('env_vars', {})
    volumes = config.get('volumes', [])
    depends_on = config.get('depends_on', [])

    compose_config = {
        'version': '3.8',
        'services': {
            service_name: {
                'image': image_name,
                'build': {
                    'context': '.',
                    'dockerfile': 'Dockerfile'
                },
                'ports': [
                    f'{port}:{port}'
                ],
                'environment': env_vars if env_vars else {},
                'restart': 'unless-stopped',
                'healthcheck': {
                    'test': ['CMD', 'curl', '-f', f'http://localhost:{port}/api/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3,
                    'start_period': '40s'
                }
            }
        }
    }

    # Add volumes if specified
    if volumes:
        compose_config['services'][service_name]['volumes'] = volumes

    # Add dependencies if specified
    if depends_on:
        compose_config['services'][service_name]['depends_on'] = depends_on

    # Convert to YAML
    yaml_content = yaml.dump(compose_config, default_flow_style=False, sort_keys=False)

    return yaml_content


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'Missing configuration JSON argument'
        }))
        sys.exit(1)

    try:
        # Parse configuration from command line argument
        config = json.loads(sys.argv[1])

        # Generate docker-compose.yml
        compose_content = generate_docker_compose(config)

        # Output result
        print(json.dumps({
            'success': True,
            'docker_compose': compose_content
        }))

    except json.JSONDecodeError as e:
        print(json.dumps({
            'error': f'Invalid JSON configuration: {e}'
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            'error': f'Error generating docker-compose.yml: {e}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
