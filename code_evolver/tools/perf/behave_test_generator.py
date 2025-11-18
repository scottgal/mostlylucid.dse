#!/usr/bin/env python3
"""
Behave BDD Test Generator
Generates Behave step definitions from Gherkin features with plausible data
"""
import json
import sys
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def parse_feature_file(content: str) -> Dict[str, Any]:
    """
    Parse Gherkin feature file content

    Args:
        content: Gherkin feature content

    Returns:
        Parsed feature structure
    """
    lines = content.strip().split('\n')
    feature = {
        'name': '',
        'description': [],
        'scenarios': []
    }

    current_scenario = None
    current_section = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('Feature:'):
            feature['name'] = stripped.replace('Feature:', '').strip()
        elif stripped.startswith('Scenario:') or stripped.startswith('Scenario Outline:'):
            if current_scenario:
                feature['scenarios'].append(current_scenario)
            current_scenario = {
                'name': stripped.split(':', 1)[1].strip(),
                'type': 'outline' if 'Outline' in stripped else 'normal',
                'steps': [],
                'examples': []
            }
            current_section = 'steps'
        elif stripped.startswith('Examples:'):
            current_section = 'examples'
        elif current_scenario and stripped and not stripped.startswith('#'):
            if current_section == 'steps':
                # Parse step (Given/When/Then/And/But)
                step_match = re.match(r'(Given|When|Then|And|But)\s+(.+)', stripped)
                if step_match:
                    current_scenario['steps'].append({
                        'keyword': step_match.group(1),
                        'text': step_match.group(2)
                    })
            elif current_section == 'examples':
                if '|' in stripped:
                    current_scenario['examples'].append(stripped)
        elif not stripped.startswith('Feature:') and not current_scenario and stripped:
            feature['description'].append(stripped)

    if current_scenario:
        feature['scenarios'].append(current_scenario)

    return feature


def generate_from_tool_spec(tool_spec: Dict[str, Any]) -> str:
    """
    Generate Gherkin feature from tool specification

    Args:
        tool_spec: Tool YAML specification

    Returns:
        Gherkin feature content
    """
    tool_name = tool_spec.get('name', 'Unknown Tool')
    description = tool_spec.get('description', '')
    input_schema = tool_spec.get('input_schema', {})
    output_schema = tool_spec.get('output_schema', {})

    lines = [
        f'Feature: {tool_name}',
        f'  {description}',
        '',
        f'  Scenario: Successfully execute {tool_name}',
        '    Given the tool is properly configured',
    ]

    # Add input parameters
    for param_name, param_spec in input_schema.items():
        param_type = param_spec.get('type', 'string')
        param_desc = param_spec.get('description', param_name)
        if param_spec.get('required', False):
            lines.append(f'    And I provide {param_name} as "{param_desc}"')

    lines.append(f'    When I execute the {tool_name} tool')
    lines.append('    Then the execution should succeed')

    # Add output validations
    if output_schema:
        lines.append('    And the output should contain valid data')

    lines.append('')
    lines.append(f'  Scenario: Handle invalid input for {tool_name}')
    lines.append('    Given the tool is properly configured')
    lines.append('    And I provide invalid input data')
    lines.append(f'    When I execute the {tool_name} tool')
    lines.append('    Then the execution should fail gracefully')
    lines.append('    And an error message should be provided')

    return '\n'.join(lines)


