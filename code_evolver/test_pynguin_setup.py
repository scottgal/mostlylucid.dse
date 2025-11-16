"""Test pynguin setup and generate tests for a simple module."""
import os
import sys
import subprocess
from pathlib import Path
import shutil

# Set the required environment variable
os.environ['PYNGUIN_DANGER_AWARE'] = '1'

# Test 1: Check if pynguin is installed
print("=" * 70)
print("TEST 1: Checking pynguin installation...")
print("=" * 70)

try:
    result = subprocess.run(
        [sys.executable, '-m', 'pynguin', '--version'],
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"Pynguin version check: {'SUCCESS' if result.returncode == 0 else 'FAILED'}")
    if result.stdout:
        print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Errors: {result.stderr[:200]}")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

# Test 2: Create a simple test module
print("\n" + "=" * 70)
print("TEST 2: Creating simple test module...")
print("=" * 70)

test_dir = Path(__file__).parent / "test_pynguin_module"
test_dir.mkdir(exist_ok=True)

# Create a simple calculator module
calc_code = '''"""Simple calculator for testing pynguin."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def is_even(n: int) -> bool:
    """Check if number is even."""
    return n % 2 == 0
'''

calc_file = test_dir / "calculator.py"
calc_file.write_text(calc_code, encoding='utf-8')
print(f"Created test module: {calc_file}")

# Test 3: Run pynguin on the test module
print("\n" + "=" * 70)
print("TEST 3: Running pynguin to generate tests...")
print("=" * 70)

tests_dir = test_dir / "tests_pynguin"
tests_dir.mkdir(exist_ok=True)

try:
    pynguin_cmd = [
        sys.executable, '-m', 'pynguin',
        '--project-path', str(test_dir),
        '--module-name', 'calculator',
        '--output-path', str(tests_dir),
        '--maximum-search-time', '30',
        '--assertion-generation', 'MUTATION_ANALYSIS'
        # Removed --test-case-output (not supported in pynguin 0.43.0)
    ]

    print(f"Running: {' '.join(pynguin_cmd)}")
    print("This may take 30-40 seconds...")

    result = subprocess.run(
        pynguin_cmd,
        capture_output=True,
        text=True,
        timeout=45,
        env=os.environ.copy()  # Pass environment with PYNGUIN_DANGER_AWARE
    )

    print(f"\nPynguin exit code: {result.returncode}")

    if result.stdout:
        print(f"\nStdout (last 500 chars):\n{result.stdout[-500:]}")
    if result.stderr:
        print(f"\nStderr (last 500 chars):\n{result.stderr[-500:]}")

    # Check if tests were generated
    test_files = list(tests_dir.glob("test_*.py"))
    if test_files:
        print(f"\n[SUCCESS] Pynguin generated {len(test_files)} test file(s):")
        for test_file in test_files:
            print(f"  - {test_file.name} ({test_file.stat().st_size} bytes)")

            # Show first 30 lines of test
            content = test_file.read_text(encoding='utf-8')
            lines = content.split('\n')[:30]
            print(f"\nFirst 30 lines of {test_file.name}:")
            print("```python")
            for i, line in enumerate(lines, 1):
                print(f"{i:3d}: {line}")
            print("```")

            # Count test functions
            test_count = len([line for line in content.split('\n') if line.strip().startswith('def test_')])
            print(f"\nTotal test functions: {test_count}")

        print("\n" + "=" * 70)
        print("[SUCCESS] Pynguin is working correctly!")
        print("=" * 70)
        print("\nYou can now:")
        print("1. Enable pynguin in config.yaml (already done)")
        print("2. Set PYNGUIN_DANGER_AWARE=1 in your environment (already done)")
        print("3. Restart your terminal for the environment variable to take effect")
        print("4. Create new workflow nodes - pynguin tests will be auto-generated")

    else:
        print(f"\n[FAILED] Pynguin did not generate any test files")
        print("Pynguin may have compatibility issues on this system")

except subprocess.TimeoutExpired:
    print("[FAILED] Pynguin timed out after 45 seconds")
except Exception as e:
    print(f"[FAILED] Error running pynguin: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
print("\n" + "=" * 70)
print("Cleaning up test directory...")
print("=" * 70)
try:
    shutil.rmtree(test_dir, ignore_errors=True)
    print("Cleanup complete")
except Exception as e:
    print(f"Cleanup warning: {e}")
