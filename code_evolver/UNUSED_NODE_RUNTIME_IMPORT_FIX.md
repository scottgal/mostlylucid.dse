# Unused node_runtime Import Fix - Complete Solution

## Problem Statement

**Error Pattern:**
```
ModuleNotFoundError: No module named 'node_runtime'
```

### Root Causes

1. **Initial Code Generation** - The LLM was told to ALWAYS include `from node_runtime import call_tool` even when not needed
2. **Repair System Misinterpretation** - When tests failed with ModuleNotFoundError, the repair system would ADD path setup instead of REMOVING the unused import
3. **Escalation Loop** - The system would try to "fix" the import by adding more code, making it worse

### Example Bad Code

```python
import json
import sys
from node_runtime import call_tool  # ← UNUSED! Never called

def calculate(x, y):
    return x + y  # Simple calculation, no tools needed

def main():
    input_data = json.load(sys.stdin)
    result = calculate(input_data["x"], input_data["y"])
    print(json.dumps({"result": result}))
```

**Test Failure:**
```
ModuleNotFoundError: No module named 'node_runtime'
```

**Previous "Fix" (WRONG!):**
```python
import json
import sys
from pathlib import Path  # ← Added by repair
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # ← Added by repair
from node_runtime import call_tool  # ← STILL UNUSED!
```

This makes it worse - more code, still doesn't use call_tool, and tests still fail if run from different paths.

## The Complete Fix

### 1. Fixed Code Generation Prompt

**File:** `chat_cli.py` line ~2322

**Before:**
```
- from node_runtime import call_tool (REQUIRED for content generation and project management tasks)
```

**After:**
```
- from node_runtime import call_tool (ONLY if you actually call this function - do NOT import if unused)
```

**Impact:** LLM will only include the import when `call_tool()` is actually needed.

### 2. Fixed Repair Logic

**File:** `chat_cli.py` lines ~4259-4274

**Before (Wrong Logic):**
```
- If call_tool() import is failing with ModuleNotFoundError, FIX THE PATH:
  Add these lines BEFORE the import...
```

This always tries to fix the path, even when the import is unused.

**After (Correct Logic):**
```
- CRITICAL: Handle call_tool() imports correctly based on ACTUAL USAGE:
  * If the code actually CALLS call_tool() somewhere:
    - Keep the call_tool() calls
    - Add path setup if ModuleNotFoundError
  * If the code DOES NOT call call_tool() anywhere (UNUSED IMPORT):
    - REMOVE the import statement
    - REMOVE any path setup related to node_runtime
    - ModuleNotFoundError for unused import means DELETE the import!
```

**Impact:** Repair system now checks if `call_tool()` is actually used before deciding to add path setup vs remove import.

### 3. Created Automated Tool

**Files:**
- `tools/executable/remove_unused_node_runtime_import.py`
- `tools/executable/remove_unused_node_runtime_import.yaml`

**What It Does:**
1. Parses the code using AST to check if `call_tool()` is actually called
2. If NOT used, removes:
   - `from node_runtime import call_tool`
   - `from pathlib import Path` (if only for node_runtime)
   - `sys.path.insert(...)` for node_runtime
   - `import logging` (if only added by repair)
   - `logging.basicConfig(...)`
   - `logging.debug(...)` calls
   - `try/except` wrappers added by repair
3. If used, keeps everything intact

**Usage:**
```bash
# Via CLI
echo '{"code": "..."}' | python tools/executable/remove_unused_node_runtime_import.py

# Via call_tool
from node_runtime import call_tool
result = call_tool("remove_unused_node_runtime_import", code="...")
```

**Example Output:**
```json
{
  "success": true,
  "was_modified": true,
  "changes": [
    "Removed: from node_runtime import call_tool",
    "Removed: sys.path.insert for node_runtime",
    "Removed: logging.basicConfig (added by repair)"
  ],
  "cleaned_code": "import json\nimport sys\n\ndef calculate(x, y):\n..."
}
```

## Testing The Fix

### Before Fix

