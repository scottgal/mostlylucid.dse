#!/usr/bin/env python3
"""
Demonstration of Code Contracts System

This script demonstrates:
1. Loading contracts from YAML
2. Validating code against contracts
3. Generating compliance reports
4. Using custom validators
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.code_contract import CodeContract, ContractLoader
from src.contract_validator import ContractValidator


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def demo_1_load_contracts():
    """Demo: Load contracts from YAML files."""
    print_section("Demo 1: Loading Contracts")

    contracts_dir = Path(__file__).parent / "contracts"

    if not contracts_dir.exists():
        print(f"⚠️  Contracts directory not found: {contracts_dir}")
        return None

    loader = ContractLoader(contracts_dir)
    contracts = loader.load_all_contracts()

    print(f"✅ Loaded {len(contracts)} contracts:\n")
    for contract in contracts:
        print(f"  📋 {contract.name}")
        print(f"     ID: {contract.contract_id}")
        print(f"     Rules: {len(contract.rules)}")
        print(f"     Tags: {', '.join(contract.tags)}")
        print()

    return loader


def demo_2_validate_good_code(loader):
    """Demo: Validate code that passes all checks."""
    print_section("Demo 2: Validating Compliant Code")

    # Good code with logging
    good_code = '''
"""Example module with proper logging."""
import logging

logger = logging.getLogger(__name__)

def process_data(data: dict) -> dict:
    """Process data with logging.

    Args:
        data: Input data dictionary

    Returns:
        Processed data dictionary
    """
    logger.info("Starting data processing")

    try:
        result = {"processed": True, "data": data}
        logger.debug(f"Processed: {result}")
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
'''

    # Validate against enterprise logging contract
    contract = loader.get_contract("enterprise_logging")
    if not contract:
        print("⚠️  Enterprise logging contract not found")
        return

    validator = ContractValidator()
    report = validator.validate(good_code, contract, "example_good.py")

    print(f"Code Path: example_good.py")
    print(f"Contract: {contract.name}\n")

    if report.is_compliant:
        print(f"✅ Code is COMPLIANT!")
        print(f"   Compliance Score: {report.compliance_score:.1%}")
        print(f"   Passed Rules: {len(report.passed_rules)}")
    else:
        print(f"❌ Code is NON-COMPLIANT")
        print(f"   Errors: {report.error_count}")
        print(f"   Warnings: {report.warning_count}")


def demo_3_validate_bad_code(loader):
    """Demo: Validate code that fails checks."""
    print_section("Demo 3: Validating Non-Compliant Code")

    # Bad code without logging
    bad_code = '''
def process_data(data):
    result = {"processed": True, "data": data}
    return result
'''

    contract = loader.get_contract("enterprise_logging")
    if not contract:
        print("⚠️  Enterprise logging contract not found")
        return

    validator = ContractValidator()
    report = validator.validate(bad_code, contract, "example_bad.py")

    print(f"Code Path: example_bad.py")
    print(f"Contract: {contract.name}\n")

    if report.is_compliant:
        print(f"✅ Code is COMPLIANT!")
    else:
        print(f"❌ Code is NON-COMPLIANT")
        print(f"   Compliance Score: {report.compliance_score:.1%}")
        print(f"   Errors: {report.error_count}")
        print(f"   Warnings: {report.warning_count}\n")

        print("Violations:")
        for i, violation in enumerate(report.violations, 1):
            severity_icon = {
                "error": "❌",
                "warning": "⚠️",
                "info": "ℹ️"
            }.get(violation.rule.severity.value, "•")

            print(f"\n{i}. {severity_icon} {violation.rule.name}")
            print(f"   Rule ID: {violation.rule.rule_id}")
            print(f"   Message: {violation.message}")
            if violation.suggestion:
                print(f"   Suggestion: {violation.suggestion}")


def demo_4_multiple_contracts(loader):
    """Demo: Validate against multiple contracts."""
    print_section("Demo 4: Multiple Contract Validation")

    code = '''
"""Example with some issues."""
import logging

logger = logging.getLogger(__name__)

def very_long_function_that_should_be_refactored(data):
    """This function is too long."""
    logger.info("Starting")
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
    if data:
        if True:
            if False:
                if data:
                    if True:
                        if False:
                            pass
    return sum([line_1, line_2, line_3])
'''

    # Validate against multiple contracts
    contract_ids = ["enterprise_logging", "code_quality"]
    validator = ContractValidator()

    print("Validating code against multiple contracts:\n")

    all_errors = 0
    all_warnings = 0

    for contract_id in contract_ids:
        contract = loader.get_contract(contract_id)
        if not contract:
            print(f"⚠️  Contract not found: {contract_id}")
            continue

        report = validator.validate(code, contract, "example_multi.py")

        status = "✅ PASS" if report.is_compliant else "❌ FAIL"
        print(f"{status} {contract.name}")
        print(f"      Score: {report.compliance_score:.1%}, "
              f"Errors: {report.error_count}, Warnings: {report.warning_count}")

        all_errors += report.error_count
        all_warnings += report.warning_count

    print(f"\n📊 Overall: {all_errors} errors, {all_warnings} warnings across all contracts")


def demo_5_markdown_report(loader):
    """Demo: Generate markdown compliance report."""
    print_section("Demo 5: Markdown Compliance Report")

    code = '''
import pickle

def load_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)
'''

    contract = loader.get_contract("library_restrictions")
    if not contract:
        print("⚠️  Library restrictions contract not found")
        return

    validator = ContractValidator()
    report = validator.validate(code, contract, "example_unsafe.py")

    markdown = report.to_markdown()
    print("Generated Markdown Report:\n")
    print(markdown)


def demo_6_contract_structure():
    """Demo: Programmatically create and use contracts."""
    print_section("Demo 6: Creating Contracts Programmatically")

    from src.code_contract import (
        CodeContract,
        ContractRule,
        ContractType,
        ContractSeverity
    )

    # Create a simple contract
    contract = CodeContract(
        contract_id="demo_contract",
        name="Demo Contract",
        description="A programmatically created contract",
        version="1.0.0",
        tags=["demo"],
        rules=[
            ContractRule(
                rule_id="DEMO-001",
                name="Must Import JSON",
                description="Code must import json module",
                rule_type=ContractType.LIBRARY,
                severity=ContractSeverity.ERROR,
                pattern="^json$",
                required=True
            )
        ]
    )

    print(f"Created contract: {contract.name}")
    print(f"  ID: {contract.contract_id}")
    print(f"  Rules: {len(contract.rules)}\n")

    # Test it
    code_with_json = "import json\n"
    code_without_json = "import sys\n"

    validator = ContractValidator()

    print("Testing code WITH json import:")
    report1 = validator.validate(code_with_json, contract)
    print(f"  {'✅ PASS' if report1.is_compliant else '❌ FAIL'}\n")

    print("Testing code WITHOUT json import:")
    report2 = validator.validate(code_without_json, contract)
    print(f"  {'✅ PASS' if report2.is_compliant else '❌ FAIL'}")
    if report2.violations:
        print(f"  Message: {report2.violations[0].message}")


def main():
    """Run all demonstrations."""
    print("\n" + "🎯" * 40)
    print(" CODE CONTRACTS SYSTEM DEMONSTRATION")
    print("🎯" * 40)

    # Demo 1: Load contracts
    loader = demo_1_load_contracts()
    if not loader:
        print("\n⚠️  Cannot continue without contracts directory")
        return

    # Demo 2: Validate good code
    demo_2_validate_good_code(loader)

    # Demo 3: Validate bad code
    demo_3_validate_bad_code(loader)

    # Demo 4: Multiple contracts
    demo_4_multiple_contracts(loader)

    # Demo 5: Markdown report
    demo_5_markdown_report(loader)

    # Demo 6: Programmatic contracts
    demo_6_contract_structure()

    print("\n" + "=" * 80)
    print(" ✅ Demonstration Complete!")
    print("=" * 80 + "\n")

    print("Next steps:")
    print("  1. Review the contracts in contracts/ directory")
    print("  2. Customize contracts for your organization")
    print("  3. Integrate with code generation pipeline")
    print("  4. Run contract validation as part of CI/CD")
    print("  5. Generate tests from contracts")
    print("\nSee CODE_CONTRACTS_GUIDE.md for full documentation.\n")


if __name__ == "__main__":
    main()
