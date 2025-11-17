#!/usr/bin/env python3
"""
Node Runtime Import Validator

Validates that node_runtime imports come AFTER sys.path.insert() setup.
This prevents ModuleNotFoundError at runtime.

Exit codes:
  0 - Validation passed
  1 - Validation failed (wrong import order)
  2 - Error (file not found, syntax error, etc.)
"""

import sys
import ast
from pathlib import Path
from typing import Optional, Tuple


def find_node_runtime_import(tree: ast.AST) -> Optional[int]:
    """
    Find the line number of node_runtime import.

    Returns:
        Line number (1-indexed) or None if not found
    """
    for node in ast.walk(tree):
        # Check for: from node_runtime import ...
        if isinstance(node, ast.ImportFrom):
            if node.module == 'node_runtime':
                return node.lineno

        # Check for: import node_runtime
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'node_runtime':
                    return node.lineno

    return None


def find_path_setup(tree: ast.AST) -> Optional[int]:
    """
    Find the line number of sys.path.insert() call.

    Looks for: sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    Returns:
        Line number (1-indexed) or None if not found
    """
    for node in ast.walk(tree):
        # Look for expression statements that are function calls
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value

            # Check if it's sys.path.insert()
            if (isinstance(call.func, ast.Attribute) and
                call.func.attr == 'insert' and
                isinstance(call.func.value, ast.Attribute) and
                call.func.value.attr == 'path' and
                isinstance(call.func.value.value, ast.Name) and
                call.func.value.value.id == 'sys'):
                return node.lineno

    return None


def validate_file(filepath: str) -> Tuple[bool, str]:
    """
    Validate a Python file for correct node_runtime import order.

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

    # Parse the file
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Find import lines
    node_runtime_line = find_node_runtime_import(tree)
    path_setup_line = find_path_setup(tree)

    # If no node_runtime import, validation passes
    if node_runtime_line is None:
        return True, "OK: No node_runtime import found"

    # If node_runtime import exists but no path setup, that's an error
    if path_setup_line is None:
        return False, (
            f"FAIL: node_runtime import at line {node_runtime_line} "
            f"but no sys.path.insert() found!\n"
            f"  Add this BEFORE the import:\n"
            f"    import sys\n"
            f"    from pathlib import Path\n"
            f"    sys.path.insert(0, str(Path(__file__).parent.parent.parent))"
        )

    # Check order: path setup must come BEFORE node_runtime import
    if node_runtime_line < path_setup_line:
        return False, (
            f"FAIL: Wrong import order!\n"
            f"  node_runtime import at line {node_runtime_line}\n"
            f"  sys.path.insert() at line {path_setup_line}\n"
            f"\n"
            f"  Fix: Move the node_runtime import to AFTER line {path_setup_line}\n"
            f"\n"
            f"  Correct order:\n"
            f"    1. import sys\n"
            f"    2. from pathlib import Path\n"
            f"    3. sys.path.insert(0, ...)\n"
            f"    4. from node_runtime import call_tool  <-- AFTER path setup!"
        )

    # All good!
    return True, f"OK: Import order is correct (path setup at line {path_setup_line}, import at line {node_runtime_line})"


def fix_import_order(filepath: str) -> Tuple[bool, str]:
    """
    Automatically fix node_runtime import order.

    Args:
        filepath: Path to Python file

    Returns:
        (success, message)
    """
    path = Path(filepath)

    if not path.exists():
        return False, f"File not found: {filepath}"

    try:
        content = path.read_text(encoding='utf-8')
        lines = content.split('\n')
    except Exception as e:
        return False, f"Error reading file: {e}"

    # Parse to find line numbers
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    node_runtime_line = find_node_runtime_import(tree)
    path_setup_line = find_path_setup(tree)

    # If no issue, nothing to fix
    if node_runtime_line is None:
        return True, "No fix needed: No node_runtime import"

    if path_setup_line is None:
        return False, "Cannot auto-fix: No sys.path.insert() found"

    if node_runtime_line > path_setup_line:
        return True, "No fix needed: Import order already correct"

    # Fix the order
    # Find the actual import line (AST line numbers are 1-indexed)
    node_runtime_import_line = lines[node_runtime_line - 1]

    # Remove the import from wrong position
    lines.pop(node_runtime_line - 1)

    # Insert it after path setup (adjust index since we removed a line)
    if node_runtime_line < path_setup_line:
        path_setup_line -= 1

    # Insert after path setup line
    lines.insert(path_setup_line, node_runtime_import_line)

    # Write back
    fixed_content = '\n'.join(lines)
    try:
        path.write_text(fixed_content, encoding='utf-8')
        return True, (
            f"FIXED: Moved node_runtime import from line {node_runtime_line} "
            f"to after line {path_setup_line + 1}"
        )
    except Exception as e:
        return False, f"Error writing file: {e}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: node_runtime_import_validator.py <python_file> [--fix]", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    auto_fix = len(sys.argv) > 2 and sys.argv[2] == '--fix'

    if auto_fix:
        is_valid, message = fix_import_order(filepath)
        print(message)
        sys.exit(0 if is_valid else 1)
    else:
        is_valid, message = validate_file(filepath)
        print(message)

        if is_valid:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
