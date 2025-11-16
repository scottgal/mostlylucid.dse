#!/usr/bin/env python3
"""
Test runner for scheduler system.

Runs all scheduler tests and provides a comprehensive report.
"""

import sys
import os
import unittest
import time
from io import StringIO

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(__file__))


def run_test_suite(test_file, description):
    """Run a single test suite and return results."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"File: {test_file}")
    print(f"{'='*70}\n")

    # Import the test module
    module_name = test_file.replace('.py', '').replace('/', '.')
    if module_name.startswith('tests.'):
        module_name = module_name[6:]  # Remove 'tests.' prefix

    try:
        # Dynamic import
        module = __import__(f'tests.{module_name}', fromlist=[''])

        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)

        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return result

    except Exception as e:
        print(f"\n❌ Failed to run {test_file}: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_summary(results):
    """Print a summary of all test results."""
    print(f"\n\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    for description, result in results:
        if result is None:
            print(f"❌ {description}: FAILED TO RUN")
            continue

        tests_run = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0

        total_tests += tests_run
        total_failures += failures
        total_errors += errors
        total_skipped += skipped

        status = "✅ PASSED" if (failures == 0 and errors == 0) else "❌ FAILED"

        print(f"{status} {description}")
        print(f"    Tests run: {tests_run}")
        if failures > 0:
            print(f"    Failures: {failures}")
        if errors > 0:
            print(f"    Errors: {errors}")
        if skipped > 0:
            print(f"    Skipped: {skipped}")

    print(f"\n{'='*70}")
    print(f"OVERALL RESULTS")
    print(f"{'='*70}")
    print(f"Total tests run: {total_tests}")
    print(f"Total failures: {total_failures}")
    print(f"Total errors: {total_errors}")
    print(f"Total skipped: {total_skipped}")

    all_passed = (total_failures == 0 and total_errors == 0)
    if all_passed:
        print(f"\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ SOME TESTS FAILED")

    return all_passed


def main():
    """Main test runner."""
    print("="*70)
    print("SCHEDULER SYSTEM TEST SUITE")
    print("="*70)

    start_time = time.time()

    # Define test suites
    test_suites = [
        ('tests/test_scheduler_db_unit.py', 'Database Unit Tests'),
        ('tests/test_scheduler_service_unit.py', 'Scheduler Service Unit Tests'),
        ('tests/test_scheduler_integration.py', 'Integration Tests'),
    ]

    results = []

    # Run each test suite
    for test_file, description in test_suites:
        result = run_test_suite(test_file, description)
        results.append((description, result))

    # Print summary
    all_passed = print_summary(results)

    duration = time.time() - start_time
    print(f"\nTotal time: {duration:.2f} seconds")

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
