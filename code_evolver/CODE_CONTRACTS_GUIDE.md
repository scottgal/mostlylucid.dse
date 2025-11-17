# Code Contracts System - Complete Guide

## Overview

The Code Contracts system provides a comprehensive framework for specifying and enforcing rules on generated code. This enables organizations to maintain standards for logging, code structure, library usage, and other requirements.

## Key Features

- **YAML-based Contract Specification** - Easy to read and maintain
- **Multiple Contract Types** - Structural, behavioral, library, metric, pattern, documentation
- **Severity Levels** - Error, warning, info
- **Custom Validators** - Extensible validation framework
- **Compliance Reports** - Detailed reports in JSON, Markdown, or text format
- **Integration with Code Generation** - Validate during and after code generation
- **Test Generation** - Generate tests from contract specifications

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Contracts System                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Contract   │      │  Contract    │                    │
│  │   Loader     │─────▶│  Validator   │                    │
│  └──────────────┘      └──────────────┘                    │
│         │                     │                             │
│         │                     │                             │
│         ▼                     ▼                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Contract   │      │  Compliance  │                    │
│  │    Specs     │      │   Report     │                    │
│  │   (YAML)     │      │              │                    │
│  └──────────────┘      └──────────────┘                    │
│         │                     │                             │
│         │                     │                             │
│         ▼                     ▼                             │
│  ┌──────────────────────────────────────┐                  │
│  │     Code Generation Pipeline         │                  │
│  │  (Tools, Tests, Documentation)       │                  │
│  └──────────────────────────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Contract Structure

### YAML Format

```yaml
contract_id: "unique_id"
name: "Human Readable Name"
description: "Detailed description"
version: "1.0.0"
tags:
  - tag1
  - tag2
author: "Author Name"
created_at: "2025-01-17"

rules:
  - rule_id: "RULE-001"
    name: "Rule Name"
    description: "What this rule enforces"
    rule_type: "structural"  # structural, behavioral, library, metric, pattern, documentation
    severity: "error"  # error, warning, info
    pattern: "regex_pattern"  # For pattern matching
    required: true  # true = must be present, false = must be absent
    max_value: 50  # For metric rules
    min_value: 1   # For metric rules
    applies_to:  # Where this rule applies
      - "function"
      - "class"
      - "module"
    exceptions:  # Patterns to exclude
      - "test_*"
      - "_*"
    validator: "custom_validator_name"  # Name of custom validator
    validator_config:  # Configuration for validator
      key: value
```

## Built-in Validators

### 1. Logging Validator (`has_logging`)

Ensures code has proper logging:

```python
validator: "has_logging"
validator_config:
  min_calls: 1  # Minimum number of log calls required
```

**Checks:**
- Logging import present
- Logger instance created (`logger = logging.getLogger(__name__)`)
- Logging calls present

### 2. Call Tool Wrapper (`has_call_tool_wrapper`)

Ensures functions are wrapped with call_tool for monitoring:

```python
validator: "has_call_tool_wrapper"
validator_config:
  skip_private: true  # Skip private functions (_*)
```

**Checks:**
- `call_tool()` at start of function
- `call_tool()` at end of function

### 3. Function Length (`max_function_length`)

Limits function length to encourage refactoring:

```python
validator: "max_function_length"
max_value: 50
validator_config:
  max_lines: 50
```

### 4. Cyclomatic Complexity (`cyclomatic_complexity`)

Limits function complexity:

```python
validator: "cyclomatic_complexity"
max_value: 10
validator_config:
  max_complexity: 10
```

### 5. Docstrings (`has_docstring`)

Requires documentation:

```python
validator: "has_docstring"
validator_config:
  require_module_docstring: true
  skip_private: true
```

### 6. Type Hints (`has_type_hints`)

Requires type annotations:

```python
validator: "has_type_hints"
validator_config:
  require_return_type: true
  require_param_types: true
  skip_private: true
```

### 7. Library Rules (`forbidden_library`, `required_import`)

Controls library usage:

```python
# Forbidden library
rule_type: "library"
pattern: "^pickle$"
required: false  # Must NOT be present

# Required library
rule_type: "library"
pattern: "^logging$"
required: true  # Must be present
```

## Example Contracts

### Enterprise Logging Contract

Ensures comprehensive logging for compliance:

```yaml
contract_id: "enterprise_logging"
name: "Enterprise Logging Requirements"
rules:
  - rule_id: "LOG-001"
    name: "Logging Import Required"
    rule_type: "library"
    severity: "error"
    pattern: "^logging$"
    required: true

  - rule_id: "LOG-002"
    name: "Logger Instance Required"
    rule_type: "structural"
    severity: "error"
    validator: "has_logging"
```