def extract_step_patterns(scenarios: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """
    Extract unique step patterns from scenarios

    Args:
        scenarios: List of parsed scenarios

    Returns:
        List of (step_text, keyword) tuples
    """
    patterns = []
    seen = set()

    for scenario in scenarios:
        # Ensure scenario is a dict and has steps
        if not isinstance(scenario, dict):
            continue

        steps = scenario.get('steps', [])
        if not isinstance(steps, list):
            continue

        for step in steps:
            # Ensure step is a dict with required fields
            if not isinstance(step, dict):
                continue

            text = step.get('text', '')
            keyword = step.get('keyword', '')

            # Ensure both are strings
            if not isinstance(text, str) or not isinstance(keyword, str):
                continue

            # Normalize keyword (And/But -> Given/When/Then based on context)
            if keyword in ['And', 'But']:
                keyword = 'Given'  # Default, could be smarter

            # Create pattern by replacing quoted strings and numbers with placeholders
            pattern = re.sub(r'"[^"]*"', '"{param}"', text)
            pattern = re.sub(r'\b\d+\b', '{number}', pattern)

            pattern_key = (pattern, keyword)
            if pattern_key not in seen:
                seen.add(pattern_key)
                patterns.append((text, keyword, pattern))

    return patterns


def generate_step_definitions(feature: Dict[str, Any],
                             static_analysis: Dict[str, Any]) -> str:
    """
    Generate Behave step definitions from feature

    Args:
        feature: Parsed feature structure
        static_analysis: Static analysis results

    Returns:
        Python step definitions code
    """
    lines = [
        '"""',
        f'Step definitions for: {feature["name"]}',
        'Auto-generated Behave step definitions',
        '"""',
        'from behave import given, when, then, step',
        'import json',
        '',
        'try:',
        '    from faker import Faker',
        '    fake = Faker()',
        'except ImportError:',
        '    fake = None',
        '',
        ''
    ]

    # Extract step patterns
    patterns = extract_step_patterns(feature['scenarios'])

    # Generate step definitions
    for i, (text, keyword, pattern) in enumerate(patterns):
        # Ensure keyword is a string before calling .lower()
        if not isinstance(keyword, str):
            continue

        # Determine decorator
        decorator = keyword.lower()

        # Ensure text is a string
        if not isinstance(text, str):
            continue

        # Create step function
        function_name = re.sub(r'[^a-z0-9_]', '_', text.lower())
        function_name = re.sub(r'_+', '_', function_name).strip('_')

        # Extract parameters from pattern
        params = re.findall(r'\{(\w+)\}', pattern)
        param_str = ', '.join(params) if params else ''

        lines.append(f'@{decorator}(\'.*{re.escape(text[:30])}.*\')')
        lines.append(f'def step_{function_name}_{i}(context{", " + param_str if param_str else ""}):')
        lines.append(f'    """Step: {text}"""')

        # Add implementation based on keyword
        if keyword == 'Given':
            lines.append('    # Setup/precondition')
            lines.append('    context.test_data = {}')
            if param_str:
                for param in params:
                    lines.append(f'    context.test_data["{param}"] = {param}')
        elif keyword == 'When':
            lines.append('    # Action/execution')
            lines.append('    try:')
            lines.append('        # Execute the action here')
            lines.append('        context.result = {"success": True}')
            lines.append('    except Exception as e:')
            lines.append('        context.error = str(e)')
            lines.append('        context.result = {"success": False, "error": str(e)}')
        elif keyword == 'Then':
            lines.append('    # Assertion/verification')
            lines.append('    assert hasattr(context, "result"), "No result found"')
            if 'succeed' in text.lower() or 'success' in text.lower():
                lines.append('    assert context.result.get("success"), "Expected success"')
            elif 'fail' in text.lower() or 'error' in text.lower():
                lines.append('    assert not context.result.get("success"), "Expected failure"')

        lines.append('    pass')
        lines.append('')
        lines.append('')

    return '\n'.join(lines)


def run_behave(feature_path: str) -> Dict[str, Any]:
    """
    Execute Behave tests

    Args:
        feature_path: Path to feature directory

    Returns:
        Test results
    """
    try:
        cmd = [
            'behave',
            feature_path,
            '--format', 'json',
            '--no-capture'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        # Parse JSON output
        test_results = {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }

        # Try to parse JSON output
        try:
            if result.stdout:
                json_output = json.loads(result.stdout)
                test_results['scenarios'] = json_output
        except json.JSONDecodeError:
            pass

        return test_results

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Test execution timeout'
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'Behave not installed. Run: pip install behave'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def load_static_analysis(path: Optional[str]) -> Dict[str, Any]:
    """
    Load static analysis results

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


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        feature_file = input_data.get('feature_file')
        feature_content = input_data.get('feature_content')
        tool_spec_path = input_data.get('tool_spec')
        static_analysis_path = input_data.get('static_analysis_path')
        mode = input_data.get('mode', 'both')
        output_path = input_data.get('output_path', './features/steps')
        feature_output_path = input_data.get('feature_output_path', './features')

        # Load static analysis
        static_analysis = load_static_analysis(static_analysis_path)

        # Determine feature source
        if tool_spec_path and os.path.exists(tool_spec_path):
            # Generate from tool spec
            import yaml
            with open(tool_spec_path, 'r') as f:
                tool_spec = yaml.safe_load(f)
            feature_content = generate_from_tool_spec(tool_spec)

        # Load or use provided feature content
        if not feature_content and feature_file and os.path.exists(feature_file):
            with open(feature_file, 'r') as f:
                feature_content = f.read()

        if not feature_content:
            # Create a basic feature for testing
            feature_content = '''Feature: Basic Test
  Basic test feature

  Scenario: Basic scenario
    Given the system is ready
    When I perform an action
    Then the result should be successful
'''

        # Parse feature
        feature = parse_feature_file(feature_content)

        # Generate step definitions
        steps_content = generate_step_definitions(feature, static_analysis)

        # Create output directories
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(feature_output_path, exist_ok=True)

        # Write files
        steps_file_path = os.path.join(output_path, 'steps.py')
        with open(steps_file_path, 'w') as f:
            f.write(steps_content)

        # Ensure feature name is a string and sanitize it for filename
        feature_name = feature.get("name", "unnamed_feature")
        if not isinstance(feature_name, str):
            feature_name = "unnamed_feature"
        safe_feature_name = feature_name.lower().replace(" ", "_")
        feature_file_path = os.path.join(feature_output_path, f'{safe_feature_name}.feature')
        with open(feature_file_path, 'w') as f:
            f.write(feature_content)

        result = {
            'success': True,
            'steps_file_path': steps_file_path,
            'feature_file_path': feature_file_path,
            'scenarios_count': len(feature['scenarios']),
            'mode': mode
        }

        # Run tests if requested
        if mode in ['run', 'both']:
            test_results = run_behave(feature_output_path)
            result['results'] = test_results
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
