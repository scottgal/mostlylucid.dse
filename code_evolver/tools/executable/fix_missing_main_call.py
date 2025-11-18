#!/usr/bin/env python3
"""
Fix Missing main() Call
Detects when code has a main() function but doesn't call it.
"""
import json
import sys
import re


def has_main_function(code: str) -> bool:
    """Check if code has a main() function definition."""
    # Look for 'def main(' or 'def main (' or 'def main():'
    pattern = r'^\s*def\s+main\s*\('
    return bool(re.search(pattern, code, re.MULTILINE))


def has_main_call(code: str) -> bool:
    """Check if code already calls main()."""
    # Look for common patterns of calling main()
    patterns = [
        r'if\s+__name__\s*==\s*[\'"]__main__[\'"].*main\(\)',  # if __name__ == '__main__': main()
        r'main\(\)\s*$',  # Direct call at end (less common but valid)
    ]

    for pattern in patterns:
        if re.search(pattern, code, re.DOTALL):
            return True
    return False


def fix_missing_main_call(code: str) -> tuple[str, str, str]:
    """
    Add 'if __name__ == "__main__": main()' to code if missing.

    Returns:
        (fixed_code, explanation, location)
    """
    # Check if main() function exists
    if not has_main_function(code):
        return code, "No main() function found - no fix needed", "N/A"

    # Check if main() is already being called
    if has_main_call(code):
        return code, "Code already calls main() - no fix needed", "N/A"

    # Add the main() call at the end of the file
    # Ensure proper spacing
    fixed_code = code.rstrip() + '\n\nif __name__ == \'__main__\':\n    main()\n'

    explanation = "Added 'if __name__ == '__main__': main()' to execute main() function"
    location = "end of file"

    return fixed_code, explanation, location


def main():
    """Main entry point."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        source_code = input_data.get('source_code', '')
        apply_fix = input_data.get('apply_fix', True)

        if not source_code:
            print(json.dumps({
                "success": False,
                "fixed": False,
                "message": "No source code provided",
                "can_retry": False
            }))
            return

        # Check state
        has_main = has_main_function(source_code)
        has_call = has_main_call(source_code)

        # Apply fix if requested
        if apply_fix:
            fixed_code, explanation, location = fix_missing_main_call(source_code)
            fixed = (fixed_code != source_code)
        else:
            fixed_code = source_code
            fixed = False
            explanation = "Fix not applied (apply_fix=false)"
            location = "N/A"

        # Determine message
        if not has_main:
            message = "No main() function found - no fix needed"
        elif has_call:
            message = "Code already calls main() - no fix needed"
        elif fixed:
            message = "Added missing main() call"
        else:
            message = "Fix available but not applied"

        # Return result
        result = {
            "success": True,
            "fixed": fixed,
            "message": message,
            "fixed_code": fixed_code if apply_fix else None,
            "explanation": explanation,
            "has_main_function": has_main,
            "has_main_call": has_call,
            "can_retry": fixed,  # Retry if we fixed something
            "location": location if fixed else None
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "fixed": False,
            "message": f"Error: {str(e)}",
            "can_retry": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
