#!/usr/bin/env python3
"""
Ruff Checker and Auto-Fixer

Ruff is an extremely fast Python linter and formatter written in Rust.
It can replace flake8, isort, pyupgrade, and more with a single tool.

This tool runs ruff to check code quality and optionally apply fixes.

Usage:
    # Check only
    python ruff_checker.py <file_path>

    # Check and auto-fix
    python ruff_checker.py <file_path> --fix

    # JSON output
    python ruff_checker.py <file_path> --json

Exit codes:
    0 - No issues found (or all fixed)
    1 - Issues found
    2 - Error (file not found, ruff not installed)
"""

import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, Any


def check_ruff_installed() -> bool:
    """Check if ruff is installed."""
    try:
        result = subprocess.run(
            ["ruff", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_ruff() -> bool:
    """Attempt to install ruff via pip."""
    print("Ruff not found. Attempting to install...", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "ruff", "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print("Ruff installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"Failed to install ruff: {result.stderr}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error installing ruff: {e}", file=sys.stderr)
        return False


def run_ruff_check(
    file_path: Path, auto_fix: bool = False, output_format: str = "text"
) -> Dict[str, Any]:
    """
    Run ruff check on a file.

    Args:
        file_path: Path to file to check
        auto_fix: Apply safe fixes automatically
        output_format: 'text', 'json', or 'github'

    Returns:
        Dictionary with results:
        {
            'success': bool,
            'issues_found': int,
            'issues_fixed': int,
            'output': str,
            'issues': List[Dict]  # Only if output_format='json'
        }
    """
    # Build command
    cmd = ["ruff", "check"]

    if auto_fix:
        cmd.append("--fix")

    if output_format == "json":
        cmd.append("--output-format=json")

    cmd.append(str(file_path))

    # Run ruff
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        # Parse results
        if output_format == "json" and output:
            try:
                issues = json.loads(output)
                return {
                    "success": result.returncode == 0,
                    "issues_found": len(issues),
                    "issues_fixed": 0
                    if not auto_fix
                    else len([i for i in issues if i.get("fix")]),
                    "output": output,
                    "issues": issues,
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "issues_found": 0,
                    "issues_fixed": 0,
                    "output": f"Failed to parse JSON output: {output}",
                    "issues": [],
                }
        else:
            # Text output - count lines with issues
            issue_count = len(
                [
                    line
                    for line in output.split("\n")
                    if line.strip() and not line.startswith("Found")
                ]
            )
            return {
                "success": result.returncode == 0,
                "issues_found": issue_count if result.returncode != 0 else 0,
                "issues_fixed": 0,  # Can't determine from text output
                "output": output,
                "issues": [],
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "issues_found": 0,
            "issues_fixed": 0,
            "output": "Ruff check timed out (30s)",
            "issues": [],
        }
    except Exception as e:
        return {
            "success": False,
            "issues_found": 0,
            "issues_fixed": 0,
            "output": f"Error running ruff: {e}",
            "issues": [],
        }


def run_ruff_format(file_path: Path, check_only: bool = False) -> Dict[str, Any]:
    """
    Run ruff format on a file (replaces black).

    Args:
        file_path: Path to file to format
        check_only: Only check if formatting is needed

    Returns:
        Dictionary with results
    """
    cmd = ["ruff", "format"]

    if check_only:
        cmd.append("--check")

    cmd.append(str(file_path))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        return {
            "success": result.returncode == 0,
            "formatted": not check_only and result.returncode == 0,
            "needs_formatting": check_only and result.returncode != 0,
            "output": output,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "formatted": False,
            "needs_formatting": False,
            "output": "Ruff format timed out (30s)",
        }
    except Exception as e:
        return {
            "success": False,
            "formatted": False,
            "needs_formatting": False,
            "output": f"Error running ruff format: {e}",
        }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run ruff linter/formatter on Python code"
    )
    parser.add_argument("file_path", help="Path to Python file")
    parser.add_argument("--fix", action="store_true", help="Apply safe auto-fixes")
    parser.add_argument(
        "--format", action="store_true", help="Also run ruff format (code formatting)"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--install", action="store_true", help="Install ruff if not found"
    )

    args = parser.parse_args()

    # Check file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check ruff is installed
    if not check_ruff_installed():
        if args.install:
            if not install_ruff():
                sys.exit(2)
        else:
            print(
                "Error: ruff is not installed. Run with --install or: pip install ruff",
                file=sys.stderr,
            )
            sys.exit(2)

    # Run ruff check
    check_results = run_ruff_check(
        file_path, auto_fix=args.fix, output_format="json" if args.json else "text"
    )

    # Optionally run ruff format
    format_results = None
    if args.format:
        format_results = run_ruff_format(file_path, check_only=not args.fix)

    # Output results
    if args.json:
        output = {
            "file": str(file_path),
            "check": check_results,
            "format": format_results,
        }
        print(json.dumps(output, indent=2))
    else:
        # Text output
        if check_results["output"]:
            print(check_results["output"])

        if format_results and format_results["output"]:
            print("\nFormat check:")
            print(format_results["output"])

        # Summary
        if check_results["issues_found"] > 0:
            print(
                f"\n[RUFF] Found {check_results['issues_found']} issue(s)",
                file=sys.stderr,
            )
            if args.fix:
                print(
                    f"[RUFF] Fixed {check_results['issues_fixed']} issue(s)",
                    file=sys.stderr,
                )
        else:
            print("\n[RUFF] No issues found")

    # Exit code
    if not check_results["success"]:
        sys.exit(1)
    if format_results and not format_results["success"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
