#!/usr/bin/env python3
"""
Autoflake Checker and Auto-Fixer

Autoflake removes unused imports and unused variables from Python code.
It's deterministic and fast, making it ideal for automated code cleanup.

Usage:
    # Check only (dry-run)
    python autoflake_checker.py <file_path>

    # Check and auto-fix
    python autoflake_checker.py <file_path> --fix

    # Aggressive mode (remove all unused imports)
    python autoflake_checker.py <file_path> --fix --aggressive

Exit codes:
    0 - No issues found (or all fixed)
    1 - Issues found
    2 - Error (file not found, autoflake not installed)
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any


def check_autoflake_installed() -> bool:
    """Check if autoflake is installed."""
    try:
        result = subprocess.run(
            ['autoflake', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_autoflake() -> bool:
    """Attempt to install autoflake via pip."""
    print("Autoflake not found. Attempting to install...", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'autoflake', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("Autoflake installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"Failed to install autoflake: {result.stderr}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error installing autoflake: {e}", file=sys.stderr)
        return False


def run_autoflake(
    file_path: Path,
    auto_fix: bool = False,
    remove_all_unused: bool = False,
    remove_duplicate_keys: bool = True,
    remove_unused_variables: bool = True
) -> Dict[str, Any]:
    """
    Run autoflake on a file.

    Args:
        file_path: Path to file to check
        auto_fix: Apply fixes (--in-place)
        remove_all_unused: Remove all unused imports (not just stdlib)
        remove_duplicate_keys: Remove duplicate dictionary keys
        remove_unused_variables: Remove unused variables

    Returns:
        Dictionary with results:
        {
            'success': bool,
            'changes_needed': bool,
            'output': str,
            'diff': str
        }
    """
    # Build command
    cmd = ['autoflake']

    # Options
    if remove_all_unused:
        cmd.append('--remove-all-unused-imports')
    else:
        cmd.append('--remove-unused-variables') if remove_unused_variables else None

    if remove_duplicate_keys:
        cmd.append('--remove-duplicate-keys')

    # Check or fix mode
    if auto_fix:
        cmd.append('--in-place')
    else:
        # Dry-run mode - shows what would be changed
        pass

    cmd.append(str(file_path))

    # Remove None values
    cmd = [c for c in cmd if c is not None]

    # Run autoflake
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        # In check mode, autoflake outputs the cleaned file to stdout
        # Compare with original to detect changes
        if not auto_fix and output:
            with open(file_path, 'r', encoding='utf-8') as f:
                original = f.read()

            changes_needed = output != original
        else:
            # In fix mode, check if file was modified
            changes_needed = result.returncode == 0 and bool(output)

        return {
            'success': True,
            'changes_needed': changes_needed,
            'output': output if changes_needed else 'No changes needed',
            'diff': output if not auto_fix else ''
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'changes_needed': False,
            'output': 'Autoflake timed out (30s)',
            'diff': ''
        }
    except Exception as e:
        return {
            'success': False,
            'changes_needed': False,
            'output': f'Error running autoflake: {e}',
            'diff': ''
        }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Remove unused imports and variables with autoflake'
    )
    parser.add_argument('file_path', help='Path to Python file')
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply fixes in-place'
    )
    parser.add_argument(
        '--aggressive',
        action='store_true',
        help='Remove all unused imports (not just stdlib)'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install autoflake if not found'
    )

    args = parser.parse_args()

    # Check file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check autoflake is installed
    if not check_autoflake_installed():
        if args.install:
            if not install_autoflake():
                sys.exit(2)
        else:
            print("Error: autoflake is not installed. Run with --install or: pip install autoflake", file=sys.stderr)
            sys.exit(2)

    # Run autoflake
    results = run_autoflake(
        file_path,
        auto_fix=args.fix,
        remove_all_unused=args.aggressive
    )

    # Output results
    if results['output']:
        print(results['output'])

    # Summary
    if results['changes_needed']:
        if args.fix:
            print(f"\n[AUTOFLAKE] Fixed unused imports/variables in {file_path}", file=sys.stderr)
        else:
            print(f"\n[AUTOFLAKE] Found unused imports/variables (run with --fix to apply)", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"\n[AUTOFLAKE] No unused imports/variables found")

    sys.exit(0)


if __name__ == '__main__':
    main()