```bash
$ cd nodes/calculate_machine_utilization_1763346883
$ python test_main.py
ModuleNotFoundError: No module named 'node_runtime'
```

### After Fix

```bash
$ python test_main.py
Testing main() interface...
OK main() function exists

$ echo '{"hours_used": 432, "hours_available": 720}' | python main.py
{"result": 60.0}
```

## Integration

### Static Analysis Pipeline

Add to code validation before tests:

```python
# Check for unused node_runtime imports
result = call_tool("remove_unused_node_runtime_import", code=code)
if result['was_modified']:
    code = result['cleaned_code']
    print(f"Cleaned code: {len(result['changes'])} changes")
```

### Repair System

The repair prompt now intelligently decides:

```
IF call_tool is used in code:
    → Add path setup if ModuleNotFoundError
ELSE:
    → Remove the import
END IF
```

### Future Code Generation

The LLM prompt now emphasizes conditional import:

```
ONLY include:
  from node_runtime import call_tool

IF you actually call call_tool() in your code.
DO NOT import if unused.
```

## When to Use call_tool

### ✅ DO Import node_runtime When:

1. **Content Generation**
   ```python
   joke = call_tool("content_generator", "Tell me a joke about coding")
   ```

2. **LLM-Based Tasks**
   ```python
   summary = call_tool("summarizer", long_text)
   ```

3. **Complex Workflows**
   ```python
   outline = call_tool("outline_generator", f"Create WBS for: {project}")
   ```

### ❌ DO NOT Import When:

1. **Simple Calculations**
   ```python
   def calculate(x, y):
       return x + y  # No LLM needed!
   ```

2. **Data Processing**
   ```python
   def sort_list(items):
       return sorted(items)  # Pure Python!
   ```

3. **File Operations**
   ```python
   def save_file(path, content):
       with open(path, 'w') as f:
           f.write(content)  # No tools needed!
   ```

## Prevention Checklist

Before committing generated code, verify:

- [ ] Is `call_tool()` actually called in the code?
- [ ] If YES, is the import present?
- [ ] If NO, is the import removed?
- [ ] Are there any leftover path setup lines?
- [ ] Are there debug logging statements from repair?
- [ ] Do tests pass without ModuleNotFoundError?

## Automated Fix Command

To automatically clean a file:

```bash
# Clean single file
python -c "
import json
with open('nodes/MY_NODE/main.py') as f:
    code = f.read()
print(json.dumps({'code': code}))
" | python tools/executable/remove_unused_node_runtime_import.py | \
python -c "
import json, sys
result = json.load(sys.stdin)
with open('nodes/MY_NODE/main.py', 'w') as f:
    f.write(result['cleaned_code'])
print('Cleaned!', result['changes'])
"
```

## Summary

**Problem:** Unused `from node_runtime import call_tool` causing ModuleNotFoundError

**Root Causes:**
1. Prompt told LLM to always include import
2. Repair system tried to fix path instead of removing unused import

**Solution:**
1. ✅ Updated code generation prompt to be conditional
2. ✅ Updated repair logic to check usage before fixing
3. ✅ Created automated tool to detect and remove unused imports
4. ✅ Tool also cleans up repair artifacts (logging, try/except, etc.)

**Result:** Generated code only imports what it uses, tests pass, no more ModuleNotFoundError for unused imports!

## Files Modified

1. `chat_cli.py:2322` - Code generation prompt
2. `chat_cli.py:4259-4274` - Repair logic
3. `tools/executable/remove_unused_node_runtime_import.py` - Cleanup tool (NEW)
4. `tools/executable/remove_unused_node_runtime_import.yaml` - Tool spec (NEW)
5. `UNUSED_NODE_RUNTIME_IMPORT_FIX.md` - This documentation (NEW)

## Future Work

- [ ] Add this tool to static analysis pipeline (run before tests)
- [ ] Create pre-commit hook to auto-clean generated code
- [ ] Add AST-based import optimizer for all unused imports (not just node_runtime)
- [ ] Create pattern matcher in fix_template_store for this common issue

---

**Status:** ✅ FIXED

Generated nodes now work correctly without unused imports!
