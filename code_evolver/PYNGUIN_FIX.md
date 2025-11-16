# Pynguin Test Generation - Fixed

## Problem
You were seeing:
```
Pynguin did not generate tests (exit code: 1)
```

## Root Cause
The skip condition was incomplete. It only checked for:
```python
if 'call_tool(' not in code:  # Only checks for function CALLS
```

But **didn't check for imports**! So code like this passed the check:
```python
from node_runtime import call_tool  # ← Import exists
# ... but call_tool() never called
```

Pynguin tried to analyze it, couldn't import `node_runtime`, and failed.

## Fix Applied ✓

**Updated skip condition (chat_cli.py line 3412-3428):**
```python
# Skip Pynguin if code uses node_runtime (imports or calls)
has_node_runtime = (
    'from node_runtime import' in code or
    'import node_runtime' in code or
    'call_tool(' in code
)

if pynguin_enabled and not has_node_runtime:
    # Only use Pynguin for pure Python code
    pynguin_result = self._generate_tests_with_pynguin(...)
elif pynguin_enabled and has_node_runtime:
    console.print("[dim]Skipping Pynguin (code uses node_runtime/external tools)[/dim]")
```

**Better error diagnostics (chat_cli.py line 6080-6097):**
- Now shows specific failure reasons (ImportError, timeout, etc.)
- Clearer feedback: "Falling back to LLM-based test generation..."
- First error line extracted from stderr

## What You'll See Now

### Before (Broken):
```
> Trying Pynguin for fast test generation...
[yellow]Pynguin did not generate tests (exit code: 1)[/yellow]
```

### After (Fixed):
```
[dim]Skipping Pynguin (code uses node_runtime/external tools)[/dim]
OK Generated smoke test for external tool code
```

## When Pynguin IS Used

Pynguin will **only** run on:
- ✅ Pure Python code (no node_runtime imports)
- ✅ No external tool calls
- ✅ Standard library + pip packages only

Example - Pynguin WILL run:
```python
import json
import math

def calculate_area(radius):
    return math.pi * radius ** 2

def main():
    data = json.loads(sys.stdin.read())
    print(calculate_area(data['radius']))
```

Example - Pynguin SKIPPED:
```python
from node_runtime import call_tool  # ← Has node_runtime

def main():
    result = call_tool("content_generator", "write a story")
    print(json.dumps({"result": result}))
```

## Configuration (Optional)

You can control Pynguin behavior in config.yaml:

```yaml
testing:
  use_pynguin: true          # Enable/disable Pynguin (default: true)
  use_pynguin_tdd: true      # Use Pynguin for TDD templates (default: true)
  pynguin_timeout: 30        # Max seconds for test generation (default: 30)
  pynguin_min_coverage: 0.70 # Minimum coverage threshold (default: 70%)
```

To **disable Pynguin completely**:
```yaml
testing:
  use_pynguin: false
```

## Result

✅ **No more Pynguin failures on node_runtime code**
✅ **Clearer error messages when Pynguin does fail**
✅ **Automatic fallback to LLM-based test generation**
✅ **Faster workflow (no wasted 30s waiting for Pynguin to fail)**

---

**Files Modified:**
- `chat_cli.py` lines 3412-3428 (skip condition)
- `chat_cli.py` lines 6080-6097 (error diagnostics)

**Status:** FIXED ✓