**Use Case:** Company requires all code to have logging for auditing and debugging.

### Call Tool Wrapper Contract

Ensures operation tracking:

```yaml
contract_id: "call_tool_wrapper"
name: "Call Tool Wrapper Requirements"
rules:
  - rule_id: "TOOL-001"
    name: "Call Tool Wrapper Required"
    rule_type: "structural"
    severity: "error"
    validator: "has_call_tool_wrapper"
    validator_config:
      skip_private: true
```

**Use Case:** Track all tool operations for performance monitoring and debugging.

### Code Quality Contract

General maintainability standards:

```yaml
contract_id: "code_quality"
name: "Code Quality Standards"
rules:
  - rule_id: "QUAL-001"
    name: "Maximum Function Length"
    rule_type: "metric"
    severity: "warning"
    validator: "max_function_length"
    max_value: 50

  - rule_id: "QUAL-002"
    name: "Complexity Limit"
    rule_type: "metric"
    severity: "warning"
    validator: "cyclomatic_complexity"
    max_value: 10
```

**Use Case:** Maintain code quality by limiting function size and complexity.

### Library Restrictions Contract

Security and dependency management:

```yaml
contract_id: "library_restrictions"
name: "Library Usage Restrictions"
rules:
  - rule_id: "LIB-001"
    name: "No Eval or Exec"
    rule_type: "pattern"
    severity: "error"
    pattern: '\b(eval|exec)\s*\('
    required: false  # Must NOT be present

  - rule_id: "LIB-004"
    name: "Import Placeholder Pattern"
    description: "Use try/except with AUTO-INSTALL comment for pip installs"
    rule_type: "pattern"
    severity: "info"
    pattern: '# AUTO-INSTALL:'
```

**Use Case:** Prevent security issues and manage dependencies transparently.

## Usage

### 1. Command Line Tool

Validate code against a contract:

```bash
# Using contract ID (loads from contracts/ directory)
python -c "..." --contract enterprise_logging --code-file mycode.py

# Using contract file path
python -c "..." --contract contracts/code_quality.yaml --code-file mycode.py

# Output formats
python -c "..." --contract ... --code-file ... --format json
python -c "..." --contract ... --code-file ... --format markdown
python -c "..." --contract ... --code-file ... --format text
```

### 2. Python API

```python
from pathlib import Path
from src.code_contract import ContractLoader
from src.contract_validator import ContractValidator

# Load contracts
loader = ContractLoader(Path("contracts"))
loader.load_all_contracts()

# Get specific contract
contract = loader.get_contract("enterprise_logging")

# Load code
with open("mycode.py") as f:
    code = f.read()

# Validate
validator = ContractValidator()
report = validator.validate(code, contract, "mycode.py")

# Check compliance
if report.is_compliant:
    print("✅ Code is compliant!")
else:
    print(f"❌ Code has {report.error_count} errors")
    for violation in report.violations:
        print(violation)

# Generate report
print(report.to_markdown())
```

### 3. Integration with Code Generation

```python
from src.tools_manager import ToolsManager
from src.code_contract import ContractLoader
from src.contract_validator import ContractValidator

def generate_and_validate(tool_spec, contracts_to_apply):
    # Generate code
    tools_mgr = ToolsManager()
    generated_code = tools_mgr.generate_tool(tool_spec)

    # Validate against contracts
    loader = ContractLoader(Path("contracts"))
    loader.load_all_contracts()

    validator = ContractValidator()

    all_violations = []
    for contract_id in contracts_to_apply:
        contract = loader.get_contract(contract_id)
        report = validator.validate(generated_code, contract)
        all_violations.extend(report.violations)

    if all_violations:
        # Fix or reject code
        print("Contract violations found:")
        for v in all_violations:
            print(f"  - {v}")
        return None

    return generated_code
```

### 4. Test Generation from Contracts

```python
def generate_contract_tests(contract, code_path):
    """Generate pytest tests from contract rules."""
    validator = ContractValidator()

    with open(code_path) as f:
        code = f.read()

    report = validator.validate(code, contract, code_path)

    # Generate test cases
    test_code = [
        "import pytest",
        "",
        f"def test_{contract.contract_id}_compliance():",
        f'    """Test compliance with {contract.name}."""',
    ]

    for rule in contract.rules:
        test_code.append(f"    # Test: {rule.name}")
        if rule in report.passed_rules:
            test_code.append(f"    assert True  # {rule.rule_id} passed")
        else:
            test_code.append(f"    # FIXME: {rule.rule_id} failed")

    return "\n".join(test_code)
```

## Generic Import Placeholder

For transparent pip installs, use this pattern:

