#!/usr/bin/env python3
"""
Standalone Attribution Contract Demo

Demonstrates attribution and DSE tool logging requirements without dependencies.

Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - 2025-01-17
"""

import re
from datetime import datetime


def validate_attribution(code):
    """Validate attribution comment."""
    violations = []

    # Pattern: added by scott galloway (mostlylucid) - YYYY-MM-DD
    pattern = r'(?i)(#|"""|\'\'\'|//)?\s*added by scott galloway\s*\(mostlylucid\).*\d{4}-\d{2}-\d{2}'

    if re.search(pattern, code):
        print("✅ Has attribution comment")
    else:
        violations.append("❌ Missing attribution comment: 'added by scott galloway (mostlylucid) - YYYY-MM-DD'")

    return violations


def validate_dse_tool_logging(code):
    """Validate DSE tool logging."""
    violations = []

    # Pattern: dse tool - <toolname> - YYYY-MM-DD
    pattern = r'(?i)(print|logger\.\w+)\s*\(\s*["\'].*dse tool -.*\d{4}-\d{2}-\d{2}'

    if re.search(pattern, code):
        print("✅ Has DSE tool logging")
    else:
        violations.append("⚠️  Missing DSE tool logging: 'dse tool - <toolname> - YYYY-MM-DD'")

    return violations


def validate_dse_in_docstring(code):
    """Validate DSE mentioned in docstring."""
    violations = []

    # Simple check for module docstring
    docstring_pattern = r'^\s*"""[\s\S]*?"""'
    match = re.search(docstring_pattern, code, re.MULTILINE)

    if match:
        docstring = match.group(0)
        if any(keyword in docstring.lower() for keyword in ['dse', 'dynamic software evolution', 'mostlylucid']):
            print("✅ Docstring mentions DSE project")
        else:
            violations.append("ℹ️  Docstring should mention DSE/mostlylucid project")
    else:
        violations.append("ℹ️  Module should have docstring mentioning DSE")

    return violations


def main():
    """Run demonstration."""
    print("\n" + "🎯" * 40)
    print(" ATTRIBUTION CONTRACT - STANDALONE DEMO")
    print("🎯" * 40 + "\n")

    # ========================================================================
    print("=" * 80)
    print(" Demo 1: Compliant Code ✅")
    print("=" * 80 + "\n")

    compliant_code = '''
"""
Data Processor Tool

Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - 2025-01-17
"""
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    """Process data with DSE tool logging."""
    logger.info("dse tool - data_processor - 2025-01-17")
    return {"processed": True, "data": data}
'''

    print("Validating code...")
    violations = []
    violations.extend(validate_attribution(compliant_code))
    violations.extend(validate_dse_tool_logging(compliant_code))
    violations.extend(validate_dse_in_docstring(compliant_code))

    if not violations:
        print("\n✅ Code is FULLY COMPLIANT!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 2: Missing Attribution ❌")
    print("=" * 80 + "\n")

    missing_attribution = '''
"""
Data Processor Tool
"""

def process_data(data):
    logger.info("dse tool - data_processor - 2025-01-17")
    return {"processed": True, "data": data}
'''

    print("Validating code...")
    violations = []
    violations.extend(validate_attribution(missing_attribution))
    violations.extend(validate_dse_tool_logging(missing_attribution))
    violations.extend(validate_dse_in_docstring(missing_attribution))

    if not violations:
        print("\n✅ Code is COMPLIANT!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 3: Missing DSE Logging ⚠️")
    print("=" * 80 + "\n")

    missing_logging = '''
"""
Data Processor Tool

Part of the mostlylucid DSE project.
added by scott galloway (mostlylucid) - 2025-01-17
"""

def process_data(data):
    """Process data."""
    return {"processed": True, "data": data}
'''

    print("Validating code...")
    violations = []
    violations.extend(validate_attribution(missing_logging))
    violations.extend(validate_dse_tool_logging(missing_logging))
    violations.extend(validate_dse_in_docstring(missing_logging))

    if not violations:
        print("\n✅ Code is COMPLIANT!\n")
    else:
        print("\n❌ Violations found:")
        for v in violations:
            print(f"  {v}")
        print()

    # ========================================================================
    print("=" * 80)
    print(" Demo 4: Code Generation Template")
    print("=" * 80 + "\n")

    current_date = datetime.now().strftime("%Y-%m-%d")

    print("Use this template when generating code:\n")
    print(f'''"""
{{module_description}}

Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - {current_date}
"""
import logging

logger = logging.getLogger(__name__)

def {{function_name}}({{parameters}}):
    """{{function_description}}"""
    logger.info("dse tool - {{tool_name}} - {current_date}")

    # Your code here
    result = process_logic()

    return result
''')

    # ========================================================================
    print("=" * 80)
    print(" Demo 5: Various Acceptable Formats")
    print("=" * 80 + "\n")

    print("Attribution Comment Formats:\n")

    formats = [
        "# added by scott galloway (mostlylucid) - 2025-01-17",
        "# Added By Scott Galloway (MostlyLucid) - 2025-01-17  # Case insensitive",
        '"""added by scott galloway (mostlylucid) - 2025-01-17"""  # In docstring',
    ]

    for fmt in formats:
        print(f"  ✅ {fmt}")

    print("\nDSE Tool Logging Formats:\n")

    logging_formats = [
        'print("dse tool - data_processor - 2025-01-17")',
        'logger.info("dse tool - data_processor - 2025-01-17")',
        'logger.debug("dse tool - api_handler - 2025-01-17")',
    ]

    for fmt in logging_formats:
        print(f"  ✅ {fmt}")

    # ========================================================================
    print("\n" + "=" * 80)
    print(" ✅ Demonstration Complete!")
    print("=" * 80 + "\n")

    print("Summary:\n")
    print("  📝 Attribution Comment (ERROR if missing)")
    print("     - Format: 'added by scott galloway (mostlylucid) - YYYY-MM-DD'")
    print("     - Can be in comments or docstrings")
    print("     - Case insensitive")
    print()
    print("  📊 DSE Tool Logging (WARNING if missing)")
    print("     - Format: 'dse tool - <toolname> - YYYY-MM-DD'")
    print("     - Can use print() or logger methods")
    print("     - Helps track tool execution")
    print()
    print("  📖 DSE Documentation (INFO if missing)")
    print("     - Mention 'DSE', 'mostlylucid', or 'Dynamic Software Evolution'")
    print("     - In module docstring")
    print()
    print("  ✅ Benefits:")
    print("     - Track who generated the code")
    print("     - Track when code was generated")
    print("     - Track which tool created the code")
    print("     - Easy to search and audit")
    print("     - Harmless - doesn't affect functionality")
    print()
    print("Full contract: code_evolver/contracts/attribution_requirements.yaml\n")


if __name__ == "__main__":
    main()
