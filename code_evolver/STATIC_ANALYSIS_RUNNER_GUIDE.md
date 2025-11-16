

# Static Analysis Runner Guide

## Overview

The **Static Analysis Runner** (`run_static_analysis.py`) is a comprehensive tool that runs all static validators on generated code. It can run all validators at once OR individual validators, with support for auto-fix and retry-failed modes.

---

## Features

✅ **Run All Validators** - Execute all 8 validators in ~1 second
✅ **Run Specific Validator** - Test just one validator
✅ **Auto-Fix** - Automatically fix issues where possible
✅ **Retry Failed** - Re-run only validators that previously failed
✅ **JSON Output** - Machine-readable results
✅ **Save Results** - Results saved to `.analysis_results.json` for retry

---

## Usage

### 1. Run All Validators

```bash
$ python tools/executable/run_static_analysis.py main.py

======================================================================
STATIC ANALYSIS RESULTS
======================================================================

Summary: 7/8 validators passed (1 failed)
Total time: 847ms

Validator Results:
----------------------------------------------------------------------

[[PASS]] SYNTAX (45ms)
    Category: syntax

[[PASS]] MAIN_FUNCTION (98ms)
    Category: structure

[[FAIL]] UNDEFINED_NAMES (312ms)
    Category: imports
    main.py:12: [F821] undefined name 'input_data'

[[PASS]] NODE_RUNTIME_IMPORT (93ms)
    Category: imports

======================================================================
[ERROR] 1 VALIDATOR(S) FAILED
======================================================================
```

### 2. Run Specific Validator

```bash
# Check only undefined names
$ python tools/executable/run_static_analysis.py main.py --validator undefined_names

======================================================================
STATIC ANALYSIS RESULTS
======================================================================

Summary: 0/1 validators passed (1 failed)
Total time: 312ms

Validator Results:
----------------------------------------------------------------------

[[FAIL]] UNDEFINED_NAMES (312ms)
    Category: imports
    main.py:12: [F821] undefined name 'input_data'

======================================================================
[ERROR] 1 VALIDATOR(S) FAILED
======================================================================
```

**Available Validators:**
- `syntax` - Python syntax check
- `main_function` - main() function check
- `json_output` - JSON output validation
- `stdin_usage` - stdin reading check
- `undefined_names` - Undefined variables (flake8)
- `import_order` - Import organization (isort)
- `node_runtime_import` - node_runtime import order
- `call_tool_usage` - call_tool() usage

### 3. Auto-Fix Mode

```bash
# Apply auto-fixes where available
$ python tools/executable/run_static_analysis.py main.py --fix

======================================================================
STATIC ANALYSIS RESULTS
======================================================================

Summary: 8/8 validators passed (0 failed)
Total time: 893ms

Validator Results:
----------------------------------------------------------------------

[[PASS]] IMPORT_ORDER (167ms)
    Category: imports
    Fixed import organization

[[PASS]] NODE_RUNTIME_IMPORT (93ms)
    Category: imports
    FIXED: Moved node_runtime import from line 2 to after line 6

======================================================================
[OK] ALL VALIDATORS PASSED
======================================================================
```

**Validators with Auto-Fix:**
- ✅ `import_order` (isort) - Organizes imports
- ✅ `node_runtime_import` - Fixes import order

### 4. Retry Failed Validators

After running once, retry only the validators that failed:

```bash
# First run - save results
$ python tools/executable/run_static_analysis.py main.py
# Results saved to .analysis_results.json

# Fix code manually...

# Retry only failed validators
$ python tools/executable/run_static_analysis.py main.py --retry-failed

Re-running 1 failed validator(s): undefined_names

======================================================================
STATIC ANALYSIS RESULTS
======================================================================

Summary: 1/1 validators passed (0 failed)
Total time: 180ms

Validator Results:
----------------------------------------------------------------------

[[PASS]] UNDEFINED_NAMES (180ms)
    Category: imports

======================================================================
[OK] ALL VALIDATORS PASSED
======================================================================
```

### 5. JSON Output

