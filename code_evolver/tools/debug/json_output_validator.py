#!/usr/bin/env python3
"""
JSON Output Validator

Validates that Python code outputs valid JSON.
Checks for json.dumps() calls and proper structure.

Exit codes:
  0 - Valid JSON output
  1 - Missing or invalid JSON output
  2 - Error
"""

import sys
import ast
from pathlib import Path
from typing import Tuple, List


def find_json_dumps(tree: ast.AST) -> List[int]:
    """
    Find all json.dumps() calls in the code.

    Returns:
        List of line numbers where json.dumps() is called
    """
    dumps_lines = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for json.dumps()
            if isinstance(node.func, ast.Attribute):
                if (node.func.attr == 'dumps' and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'json'):
                    dumps_lines.append(node.lineno)

    return dumps_lines


def find_print_statements(tree: ast.AST) -> List[int]:
    """
    Find all print() calls in the code.

    Returns:
        List of line numbers where print() is called
    """
    print_lines = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'print':
                print_lines.append(node.lineno)

    return print_lines


def has_json_import(tree: ast.AST) -> bool:
    """Check if json module is imported."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'json':
                    return True
        if isinstance(node, ast.ImportFrom):
            if node.module == 'json':
                return True
    return False


def validate_json_output(filepath: str) -> Tuple[bool, str]:
    """
    Validate that a Python file outputs valid JSON.

    Args:
        filepath: Path to Python file

    Returns:
        (is_valid, message)
    """
    path = Path(filepath)

    if not path.exists():
        return False, f"File not found: {filepath}"

    if not path.suffix == '.py':
        return True, "Skipped: Not a Python file"

    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Error reading file: {e}"

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Check if this file should output JSON (has json import and main function)
    has_main = any(
        isinstance(node, ast.FunctionDef) and node.name == 'main'
        for node in ast.walk(tree)
    )

    if not has_main:
        return True, "Skipped: No main() function (not a node entrypoint)"

    # Find JSON-related code
    has_import = has_json_import(tree)
    dumps_lines = find_json_dumps(tree)
    print_lines = find_print_statements(tree)

    # If no json import, check if it needs one
    if not has_import:
        return False, (
            "FAIL: No json import found\n"
            "  Add: import json"
        )

    # If no json.dumps() calls, that's suspicious for a node
    if not dumps_lines:
        return False, (
            "FAIL: No json.dumps() calls found\n"
            "  Nodes should output JSON using:\n"
            "    print(json.dumps({'result': your_data}))"
        )

    # Check if json.dumps() is used with print()
    # This is a heuristic - we look for print() calls near json.dumps()
    if not print_lines:
        return False, (
            f"FAIL: json.dumps() at line {dumps_lines[0]} but no print() found\n"
            "  Output JSON with:\n"
            "    print(json.dumps({'result': your_data}))"
        )

    # All checks passed
    return True, (
        f"OK: JSON output found (json.dumps at line {dumps_lines[0]}, "
        f"print at line {print_lines[0]})"
    )


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: json_output_validator.py <python_file>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    is_valid, message = validate_json_output(filepath)

    print(message)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
