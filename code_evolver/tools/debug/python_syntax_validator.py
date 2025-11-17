#!/usr/bin/env python3
"""
Python Syntax Validator

Fast syntax check using Python's AST parser.
Catches syntax errors before running expensive LLM tools.

Exit codes:
  0 - Valid syntax
  1 - Syntax error
  2 - Error (file not found, etc.)
"""

import sys
import ast
from pathlib import Path
from typing import Tuple


def validate_syntax(filepath: str) -> Tuple[bool, str]:
    """
    Validate Python file syntax.

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
        ast.parse(content, filename=str(path))
        return True, "OK: Valid Python syntax"
    except SyntaxError as e:
        return False, (
            f"FAIL: Syntax error at line {e.lineno}:\n"
            f"  {e.msg}\n"
            f"  {e.text.strip() if e.text else ''}\n"
            f"  {' ' * (e.offset - 1) if e.offset else ''}^"
        )
    except Exception as e:
        return False, f"Error parsing file: {e}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python_syntax_validator.py <python_file>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    is_valid, message = validate_syntax(filepath)

    print(message)
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
