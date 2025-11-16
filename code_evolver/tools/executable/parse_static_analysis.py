#!/usr/bin/env python3
"""
Parse Static Analysis Results
Extracts schemas, patterns, and hints from static analysis for test generation
"""
import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


def parse_analysis_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a single static analysis file

    Args:
        file_path: Path to analysis JSON file

    Returns:
        Parsed analysis data
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {'error': str(e), 'file': file_path}


def extract_schemas(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract JSON schemas from analysis results

    Args:
        analysis: Static analysis results

    Returns:
        List of extracted schemas
    """
    schemas = []

    # Look for input/output schemas
    if 'input_schema' in analysis:
        schemas.append({
            'type': 'input',
            'schema': analysis['input_schema']
        })

    if 'output_schema' in analysis:
        schemas.append({
            'type': 'output',
            'schema': analysis['output_schema']
        })

    # Look for JSON validation results
    if 'validators' in analysis:
        json_validator = analysis['validators'].get('json_output', {})
        if json_validator.get('valid') and 'schema' in json_validator:
            schemas.append({
                'type': 'validated_output',
                'schema': json_validator['schema']
            })

    return schemas


def extract_patterns(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract code patterns and common values

    Args:
        analysis: Static analysis results

    Returns:
        Extracted patterns
    """
    patterns = {
        'imports': [],
        'functions': [],
        'common_values': [],
        'error_types': [],
        'data_types': []
    }

    # Extract from validators
    validators = analysis.get('validators', {})

    # Import patterns
    import_validator = validators.get('import_order', {})
    if import_validator.get('valid'):
        patterns['imports'] = import_validator.get('imports', [])

    # Function patterns
    syntax_validator = validators.get('syntax', {})
    if 'functions' in syntax_validator:
        patterns['functions'] = syntax_validator['functions']

    # Security patterns (things to avoid in tests)
    security_validator = validators.get('security', {})
    if security_validator.get('issues'):
        patterns['security_issues'] = security_validator['issues']

    # Undefined names (for data generation hints)
    undefined_validator = validators.get('undefined_names', {})
    if not undefined_validator.get('valid'):
        patterns['undefined_names'] = undefined_validator.get('undefined', [])

    # Type hints
    type_validator = validators.get('type_checking', {})
    if 'types' in type_validator:
        patterns['type_hints'] = type_validator['types']

    return patterns


def generate_test_hints(schemas: List[Dict[str, Any]],
                        patterns: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate hints for test data generation

    Args:
        schemas: Extracted schemas
        patterns: Extracted patterns

    Returns:
        Test generation hints
    """
    hints = {
        'data_types': set(),
        'common_patterns': [],
        'boundary_values': [],
        'error_cases': []
    }

    # Extract data types from schemas
    for schema_entry in schemas:
        schema = schema_entry.get('schema', {})
        if isinstance(schema, dict):
            for key, value in schema.items():
                if isinstance(value, dict) and 'type' in value:
                    hints['data_types'].add(value['type'])

    # Extract common patterns
    if patterns.get('imports'):
        # Identify commonly used libraries for data generation
        common_libs = ['faker', 'random', 'datetime', 'uuid']
        for imp in patterns['imports']:
            for lib in common_libs:
                if lib in imp.lower():
                    hints['common_patterns'].append(f'uses_{lib}')

    # Extract boundary cases from patterns
    if patterns.get('security_issues'):
        for issue in patterns['security_issues']:
            hints['error_cases'].append({
                'type': 'security',
                'pattern': issue.get('test_name', 'unknown')
            })

    # Convert set to list for JSON serialization
    hints['data_types'] = list(hints['data_types'])

    return hints


def aggregate_quality_metrics(analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate quality metrics across multiple analysis results

    Args:
        analysis_results: List of analysis results

    Returns:
        Aggregated metrics
    """
    metrics = {
        'total_files': len(analysis_results),
        'validators': defaultdict(lambda: {'passed': 0, 'failed': 0}),
        'complexity': {
            'average': 0.0,
            'max': 0.0,
            'min': float('inf')
        },
        'issues': {
            'total': 0,
            'by_type': defaultdict(int)
        }
    }

    for analysis in analysis_results:
        if 'error' in analysis:
            continue

        # Aggregate validator results
        validators = analysis.get('validators', {})
        for validator_name, validator_result in validators.items():
            if isinstance(validator_result, dict):
                is_valid = validator_result.get('valid', False)
                if is_valid:
                    metrics['validators'][validator_name]['passed'] += 1
                else:
                    metrics['validators'][validator_name]['failed'] += 1

        # Aggregate complexity
        complexity_data = validators.get('complexity', {})
        if 'average_complexity' in complexity_data:
            avg = complexity_data['average_complexity']
            metrics['complexity']['average'] += avg
            metrics['complexity']['max'] = max(metrics['complexity']['max'], avg)
            metrics['complexity']['min'] = min(metrics['complexity']['min'], avg)

        # Count issues
        for validator_result in validators.values():
            if isinstance(validator_result, dict) and not validator_result.get('valid', True):
                metrics['issues']['total'] += 1
                issue_type = validator_result.get('type', 'unknown')
                metrics['issues']['by_type'][issue_type] += 1

    # Calculate average complexity
    if metrics['total_files'] > 0:
        metrics['complexity']['average'] /= metrics['total_files']

    # Convert defaultdict to regular dict for JSON serialization
    metrics['validators'] = dict(metrics['validators'])
    metrics['issues']['by_type'] = dict(metrics['issues']['by_type'])

    return metrics


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        analysis_file = input_data.get('analysis_file')
        registry_path = input_data.get('registry_path')
        extract_schemas_flag = input_data.get('extract_schemas', True)
        extract_patterns_flag = input_data.get('extract_patterns', True)

        # Collect analysis files
        analysis_results = []

        if analysis_file and os.path.exists(analysis_file):
            analysis_results.append(parse_analysis_file(analysis_file))
        elif registry_path and os.path.exists(registry_path):
            # Find all static_analysis.json files in registry
            for root, dirs, files in os.walk(registry_path):
                for file in files:
                    if file == 'static_analysis.json':
                        file_path = os.path.join(root, file)
                        analysis_results.append(parse_analysis_file(file_path))

        if not analysis_results:
            # Create a minimal result
            analysis_results = [{
                'validators': {},
                'message': 'No analysis files found'
            }]

        # Extract schemas and patterns
        all_schemas = []
        all_patterns = {
            'imports': [],
            'functions': [],
            'common_values': [],
            'error_types': [],
            'data_types': []
        }

        for analysis in analysis_results:
            if 'error' in analysis:
                continue

            if extract_schemas_flag:
                schemas = extract_schemas(analysis)
                all_schemas.extend(schemas)

            if extract_patterns_flag:
                patterns = extract_patterns(analysis)
                # Merge patterns
                for key in all_patterns:
                    if key in patterns:
                        if isinstance(patterns[key], list):
                            all_patterns[key].extend(patterns[key])

        # Generate test hints
        test_hints = generate_test_hints(all_schemas, all_patterns)

        # Aggregate quality metrics
        quality_metrics = aggregate_quality_metrics(analysis_results)

        # Output result
        print(json.dumps({
            'success': True,
            'schemas': all_schemas,
            'patterns': all_patterns,
            'test_hints': test_hints,
            'quality_metrics': quality_metrics,
            'files_processed': len(analysis_results)
        }, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
