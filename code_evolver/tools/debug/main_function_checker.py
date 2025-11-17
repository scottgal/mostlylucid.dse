#!/usr/bin/env python3
"""
Main Function Checker

Validates that node code has a proper main() function and __main__ block.

Exit codes:
  0 - Valid main() function
  1 - Missing or invalid main()
  2 - Error
"""

import sys
import ast
from pathlib import Path
from typing import Tuple, Optional


def find_main_function(tree: ast.AST) -> Optional[ast.FunctionDef]:
    """Find the main() function definition."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'main':
            return node
    return None


def has_main_block(tree: ast.AST) -> bool:
    """Check for if __name__ == '__main__': block."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check if it's the __name__ == '__main__' pattern
            if isinstance(node.test, ast.Compare):
                if (isinstance(node.test.left, ast.Name) and
                    node.test.left.id == '__name__'):
                    for comparator in node.test.comparators:
                        if isinstance(comparator, ast.Constant):
                            if comparator.value == '__main__':
                                return True
    return False


def check_main_calls_in_block(tree: ast.AST) -> bool:
    """Check if main() is called in __main__ block."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Found __name__ == '__main__' check
            if isinstance(node.test, ast.Compare):
                if (isinstance(node.test.left, ast.Name) and
                    node.test.left.id == '__name__'):
                    # Check if main() is called in the body
                    for stmt in node.body:
                        if isinstance(stmt, ast.Expr):
                            if (isinstance(stmt.value, ast.Call) and
                                isinstance(stmt.value.func, ast.Name) and
                                stmt.value.func.id == 'main'):
                                return True
    return False


def validate_main_function(filepath: str) -> Tuple[bool, str]:
    """
    Validate that a node has proper main() function.

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

    # Check for main() function
    main_func = find_main_function(tree)
    if not main_func:
        return False, (
            "FAIL: No main() function found\n"
            "  Node code should have:\n"
            "    def main():\n"
            "        # Your code here\n"
            "        pass"
        )

    # Check for __main__ block
    has_block = has_main_block(tree)
    if not has_block:
        return False, (
            f"FAIL: main() function exists but no __main__ block\n"
            f"  Add this at the end:\n"
            f"    if __name__ == '__main__':\n"
            f"        main()"
        )

    # Check if main() is called in __main__ block
    calls_main = check_main_calls_in_block(tree)
    if not calls_main:
        return False, (
            "FAIL: __main__ block exists but doesn't call main()\n"
            "  Fix:\n"
            "    if __name__ == '__main__':\n"
            "        main()  # <-- Add this call"
        )

    # All checks passed
    return True, (
        f"OK: main() function found at line {main_func.lineno} "
        f"and properly called in __main__ block"
    )


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: main_function_checker.py <python_file>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    is_valid, message = validate_main_function(filepath)

    print(message)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
