#!/usr/bin/env python3
"""Test the circular import fixer tool."""

import json
import subprocess
import sys

def test_circular_import_detection():
    """Test that circular imports are detected and fixed."""

    # Test case 1: Code with circular import
    test_code_with_circular = """from main import validate_input_code

def validate_input_code(data):
    return True

def process_data(data):
    if validate_input_code(data):
        return "valid"
    return "invalid"
"""

    # Create input JSON
    input_data = {
        "code": test_code_with_circular,
        "filename": "main.py"
    }

    # Run the fixer tool
    result = subprocess.run(
        ["python", "tools/executable/circular_import_fixer.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    print("Test 1: Code with circular import")
    print("=" * 60)
    print(f"Exit code: {result.returncode}")
    print(f"\nOutput:\n{result.stdout}")

    if result.stderr:
        print(f"\nErrors:\n{result.stderr}")

    # Parse result
    try:
        output = json.loads(result.stdout)
        assert output["fixed"] == True, "Expected fix to be applied"
        assert len(output["removed_imports"]) == 1, "Expected 1 import to be removed"
        assert "from main import validate_input_code" in output["removed_imports"][0]
        # Line count includes blank lines
        assert output["original_lines"] == 10
        assert output["fixed_lines"] == 9
        print("\n[PASS] Test 1: Circular import correctly detected and removed")
    except Exception as e:
        print(f"\n[FAIL] Test 1: {e}")
        return False

    # Test case 2: Code without circular imports
    test_code_clean = """import json

def validate_input_code(data):
    return True
"""

    input_data2 = {
        "code": test_code_clean,
        "filename": "main.py"
    }

    result2 = subprocess.run(
        ["python", "tools/executable/circular_import_fixer.py"],
        input=json.dumps(input_data2),
        capture_output=True,
        text=True
    )

    print("\n\nTest 2: Code without circular imports")
    print("=" * 60)
    print(f"Exit code: {result2.returncode}")
    print(f"\nOutput:\n{result2.stdout}")

    try:
        output2 = json.loads(result2.stdout)
        assert output2["fixed"] == False, "Expected no fix needed"
        assert len(output2["removed_imports"]) == 0, "Expected 0 imports removed"
        print("\n[PASS] Test 2: Clean code correctly identified")
    except Exception as e:
        print(f"\n[FAIL] Test 2: {e}")
        return False

    # Test case 3: Multiple circular imports
    test_code_multiple = """from main import func1, func2
import main

def func1():
    return 1

def func2():
    return 2
"""

    input_data3 = {
        "code": test_code_multiple,
        "filename": "main.py"
    }

    result3 = subprocess.run(
        ["python", "tools/executable/circular_import_fixer.py"],
        input=json.dumps(input_data3),
        capture_output=True,
        text=True
    )

    print("\n\nTest 3: Multiple circular imports")
    print("=" * 60)
    print(f"Exit code: {result3.returncode}")
    print(f"\nOutput:\n{result3.stdout}")

    try:
        output3 = json.loads(result3.stdout)
        assert output3["fixed"] == True, "Expected fix to be applied"
        assert len(output3["removed_imports"]) == 2, "Expected 2 imports to be removed"
        print("\n[PASS] Test 3: Multiple circular imports correctly removed")
    except Exception as e:
        print(f"\n[FAIL] Test 3: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    return True

if __name__ == "__main__":
    success = test_circular_import_detection()
    sys.exit(0 if success else 1)
