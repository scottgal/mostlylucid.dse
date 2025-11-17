#!/usr/bin/env python3
"""
Test script for smart_faker tool
"""
import json
import subprocess
import sys


def test_tool(test_name, input_data):
    """Run the tool with given input and return result"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Input: {json.dumps(input_data, indent=2)}\n")

    try:
        result = subprocess.run(
            ['python', '/home/user/mostlylucid.dse/code_evolver/tools/executable/smart_faker.py'],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            output = json.loads(result.stdout)
            print(f"✅ SUCCESS")
            print(f"Output:\n{json.dumps(output, indent=2)[:500]}...\n")
            return True
        else:
            print(f"❌ FAILED")
            print(f"Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False


def main():
    """Run all tests"""
    print("Testing Smart Faker Tool")
    print("="*60)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Plain English - Simple
    if test_tool(
        "Plain English - Simple User Data",
        {
            "prompt": "I need user data with name, email, and age",
            "count": 3,
            "output_format": "json"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 2: JSON Schema
    if test_tool(
        "JSON Schema Input",
        {
            "prompt": json.dumps({
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "active": {"type": "boolean"}
                },
                "required": ["id", "name", "email"]
            }),
            "count": 2,
            "output_format": "json"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 3: CSV Output
    if test_tool(
        "CSV Output Format",
        {
            "prompt": "Product with sku, name, price, stock",
            "count": 5,
            "output_format": "csv"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 4: Code snippet (Python class)
    if test_tool(
        "Code Snippet - Python Class",
        {
            "prompt": """
            class Employee:
                def __init__(self, employee_id, name, department, salary):
                    self.employee_id = employee_id
                    self.name = name
                    self.department = department
                    self.salary = salary
            """,
            "count": 3,
            "output_format": "json"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 5: Single item (not array)
    if test_tool(
        "Single Item Generation",
        {
            "prompt": "User with username, email, and registration_date",
            "count": 1,
            "output_format": "json"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 6: Example JSON input
    if test_tool(
        "Example JSON Input",
        {
            "prompt": """
            Here's an example:
            {
                "order_id": "ORD-123",
                "customer": "John Doe",
                "total": 99.99,
                "status": "shipped"
            }
            """,
            "count": 2,
            "output_format": "json"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 7: JSONL format
    if test_tool(
        "JSONL Output Format",
        {
            "prompt": "Log entry with timestamp, level, and message",
            "count": 3,
            "output_format": "jsonl"
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 8: With seed (reproducibility)
    if test_tool(
        "Reproducible with Seed",
        {
            "prompt": "User with name and email",
            "count": 2,
            "output_format": "json",
            "seed": 42
        }
    ):
        tests_passed += 1
    else:
        tests_failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print(f"Total: {tests_passed + tests_failed}")

    if tests_failed == 0:
        print(f"\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
