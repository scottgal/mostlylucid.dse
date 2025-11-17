#!/usr/bin/env python3
"""
Pyupgrade Checker and Auto-Fixer

Pyupgrade automatically upgrades Python syntax for newer versions.
It modernizes code to use newer Python features (f-strings, type hints, etc.)

Usage:
    # Check only (dry-run)
    python pyupgrade_checker.py <file_path>

    # Check and auto-fix (defaults to Python 3.8+)
    python pyupgrade_checker.py <file_path> --fix

    # Target specific Python version
    python pyupgrade_checker.py <file_path> --fix --py39-plus

Exit codes:
    0 - No issues found (or all fixed)
    1 - Issues found
    2 - Error (file not found, pyupgrade not installed)
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


def check_pyupgrade_installed() -> bool:
    """Check if pyupgrade is installed."""
    try:
        result = subprocess.run(
            ['pyupgrade', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_pyupgrade() -> bool:
    """Attempt to install pyupgrade via pip."""
    print("Pyupgrade not found. Attempting to install...", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'pyupgrade', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("Pyupgrade installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"Failed to install pyupgrade: {result.stderr}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error installing pyupgrade: {e}", file=sys.stderr)
        return False


def run_pyupgrade(
    file_path: Path,
    auto_fix: bool = False,
    python_version: str = 'py38-plus',
    keep_runtime_typing: bool = False
) -> Dict[str, Any]:
    """
    Run pyupgrade on a file.

    Args:
        file_path: Path to file to check
        auto_fix: Apply fixes in-place
        python_version: Target Python version (py36-plus, py37-plus, py38-plus, etc.)
        keep_runtime_typing: Keep runtime typing (don't remove quotes from annotations)

    Returns:
        Dictionary with results:
        {
            'success': bool,
            'changes_needed': bool,
            'output': str,
            'original': str,
            'upgraded': str
        }
    """
    # Build command
    cmd = ['pyupgrade', f'--{python_version}']

    if keep_runtime_typing:
        cmd.append('--keep-runtime-typing')

    # Read original file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        return {
            'success': False,
            'changes_needed': False,
            'output': f'Error reading file: {e}',
            'original': '',
            'upgraded': ''
        }

    if auto_fix:
        # Fix in-place
        cmd.append(str(file_path))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Read modified file
            with open(file_path, 'r', encoding='utf-8') as f:
                upgraded_content = f.read()

            changes_needed = original_content != upgraded_content

            return {
                'success': True,
                'changes_needed': changes_needed,
                'output': f'Upgraded to {python_version}' if changes_needed else 'No changes needed',
                'original': original_content,
                'upgraded': upgraded_content
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'changes_needed': False,
                'output': 'Pyupgrade timed out (30s)',
                'original': original_content,
                'upgraded': ''
            }
        except Exception as e:
            return {
                'success': False,
                'changes_needed': False,
                'output': f'Error running pyupgrade: {e}',
                'original': original_content,
                'upgraded': ''
            }
    else:
        # Check mode - pass content via stdin
        cmd.append('-')

        try:
            result = subprocess.run(
                cmd,
                input=original_content,
                capture_output=True,
                text=True,
                timeout=30
            )

            upgraded_content = result.stdout

            changes_needed = original_content != upgraded_content

            return {
                'success': True,
                'changes_needed': changes_needed,
                'output': upgraded_content if changes_needed else 'No changes needed',
                'original': original_content,
                'upgraded': upgraded_content
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'changes_needed': False,
                'output': 'Pyupgrade timed out (30s)',
                'original': original_content,
                'upgraded': ''
            }
        except Exception as e:
            return {
                'success': False,
                'changes_needed': False,
                'output': f'Error running pyupgrade: {e}',
                'original': original_content,
                'upgraded': ''
            }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Modernize Python syntax with pyupgrade'
    )
    parser.add_argument('file_path', help='Path to Python file')
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply fixes in-place'
    )
    parser.add_argument(
        '--py36-plus',
        action='store_const',
        const='py36-plus',
        dest='python_version',
        help='Target Python 3.6+'
    )
    parser.add_argument(
        '--py37-plus',
        action='store_const',
        const='py37-plus',
        dest='python_version',
        help='Target Python 3.7+'
    )
    parser.add_argument(
        '--py38-plus',
        action='store_const',
        const='py38-plus',
        dest='python_version',
        help='Target Python 3.8+ (default)'
    )
    parser.add_argument(
        '--py39-plus',
        action='store_const',
        const='py39-plus',
        dest='python_version',
        help='Target Python 3.9+'
    )
    parser.add_argument(
        '--py310-plus',
        action='store_const',
        const='py310-plus',
        dest='python_version',
        help='Target Python 3.10+'
    )
    parser.add_argument(
        '--py311-plus',
        action='store_const',
        const='py311-plus',
        dest='python_version',
        help='Target Python 3.11+'
    )
    parser.add_argument(
        '--keep-runtime-typing',
        action='store_true',
        help='Keep runtime typing annotations'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install pyupgrade if not found'
    )

    args = parser.parse_args()

    # Default to py38-plus
    if not args.python_version:
        args.python_version = 'py38-plus'

    # Check file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check pyupgrade is installed
    if not check_pyupgrade_installed():
        if args.install:
            if not install_pyupgrade():
                sys.exit(2)
        else:
            print("Error: pyupgrade is not installed. Run with --install or: pip install pyupgrade", file=sys.stderr)
            sys.exit(2)

    # Run pyupgrade
    results = run_pyupgrade(
        file_path,
        auto_fix=args.fix,
        python_version=args.python_version,
        keep_runtime_typing=args.keep_runtime_typing
    )

    # Output results
    if results['changes_needed'] and not args.fix:
        print(results['output'])

    # Summary
    if results['changes_needed']:
        if args.fix:
            print(f"\n[PYUPGRADE] Modernized code to {args.python_version} in {file_path}", file=sys.stderr)
        else:
            print(f"\n[PYUPGRADE] Code can be modernized to {args.python_version} (run with --fix to apply)", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"\n[PYUPGRADE] Code is already modern ({args.python_version})")

    sys.exit(0)


if __name__ == '__main__':
    main()
