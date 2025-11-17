#!/usr/bin/env python3
"""
Static Analysis Runner

Runs static validators on generated code and reports results.
Can run all validators or specific ones.

Usage:
    # Run all validators
    python run_static_analysis.py <code_file>

    # Run specific validator
    python run_static_analysis.py <code_file> --validator syntax

    # Run with auto-fix
    python run_static_analysis.py <code_file> --fix

    # Re-run only failed validators
    python run_static_analysis.py <code_file> --retry-failed

Exit codes:
    0 - All validators passed
    1 - One or more validators failed
    2 - Error (file not found, etc.)
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidatorConfig:
    """Configuration for a single validator."""
    name: str
    script: str
    category: str
    priority: int
    supports_autofix: bool
    description: str


# All available validators (in priority order)
VALIDATORS = [
    ValidatorConfig(
        name="syntax",
        script="python_syntax_validator.py",
        category="syntax",
        priority=200,
        supports_autofix=False,
        description="Validates Python syntax using AST parser"
    ),
    ValidatorConfig(
        name="main_function",
        script="main_function_checker.py",
        category="structure",
        priority=180,
        supports_autofix=False,
        description="Ensures main() function and __main__ block exist"
    ),
    ValidatorConfig(
        name="json_output",
        script="json_output_validator.py",
        category="structure",
        priority=150,
        supports_autofix=False,
        description="Validates JSON output with json.dumps()"
    ),
    ValidatorConfig(
        name="stdin_usage",
        script="stdin_usage_validator.py",
        category="usage",
        priority=140,
        supports_autofix=False,
        description="Checks stdin reading with json.load(sys.stdin)"
    ),
    ValidatorConfig(
        name="undefined_names",
        script="flake8",  # External tool
        category="imports",
        priority=120,
        supports_autofix=False,
        description="Detects undefined variables and missing imports"
    ),
    ValidatorConfig(
        name="import_order",
        script="isort",  # External tool
        category="imports",
        priority=110,
        supports_autofix=True,
        description="Validates and fixes import organization"
    ),
    ValidatorConfig(
        name="node_runtime_import",
        script="node_runtime_import_validator.py",
        category="imports",
        priority=100,
        supports_autofix=True,
        description="Validates node_runtime import order"
    ),
    ValidatorConfig(
        name="call_tool_usage",
        script="call_tool_validator.py",
        category="usage",
        priority=90,
        supports_autofix=False,
        description="Validates call_tool() usage"
    ),
]


class StaticAnalysisRunner:
    """Runs static analysis validators on code files."""

    def __init__(self, tools_dir: str = None):
        """
        Initialize runner.

        Args:
            tools_dir: Directory containing validator scripts
        """
        if tools_dir is None:
            # Auto-detect tools directory
            script_dir = Path(__file__).parent
            self.tools_dir = script_dir
        else:
            self.tools_dir = Path(tools_dir)

    def run_validator(
        self,
        validator: ValidatorConfig,
        code_file: str,
        auto_fix: bool = False
    ) -> Tuple[bool, str, float]:
        """
        Run a single validator.

        Args:
            validator: Validator configuration
            code_file: Path to code file
            auto_fix: Apply auto-fix if available

        Returns:
            (passed, output, execution_time_ms)
        """
        # Build command
        if validator.script.endswith('.py'):
            cmd = ['python', str(self.tools_dir / validator.script), code_file]
            if auto_fix and validator.supports_autofix:
                cmd.append('--fix')
        elif validator.script == 'flake8':
            cmd = ['flake8', '--select=F821,F401,F811,E999', '--format=pylint', code_file]
        elif validator.script == 'isort':
            if auto_fix:
                cmd = ['isort', code_file]
            else:
                cmd = ['isort', '--check-only', '--diff', code_file]
        else:
            return False, f"Unknown validator script: {validator.script}", 0

        # Run validator
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            execution_time = (time.time() - start_time) * 1000

            passed = result.returncode == 0
            output = result.stdout.strip() if result.stdout else result.stderr.strip()

            return passed, output, execution_time

        except subprocess.TimeoutExpired:
            execution_time = 30000
            return False, "Validator timed out (30s)", execution_time
        except FileNotFoundError:
            return False, f"Validator not found: {validator.script}", 0
        except Exception as e:
            return False, f"Error running validator: {e}", 0

    def run_all_validators(
        self,
        code_file: str,
        auto_fix: bool = False,
        validators_to_run: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """
        Run all (or specified) validators.

        Args:
            code_file: Path to code file
            auto_fix: Apply auto-fixes where available
            validators_to_run: Optional list of validator names to run

        Returns:
            Dict mapping validator name to results
        """
        # Sort validators by priority
        sorted_validators = sorted(VALIDATORS, key=lambda v: v.priority, reverse=True)

        # Filter if specific validators requested
        if validators_to_run:
            sorted_validators = [
                v for v in sorted_validators
                if v.name in validators_to_run
            ]

        results = {}
        total_time = 0

        for validator in sorted_validators:
            passed, output, exec_time = self.run_validator(validator, code_file, auto_fix)
            total_time += exec_time

            results[validator.name] = {
                'validator': validator.name,
                'category': validator.category,
                'priority': validator.priority,
                'passed': passed,
                'output': output,
                'execution_time_ms': exec_time,
                'supports_autofix': validator.supports_autofix,
                'description': validator.description
            }

        results['_summary'] = {
            'total_validators': len(results) - 1,  # -1 for _summary itself
            'passed': sum(1 for r in results.values() if isinstance(r, dict) and r.get('passed')),
            'failed': sum(1 for r in results.values() if isinstance(r, dict) and not r.get('passed')),
            'total_time_ms': total_time
        }

        return results

    def print_results(self, results: Dict, verbose: bool = True):
        """
        Print validation results in a nice format.

        Args:
            results: Results from run_all_validators()
            verbose: Show detailed output
        """
        summary = results.get('_summary', {})

        print("\n" + "="*70)
        print("STATIC ANALYSIS RESULTS")
        print("="*70)

        # Print summary
        total = summary.get('total_validators', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        total_time = summary.get('total_time_ms', 0)

        print(f"\nSummary: {passed}/{total} validators passed ({failed} failed)")
        print(f"Total time: {total_time:.0f}ms")

        # Print individual results
        print("\nValidator Results:")
        print("-" * 70)

        for name, result in results.items():
            if name == '_summary':
                continue

            status = "[PASS]" if result['passed'] else "[FAIL]"
            exec_time = result['execution_time_ms']

            print(f"\n[{status}] {result['validator'].upper()} ({exec_time:.0f}ms)")
            print(f"    Category: {result['category']}")

            if verbose or not result['passed']:
                output = result['output']
                if output:
                    # Indent output
                    for line in output.split('\n'):
                        print(f"    {line}")

        print("\n" + "="*70)

        # Overall result
        if failed == 0:
            print("[OK] ALL VALIDATORS PASSED")
        else:
            print(f"[ERROR] {failed} VALIDATOR(S) FAILED")

        print("="*70 + "\n")

    def get_failed_validators(self, results: Dict) -> List[str]:
        """Get list of failed validator names."""
        return [
            name for name, result in results.items()
            if name != '_summary' and not result['passed']
        ]


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Run static analysis validators on generated code'
    )
    parser.add_argument('code_file', help='Path to Python code file')
    parser.add_argument(
        '--validator',
        help='Run specific validator (syntax, main_function, etc.)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply auto-fixes where available'
    )
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Re-run only previously failed validators (requires .analysis_results.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Check if code file exists
    code_file = Path(args.code_file)
    if not code_file.exists():
        print(f"Error: File not found: {code_file}", file=sys.stderr)
        sys.exit(2)

    runner = StaticAnalysisRunner()

    # Determine which validators to run
    validators_to_run = None

    if args.retry_failed:
        # Load previous results
        results_file = code_file.parent / '.analysis_results.json'
        if results_file.exists():
            with open(results_file, 'r') as f:
                prev_results = json.load(f)
            validators_to_run = runner.get_failed_validators(prev_results)
            if not validators_to_run:
                print("No failed validators to retry. All validators passed previously.")
                sys.exit(0)
            print(f"Re-running {len(validators_to_run)} failed validator(s): {', '.join(validators_to_run)}")
        else:
            print("No previous results found. Run without --retry-failed first.", file=sys.stderr)
            sys.exit(2)

    elif args.validator:
        validators_to_run = [args.validator]

    # Run validators
    results = runner.run_all_validators(
        str(code_file),
        auto_fix=args.fix,
        validators_to_run=validators_to_run
    )

    # Save results for --retry-failed
    results_file = code_file.parent / '.analysis_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        runner.print_results(results, verbose=args.verbose)

    # Exit code
    summary = results['_summary']
    if summary['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
