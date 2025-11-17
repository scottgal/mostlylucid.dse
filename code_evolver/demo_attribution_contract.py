#!/usr/bin/env python3
"""
Demonstration of Attribution Contract System

This shows how to enforce:
1. Attribution comments: "added by scott galloway (mostlylucid)" with date
2. DSE tool logging: "dse tool - <toolname>" with date

These are harmless but always-checked markers for code generation tracking.

Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - 2025-01-17
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


def demo_compliant_code():
    """Demonstrate code that passes attribution requirements."""
    print_section("✅ COMPLIANT CODE - Passes All Attribution Checks")

    compliant_code = '''
"""
Data Processor Tool

This tool processes data with proper attribution and logging.
Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - 2025-01-17
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def process_data(data):
    """Process data with DSE tool logging."""
    logger.info("dse tool - data_processor - 2025-01-17")

    result = {"processed": True, "data": data}
    return result
'''

    print("Code Example:")
    print("-" * 80)
    print(compliant_code)
    print("-" * 80 + "\n")

    # Load contract
    contracts_dir = Path(__file__).parent / "contracts"
    loader = ContractLoader(contracts_dir)
    loader.load_all_contracts()

    contract = loader.get_contract("attribution_requirements")
    if not contract:
        print("⚠️  Attribution contract not found")
        return

    # Validate
    validator = ContractValidator()
    report = validator.validate(compliant_code, contract, "data_processor.py")

    print(f"Contract: {contract.name}\n")
    print(f"Results:")
    print(f"  Compliance Score: {report.compliance_score:.1%}")
    print(f"  Errors: {report.error_count}")
    print(f"  Warnings: {report.warning_count}")
    print(f"  Info: {report.info_count}")
    print(f"  Status: {'✅ COMPLIANT' if report.is_compliant else '❌ NON-COMPLIANT'}")

    if report.passed_rules:
        print(f"\n  Passed Rules:")
        for rule in report.passed_rules:
            print(f"    ✅ {rule.name}")


def demo_missing_attribution():
    """Demonstrate code missing attribution comment."""
    print_section("❌ NON-COMPLIANT - Missing Attribution Comment")

    missing_attribution = '''
"""
Data Processor Tool

This tool processes data but is missing the attribution comment.
"""
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    """Process data."""
    logger.info("dse tool - data_processor - 2025-01-17")
    return {"processed": True, "data": data}
'''

    print("Code Example:")
    print("-" * 80)
    print(missing_attribution)
    print("-" * 80 + "\n")

    # Load and validate
    contracts_dir = Path(__file__).parent / "contracts"
    loader = ContractLoader(contracts_dir)
    loader.load_all_contracts()

    contract = loader.get_contract("attribution_requirements")
    if not contract:
        print("⚠️  Attribution contract not found")
        return

    validator = ContractValidator()
    report = validator.validate(missing_attribution, contract, "bad_processor.py")

    print(f"Results: {'✅ COMPLIANT' if report.is_compliant else '❌ NON-COMPLIANT'}\n")

    if report.violations:
        print("Violations Found:")
        for v in report.violations:
            if v.rule.rule_id == "ATTR-001":
                print(f"\n  ❌ {v.rule.name}")
                print(f"     {v.message}")
                print(f"\n  💡 Suggestion:")
                print(f"     {v.suggestion}")


def demo_missing_dse_logging():
    """Demonstrate code missing DSE tool logging."""
    print_section("❌ NON-COMPLIANT - Missing DSE Tool Logging")

    missing_logging = '''
"""
Data Processor Tool

Part of the mostlylucid DSE project.
added by scott galloway (mostlylucid) - 2025-01-17
"""

def process_data(data):
    """Process data without DSE logging."""
    return {"processed": True, "data": data}
