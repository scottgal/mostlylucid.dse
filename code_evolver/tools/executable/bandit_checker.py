#!/usr/bin/env python3
"""
Bandit Security Scanner

Bandit is a tool designed to find common security issues in Python code.
It scans for vulnerabilities like SQL injection, hardcoded passwords, etc.

Usage:
    # Scan file or directory
    python bandit_checker.py <file_path>

    # JSON output
    python bandit_checker.py <file_path> --json

    # Set severity level
    python bandit_checker.py <file_path> --level high

Exit codes:
    0 - No security issues found
    1 - Security issues found
    2 - Error (file not found, bandit not installed)
"""

import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional


def check_bandit_installed() -> bool:
    """Check if bandit is installed."""
    try:
        result = subprocess.run(
            ['bandit', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_bandit() -> bool:
    """Attempt to install bandit via pip."""
    print("Bandit not found. Attempting to install...", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'bandit', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("Bandit installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"Failed to install bandit: {result.stderr}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error installing bandit: {e}", file=sys.stderr)
        return False


def run_bandit(
    file_path: Path,
    output_json: bool = False,
    severity_level: Optional[str] = None,
    confidence_level: Optional[str] = None,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Run bandit on a file or directory.

    Args:
        file_path: Path to file or directory to scan
        output_json: Output results as JSON
        severity_level: Filter by severity (low, medium, high)
        confidence_level: Filter by confidence (low, medium, high)
        recursive: Recursively scan directories

    Returns:
        Dictionary with results:
        {
            'success': bool,
            'issues_found': int,
            'high_severity': int,
            'medium_severity': int,
            'low_severity': int,
            'output': str,
            'issues': List[Dict]  # Only if output_json=True
        }
    """
    # Build command
    cmd = ['bandit']

    if output_json:
        cmd.extend(['-f', 'json'])

    if severity_level:
        cmd.extend(['-ll', severity_level.upper()])

    if confidence_level:
        cmd.extend(['-i', confidence_level.upper()])

    if file_path.is_dir() and recursive:
        cmd.append('-r')

    cmd.append(str(file_path))

    # Run bandit
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        # Parse results
        if output_json and output:
            try:
                data = json.loads(output)
                results = data.get('results', [])
                metrics = data.get('metrics', {})

                # Count by severity
                high_count = sum(1 for r in results if r.get('issue_severity') == 'HIGH')
                medium_count = sum(1 for r in results if r.get('issue_severity') == 'MEDIUM')
                low_count = sum(1 for r in results if r.get('issue_severity') == 'LOW')

                return {
                    'success': result.returncode == 0,
                    'issues_found': len(results),
                    'high_severity': high_count,
                    'medium_severity': medium_count,
                    'low_severity': low_count,
                    'output': output,
                    'issues': results,
                    'metrics': metrics
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'issues_found': 0,
                    'high_severity': 0,
                    'medium_severity': 0,
                    'low_severity': 0,
                    'output': f'Failed to parse JSON output: {output}',
                    'issues': []
                }
        else:
            # Parse text output
            issue_count = 0
            if output:
                # Count lines starting with '>>' which indicate issues
                issue_count = len([line for line in output.split('\n') if line.strip().startswith('>>')])

            return {
                'success': result.returncode == 0,
                'issues_found': issue_count,
                'high_severity': 0,
                'medium_severity': 0,
                'low_severity': 0,
                'output': output if output else 'No issues found',
                'issues': []
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'issues_found': 0,
            'high_severity': 0,
            'medium_severity': 0,
            'low_severity': 0,
            'output': 'Bandit timed out (60s)',
            'issues': []
        }
    except Exception as e:
        return {
            'success': False,
            'issues_found': 0,
            'high_severity': 0,
            'medium_severity': 0,
            'low_severity': 0,
            'output': f'Error running bandit: {e}',
            'issues': []
        }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run bandit security scanner on Python code'
    )
    parser.add_argument('file_path', help='Path to Python file or directory')
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--level',
        choices=['low', 'medium', 'high'],
        help='Minimum severity level to report'
    )
    parser.add_argument(
        '--confidence',
        choices=['low', 'medium', 'high'],
        help='Minimum confidence level to report'
    )
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not recursively scan directories'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install bandit if not found'
    )

    args = parser.parse_args()

    # Check file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check bandit is installed
    if not check_bandit_installed():
        if args.install:
            if not install_bandit():
                sys.exit(2)
        else:
            print("Error: bandit is not installed. Run with --install or: pip install bandit", file=sys.stderr)
            sys.exit(2)

    # Run bandit
    results = run_bandit(
        file_path,
        output_json=args.json,
        severity_level=args.level,
        confidence_level=args.confidence,
        recursive=not args.no_recursive
    )

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(results['output'])

        # Summary
        if results['issues_found'] > 0:
            print(f"\n[BANDIT] Found {results['issues_found']} security issue(s)", file=sys.stderr)
            if results.get('high_severity', 0) > 0:
                print(f"  - {results['high_severity']} HIGH severity", file=sys.stderr)
            if results.get('medium_severity', 0) > 0:
                print(f"  - {results['medium_severity']} MEDIUM severity", file=sys.stderr)
            if results.get('low_severity', 0) > 0:
                print(f"  - {results['low_severity']} LOW severity", file=sys.stderr)
        else:
            print("\n[BANDIT] No security issues found")

    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
