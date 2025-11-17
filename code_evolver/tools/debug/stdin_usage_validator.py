#!/usr/bin/env python3
"""
Stdin Usage Validator

Validates that node code properly reads from stdin using json.load(sys.stdin).

Exit codes:
  0 - Valid stdin usage
  1 - Invalid or missing stdin read
  2 - Error
"""

import sys
import ast
from pathlib import Path
from typing import Tuple


def has_json_load_stdin(tree: ast.AST) -> Tuple[bool, int]:
    """
    Check if code has json.load(sys.stdin).

    Returns:
        (has_it, line_number)
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for json.load()
            if isinstance(node.func, ast.Attribute):
                if (node.func.attr == 'load' and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'json'):

                    # Check if argument is sys.stdin
                    if node.args:
                        arg = node.args[0]
                        if isinstance(arg, ast.Attribute):
                            if (arg.attr == 'stdin' and
                                isinstance(arg.value, ast.Name) and
                                arg.value.id == 'sys'):
                                return True, node.lineno

    return False, 0


def has_input_data_usage(tree: ast.AST) -> bool:
    """Check if code uses input_data variable."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id == 'input_data':
                return True
    return False


def validate_stdin_usage(filepath: str) -> Tuple[bool, str]:
    """
    Validate stdin usage in Python file.

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

    # Check if code uses input_data
    uses_input_data = has_input_data_usage(tree)

    if not uses_input_data:
        # No input_data used - stdin read not required
        return True, "OK: No input_data usage (stdin read not required)"

    # If input_data is used, must read from stdin
    has_stdin, line = has_json_load_stdin(tree)

    if not has_stdin:
        return False, (
            "FAIL: Code uses 'input_data' but doesn't read from stdin\n"
            "  Add:\n"
            "    import json\n"
            "    import sys\n"
            "    input_data = json.load(sys.stdin)"
        )

    # All checks passed
    return True, f"OK: Proper stdin read found at line {line}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: stdin_usage_validator.py <python_file>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    is_valid, message = validate_stdin_usage(filepath)

    print(message)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