'''

    print("Code Example:")
    print("-" * 80)
    print(missing_logging)
    print("-" * 80 + "\n")

    # Load and validate
    contracts_dir = Path(__file__).parent / "contracts"
    loader = ContractLoader(contracts_dir)
    loader.load_all_contracts()

    contract = loader.get_contract("attribution_requirements")
    if not contract:
        print("⚠️  Attribution contract not found")
        return

    validator = ContractValidator()
    report = validator.validate(missing_logging, contract, "bad_processor.py")

    print(f"Results: {'✅ COMPLIANT' if report.is_compliant else '❌ NON-COMPLIANT'}\n")

    if report.violations:
        print("Violations Found:")
        for v in report.violations:
            if v.rule.rule_id == "ATTR-002":
                print(f"\n  ⚠️  {v.rule.name}")
                print(f"     {v.message}")
                print(f"\n  💡 Suggestion:")
                print(f"     {v.suggestion}")


def demo_template_for_codegen():
    """Show template for code generation."""
    print_section("📋 Template for Code Generation")

    print("When generating code, use this template to ensure compliance:\n")

    template = '''"""
{module_description}

Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - {current_date}
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def {function_name}({parameters}):
    """
    {function_description}
    """
    # Log DSE tool execution
    logger.info("dse tool - {tool_name} - {current_date}")

    # Your code here
    result = process_logic()

    return result
'''

    print(template)

    print("\nVariable substitutions:")
    print("  {module_description}  - Brief description of the module")
    print("  {current_date}        - YYYY-MM-DD format")
    print("  {function_name}       - Name of the main function")
    print("  {parameters}          - Function parameters")
    print("  {function_description}- What the function does")
    print("  {tool_name}           - Name of the DSE tool")


def demo_various_formats():
    """Show various acceptable attribution formats."""
    print_section("📝 Acceptable Attribution Formats")

    formats = [
        ("Single-line comment", "# added by scott galloway (mostlylucid) - 2025-01-17"),
        ("In module docstring", '"""\nModule description.\nadded by scott galloway (mostlylucid) - 2025-01-17\n"""'),
        ("Case insensitive", "# Added By Scott Galloway (MostlyLucid) - 2025-01-17"),
        ("With extra text", "# Generated by DSE, added by scott galloway (mostlylucid) - 2025-01-17"),
    ]

    for name, example in formats:
        print(f"✅ {name}:")
        print(f"   {example}")
        print()

    print("DSE Tool Logging Formats:")
    logging_formats = [
        ("Using print", 'print("dse tool - data_processor - 2025-01-17")'),
        ("Using logger.info", 'logger.info("dse tool - data_processor - 2025-01-17")'),
        ("Using logger.debug", 'logger.debug("dse tool - api_handler - 2025-01-17")'),
        ("With extra info", 'logger.info("dse tool - validator - 2025-01-17 - Processing request")'),
    ]

    for name, example in logging_formats:
        print(f"✅ {name}:")
        print(f"   {example}")
        print()


def main():
    """Run all demonstrations."""
    print("\n" + "🎯" * 40)
    print(" ATTRIBUTION CONTRACT DEMONSTRATION")
    print(" Harmless but Always-Checked Code Markers")
    print("🎯" * 40)

    demo_compliant_code()
    demo_missing_attribution()
    demo_missing_dse_logging()
    demo_template_for_codegen()
    demo_various_formats()

    print("\n" + "=" * 80)
    print(" ✅ Demonstration Complete!")
    print("=" * 80 + "\n")

    print("Key Takeaways:")
    print()
    print("  1. ✅ Attribution comments track who created the code")
    print("     Format: 'added by scott galloway (mostlylucid) - YYYY-MM-DD'")
    print()
    print("  2. ✅ DSE tool logging tracks tool execution")
    print("     Format: 'dse tool - <toolname> - YYYY-MM-DD'")
    print()
    print("  3. ✅ Both are harmless markers for tracking")
    print("     - Don't affect functionality")
    print("     - Help with auditing and debugging")
    print("     - Easy to search and filter")
    print()
    print("  4. ✅ Contract enforces these automatically")
    print("     - Error for missing attribution")
    print("     - Warning for missing DSE logging")
    print("     - Info for missing DSE in docstring")
    print()
    print("See contracts/attribution_requirements.yaml for full details.\n")


if __name__ == "__main__":
    main()
