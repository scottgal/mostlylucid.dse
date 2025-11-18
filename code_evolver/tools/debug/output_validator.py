#!/usr/bin/env python3
"""
Output Validator

Validates that every tool produces output. Checks that:
1. Code has a main() function
2. main() function produces output (print, return, or write to file/stdout)
3. For stdin-based main(), ensures JSON output is produced

Exit codes:
  0 - Valid output production
  1 - Missing or insufficient output
  2 - Error
"""

import sys
import ast
from pathlib import Path
from typing import Tuple, List, Set


def find_main_function(tree: ast.AST) -> ast.FunctionDef | None:
    """Find the main() function definition."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'main':
            return node
    return None


def has_output_statement(func: ast.FunctionDef) -> Tuple[bool, List[str]]:
    """
    Check if function has output statements.

    Returns:
        (has_output, list of output types found)
    """
    output_types = []

    for node in ast.walk(func):
        # Check for print() calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'print':
                output_types.append('print')

        # Check for sys.stdout.write()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (node.func.attr == 'write' and
                    isinstance(node.func.value, ast.Attribute) and
                    node.func.value.attr == 'stdout'):
                    output_types.append('stdout.write')

        # Check for return statements (non-None)
        if isinstance(node, ast.Return) and node.value is not None:
            output_types.append('return')

        # Check for file writes
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ['write', 'writelines']:
                    output_types.append('file.write')

    return (len(output_types) > 0, list(set(output_types)))


def has_json_output(tree: ast.AST, func: ast.FunctionDef) -> bool:
    """Check if main() produces JSON output."""
    # Check for json.dumps() in the function
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (node.func.attr == 'dumps' and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'json'):
                    return True
    return False


def reads_stdin(func: ast.FunctionDef) -> bool:
    """Check if function reads from stdin."""
    for node in ast.walk(func):
        # Check for json.load(sys.stdin)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'load':
                    for arg in node.args:
                        if isinstance(arg, ast.Attribute):
                            if (arg.attr == 'stdin' and
                                isinstance(arg.value, ast.Name) and
                                arg.value.id == 'sys'):
                                return True

        # Check for sys.stdin.read()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (node.func.attr in ['read', 'readline', 'readlines'] and
                    isinstance(node.func.value, ast.Attribute) and
                    node.func.value.attr == 'stdin'):
                    return True

    return False


def validate_output(filepath: str) -> Tuple[bool, str]:
    """
    Validate that code produces output.

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

    # Find main() function
    main_func = find_main_function(tree)
    if not main_func:
        return True, "Skipped: No main() function (not a node entrypoint)"

    # Check if main() produces output
    has_output, output_types = has_output_statement(main_func)

    if not has_output:
        return False, (
            "FAIL: main() function produces no output\n"
            "  Every tool must produce output via:\n"
            "  - print() statements\n"
            "  - return values\n"
            "  - file writes\n"
            "  Add output to your main() function."
        )

    # If reads from stdin, should output JSON
    if reads_stdin(main_func):
        if not has_json_output(tree, main_func):
            return False, (
                "FAIL: main() reads from stdin but doesn't output JSON\n"
                "  Stdin-based tools should output JSON:\n"
                "    print(json.dumps({'result': your_data}))"
            )

        # Check for print with json.dumps
        has_print_json = False
        for node in ast.walk(main_func):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    # Check if argument is json.dumps()
                    for arg in node.args:
                        if isinstance(arg, ast.Call):
                            if isinstance(arg.func, ast.Attribute):
                                if (arg.func.attr == 'dumps' and
                                    isinstance(arg.func.value, ast.Name) and
                                    arg.func.value.id == 'json'):
                                    has_print_json = True

        if not has_print_json:
            return False, (
                f"FAIL: JSON output found but not printed\n"
                f"  Output types: {', '.join(output_types)}\n"
                f"  Use: print(json.dumps({{'result': data}}))"
            )

    # All checks passed
    output_desc = ', '.join(output_types)
    return True, f"OK: main() produces output via {output_desc}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: output_validator.py <python_file>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    is_valid, message = validate_output(filepath)

    print(message)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