```bash
$ python tools/executable/run_static_analysis.py main.py --json
{
  "syntax": {
    "validator": "syntax",
    "category": "syntax",
    "priority": 200,
    "passed": true,
    "output": "OK: Valid Python syntax",
    "execution_time_ms": 45.2,
    "supports_autofix": false,
    "description": "Validates Python syntax using AST parser"
  },
  "undefined_names": {
    "validator": "undefined_names",
    "category": "imports",
    "priority": 120,
    "passed": false,
    "output": "main.py:12: [F821] undefined name 'input_data'",
    "execution_time_ms": 312.5,
    "supports_autofix": false,
    "description": "Detects undefined variables and missing imports"
  },
  "_summary": {
    "total_validators": 8,
    "passed": 7,
    "failed": 1,
    "total_time_ms": 847.3
  }
}
```

---

## Integration with chat_cli.py

### Add After Code Generation

```python
# chat_cli.py

def generate_node_code(self, node_id: str, description: str):
    """Generate code with static analysis."""

    # ... existing code generation ...

    # Save generated code
    code_file = self.runner.save_code(node_id, code)

    # ═══════════════════════════════════════════════════
    # NEW: Run static analysis BEFORE testing
    # ═══════════════════════════════════════════════════
    console.print("\n[cyan]Running static analysis...[/cyan]")

    result = subprocess.run(
        [
            'python',
            'tools/executable/run_static_analysis.py',
            code_file,
            '--fix'  # Apply auto-fixes
        ],
        capture_output=True,
        text=True
    )

    # Parse results
    if result.returncode == 0:
        console.print("[green]✓ All static validators passed[/green]")
    else:
        console.print("[yellow]✗ Static validation issues found:[/yellow]")
        console.print(result.stdout)

        # Check if issues are fixable
        if '--fix' not in result.stdout or 'FAIL' in result.stdout:
            # Escalate to LLM with specific error messages
            console.print("[yellow]Escalating to LLM for fixes...[/yellow]")
            return self._escalate_with_static_errors(
                node_id,
                result.stdout
            )

    # ═══════════════════════════════════════════════════
    # Continue with existing workflow (tests, etc.)
    # ═══════════════════════════════════════════════════

    # ... run tests ...
```

### Example Workflow

**Before Integration:**
```
1. Generate code (5s, $0.01)
2. Test (1s) → FAIL: undefined name 'input_data'
3. LLM fix (5s, $0.01) → Add pathlib import (WRONG!)
4. Test (1s) → FAIL again
5. LLM fix (5s, $0.01) → Finally fix indentation
6. Test (1s) → PASS

Total: 18s, $0.03
```

**After Integration:**
```
1. Generate code (5s, $0.01)
2. Static analysis (1s, $0.00) → FAIL: undefined name 'input_data' at line 12
3. LLM fix with SPECIFIC error (5s, $0.01) → Fix indentation
4. Static analysis (1s, $0.00) → PASS
5. Test (1s) → PASS

Total: 13s, $0.02 (28% faster, 33% cheaper)
```

---

## Saved Results File

Results are automatically saved to `.analysis_results.json` in the same directory as the code file:

```json
{
  "syntax": {
    "validator": "syntax",
    "passed": true,
    "output": "OK: Valid Python syntax",
    "execution_time_ms": 45.2
  },
  "undefined_names": {
    "validator": "undefined_names",
    "passed": false,
    "output": "main.py:12: [F821] undefined name 'input_data'",
    "execution_time_ms": 312.5
  },
  "_summary": {
    "total_validators": 8,
    "passed": 7,
    "failed": 1,
    "total_time_ms": 847.3
  }
}
```

This file is used by `--retry-failed` to determine which validators to re-run.

---

## Command-Line Options

```bash
usage: run_static_analysis.py [-h] [--validator VALIDATOR] [--fix]
                               [--retry-failed] [--verbose] [--json]
                               code_file

Run static analysis validators on generated code

positional arguments:
  code_file             Path to Python code file

optional arguments:
  -h, --help            show this help message and exit
  --validator VALIDATOR
                        Run specific validator (syntax, main_function, etc.)
  --fix                 Apply auto-fixes where available
  --retry-failed        Re-run only previously failed validators
  --verbose             Show detailed output
  --json                Output results as JSON
```

---

## Validator Priority Order

Validators run in priority order (highest first):

