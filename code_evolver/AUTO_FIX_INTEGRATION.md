# Auto-Fix Integration Guide

## Overview

Static validators can now **automatically fix** common issues instead of just reporting them.

## How Auto-Fix Works

### 1. Validator Detects Issue

```bash
$ python tools/executable/node_runtime_import_validator.py main.py
FAIL: Wrong import order!
  node_runtime import at line 2
  sys.path.insert() at line 8
```

### 2. Auto-Fix Applies Fix

```bash
$ python tools/executable/node_runtime_import_validator.py main.py --fix
FIXED: Moved node_runtime import from line 2 to after line 8
```

### 3. Validation Passes

```bash
$ python tools/executable/node_runtime_import_validator.py main.py
OK: Import order is correct (path setup at line 7, import at line 8)
```

---

## Integration with Code Evolver

### Current Workflow (Without Auto-Fix)

```
1. Generate code                      → 5s, $0.01
2. Test code                          → 1s
3. FAIL: ModuleNotFoundError
4. Escalate to LLM for fix           → 5s, $0.01
5. Regenerate code                    → 5s, $0.01
6. Test code                          → 1s
7. SUCCESS

Total: 17s, $0.03
```

### New Workflow (With Static Auto-Fix)

```
1. Generate code                      → 5s, $0.01
2. Run static validators with --fix   → 0.1s, $0.00  ← AUTO-FIX!
3. Test code                          → 1s
4. SUCCESS

Total: 6.1s, $0.01
```

**Savings:** 64% faster, 67% cheaper! 🎉

---

## Implementing Auto-Fix in chat_cli.py

### Option 1: Replace Inline Fix with Static Validator

**Current (Inline Fix):**
```python
# chat_cli.py lines 2276-2319
if needs_call_tool:
    lines = code.split('\n')
    # ... manual reordering logic ...
    code = '\n'.join(lines)
```

**New (Static Validator):**
```python
# After generating code, before testing
def apply_static_fixes(self, code_file: str) -> bool:
    """
    Run static validators with auto-fix enabled.

    Returns:
        True if all fixes applied successfully
    """
    import subprocess

    # List of validators that support auto-fix
    validators = [
        'tools/executable/node_runtime_import_validator.py',
        # Add more auto-fix validators here
    ]

    for validator in validators:
        result = subprocess.run(
            ['python', validator, code_file, '--fix'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            if 'FIXED' in result.stdout:
                console.print(f"[green]{result.stdout.strip()}[/green]")
        else:
            console.print(f"[yellow]Auto-fix failed: {result.stdout}[/yellow]")
            return False

    return True
```

**Usage:**
```python
# In generate_node_code():
code_file = self.runner.save_code(node_id, code)

# Apply static fixes before testing
if self.apply_static_fixes(code_file):
    console.print("[green]✓ Static fixes applied[/green]")

# Now run tests
stdout, stderr, metrics = self.runner.run_node(node_id, test_input)
```

---

### Option 2: Add to Validation Pipeline

**Before Testing:**
```python
def validate_and_fix_code(self, node_id: str) -> Tuple[bool, List[str]]:
    """
    Run all static validators and auto-fix issues.

    Returns:
        (all_passed, error_messages)
    """
    code_file = self.runner.get_node_main_path(node_id)
    errors = []

    # 1. Syntax check (no auto-fix)
    if not self._check_syntax(code_file):
        errors.append("Syntax error")
        return False, errors

    # 2. Import order (auto-fix enabled)
    result = subprocess.run(
        ['python', 'tools/executable/node_runtime_import_validator.py',
         code_file, '--fix'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 and 'FIXED' not in result.stdout:
        errors.append(f"Import order: {result.stdout}")

    # 3. JSON output (auto-fix could add json.dumps wrapper)
    # ... more validators ...

    return len(errors) == 0, errors
```

**Integration:**
```python
# In generate_node_code():
code_file = self.runner.save_code(node_id, code)

# Validate and auto-fix
passed, errors = self.validate_and_fix_code(node_id)

if not passed:
    console.print("[yellow]Static validation issues found:[/yellow]")
    for error in errors:
        console.print(f"  • {error}")

    # Only escalate to LLM if static fixes can't handle it
    if self._should_escalate(errors):
        return self._escalate_to_llm(node_id, errors)

# Tests
stdout, stderr, metrics = self.runner.run_node(node_id, test_input)
```

---

## Auto-Fix Capabilities

### ✅ Node Runtime Import Validator

**Can Auto-Fix:**
- ✅ Wrong import order (moves import after path setup)

**Cannot Auto-Fix:**
- ❌ Missing path setup (too complex, needs LLM)

**Example:**
```bash
# Before
from node_runtime import call_tool
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# After --fix
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool
```

---

### 🔄 Future Auto-Fix Validators

#### JSON Output Auto-Fixer

**Can Auto-Fix:**
- Add `import json` if missing
- Wrap return value with `json.dumps()`
- Wrap print with `json.dumps()`

**Example:**
```python
# Before
def main():
    result = {'data': 42}
    print(result)

# After --fix
import json

def main():
    result = {'data': 42}
    print(json.dumps(result))
```

---

#### Import Organizer (isort)

**Already Supported:**
```bash
$ isort --check-only main.py  # Check mode
$ isort main.py               # Fix mode
```

**Integration:**
```yaml
# tools/executable/isort_import_checker.yaml
auto_fix:
  enabled: true
  command: "isort"
  args: ["{source_file}"]  # Auto-fixes in-place
```

---

#### Missing Import Auto-Fixer

