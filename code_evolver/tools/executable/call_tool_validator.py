#!/usr/bin/env python3
"""
call_tool() Usage Validator

Validates that call_tool() is used correctly with proper arguments.

Exit codes:
  0 - Valid call_tool() usage
  1 - Invalid usage
  2 - Error
"""

import sys
import ast
from pathlib import Path
from typing import Tuple, List


class CallToolVisitor(ast.NodeVisitor):
    """AST visitor to find call_tool() calls."""

    def __init__(self):
        self.call_tool_calls = []

    def visit_Call(self, node):
        # Check for call_tool() function calls
        if isinstance(node.func, ast.Name) and node.func.id == 'call_tool':
            self.call_tool_calls.append({
                'line': node.lineno,
                'args': len(node.args),
                'kwargs': len(node.keywords)
            })
        self.generic_visit(node)


def validate_call_tool_usage(filepath: str) -> Tuple[bool, str]:
    """
    Validate call_tool() usage in Python file.

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

    # Find all call_tool() calls
    visitor = CallToolVisitor()
    visitor.visit(tree)

    if not visitor.call_tool_calls:
        # No call_tool() usage - that's fine
        return True, "OK: No call_tool() usage (not required)"

    # Check if node_runtime is imported
    has_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'node_runtime':
                for alias in node.names:
                    if alias.name == 'call_tool':
                        has_import = True
                        break

    if not has_import:
        first_call = visitor.call_tool_calls[0]
        return False, (
            f"FAIL: call_tool() used at line {first_call['line']} "
            f"but not imported\n"
            f"  Add:\n"
            f"    from node_runtime import call_tool"
        )

    # Validate each call
    errors = []
    for call in visitor.call_tool_calls:
        # call_tool() expects 2 arguments: (tool_name, prompt)
        if call['args'] < 2:
            errors.append(
                f"  Line {call['line']}: call_tool() expects 2 arguments "
                f"(tool_name, prompt), got {call['args']}"
            )

        if call['args'] > 2:
            errors.append(
                f"  Line {call['line']}: call_tool() expects 2 arguments, "
                f"got {call['args']}"
            )

    if errors:
        return False, (
            f"FAIL: Invalid call_tool() usage:\n" +
            "\n".join(errors) +
            "\n\n  Correct usage:\n"
            "    result = call_tool('tool_name', 'your prompt here')"
        )

    # All checks passed
    return True, (
        f"OK: {len(visitor.call_tool_calls)} call_tool() call(s) found, "
        f"all valid"
    )


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: call_tool_validator.py <python_file>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    is_valid, message = validate_call_tool_usage(filepath)

    print(message)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
