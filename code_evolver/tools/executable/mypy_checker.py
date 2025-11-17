#!/usr/bin/env python3
"""
MyPy Type Checker

MyPy is a static type checker for Python that finds type errors before runtime.
Provides comprehensive type checking with detailed error messages and suggestions.

Usage:
    # Check with strict mode
    python mypy_checker.py <file_path>

    # Check with specific flags
    python mypy_checker.py <file_path> --no-strict

    # JSON output
    python mypy_checker.py <file_path> --json

Exit codes:
    0 - No type errors found
    1 - Type errors found
    2 - Error (file not found, mypy not installed)
"""

import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional


def check_mypy_installed() -> bool:
    """Check if mypy is installed."""
    try:
        result = subprocess.run(
            ['mypy', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_mypy() -> bool:
    """Attempt to install mypy via pip."""
    print("MyPy not found. Attempting to install...", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'mypy', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("MyPy installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"Failed to install mypy: {result.stderr}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error installing mypy: {e}", file=sys.stderr)
        return False


def run_mypy(
    file_path: Path,
    strict: bool = True,
    show_error_codes: bool = True,
    output_json: bool = False,
    ignore_missing_imports: bool = False,
    check_untyped_defs: bool = True
) -> Dict[str, Any]:
    """
    Run mypy on a file.

    Args:
        file_path: Path to file to check
        strict: Enable strict mode (all strictness flags)
        show_error_codes: Show error codes in output
        output_json: Output results as JSON
        ignore_missing_imports: Ignore missing imports
        check_untyped_defs: Check untyped function definitions

    Returns:
        Dictionary with results:
        {
            'success': bool,
            'errors_found': int,
            'output': str,
            'errors': List[Dict]  # Only if output_json=True
        }
    """
    # Build command
    cmd = ['mypy']

    if strict:
        cmd.append('--strict')
    else:
        if check_untyped_defs:
            cmd.append('--check-untyped-defs')

    if show_error_codes:
        cmd.append('--show-error-codes')

    if ignore_missing_imports:
        cmd.append('--ignore-missing-imports')

    if output_json:
        # MyPy doesn't have native JSON output, but we can parse the text output
        cmd.append('--show-column-numbers')

    cmd.append(str(file_path))

    # Run mypy
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        # Parse output
        errors = []
        if output:
            for line in output.split('\n'):
                if line.strip() and ':' in line:
                    # Parse mypy output format: file.py:line:col: error: message [code]
                    parts = line.split(':', 4)
                    if len(parts) >= 4:
                        error_obj = {
                            'file': parts[0].strip(),
                            'line': parts[1].strip() if parts[1].strip().isdigit() else None,
                            'column': parts[2].strip() if len(parts) > 2 and parts[2].strip().isdigit() else None,
                            'level': parts[3].strip() if len(parts) > 3 else 'error',
                            'message': parts[4].strip() if len(parts) > 4 else line
                        }
                        errors.append(error_obj)

        error_count = len(errors)

        return {
            'success': result.returncode == 0,
            'errors_found': error_count,
            'output': output if output else 'Success: no issues found',
            'errors': errors
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'errors_found': 0,
            'output': 'MyPy timed out (60s)',
            'errors': []
        }
    except Exception as e:
        return {
            'success': False,
            'errors_found': 0,
            'output': f'Error running mypy: {e}',
            'errors': []
        }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run mypy type checker on Python code'
    )
    parser.add_argument('file_path', help='Path to Python file')
    parser.add_argument(
        '--no-strict',
        action='store_true',
        help='Disable strict mode'
    )
    parser.add_argument(
        '--ignore-missing-imports',
        action='store_true',
        help='Ignore missing imports'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install mypy if not found'
    )

    args = parser.parse_args()

    # Check file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check mypy is installed
    if not check_mypy_installed():
        if args.install:
            if not install_mypy():
                sys.exit(2)
        else:
            print("Error: mypy is not installed. Run with --install or: pip install mypy", file=sys.stderr)
            sys.exit(2)

    # Run mypy
    results = run_mypy(
        file_path,
        strict=not args.no_strict,
        output_json=args.json,
        ignore_missing_imports=args.ignore_missing_imports
    )

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(results['output'])

        # Summary
        if results['errors_found'] > 0:
            print(f"\n[MYPY] Found {results['errors_found']} type error(s)", file=sys.stderr)
        else:
            print("\n[MYPY] Success: no issues found")

    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
