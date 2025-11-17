#!/usr/bin/env python3
"""
Standalone demonstration of Code Contracts System

This version doesn't import from src to avoid dependency issues.
"""

import ast
import re
import yaml
from pathlib import Path


def validate_logging_contract(code):
    """Simple validation for logging contract."""
    violations = []

    # Check for logging import
    if "import logging" not in code:
        violations.append("❌ Missing logging import")
    else:
        print("✅ Has logging import")

    # Check for logger instance
    if "logging.getLogger" not in code:
        violations.append("❌ No logger instance created")
    else:
        print("✅ Has logger instance")

    # Check for log calls
    log_patterns = ['logger.info', 'logger.debug', 'logger.warning', 'logger.error']
    has_log_call = any(pattern in code for pattern in log_patterns)

    if has_log_call:
        print("✅ Has logging calls")
    else:
        violations.append("⚠️  No logging calls found")

    return violations


def validate_function_length(code, max_lines=50):
    """Simple validation for function length."""
    violations = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"❌ Syntax error: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Calculate function length
            func_lines = []
            for child in ast.walk(node):
                if hasattr(child, 'lineno'):
                    func_lines.append(child.lineno)

            if func_lines:
                func_length = max(func_lines) - min(func_lines) + 1

                if func_length > max_lines:
                    violations.append(
                        f"⚠️  Function '{node.name}' is {func_length} lines (max: {max_lines})"
                    )
                else:
                    print(f"✅ Function '{node.name}' is {func_length} lines (within limit)")

    return violations


def validate_forbidden_patterns(code, patterns):
    """Check for forbidden patterns."""
    violations = []

    for pattern_name, pattern in patterns.items():
        if re.search(pattern, code):
            violations.append(f"❌ Forbidden pattern found: {pattern_name}")
        else:
            print(f"✅ No {pattern_name} found")

    return violations


def main():
    """Run demonstrations."""
    print("\n" + "🎯" * 40)
    print(" CODE CONTRACTS SYSTEM - STANDALONE DEMO")
    print("🎯" * 40 + "\n")

    # ========================================================================
    print("=" * 80)
    print(" Demo 1: Valid Code with Logging")
    print("=" * 80 + "\n")

    good_code = '''
"""Example module with proper logging."""
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    """Process data with logging."""
    logger.info("Starting data processing")
    result = {"processed": True, "data": data}
    logger.debug(f"Processed: {result}")
    return result
'''

    print("Validating logging contract...")
    violations = validate_logging_contract(good_code)

    if not violations:
        print("\n✅ Code is COMPLIANT with logging contract!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 2: Invalid Code without Logging")
    print("=" * 80 + "\n")

    bad_code = '''
def process_data(data):
    result = {"processed": True, "data": data}
    return result
'''

    print("Validating logging contract...")
    violations = validate_logging_contract(bad_code)

    if not violations:
        print("\n✅ Code is COMPLIANT!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 3: Function Length Validation")
    print("=" * 80 + "\n")

    long_code = '''
def short_function():
    return 42

def very_long_function():
    line_1 = 1
    line_2 = 2
    line_3 = 3
    line_4 = 4
    line_5 = 5
    line_6 = 6
    line_7 = 7
    line_8 = 8
    line_9 = 9
    line_10 = 10
    line_11 = 11
    line_12 = 12
    line_13 = 13
    line_14 = 14
    line_15 = 15
    line_16 = 16
    line_17 = 17
    line_18 = 18
    line_19 = 19
    line_20 = 20
    line_21 = 21
    line_22 = 22
    line_23 = 23
    line_24 = 24
    line_25 = 25
    line_26 = 26
    line_27 = 27
    line_28 = 28
    line_29 = 29
    line_30 = 30
    line_31 = 31
    line_32 = 32
    line_33 = 33
    line_34 = 34
    line_35 = 35
    line_36 = 36
    line_37 = 37
    line_38 = 38
    line_39 = 39
    line_40 = 40
    line_41 = 41
    line_42 = 42
    line_43 = 43
    line_44 = 44
    line_45 = 45
    line_46 = 46
    line_47 = 47
    line_48 = 48
    line_49 = 49
    line_50 = 50
    line_51 = 51
    line_52 = 52
    line_53 = 53
    line_54 = 54
    line_55 = 55
    return sum(range(56))
'''

    print("Validating function length (max 50 lines)...")
    violations = validate_function_length(long_code, max_lines=50)

    if not violations:
        print("\n✅ All functions within length limit!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 4: Forbidden Patterns")
    print("=" * 80 + "\n")

    unsafe_code = '''
import pickle

def dangerous_eval(code_str):
    return eval(code_str)

def load_pickle(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)
'''

    forbidden = {
        "eval()": r'\beval\s*\(',
        "exec()": r'\bexec\s*\(',
        "pickle import": r'import\s+pickle'
    }

    print("Checking for forbidden patterns...")
    violations = validate_forbidden_patterns(unsafe_code, forbidden)

    if not violations:
        print("\n✅ No forbidden patterns found!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 5: Loading Contracts from YAML")
    print("=" * 80 + "\n")

    contracts_dir = Path(__file__).parent / "contracts"

    if contracts_dir.exists():
        print(f"📁 Contracts directory: {contracts_dir}\n")

        yaml_files = list(contracts_dir.glob("*.yaml"))
        print(f"Found {len(yaml_files)} contract files:\n")

        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    contract_data = yaml.safe_load(f)

                print(f"  📋 {contract_data.get('name', 'Unknown')}")
                print(f"     ID: {contract_data.get('contract_id', 'N/A')}")
                print(f"     Rules: {len(contract_data.get('rules', []))}")
                print(f"     Tags: {', '.join(contract_data.get('tags', []))}")
                print()

            except Exception as e:
                print(f"  ⚠️  Error loading {yaml_file.name}: {e}")
    else:
        print(f"⚠️  Contracts directory not found: {contracts_dir}\n")

    # ========================================================================
    print("=" * 80)
    print(" ✅ Demonstration Complete!")
    print("=" * 80 + "\n")

    print("The Code Contracts system provides:\n")
    print("  ✅ Logging enforcement for compliance")
    print("  ✅ Function length limits for maintainability")
    print("  ✅ Forbidden pattern detection for security")
    print("  ✅ YAML-based contract specifications")
    print("  ✅ Extensible validation framework")
    print("  ✅ Integration with code generation")
    print("\nNext steps:")
    print("  1. Review contracts in code_evolver/contracts/")
    print("  2. Read CODE_CONTRACTS_GUIDE.md for full documentation")
    print("  3. Run: pytest code_evolver/tests/test_code_contracts.py")
    print("  4. Integrate with your code generation pipeline\n")


if __name__ == "__main__":
    main()