```python
# Standard import with auto-install fallback
try:
    import requests
except ImportError:
    # AUTO-INSTALL: requests
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests
```

This pattern:
- Tries to import the package
- If missing, automatically installs it
- Re-imports after installation
- Uses `# AUTO-INSTALL:` marker for detection

## Custom Validators

Create custom validators for specific requirements:

```python
from src.contract_validator import ContractValidator

validator = ContractValidator()

def validate_custom_rule(code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
    """Custom validator implementation."""
    violations = []

    # Your validation logic here
    if not meets_requirement(code):
        violations.append(ContractViolation(
            rule=rule,
            location=code_path,
            message="Custom requirement not met",
            suggestion="How to fix it"
        ))

    return violations

# Register custom validator
validator.register_validator("my_custom_validator", validate_custom_rule)

# Use in contract
rule = ContractRule(
    rule_id="CUSTOM-001",
    name="Custom Rule",
    description="Custom validation",
    rule_type=ContractType.STRUCTURAL,
    severity=ContractSeverity.ERROR,
    validator="my_custom_validator"
)
```

## Compliance Reports

### Text Format

```
✅ COMPLIANT / ❌ NON-COMPLIANT
Contract: Enterprise Logging Requirements
Score: 85.0%
Errors: 1, Warnings: 2, Info: 0
```

### Markdown Format

```markdown
# Code Contract Compliance Report

**Contract:** Enterprise Logging Requirements (v1.0.0)
**Code Path:** mycode.py
**Compliance Score:** 85.0%

## Summary

- ❌ Errors: 1
- ⚠️  Warnings: 2
- ℹ️  Info: 0
- ✅ Passed: 10

## Violations

### ❌ Logger Instance Required

- **Rule ID:** LOG-002
- **Severity:** ERROR
- **Location:** mycode.py:15
- **Message:** No logger instance created
- **Suggestion:** Add: logger = logging.getLogger(__name__)
```

### JSON Format

```json
{
  "contract_id": "enterprise_logging",
  "code_path": "mycode.py",
  "is_compliant": false,
  "compliance_score": 0.85,
  "error_count": 1,
  "warning_count": 2,
  "info_count": 0,
  "violations": [
    {
      "rule_id": "LOG-002",
      "rule_name": "Logger Instance Required",
      "severity": "error",
      "location": "mycode.py",
      "line_number": 15,
      "message": "No logger instance created",
      "suggestion": "Add: logger = logging.getLogger(__name__)"
    }
  ],
  "passed_rules": ["LOG-001", "LOG-003", ...]
}
```

## Best Practices

### 1. Start with Essential Rules

Begin with critical requirements (logging, security) before adding nice-to-haves.

### 2. Use Appropriate Severity

- **ERROR**: Must be fixed before deployment
- **WARNING**: Should be fixed, may be reviewed
- **INFO**: Nice to have, informational only

### 3. Combine Contracts

Apply multiple contracts to cover different aspects:

```python
contracts_to_apply = [
    "enterprise_logging",
    "call_tool_wrapper",
    "code_quality",
    "library_restrictions"
]
```

### 4. Document Exceptions

Clearly document why certain patterns are excluded:

```yaml
exceptions:
  - "test_*"  # Test files don't need logging
  - "_internal_*"  # Internal methods are private
```

### 5. Evolve Contracts Over Time

Version your contracts and evolve them as standards change:

```yaml
version: "2.0.0"  # Updated standards
```

## Integration Points

### With Code Generation

1. **Pre-generation**: Check tool specs against contracts
2. **During generation**: Apply contract rules to templates
3. **Post-generation**: Validate generated code
4. **Before commit**: Final contract validation

### With Testing

1. **Generate tests** from contract rules
2. **Contract regression tests** ensure contracts are enforced
3. **CI/CD integration** for automatic validation

### With Documentation

1. **Include contract compliance** in generated docs
2. **Document violations** with suggestions
3. **Track compliance trends** over time

## Troubleshooting

### Contract Not Loading

- Check YAML syntax
- Verify file location in `contracts/` directory
- Check contract_id matches filename

### Validation Errors

- Review rule configuration
- Check validator name spelling
- Verify custom validators are registered

### False Positives

- Adjust pattern matching
- Use exceptions list
- Fine-tune validator_config

## Summary

The Code Contracts system provides:

- ✅ **Standardization** - Enforce organizational standards
- ✅ **Quality** - Maintain code quality automatically
- ✅ **Compliance** - Meet regulatory requirements
- ✅ **Documentation** - Clear compliance reports
- ✅ **Extensibility** - Custom validators for specific needs
- ✅ **Integration** - Works with existing tools and workflows

Use contracts to ensure generated code meets your organization's requirements for logging, structure, security, and quality.
