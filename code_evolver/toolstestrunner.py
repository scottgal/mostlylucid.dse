#!/usr/bin/env python3
"""
Standalone Tool Test Runner

A simple, standalone test runner for running individual tool unit tests
without requiring the full DSE system initialization.

Usage:
    # Run a specific test file
    python toolstestrunner.py path/to/test_file.py

    # Run all tests in a directory
    python toolstestrunner.py tests/unit/

    # Run tests for a specific tool by name
    python toolstestrunner.py --tool content_splitter

    # Run with verbose output
    python toolstestrunner.py --tool content_splitter -v

    # Run with coverage
    python toolstestrunner.py --tool content_splitter --coverage

Features:
- Runs tests independently without ToolsManager initialization
- Discovers tests by tool name or path
- Provides clean, formatted output
- Supports pytest arguments pass-through
- Works with existing pytest fixtures and conftest.py
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional
import json


class ToolTestRunner:
    """Standalone test runner for tool unit tests."""

    def __init__(self, verbose: bool = False):
        """
        Initialize test runner.

        Args:
            verbose: Print detailed output
        """
        self.verbose = verbose
        self.test_dirs = [
            Path("tests"),
            Path("tests/unit"),
            Path("tests/integration"),
            Path("tests/bdd"),
            Path("tools/tests")
        ]

    def find_tests_by_tool_name(self, tool_name: str) -> List[Path]:
        """
        Find test files for a specific tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            List of test file paths
        """
        normalized = tool_name.lower().replace(" ", "_").replace("-", "_")

        # Search patterns
        patterns = [
            f"test_{normalized}.py",
            f"test_{normalized}_*.py",
            f"{normalized}_test.py",
            f"{normalized}.test.py"
        ]

        test_files = []

        for test_dir in self.test_dirs:
            if not test_dir.exists():
                continue

            for pattern in patterns:
                matches = list(test_dir.glob(pattern))
                test_files.extend(matches)

        return test_files

    def find_tests_by_path(self, path: str) -> List[Path]:
        """
        Find test files by path (file or directory).

        Args:
            path: Path to test file or directory

        Returns:
            List of test file paths
        """
        path_obj = Path(path)

        if not path_obj.exists():
            return []

        if path_obj.is_file():
            return [path_obj] if path_obj.name.startswith("test_") else []

        # Directory - find all test files
        test_files = list(path_obj.glob("test_*.py"))
        test_files.extend(path_obj.glob("*_test.py"))

        return test_files

    def run_tests(
        self,
        test_files: List[Path],
        pytest_args: Optional[List[str]] = None,
        coverage: bool = False
    ) -> int:
        """
        Run tests using pytest.

        Args:
            test_files: List of test files to run
            pytest_args: Additional pytest arguments
            coverage: Whether to run with coverage

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        if not test_files:
            print("No test files found.")
            return 1

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        # Add test files
        cmd.extend([str(f) for f in test_files])

        # Add default arguments
        if self.verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        cmd.append("--tb=short")

        # Add coverage if requested
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov=tools",
                "--cov-report=term-missing",
                "--cov-report=html"
            ])

        # Add custom pytest arguments
        if pytest_args:
            cmd.extend(pytest_args)

        # Print what we're running
        if self.verbose:
            print(f"\n{'=' * 60}")
            print(f"Running: {' '.join(cmd)}")
            print(f"{'=' * 60}\n")
        else:
            test_names = [f.name for f in test_files]
            print(f"Running {len(test_files)} test file(s): {', '.join(test_names)}")

        # Run pytest
        try:
            result = subprocess.run(cmd, cwd=Path.cwd())
            return result.returncode

        except KeyboardInterrupt:
            print("\n\nTest run interrupted by user.")
            return 130

        except Exception as e:
            print(f"Error running tests: {e}")
            return 1

    def list_tests(self, test_files: List[Path]):
        """
        List available tests without running them.

        Args:
            test_files: List of test files
        """
        if not test_files:
            print("No test files found.")
            return

        print(f"\nFound {len(test_files)} test file(s):\n")

        for test_file in test_files:
            print(f"  - {test_file}")

            # Try to list test functions in file
            if self.verbose:
                try:
                    with open(test_file, 'r') as f:
                        content = f.read()
                        import re
                        test_funcs = re.findall(r'def (test_\w+)\(', content)
                        for func in test_funcs:
                            print(f"      • {func}")
                except Exception:
                    pass

        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Standalone Tool Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run tests for a specific tool
  %(prog)s --tool content_splitter

  # Run a specific test file
  %(prog)s tests/unit/test_content_splitter.py

  # Run all tests in a directory
  %(prog)s tests/unit/

  # Run with verbose output and coverage
  %(prog)s --tool content_splitter -v --coverage

  # List available tests without running
  %(prog)s --tool content_splitter --list

  # Pass additional pytest arguments
  %(prog)s --tool content_splitter -- -k test_basic
        """
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="Path to test file or directory (optional if --tool is used)"
    )

    parser.add_argument(
        "--tool", "-t",
        help="Tool name to test"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage report"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available tests without running them"
    )

    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional arguments to pass to pytest (use -- to separate)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.path and not args.tool:
        parser.print_help()
        print("\nError: Either path or --tool must be specified.")
        return 1

    # Create runner
    runner = ToolTestRunner(verbose=args.verbose)

    # Find test files
    test_files = []

    if args.tool:
        test_files = runner.find_tests_by_tool_name(args.tool)
        if not test_files:
            print(f"No tests found for tool: {args.tool}")
            print("\nSearched in:")
            for test_dir in runner.test_dirs:
                if test_dir.exists():
                    print(f"  - {test_dir}")
            return 1

    elif args.path:
        test_files = runner.find_tests_by_path(args.path)
        if not test_files:
            print(f"No test files found at: {args.path}")
            return 1

    # List or run tests
    if args.list:
        runner.list_tests(test_files)
        return 0

    # Run tests
    return runner.run_tests(
        test_files,
        pytest_args=args.pytest_args,
        coverage=args.coverage
    )


if __name__ == "__main__":
    sys.exit(main())
