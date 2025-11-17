# Static Analysis Tools Guide

Complete reference for the integrated static analysis validators that automatically check generated code for quality, security, and correctness issues.

## Table of Contents

1. [Overview](#overview)
2. [Validation Pipeline](#validation-pipeline)
3. [Individual Validators](#individual-validators)
4. [Configuration](#configuration)
5. [Integration Examples](#integration-examples)
6. [Escalation Workflow](#escalation-workflow)
7. [Custom Validators](#custom-validators)

---

## Overview

mostlylucid DiSE includes a comprehensive static analysis system that runs multiple validators on generated code. Each validator checks for specific issues and can auto-fix certain problems.

### Built-in Validators

| Validator | Priority | Tool | Auto-Fix | Purpose |
|-----------|----------|------|----------|---------|
| **Syntax** | 200 | AST | No | Check Python syntax validity |
| **Main Function** | 180 | AST | Yes | Ensure `main()` and `__main__` block |
| **JSON Output** | 150 | AST | No | Validate `json.dumps()` usage |
| **Stdin Usage** | 140 | AST | No | Verify `json.load(sys.stdin)` |
| **Undefined Names** | 120 | flake8 | No | Find undefined variables |
| **Import Order** | 110 | isort | Yes | Sort imports (PEP 8) |
| **Node Runtime** | 100 | AST | Yes | Fix node_runtime imports |
| **Call Tool Usage** | 90 | AST | No | Validate `call_tool()` syntax |
| **Type Checking** | 80 | mypy | No | Static type analysis |
| **Security** | 70 | bandit | No | Detect security vulnerabilities |
| **Complexity** | 60 | radon | No | Measure code complexity |

### How It Works

```
Code Generated
    ↓
Run Validators (Priority Order)
    ├─ Syntax (200)
    ├─ Main Function (180)
    ├─ JSON Output (150)
    ├─ ... more validators ...
    └─ Complexity (60)
    ↓
Collect Results
    ↓
Has Errors?
    ├─ Yes → Escalate to Stronger Model
    └─ No → Code Accepted
```

---

## Validation Pipeline

### Execution Order

Validators run in **priority order** (highest first):

1. **200**: Syntax checks (AST parsing)
2. **180**: Structure validation (main function)
3. **150**: JSON output validation
4. **140**: Stdin input validation
5. **120**: Undefined names (flake8)
6. **110**: Import ordering (isort)
7. **100**: Node runtime imports
8. **90**: Tool call validation
9. **80**: Type checking (mypy)
10. **70**: Security (bandit)
11. **60**: Complexity (radon)

### Why Priority Matters

Earlier validators catch fundamental issues before later ones run:

```python
# Without priority, this would fail at:
# - Complexity check (slow, might timeout)
# - Security check (might give false positives)
# Instead, Syntax validator catches it immediately

import json
if this is not valid:  # SyntaxError
    print("hello")
```

### Parallel Validator Execution

Independent validators can run in parallel:

```
Validator Group 1 (Sequential):
├─ Syntax (200) → Main Function (180) → JSON Output (150)
    [Must be sequential - each depends on previous]

Validator Group 2 (Can be Parallel):
├─ Undefined Names (120) ┐
├─ Import Order (110)    ├─ All run at same priority level
├─ Node Runtime (100)    ┘

Result: Faster validation with early termination
```

---

## Individual Validators

### 1. Syntax Validator (Priority 200)

**Purpose**: Verify Python syntax is valid

```python
import ast

def validate_syntax(code):
    try:
        ast.parse(code)
        return {"valid": True}
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}
```

**Detects**:
- Missing colons (`:`)
- Invalid indentation
- Unclosed brackets/parentheses
- Invalid keywords
- Malformed decorators

**Example Error**:
```
SyntaxError: invalid syntax (line 5)
    if x > 5  # Missing colon
           ^
```

**Not Auto-Fixable**: Too risky (could change meaning)

---

### 2. Main Function Validator (Priority 180)

**Purpose**: Ensure code has proper entry point structure

**Requirements**:
1. Must have a `main()` function
2. Must have `if __name__ == "__main__":` block
3. Block must call `main()`

```python
# ✓ Valid structure
def main():
    # ... code ...

if __name__ == "__main__":
    main()

# ✗ Invalid - missing __main__ block
def main():
    # ... code ...
```

**Why Required**:
- Makes code testable
- Prevents accidental execution of imports
- Enables safe module reuse

**Auto-Fixable**: Yes - adds missing block

```yaml
# Before
def main():
    print("Hello")

# After (auto-fixed)
def main():
    print("Hello")

if __name__ == "__main__":
    main()
```

---

### 3. JSON Output Validator (Priority 150)

**Purpose**: Ensure output is valid JSON using `json.dumps()`

**Requirements**:
- Must use `json.dumps()` for output
- Output must be printable JSON
- Common pattern: `print(json.dumps({"result": ...}))`

```python
# ✓ Valid
print(json.dumps({"result": value}))

# ✗ Invalid - plain print
print(f"Result: {value}")

# ✗ Invalid - returns instead of prints
return {"result": value}
```

**Why Required**:
- Enables machine-readable output
- Allows JSON parsing in pipelines
- Supports structured workflows

---

### 4. Stdin Usage Validator (Priority 140)

**Purpose**: Verify input is read from stdin using JSON

**Requirements**:
- Must use `json.load(sys.stdin)` for input
- Input should be a JSON object

```python
# ✓ Valid
import json
import sys

def main():
    input_data = json.load(sys.stdin)
    # ... use input_data ...

# ✗ Invalid - uses input()
value = input("Enter value: ")

# ✗ Invalid - uses sys.argv
import sys
value = sys.argv[1]
```

**Why Required**:
- Standardizes input handling
- Works with JSON pipelines
- Enables non-interactive execution

---

### 5. Undefined Names Validator (Priority 120)

**Tool**: flake8

**Purpose**: Find undefined variables and unused imports

**Checks**:
- **F821**: Undefined name (variable used but not defined)
- **F401**: Imported but unused
- **F811**: Redefined while unused
- **E999**: Syntax errors

```python
# ✗ F821 - undefined name
print(undefined_variable)

# ✗ F401 - unused import
import json
print("hello")

# ✓ Both fixed
import json
data = json.dumps({"hello": "world"})
print(data)
```

**Auto-Fixable**: Partially (can remove unused imports)

**Configuration**:
```yaml
static_analysis:
  validators:
    - name: "undefined_names"
      tool: "flake8"
      args: ["--select=F821,F401,F811,E999"]
```

---

### 6. Import Order Validator (Priority 110)

**Tool**: isort

**Purpose**: Ensure imports follow PEP 8 conventions

**Standard Order**:
1. Standard library imports (sys, os, json)
2. Third-party imports (numpy, requests)
3. Local imports (from . import module)

```python
# ✗ Wrong order
from mymodule import helper
import json
import sys

# ✓ Correct order (after auto-fix)
import json
import sys

from mymodule import helper
```

**Benefits**:
- Consistent code style
- Easier to spot unused imports
- Better collaboration

**Auto-Fixable**: Yes - automatically reorders

**Configuration**:
```yaml
static_analysis:
  validators:
    - name: "import_order"
      tool: "isort"
      config:
        profile: "black"
        line_length: 100
```

---

### 7. Node Runtime Validator (Priority 100)

**Purpose**: Fix node_runtime import order issues

**Requirement**:
- If using `node_runtime`, must be imported correctly

```python
# ✓ Correct
import json
import sys
from node_runtime import call_tool

def main():
    result = call_tool("translator", "...")

# ✗ Wrong - tool import in wrong place
from node_runtime import call_tool
import json
import sys
```

**Auto-Fixable**: Yes - reorders node_runtime imports to correct position

**Why**:
- Ensures predictable import order
- Works with isort configuration
- Makes code more maintainable

---

### 8. Call Tool Usage Validator (Priority 90)

**Purpose**: Validate `call_tool()` function calls

**Requirements**:
- Must import `call_tool` from `node_runtime`
- Must call with correct arguments: `call_tool(tool_name, prompt)`
- Tool name must be string
- Prompt must be string

```python
# ✓ Valid usage
from node_runtime import call_tool

result = call_tool("translator", "Translate to French: Hello")
result = call_tool("validator", prompt, extra_param="value")

# ✗ Invalid - wrong import
from tools.translator import call_tool
result = call_tool(...)

# ✗ Invalid - wrong argument count
result = call_tool("translator")  # Missing prompt

# ✗ Invalid - dynamic tool name
tool = get_tool_name()
result = call_tool(tool, prompt)  # Tool name must be literal string
```

**Error Messages**:
```
Error: call_tool() argument mismatch at line 45
  Expected: call_tool(tool_name: str, prompt: str, **kwargs)
  Got: call_tool("translator")
  Fix: Add prompt parameter
```

**Not Auto-Fixable**: Too risky (would need to infer missing arguments)

---

### 9. Type Checking (Priority 80)

**Tool**: mypy

**Purpose**: Static type analysis to catch type errors

**Checks**:
- Type mismatches
- Missing type annotations
- Incompatible operations
- None handling

```python
# ✗ Type error
def greet(name: str) -> str:
    return name + 42  # Can't add str + int

# ✓ Correct
def greet(name: str) -> str:
    return f"Hello {name}"

# ✗ Missing type annotation
def process(data):  # Type of 'data' unknown
    return data.upper()

# ✓ Type-annotated
def process(data: str) -> str:
    return data.upper()
```

**Configuration** (from config.yaml):
```yaml
static_analysis:
  validators:
    - name: "type_checking"
      tool: "mypy"
      args: ["--strict"]
```

**Strict Mode** requires:
- All function parameters typed
- All return types specified
- Proper handling of Optional types

**Auto-Fixable**: No (requires developer understanding)

---

### 10. Security Scanning (Priority 70)

**Tool**: bandit

**Purpose**: Detect security vulnerabilities

**Detects**:
- Hardcoded passwords/secrets
- SQL injection risks
- Insecure cryptography
- Unsafe file operations
- Command injection vulnerabilities

```python
# ✗ Security issues
import subprocess

password = "secret123"  # B105: hardcoded password
subprocess.call("rm -rf /")  # B602: shell=True default
open("/etc/passwd", "w").write(data)  # B101: assert_used

# ✓ Secure alternatives
import secrets
import shlex

password = os.environ.get("PASSWORD")  # From environment
subprocess.call(["rm", "-rf", "/"], shell=False)  # No shell
with open("/tmp/data.txt", "w") as f:  # Safe location
    f.write(data)
```

**Common Issues**:
- Hardcoded credentials (use environment variables)
- SQL injection (use parameterized queries)
- Insecure file operations (validate paths)
- Command injection (avoid shell=True)

**Configuration**:
```yaml
static_analysis:
  validators:
    - name: "security"
      tool: "bandit"
      args: ["-ll"]  # Low confidence level
```

**Severity Levels**:
- `HIGH`: Critical security issues
- `MEDIUM`: Potential vulnerabilities
- `LOW`: Suspicious code patterns

---

### 11. Complexity Analysis (Priority 60)

**Tool**: radon

**Purpose**: Measure code complexity to ensure maintainability

**Metrics**:
- **Cyclomatic Complexity (CC)**: Number of decision branches
  - 1-5: Simple
  - 6-10: Moderate
  - 11-20: Complex
  - 20+: Very complex

- **Maintainability Index (MI)**: Overall code health (0-100)
  - 100-20: Maintainable
  - 20-10: Complex
  - 10-0: Unmaintainable

```python
# ✗ High cyclomatic complexity (many branches)
def complex_logic(a, b, c, d):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    return a + b + c + d
                else:
                    return a + b + c
            else:
                return a + b
        else:
            return a
    else:
        return 0
# CC = 5 (acceptable but complex)

# ✓ Simpler logic
def simple_logic(a, b, c, d):
    values = [x for x in [a, b, c, d] if x > 0]
    return sum(values)
# CC = 1 (simple)
```

**Configuration**:
```yaml
static_analysis:
  validators:
    - name: "complexity"
      tool: "radon"
      config:
        max_cyclomatic: 10
        max_maintainability: 50
```

**Why It Matters**:
- Complex code is harder to test
- Higher bug rates
- Difficult to maintain
- Refactoring opportunities

---

## Configuration

### Enable/Disable Validators

```yaml
# config.yaml
static_analysis:
  enabled: true

  validators:
    - name: "syntax"
      enabled: true
      priority: 200

    - name: "undefined_names"
      enabled: true
      priority: 120

    - name: "complexity"
      enabled: false  # Disable complexity checks
      priority: 60
```

### Customize Thresholds

```yaml
static_analysis:
  validators:
    - name: "complexity"
      priority: 60
      config:
        max_cyclomatic: 15  # More lenient
        max_maintainability: 40

    - name: "type_checking"
      priority: 80
      config:
        args: []  # Disable strict mode
```

### Per-Validator Timeouts

```yaml
static_analysis:
  # Global timeout for all validators
  validator_timeout: 30

  validators:
    - name: "type_checking"
      priority: 80
      timeout: 60  # Mypy needs more time

    - name: "complexity"
      priority: 60
      timeout: 20  # Faster check
```

---

## Integration Examples

### Example 1: Code Generation with Full Validation

```python
from src.code_generator import CodeGenerator
from src.static_analysis import run_static_analysis

def generate_and_validate_code(prompt):
    """
    Generate code and validate with all checks
    """
    # Step 1: Generate code
    generator = CodeGenerator()
    code = generator.generate(prompt)

    # Step 2: Run static analysis
    results = run_static_analysis(code)

    # Step 3: Check results
    if results["passed"]:
        print("✓ Code passed all checks")
        return code
    else:
        print("✗ Validation errors found:")
        for error in results["errors"]:
            print(f"  - {error['validator']}: {error['message']}")
        return None
```

### Example 2: Escalation on Validation Failure

```python
def generate_with_escalation(prompt, max_escalation=3):
    """
    Generate code, validate, and escalate if validation fails
    """
    for attempt in range(max_escalation):
        # Generate code
        code = generator.generate(prompt, temperature=0.1 + (attempt * 0.2))

        # Validate
        results = run_static_analysis(code)

        if results["passed"]:
            return code

        # Show errors
        print(f"Attempt {attempt + 1} failed:")
        for error in results["errors"]:
            print(f"  - {error['validator']}: {error['message']}")

        if attempt < max_escalation - 1:
            # Escalate to more powerful model
            print(f"Escalating to tier {attempt + 2}...")

    raise Exception(f"Failed to generate valid code after {max_escalation} attempts")
```

### Example 3: Auto-Fix Enabled

```python
def generate_with_auto_fix(prompt):
    """
    Generate code and auto-fix common issues
    """
    code = generator.generate(prompt)

    # Run validators with auto-fix enabled
    results = run_static_analysis(
        code,
        auto_fix=True
    )

    if results["auto_fixed"]:
        print("Auto-fixed issues:")
        for fix in results["fixes"]:
            print(f"  - {fix['validator']}: {fix['description']}")

    if results["passed"]:
        return results["code"]  # Return fixed code
    else:
        print("Remaining errors that need manual fixing:")
        for error in results["errors"]:
            print(f"  - {error['message']}")
```

---

## Escalation Workflow

When validation fails, the system automatically escalates:

```
Code Generated (Temperature 0.1)
    ↓
Validate
    ├─ ✓ Pass → Accept
    └─ ✗ Fail → Escalate

Escalation Level 1 (Temperature 0.3)
    ├─ Show original errors
    ├─ Ask for fixes: "Fix these validation errors: ..."
    └─ Regenerate → Validate

Escalation Level 2 (Temperature 0.5)
    ├─ Add debugging hints
    ├─ More specific instructions
    └─ Regenerate → Validate

Escalation Level 3 (Temperature 0.7)
    ├─ Use more powerful model (GPT-4)
    ├─ Provide full context
    └─ Regenerate → Validate

Escalation Level 4 (God-mode)
    ├─ Use best available model
    ├─ Maximum temperature (0.9)
    └─ Final attempt
```

**Example Escalation Dialog**:

```
Attempt 1: Generate with codellama (temperature 0.1)
  ✗ Fails: Undefined variable 'value'

Attempt 2: Escalate - Generate with codellama (temperature 0.3)
  Prompt: "Fix these validation errors: name 'value' is not defined (line 15)"
  ✗ Fails: JSON output validation

Attempt 3: Escalate - Generate with GPT-4 (temperature 0.5)
  Prompt: "Generate code that: [original] ... Validation errors: JSON output not found ..."
  ✓ Passes all checks!
```

---

## Custom Validators

### Creating a Custom Validator

```python
from src.static_analysis import BaseValidator

class CustomValidator(BaseValidator):
    """
    Custom validator for specific requirements
    """

    def __init__(self):
        super().__init__(
            name="custom_check",
            priority=105,
            auto_fixable=False
        )

    def validate(self, code: str) -> dict:
        """
        Validate code against custom rules

        Returns:
            {
                "passed": bool,
                "errors": [{"line": int, "message": str}],
                "warnings": list
            }
        """
        errors = []

        # Example: Check for specific pattern
        if "eval(" in code:
            errors.append({
                "line": code.index("eval("),
                "message": "eval() is not allowed"
            })

        return {
            "passed": len(errors) == 0,
            "errors": errors
        }
```

### Registering Custom Validator

```yaml
# config.yaml
static_analysis:
  validators:
    - name: "custom_check"
      enabled: true
      priority: 105
      class: "my_validators.CustomValidator"
```

---

## Performance Tips

### 1. Disable Slow Validators When Not Needed

```yaml
static_analysis:
  validators:
    - name: "type_checking"  # Slowest
      enabled: false
      priority: 80

    - name: "complexity"     # Medium
      enabled: true
      priority: 60
```

### 2. Use Priority to Stop Early

```yaml
# With early validation failures, later validators won't run
static_analysis:
  validators:
    - name: "syntax"         # Runs first, fails fast
      priority: 200

    - name: "complexity"     # Only runs if syntax passes
      priority: 60
```

### 3. Adjust Timeouts

```yaml
static_analysis:
  validator_timeout: 10  # Global timeout

  validators:
    - name: "type_checking"
      timeout: 60  # Override for slow tool
```

---

## See Also

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Configuration options
- [TOOL_INVOCATION_GUIDE.md](TOOL_INVOCATION_GUIDE.md) - Using call_tool()
- [README.md](../README.md) - System overview
