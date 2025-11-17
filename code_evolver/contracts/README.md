# Code Contracts - Contract Library

This directory contains YAML-based code contract definitions for the mostlylucid DSE project.

## Available Contracts

### 1. Attribution Requirements (`attribution_requirements.yaml`)

**Purpose:** Ensure all generated code has proper attribution and tracking markers.

**Rules:**
- ✅ **ATTR-001**: Attribution comment required (ERROR)
  - Format: `added by scott galloway (mostlylucid) - YYYY-MM-DD`
  - Case insensitive
  - Can be in comments or docstrings

- ✅ **ATTR-002**: DSE tool logging required (WARNING)
  - Format: `dse tool - <toolname> - YYYY-MM-DD`
  - Can use `print()` or `logger.*()` methods

- ✅ **ATTR-003**: DSE project documentation (INFO)
  - Module docstring should mention DSE/mostlylucid

- ✅ **ATTR-004**: Generated code marker (INFO, optional)
  - Optional marker for generated code

**Use Case:** Track code generation for auditing, debugging, and project management. Harmless markers that don't affect functionality.

**Demo:** Run `python demo_attribution_standalone.py`

---

### 2. Enterprise Logging (`enterprise_logging.yaml`)

**Purpose:** Ensure comprehensive logging for compliance and debugging.

**Rules:**
- ✅ **LOG-001**: Logging import required (ERROR)
- ✅ **LOG-002**: Logger instance required (ERROR)
- ✅ **LOG-003**: Function logging required (WARNING)
- ✅ **LOG-004**: Exception logging required (ERROR)

**Use Case:** Organizations requiring logging for compliance, auditing, and debugging.

---

### 3. Call Tool Wrapper (`call_tool_wrapper.yaml`)

**Purpose:** Ensure operations are wrapped with call_tool for tracking.

**Rules:**
- ✅ **TOOL-001**: call_tool wrapper required at start/end (ERROR)
- ✅ **TOOL-002**: call_tool import required (ERROR)

**Use Case:** Track all tool operations for performance monitoring and debugging.

---

### 4. Code Quality (`code_quality.yaml`)

**Purpose:** Maintain code quality through automated checks.

**Rules:**
- ✅ **QUAL-001**: Maximum function length (50 lines) (WARNING)
- ✅ **QUAL-002**: Complexity limit (10) (WARNING)
- ✅ **QUAL-003**: Docstrings required (WARNING)
- ✅ **QUAL-004**: Type hints required (INFO)

**Use Case:** Ensure maintainable, well-documented code.

---

### 5. Library Restrictions (`library_restrictions.yaml`)

**Purpose:** Security and dependency management.

**Rules:**
- ✅ **LIB-001**: No eval/exec (ERROR)
- ✅ **LIB-002**: No pickle (WARNING)
- ✅ **LIB-003**: No deprecated libraries (WARNING)
- ✅ **LIB-004**: Import placeholder pattern (INFO)

**Use Case:** Prevent security issues and manage dependencies.

---

## Quick Start

### Load a Contract

```python
from pathlib import Path
from src.code_contract import ContractLoader

loader = ContractLoader(Path("contracts"))
loader.load_all_contracts()

contract = loader.get_contract("attribution_requirements")
```

### Validate Code

```python
from src.contract_validator import ContractValidator

validator = ContractValidator()
report = validator.validate(code, contract, "myfile.py")

if report.is_compliant:
    print(f"✅ Compliant! Score: {report.compliance_score:.1%}")
else:
    print(f"❌ Violations: {report.error_count} errors")
    for violation in report.violations:
        print(f"  - {violation.message}")
```

### Apply Multiple Contracts

```python
contracts = ["attribution_requirements", "enterprise_logging", "code_quality"]

for contract_id in contracts:
    contract = loader.get_contract(contract_id)
    report = validator.validate(code, contract)
    print(f"{contract.name}: {'✅ PASS' if report.is_compliant else '❌ FAIL'}")
```

## Creating Custom Contracts

Create a new YAML file in this directory:

```yaml
contract_id: "my_contract"
name: "My Custom Contract"
description: "Description of what this contract enforces"
version: "1.0.0"
tags:
  - custom
  - myproject
author: "Your Name"
created_at: "YYYY-MM-DD"

rules:
  - rule_id: "CUSTOM-001"
    name: "My Rule"
    description: "What this rule checks"
    rule_type: "pattern"  # pattern, structural, library, metric, documentation
    severity: "error"     # error, warning, info
    pattern: "regex_pattern_here"
    required: true        # true = must be present, false = must be absent
    applies_to:
      - "module"
      - "function"
```

## Testing Contracts

### Standalone Demo

```bash
python demo_attribution_standalone.py
```

### Full System Demo

```bash
python demo_attribution_contract.py
```

### Unit Tests

```bash
pytest tests/test_code_contracts.py -v -k attribution
```

## Contract Template for Code Generation

When generating code, use this template to ensure compliance with attribution contract:

```python
"""
{module_description}

Part of the mostlylucid DSE (Dynamic Software Evolution) project.
added by scott galloway (mostlylucid) - {YYYY-MM-DD}
"""
import logging

logger = logging.getLogger(__name__)

def {function_name}({parameters}):
    """{function_description}"""
    logger.info("dse tool - {tool_name} - {YYYY-MM-DD}")

    # Your code here
    result = process_logic()

    return result
```

## Contract Severity Levels

- **ERROR**: Must be fixed before deployment. Validation fails.
- **WARNING**: Should be fixed. Validation passes but issues reported.
- **INFO**: Nice to have. Informational only.

## Integration

### With Code Generation

```python
def generate_with_contracts(spec, contract_ids):
    code = generate_tool(spec)

    violations = []
    for contract_id in contract_ids:
        contract = loader.get_contract(contract_id)
        report = validator.validate(code, contract)
        violations.extend(report.violations)

    if violations:
        # Auto-fix or reject
        return fix_violations(code, violations)

    return code
```

### With CI/CD

```bash
# In your CI pipeline
python -c "from src.contract_validator import *; validate_all()"
```

## Best Practices

1. **Start Small**: Begin with essential contracts (attribution, logging)
2. **Appropriate Severity**: Use ERROR only for critical requirements
3. **Clear Messages**: Provide helpful suggestions in contracts
4. **Test Regularly**: Run contract validation in CI/CD
5. **Version Contracts**: Update version when rules change
6. **Document Exceptions**: Explain why certain patterns are excluded

## Documentation

- **Full Guide**: `../CODE_CONTRACTS_GUIDE.md`
- **Implementation Details**: `../../CODE_CONTRACTS_IMPLEMENTATION.md`
- **Attribution Demo**: Run `demo_attribution_standalone.py`
- **General Demo**: Run `demo_contracts_standalone.py`

## Support

For questions or issues:
1. Review the full guide: `CODE_CONTRACTS_GUIDE.md`
2. Check examples in demo files
3. Review test cases in `tests/test_code_contracts.py`
