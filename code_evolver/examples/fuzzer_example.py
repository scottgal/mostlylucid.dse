"""
Intelligent Fuzzer Examples

Demonstrates automatic fuzzing to find edge cases and break functions.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligent_fuzzer import (
    IntelligentFuzzer,
    FuzzStrategy,
    fuzz
)


# Example 1: Simple Division Function
# ====================================

print("="*70)
print("EXAMPLE 1: Fuzzing Division Function")
print("="*70)

def divide(x: int, y: int) -> float:
    """Divide x by y - will crash on y=0"""
    return x / y

fuzzer = IntelligentFuzzer(seed=42)
report = fuzzer.fuzz_function(divide, num_cases=100)

print(f"\nFunction: {report.function_name}")
print(f"Total test cases: {report.total_cases}")
print(f"Crashes: {report.crashes}")
print(f"Successful: {report.successful}")
print(f"Unique crash types: {report.unique_crashes}")

print(f"\nSample crashes:")
for i, crash in enumerate(report.crash_results[:5], 1):
    print(f"  {i}. {crash.exception_type}: {crash.exception_message}")
    print(f"     Inputs: {crash.test_case.inputs}")


# Example 2: String Processing Function
# ======================================

print("\n" + "="*70)
print("EXAMPLE 2: Fuzzing String Processing")
print("="*70)

def process_email(email: str) -> dict:
    """Extract username and domain from email"""
    parts = email.split('@')
    return {
        "username": parts[0],
        "domain": parts[1]
    }

report2 = fuzzer.fuzz_function(process_email, num_cases=100)

print(f"\nFunction: {report2.function_name}")
print(f"Total test cases: {report2.total_cases}")
print(f"Crashes: {report2.crashes}")
print(f"Successful: {report2.successful}")

print(f"\nSample crashes:")
for i, crash in enumerate(report2.crash_results[:5], 1):
    print(f"  {i}. {crash.exception_type}: {crash.exception_message}")
    print(f"     Inputs: {crash.test_case.inputs}")


# Example 3: List Processing Function
# ====================================

print("\n" + "="*70)
print("EXAMPLE 3: Fuzzing List Processing")
print("="*70)

def get_average(numbers: list) -> float:
    """Calculate average of list"""
    return sum(numbers) / len(numbers)

report3 = fuzzer.fuzz_function(get_average, num_cases=100)

print(f"\nFunction: {report3.function_name}")
print(f"Total test cases: {report3.total_cases}")
print(f"Crashes: {report3.crashes}")
print(f"Successful: {report3.successful}")

print(f"\nUnique crash types found:")
unique_types = set(c.exception_type for c in report3.crash_results)
for crash_type in unique_types:
    count = sum(1 for c in report3.crash_results if c.exception_type == crash_type)
    print(f"  - {crash_type}: {count} occurrences")


# Example 4: Mutation-Based Fuzzing
# ==================================

print("\n" + "="*70)
print("EXAMPLE 4: Mutation-Based Fuzzing")
print("="*70)

def parse_config(config: dict) -> str:
    """Parse configuration dictionary"""
    host = config['host']
    port = config['port']
    ssl = config.get('ssl', False)

    protocol = 'https' if ssl else 'http'
    return f"{protocol}://{host}:{port}"

# Provide valid examples
valid_examples = [
    {"config": {"host": "localhost", "port": 8080, "ssl": False}},
    {"config": {"host": "example.com", "port": 443, "ssl": True}},
]

report4 = fuzzer.fuzz_function(
    parse_config,
    num_cases=100,
    strategies=[FuzzStrategy.MUTATION, FuzzStrategy.ADVERSARIAL],
    valid_examples=valid_examples
)

print(f"\nFunction: {report4.function_name}")
print(f"Total test cases: {report4.total_cases}")
print(f"Crashes: {report4.crashes}")

print(f"\nSample mutation crashes:")
for i, crash in enumerate(report4.crash_results[:3], 1):
    print(f"  {i}. {crash.exception_type}")
    print(f"     Strategy: {crash.test_case.strategy.value}")
    print(f"     Inputs: {crash.test_case.inputs}")


# Example 5: Adversarial Fuzzing (Security)
# ==========================================

print("\n" + "="*70)
print("EXAMPLE 5: Adversarial/Security Fuzzing")
print("="*70)

def execute_query(query: str) -> str:
    """Unsafe SQL query execution (for demonstration)"""
    # BAD: Don't do this in real code!
    if "DROP" in query.upper():
        raise ValueError("SQL injection detected!")
    return f"Executed: {query}"

report5 = fuzzer.fuzz_function(
    execute_query,
    num_cases=50,
    strategies=[FuzzStrategy.ADVERSARIAL]
)

print(f"\nFunction: {report5.function_name}")
print(f"Total test cases: {report5.total_cases}")
print(f"Crashes (security issues found): {report5.crashes}")

print(f"\nSample adversarial inputs that caused issues:")
for i, crash in enumerate(report5.crash_results[:3], 1):
    print(f"  {i}. Input: {crash.test_case.inputs}")
    print(f"     Exception: {crash.exception_message}")


# Example 6: Generate Test Cases from Crashes
# ============================================

print("\n" + "="*70)
print("EXAMPLE 6: Generate Test Cases from Crashes")
print("="*70)

test_code = fuzzer.generate_test_cases_from_crashes(report)

print("\nGenerated pytest test code:")
print("-" * 70)
print(test_code[:800] + "\n..." if len(test_code) > 800 else test_code)
print("-" * 70)


# Example 7: Type-Aware Fuzzing
# ==============================

print("\n" + "="*70)
print("EXAMPLE 7: Type-Aware Fuzzing")
print("="*70)

def process_user_data(name: str, age: int, email: str, active: bool) -> dict:
    """Process user data with type hints"""
    if age < 0:
        raise ValueError("Age cannot be negative")
    if "@" not in email:
        raise ValueError("Invalid email")

    return {
        "name": name.upper(),
        "age": age,
        "email": email.lower(),
        "active": active,
        "category": "adult" if age >= 18 else "minor"
    }

report7 = fuzzer.fuzz_function(
    process_user_data,
    num_cases=100,
    strategies=[FuzzStrategy.TYPE_AWARE, FuzzStrategy.BOUNDARY]
)

print(f"\nFunction: {report7.function_name}")
print(f"Total test cases: {report7.total_cases}")
print(f"Crashes: {report7.crashes}")
print(f"Success rate: {(report7.successful / report7.total_cases * 100):.1f}%")

print(f"\nUnique crash types:")
for crash_type in set(c.exception_type for c in report7.crash_results):
    print(f"  - {crash_type}")


# Summary
# =======

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

all_reports = [report, report2, report3, report4, report5, report7]

print(f"\nTotal functions fuzzed: {len(all_reports)}")
print(f"Total test cases executed: {sum(r.total_cases for r in all_reports)}")
print(f"Total crashes found: {sum(r.crashes for r in all_reports)}")
print(f"Total unique crash types: {sum(r.unique_crashes for r in all_reports)}")

print("\nFunctions with most crashes:")
sorted_reports = sorted(all_reports, key=lambda r: r.crashes, reverse=True)
for r in sorted_reports[:3]:
    print(f"  - {r.function_name}: {r.crashes} crashes")

print("\n" + "="*70)
print("Fuzzing completed!")
print("="*70)
print("\nKey findings:")
print("- Division by zero errors found in divide()")
print("- Index errors found in process_email()")
print("- Type errors and division by zero in get_average()")
print("- Security issues detected in execute_query()")
print("\nUse generated test cases to improve error handling!")
