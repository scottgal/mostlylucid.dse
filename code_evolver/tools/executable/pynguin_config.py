#!/usr/bin/env python3
"""
Pynguin Test Generator Configuration for Windows

Configures and runs pynguin for automatic unit test generation on Windows.
Pynguin is a tool that automatically generates unit tests using AI and evolutionary algorithms.

Usage:
    # Generate tests for a module
    python pynguin_config.py <module_path>

    # Specify output directory
    python pynguin_config.py <module_path> --output tests/

    # Set timeout
    python pynguin_config.py <module_path> --timeout 60

Exit codes:
    0 - Tests generated successfully
    1 - Generation failed
    2 - Invalid arguments or pynguin not installed
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import platform


def check_pynguin_installed() -> bool:
    """Check if pynguin is installed."""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pynguin', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_pynguin() -> bool:
    """
    Attempt to install pynguin via pip.

    Note: Pynguin has specific requirements and may not work on all systems.
    """
    print("Pynguin not found. Attempting to install...", file=sys.stderr)

    # Check Python version (pynguin requires 3.9+)
    if sys.version_info < (3, 9):
        print("Error: Pynguin requires Python 3.9+", file=sys.stderr)
        return False

    try:
        # Install pynguin with dependencies
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'pynguin', '--quiet'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print("Pynguin installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"Failed to install pynguin: {result.stderr}", file=sys.stderr)
            return False
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Error installing pynguin: {e}", file=sys.stderr)
        return False


def run_pynguin(
    module_path: Path,
    output_dir: Optional[Path] = None,
    timeout_seconds: int = 60,
    algorithm: str = 'DYNAMOSA',
    seed: Optional[int] = None,
    max_iterations: int = 100
) -> Dict[str, Any]:
    """
    Run pynguin to generate tests for a module.

    Args:
        module_path: Path to Python module to test
        output_dir: Output directory for generated tests
        timeout_seconds: Timeout in seconds
        algorithm: Test generation algorithm (DYNAMOSA, MOSA, MIO, etc.)
        seed: Random seed for reproducibility
        max_iterations: Maximum number of iterations

    Returns:
        Dictionary with results:
        {
            'success': bool,
            'tests_generated': int,
            'output_dir': str,
            'output': str
        }
    """
    # Set default output directory
    if output_dir is None:
        output_dir = module_path.parent / 'pynguin_tests'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert module path to module name
    module_name = module_path.stem  # e.g., 'ruff_checker' from 'ruff_checker.py'

    # Build command
    cmd = [
        sys.executable, '-m', 'pynguin',
        '--project-path', str(module_path.parent),
        '--output-path', str(output_dir),
        '--module-name', module_name,
        '--algorithm', algorithm,
        '--budget', str(timeout_seconds),
        '--maximum-test-number', str(max_iterations)
    ]

    if seed is not None:
        cmd.extend(['--seed', str(seed)])

    # Windows-specific: Set environment variables
    env = os.environ.copy()
    if platform.system() == 'Windows':
        # Disable ANSI colors on Windows CMD
        env['NO_COLOR'] = '1'
        # Increase recursion limit for complex modules
        env['PYTHONRECURSIONLIMIT'] = '3000'

    # Run pynguin
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 30,  # Add buffer to pynguin timeout
            env=env
        )

        output = result.stdout.strip() if result.stdout else result.stderr.strip()

        # Count generated test files
        test_files = list(output_dir.glob('test_*.py'))
        tests_generated = len(test_files)

        return {
            'success': result.returncode == 0,
            'tests_generated': tests_generated,
            'output_dir': str(output_dir),
            'output': output,
            'test_files': [str(f) for f in test_files]
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'tests_generated': 0,
            'output_dir': str(output_dir),
            'output': f'Pynguin timed out ({timeout_seconds}s)',
            'test_files': []
        }
    except Exception as e:
        return {
            'success': False,
            'tests_generated': 0,
            'output_dir': str(output_dir),
            'output': f'Error running pynguin: {e}',
            'test_files': []
        }


def save_generated_tests_with_module(module_path: Path, test_dir: Path) -> bool:
    """
    Copy generated tests to the same directory as the module.

    Args:
        module_path: Path to original module
        test_dir: Directory with generated tests

    Returns:
        True if tests were copied successfully
    """
    try:
        import shutil

        # Find generated test files
        test_files = list(test_dir.glob('test_*.py'))

        if not test_files:
            print("No test files generated", file=sys.stderr)
            return False

        # Copy each test file to module directory
        module_dir = module_path.parent
        for test_file in test_files:
            dest = module_dir / test_file.name
            shutil.copy2(test_file, dest)
            print(f"Copied {test_file.name} to {module_dir}")

        return True

    except Exception as e:
        print(f"Error copying tests: {e}", file=sys.stderr)
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate unit tests with pynguin (Windows-compatible)'
    )
    parser.add_argument('module_path', help='Path to Python module')
    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory for generated tests'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='Timeout in seconds (default: 60)'
    )
    parser.add_argument(
        '--algorithm',
        choices=['DYNAMOSA', 'MOSA', 'MIO', 'RANDOM', 'WHOLE_SUITE'],
        default='DYNAMOSA',
        help='Test generation algorithm (default: DYNAMOSA)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=100,
        help='Maximum number of test iterations (default: 100)'
    )
    parser.add_argument(
        '--save-with-module',
        action='store_true',
        help='Save generated tests in the same directory as the module'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install pynguin if not found'
    )

    args = parser.parse_args()

    # Check module exists
    module_path = Path(args.module_path)
    if not module_path.exists():
        print(f"Error: Module not found: {module_path}", file=sys.stderr)
        sys.exit(2)

    # Check Python version
    if sys.version_info < (3, 9):
        print("Error: Pynguin requires Python 3.9+", file=sys.stderr)
        print(f"Current version: {sys.version_info.major}.{sys.version_info.minor}", file=sys.stderr)
        sys.exit(2)

    # Check pynguin is installed
    if not check_pynguin_installed():
        if args.install:
            if not install_pynguin():
                sys.exit(2)
        else:
            print("Error: pynguin is not installed.", file=sys.stderr)
            print("Install with: pip install pynguin", file=sys.stderr)
            print("Or run with --install flag", file=sys.stderr)
            print("\nNote: Pynguin requires Python 3.9+ and may not work on all systems.", file=sys.stderr)
            sys.exit(2)

    print(f"Generating tests for {module_path}...")
    print(f"Algorithm: {args.algorithm}")
    print(f"Timeout: {args.timeout}s")
    print(f"Platform: {platform.system()}")

    # Run pynguin
    results = run_pynguin(
        module_path,
        output_dir=args.output,
        timeout_seconds=args.timeout,
        algorithm=args.algorithm,
        seed=args.seed,
        max_iterations=args.max_iterations
    )

    # Output results
    print(f"\n{results['output']}")

    # Summary
    if results['tests_generated'] > 0:
        print(f"\n✓ Generated {results['tests_generated']} test file(s)")
        print(f"  Output directory: {results['output_dir']}")

        for test_file in results['test_files']:
            print(f"  - {test_file}")

        # Optionally save tests with module
        if args.save_with_module:
            print("\nCopying tests to module directory...")
            if save_generated_tests_with_module(module_path, Path(results['output_dir'])):
                print("✓ Tests copied successfully")

    else:
        print("\n✗ No tests generated", file=sys.stderr)
        if platform.system() == 'Windows':
            print("\nNote: Pynguin may have compatibility issues on Windows.", file=sys.stderr)
            print("Consider using alternative test generation methods.", file=sys.stderr)

    # Exit code
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
