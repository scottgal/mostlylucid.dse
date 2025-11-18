#!/usr/bin/env python3
"""
Fix Tool: ModuleNotFoundError Fixer

Fixes ModuleNotFoundError by adding sys.path setup before imports.
Includes built-in validation to ensure the fix was actually applied.
"""

import sys
import json
import re
from typing import Dict, Any


def fix(code: str, filename: str, error_message: str) -> Dict[str, Any]:
    """
    Fix ModuleNotFoundError by adding path setup.

    Args:
        code: The failing code
        filename: Name of the file
        error_message: The error message

    Returns:
        {
            "fixed": bool,
            "fixed_code": str (if successful),
            "message": str,
            "changes_made": List[str]
        }
    """
    # Extract module name from error
    module_match = re.search(r"No module named '(\w+)'", error_message)
    if not module_match:
        return {
            "fixed": False,
            "message": "Could not parse module name from error"
        }

    module_name = module_match.group(1)

    # Check if code actually uses this module
    uses_module = (
        f"from {module_name} import" in code or
        f"import {module_name}" in code
    )

    if not uses_module:
        # Module isn't used - just remove the import
        lines = code.split('\n')
        cleaned_lines = [
            line for line in lines
            if f"from {module_name}" not in line and f"import {module_name}" not in line
        ]

        return {
            "fixed": True,
            "fixed_code": '\n'.join(cleaned_lines),
            "message": f"Removed unused import of {module_name}",
            "changes_made": [f"Removed unused import: {module_name}"]
        }

    # Module IS used - add path setup
    # Find where the import is
    import_line_idx = None
    lines = code.split('\n')

    for i, line in enumerate(lines):
        if f"from {module_name} import" in line or f"import {module_name}" in line:
            import_line_idx = i
            break

    if import_line_idx is None:
        return {
            "fixed": False,
            "message": f"Could not find import statement for {module_name}"
        }

    # Check if path setup already exists
    if 'sys.path.insert' in code or 'sys.path.append' in code:
        return {
            "fixed": False,
            "message": "Path setup already exists in code"
        }

    # Build path setup code that dynamically finds code_evolver directory
    path_setup = [
        "from pathlib import Path",
        "import sys",
        "# Add code_evolver directory to path",
        "current = Path(__file__).resolve()",
        "while current.name != 'code_evolver' and current.parent != current:",
        "    current = current.parent",
        "if current.name == 'code_evolver':",
        "    sys.path.insert(0, str(current))"
    ]

    # Insert path setup BEFORE the import
    # Find the first non-comment, non-empty line before the import
    insert_idx = import_line_idx
    for i in range(import_line_idx - 1, -1, -1):
        line = lines[i].strip()
        if line and not line.startswith('#'):
            insert_idx = i + 1
            break
    else:
        insert_idx = 0

    # Insert the path setup
    new_lines = lines[:insert_idx] + path_setup + lines[insert_idx:]

    fixed_code = '\n'.join(new_lines)

    return {
        "fixed": True,
        "fixed_code": fixed_code,
        "message": f"Added dynamic path setup for {module_name} import",
        "changes_made": [
            "Added: from pathlib import Path",
            "Added: import sys",
            "Added: # Add code_evolver directory to path",
            "Added: current = Path(__file__).resolve()",
            "Added: while current.name != 'code_evolver' and current.parent != current:",
            "Added:     current = current.parent",
            "Added: if current.name == 'code_evolver':",
            "Added:     sys.path.insert(0, str(current))"
        ]
    }


def validate(original_code: str, fixed_code: str, fix_result: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """
    Validate that the fix was actually applied to the code.

    Args:
        original_code: Code before fix
        fixed_code: Code after fix
        fix_result: Result from fix() function
        error_message: The original error

    Returns:
        {
            "valid": bool,
            "confidence": float (0-1),
            "reason": str
        }
    """
    if not fix_result.get("fixed"):
        # Fix wasn't claimed to work, so validation passes (nothing to validate)
        return {"valid": True, "confidence": 1.0, "reason": "No fix was applied"}

    changes_made = fix_result.get("changes_made", [])

    # Validate each claimed change is actually in the fixed code
    for change in changes_made:
        if "Added: " in change:
            # Extract what was supposedly added
            added_text = change.replace("Added: ", "").strip()

            # Check if it's in the fixed code
            if added_text not in fixed_code:
                return {
                    "valid": False,
                    "confidence": 0.95,
                    "reason": f"Claimed to add '{added_text}' but it's not in fixed_code"
                }

            # Also verify it wasn't already in original code (must be NEW)
            if added_text in original_code:
                return {
                    "valid": False,
                    "confidence": 0.9,
                    "reason": f"Claimed to add '{added_text}' but it was already in original code"
                }

        elif "Removed: " in change or "Removed unused import:" in change:
            # Extract what was supposedly removed
            removed_text = change.replace("Removed: ", "").replace("Removed unused import: ", "").strip()

            # Check if it's gone from the fixed code
            if removed_text in fixed_code:
                return {
                    "valid": False,
                    "confidence": 0.95,
                    "reason": f"Claimed to remove '{removed_text}' but it's still in fixed_code"
                }

            # Verify it was in the original code
            if removed_text not in original_code:
                return {
                    "valid": False,
                    "confidence": 0.8,
                    "reason": f"Claimed to remove '{removed_text}' but it wasn't in original code"
                }

    # Verify code actually changed
    if original_code.strip() == fixed_code.strip():
        return {
            "valid": False,
            "confidence": 0.99,
            "reason": "Claimed to fix code but fixed_code is identical to original_code"
        }

    # All validations passed!
    return {
        "valid": True,
        "confidence": 0.95,
        "reason": f"All {len(changes_made)} changes validated in code"
    }


# Main entry point
if __name__ == "__main__":
    input_data = json.loads(sys.stdin.read())

    command = input_data.get("command", "fix")  # Default to fix
    code = input_data.get("code", "")
    filename = input_data.get("filename", "main.py")
    error_message = input_data.get("error_message", "")

    if command == "fix":
        # Apply the fix
        result = fix(code, filename, error_message)
        print(json.dumps(result))

    elif command == "validate":
        # Validate the fix
        original_code = input_data.get("original_code", "")
        fixed_code = input_data.get("fixed_code", "")
        fix_result = input_data.get("fix_result", {})

        result = validate(original_code, fixed_code, fix_result, error_message)
        print(json.dumps(result))

    else:
        print(json.dumps({
            "error": f"Unknown command: {command}. Use 'fix' or 'validate'"
        }))
