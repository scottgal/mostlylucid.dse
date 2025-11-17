#!/usr/bin/env python3
"""
Circular Import Fixer - Auto-Fix Tool for Code Generation Errors

This tool detects and fixes circular import patterns in generated code.
Specifically targets the common error where main.py imports from itself.

USAGE:
    echo '<code>' | python circular_import_fixer.py

INPUT (stdin):
    Python code that may contain circular imports

OUTPUT (stdout):
    {
        "fixed": true/false,
        "original_lines": 150,
        "fixed_lines": 148,
        "removed_imports": ["from main import validate_input_code", ...],
        "fixed_code": "...",
        "message": "Removed 2 circular import statements"
    }

ERROR PATTERNS DETECTED:
    - "from main import ..." in main.py
    - "import main" in main.py (if filename is main.py)

TAGS: fix, circular_import, import_error, code_repair, auto_fix
"""

import sys
import json
import re
from typing import Dict, List, Any


def detect_circular_imports(code: str, filename: str = "main.py") -> List[str]:
    """
    Detect circular import patterns in code.

    Args:
        code: Python code to check
        filename: Name of the file (default: main.py)

    Returns:
        List of problematic import lines
    """
    problematic_imports = []

    # Only check if this is main.py
    if filename.lower() != "main.py":
        return problematic_imports

    lines = code.split('\n')

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Pattern 1: "from main import ..."
        if re.match(r'^\s*from\s+main\s+import\s+', stripped):
            problematic_imports.append({
                "line_num": line_num,
                "line": line,
                "pattern": "from_main_import"
            })

        # Pattern 2: "import main"
        elif re.match(r'^\s*import\s+main\s*($|,|;)', stripped):
            problematic_imports.append({
                "line_num": line_num,
                "line": line,
                "pattern": "import_main"
            })

    return problematic_imports


def fix_circular_imports(code: str, filename: str = "main.py") -> Dict[str, Any]:
    """
    Remove circular import statements from code.

    Args:
        code: Python code to fix
        filename: Name of the file being fixed

    Returns:
        Dict with fix results and cleaned code
    """
    # Detect issues
    problematic = detect_circular_imports(code, filename)

    if not problematic:
        return {
            "fixed": False,
            "original_lines": len(code.split('\n')),
            "fixed_lines": len(code.split('\n')),
            "removed_imports": [],
            "fixed_code": code,
            "message": "No circular imports detected"
        }

    # Fix by removing problematic lines
    lines = code.split('\n')
    removed_imports = []

    for issue in sorted(problematic, key=lambda x: x["line_num"], reverse=True):
        line_idx = issue["line_num"] - 1
        if 0 <= line_idx < len(lines):
            removed_imports.append(lines[line_idx].strip())
            lines.pop(line_idx)

    fixed_code = '\n'.join(lines)

    return {
        "fixed": True,
        "original_lines": len(code.split('\n')),
        "fixed_lines": len(lines),
        "removed_imports": removed_imports,
        "fixed_code": fixed_code,
        "message": f"Removed {len(removed_imports)} circular import statement(s)"
    }


def main():
    """Read code from stdin, fix circular imports, output JSON result."""
    try:
        # Read input code
        code = sys.stdin.read()

        if not code.strip():
            print(json.dumps({
                "error": "No input code provided",
                "fixed": False
            }), file=sys.stdout)
            sys.exit(1)

        # Parse input if it's JSON with code field
        try:
            input_data = json.loads(code)
            if "code" in input_data:
                code = input_data["code"]
                filename = input_data.get("filename", "main.py")
            else:
                filename = "main.py"
        except json.JSONDecodeError:
            # Input is raw code, not JSON
            filename = "main.py"

        # Fix circular imports
        result = fix_circular_imports(code, filename)

        # Output result as JSON
        print(json.dumps(result, indent=2), file=sys.stdout)

        # Exit code: 0 if fixed or no issues, 1 if error
        sys.exit(0)

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "fixed": False,
            "message": f"Fixer tool failed: {e}"
        }), file=sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