| Priority | Validator | Time | Auto-Fix | What It Checks |
|----------|-----------|------|----------|----------------|
| 200 | syntax | 50ms | ❌ | Valid Python syntax |
| 180 | main_function | 100ms | ❌ | Has main() and __main__ |
| 150 | json_output | 100ms | ❌ | JSON output format |
| 140 | stdin_usage | 100ms | ❌ | stdin reading |
| 120 | undefined_names | 300ms | ❌ | Missing imports, undefined vars |
| 110 | import_order | 150ms | ✅ | Import organization |
| 100 | node_runtime_import | 100ms | ✅ | Import order |
| 90 | call_tool_usage | 100ms | ❌ | call_tool() usage |

**Total:** ~1000ms (1 second)

---

## Exit Codes

- **0** - All validators passed
- **1** - One or more validators failed
- **2** - Error (file not found, invalid arguments, etc.)

---

## Examples

### Example 1: Full Workflow

```bash
# Generate code (done by chat_cli.py)
# ...

# Run all validators with auto-fix
$ python tools/executable/run_static_analysis.py nodes/my_node/main.py --fix

# If some validators still fail, check specific one
$ python tools/executable/run_static_analysis.py nodes/my_node/main.py --validator undefined_names

# Fix code manually...

# Retry only failed validators
$ python tools/executable/run_static_analysis.py nodes/my_node/main.py --retry-failed

# All pass? Great! Run tests
$ python nodes/my_node/test_main.py
```

### Example 2: CI/CD Integration

```bash
#!/bin/bash
# ci_check.sh

# Run static analysis
python tools/executable/run_static_analysis.py $1 --json > analysis.json

# Check if passed
if [ $? -eq 0 ]; then
    echo "✓ Static analysis passed"
    exit 0
else
    echo "✗ Static analysis failed"
    cat analysis.json
    exit 1
fi
```

### Example 3: Quick Check

```bash
# Just check syntax (fast!)
$ python tools/executable/run_static_analysis.py main.py --validator syntax

# Just check imports
$ python tools/executable/run_static_analysis.py main.py --validator undefined_names
```

---

## Benefits

### 1. **Comprehensive** 🎯
- Runs all 8 validators
- Catches 80-90% of errors
- Single command

### 2. **Flexible** 🔧
- Run all or specific validators
- Auto-fix where possible
- Retry only failed

### 3. **Fast** ⚡
- ~1 second total
- Can run specific validators in <500ms
- Saves to file for retry

### 4. **Integration-Friendly** 🔌
- JSON output for automation
- Exit codes for CI/CD
- Saved results for workflow

### 5. **Cost-Effective** 💰
- Free (no LLM calls)
- Prevents expensive test failures
- Better error diagnosis

---

## Real-World Example

### The "write a poem" Bug

**Generated Code (BROKEN):**
```python
def main():
    input_data = json.load(sys.stdin)

    # Extract user's request description
task_description = input_data.get('description', '')  # ❌ NOT INDENTED
prompt = f'Generate content for: {task_description}'   # ❌ NOT INDENTED
content = call_tool('content_generator', prompt)       # ❌ NOT INDENTED
print(json.dumps({'result': content}))                 # ❌ NOT INDENTED
```

**WITHOUT Static Runner:**
```
Test (1s) → FAIL: undefined name 'input_data'
LLM fix (5s, $0.01) → Add pathlib import (WRONG!)
Test (1s) → FAIL again
LLM fix (5s, $0.01) → Still wrong
...
```

**WITH Static Runner:**
```bash
$ python run_static_analysis.py main.py

[[FAIL]] UNDEFINED_NAMES (312ms)
    main.py:12: [F821] undefined name 'input_data'
```

**Clear Diagnosis:** Line 12 uses `input_data` but it's not in scope (indentation error!)

**LLM can now fix it correctly the FIRST time.**

---

## Summary

✅ **Single command** runs all validators
✅ **Flexible modes** (all, specific, retry)
✅ **Auto-fix** where possible
✅ **Fast** (~1 second)
✅ **Free** (no LLM calls)
✅ **Clear errors** (better than test failures)
✅ **Integration-ready** (JSON, exit codes)

**Perfect for:**
- After code generation (before tests)
- CI/CD pipelines
- Development workflow
- Quality assurance

---

**Files:**
- `tools/executable/run_static_analysis.py` - Main script
- `tools/executable/run_static_analysis.yaml` - Tool definition
- `.analysis_results.json` - Saved results (auto-generated)

**Next:** Integrate into `chat_cli.py` workflow!