**Can Auto-Fix:**
- Add missing stdlib imports
- Add common third-party imports

**Example:**
```python
# Before
result = json.dumps({'data': 42})  # F821: undefined name 'json'

# After --fix
import json

result = json.dumps({'data': 42})
```

**Implementation:**
```python
# tools/executable/missing_import_fixer.py
COMMON_IMPORTS = {
    'json': 'import json',
    'sys': 'import sys',
    'Path': 'from pathlib import Path',
    'subprocess': 'import subprocess',
}

def fix_missing_imports(code: str, undefined_names: List[str]) -> str:
    for name in undefined_names:
        if name in COMMON_IMPORTS:
            code = COMMON_IMPORTS[name] + '\n' + code
    return code
```

---

## Best Practices

### 1. **Run Auto-Fix Before Tests**

```python
# ✅ Good: Fix issues before expensive test run
self.apply_static_fixes(code_file)
self.runner.run_node(node_id, test_input)

# ❌ Bad: Waste time testing broken code
self.runner.run_node(node_id, test_input)
self.apply_static_fixes(code_file)  # Too late!
```

### 2. **Fail Fast on Unfixable Issues**

```python
# ✅ Good: Only escalate if auto-fix can't handle it
if not self.apply_static_fixes(code_file):
    # Auto-fix failed, escalate to LLM
    return self._escalate_to_llm(node_id, errors)

# ❌ Bad: Always escalate, even for simple fixes
if validation_failed:
    return self._escalate_to_llm(node_id, errors)
```

### 3. **Log All Fixes for Learning**

```python
# Track what was auto-fixed for telemetry
fixes_applied = []

for validator in validators:
    result = subprocess.run([validator, code_file, '--fix'], ...)
    if 'FIXED' in result.stdout:
        fixes_applied.append(validator)

# Store in metrics
self.registry.save_metrics(node_id, {
    'auto_fixes_applied': fixes_applied,
    'llm_escalation_avoided': len(fixes_applied) > 0
})
```

### 4. **Preserve Code if Auto-Fix Fails**

```python
# ✅ Good: Keep backup before auto-fix
backup = Path(code_file).read_text()
try:
    self.apply_static_fixes(code_file)
except Exception as e:
    # Restore backup if fix fails
    Path(code_file).write_text(backup)
    logger.error(f"Auto-fix failed: {e}")

# ❌ Bad: No backup, broken file if fix fails
self.apply_static_fixes(code_file)
```

---

## Configuration

### Enable/Disable Auto-Fix Globally

**config.yaml:**
```yaml
code_generation:
  auto_fix:
    enabled: true
    validators:
      - node_runtime_import_validator
      - isort
      # - missing_import_fixer  # Commented out = disabled
```

### Per-Validator Configuration

**tools/executable/node_runtime_import_validator.yaml:**
```yaml
auto_fix:
  enabled: true  # Can be disabled per-validator
  safe: true     # Only fix if 100% safe
  backup: true   # Create .bak before fixing
```

---

## Metrics & Monitoring

### Track Auto-Fix Success Rate

```python
# In registry.py
def record_auto_fix(self, node_id: str, validator: str, success: bool):
    """Record auto-fix attempt for metrics."""
    metrics = {
        'validator': validator,
        'auto_fix_success': success,
        'timestamp': time.time()
    }
    self.save_auto_fix_metrics(node_id, metrics)
```

### Dashboard Metrics

```
Auto-Fix Statistics (Last 100 Generations):
  ✓ Import Order Fixed:       45 / 100 (45%)
  ✓ JSON Output Fixed:         12 / 100 (12%)
  ✓ Missing Imports Fixed:     8 / 100 (8%)
  ───────────────────────────────────────────
  Total Auto-Fixes:           65 / 100 (65%)
  LLM Escalations Avoided:    65 / 100 (65%)
  Cost Savings:               $0.65 (65 × $0.01)
  Time Savings:               325s (65 × 5s)
```

---

## Testing Auto-Fix

### Unit Tests

```python
# tests/test_auto_fix.py
def test_node_runtime_import_fixer():
    code = """
from node_runtime import call_tool
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
"""

    fixed = fix_import_order(code)

    assert 'sys.path.insert' in fixed
    assert fixed.index('sys.path.insert') < fixed.index('from node_runtime')
```

### Integration Tests

```python
# tests/test_auto_fix_integration.py
def test_full_auto_fix_pipeline():
    # Generate code with known issue
    code = generate_code_with_wrong_imports()

    # Apply auto-fix
    apply_static_fixes(code_file)

    # Verify fix
    validation = validate_file(code_file)
    assert validation.passed
```

---

## Summary

**Auto-Fix Benefits:**
- ✅ 64% faster (6s vs 17s)
- ✅ 67% cheaper ($0.01 vs $0.03)
- ✅ 100% deterministic
- ✅ Zero LLM calls for simple issues

**When to Use:**
- ✅ Import order issues
- ✅ Missing common imports
- ✅ JSON output formatting
- ✅ Code style (isort, black)

**When NOT to Use:**
- ❌ Complex logic errors
- ❌ Algorithm problems
- ❌ Semantic issues
- ❌ Ambiguous fixes

**Golden Rule:** If it can be fixed with a regex or AST transformation → Auto-fix. If it needs understanding → LLM.

---

**Status:** ✅ Auto-fix implemented for node_runtime import validator!

Next validators to add auto-fix:
- [ ] JSON output fixer
- [ ] Missing import fixer
- [ ] Docstring fixer
- [ ] Type hint fixer
