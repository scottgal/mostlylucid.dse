#!/usr/bin/env python3
"""
Create Behave Specification
Creates a Behave BDD specification for RAG storage
"""
import json
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


def create_behave_spec(tool_name: str,
                       description: Optional[str],
                       scenarios: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Create a Behave BDD specification

    Args:
        tool_name: Name of the tool
        description: Tool description
        scenarios: List of scenario definitions

    Returns:
        Behave specification dictionary
    """
    spec = {
        'name': f'{tool_name} BDD Specification',
        'version': '1.0.0',
        'type': 'behave_spec',
        'tool_name': tool_name,
        'description': description or f'BDD specification for {tool_name}',
        'scenarios': scenarios or [
            {
                'name': 'Successful execution',
                'steps': [
                    {'keyword': 'Given', 'text': 'the tool is properly configured'},
                    {'keyword': 'And', 'text': 'valid input data is provided'},
                    {'keyword': 'When', 'text': 'the tool is executed'},
                    {'keyword': 'Then', 'text': 'the execution should succeed'},
                    {'keyword': 'And', 'text': 'the output should be valid'}
                ]
            },
            {
                'name': 'Invalid input handling',
                'steps': [
                    {'keyword': 'Given', 'text': 'the tool is properly configured'},
                    {'keyword': 'And', 'text': 'invalid input data is provided'},
                    {'keyword': 'When', 'text': 'the tool is executed'},
                    {'keyword': 'Then', 'text': 'the execution should fail gracefully'},
                    {'keyword': 'And', 'text': 'an error message should be returned'}
                ]
            }
        ],
        'data_generation': {
            'use_faker': True,
            'use_static_analysis': True,
            'randomize': True
        },
        'metadata': {
            'created_by': 'create_behave_spec',
            'purpose': 'Behavioral characterization and acceptance testing',
            'rag_tags': ['bdd', 'acceptance', 'characterization', tool_name]
        }
    }

    return spec


def generate_feature_file(spec: Dict[str, Any]) -> str:
    """
    Generate Gherkin feature file content from spec

    Args:
        spec: Behave specification

    Returns:
        Feature file content
    """
    lines = [
        f'Feature: {spec["tool_name"]}',
        f'  {spec["description"]}',
        ''
    ]

    for scenario in spec['scenarios']:
        lines.append(f'  Scenario: {scenario["name"]}')
        for step in scenario['steps']:
            lines.append(f'    {step["keyword"]} {step["text"]}')
        lines.append('')

    return '\n'.join(lines)


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        tool_name = input_data.get('tool_name', 'unknown_tool')
        description = input_data.get('description')
        scenarios = input_data.get('scenarios')
        output_path = input_data.get('output_path', './specs/behave')

        # Create spec
        spec = create_behave_spec(tool_name, description, scenarios)

        # Create output directory
        os.makedirs(output_path, exist_ok=True)

        # Save spec file
        spec_filename = f'{tool_name.lower().replace(" ", "_")}_behave_spec.yaml'
        spec_path = os.path.join(output_path, spec_filename)

        with open(spec_path, 'w') as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)

        # Generate and save feature file
        feature_content = generate_feature_file(spec)
        feature_filename = f'{tool_name.lower().replace(" ", "_")}.feature'
        feature_path = os.path.join(output_path, feature_filename)

        with open(feature_path, 'w') as f:
            f.write(feature_content)

        # Output result
        print(json.dumps({
            'success': True,
            'spec_path': spec_path,
            'feature_path': feature_path,
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
