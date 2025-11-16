# Parallel Execution Fix

## Issue

The parallel execution examples in the code generation prompt were causing **test failures** because:

1. Generated code was missing imports (`import sys`, `from node_runtime import call_tools_parallel`)
2. Generated code had syntax errors in parallel calls
3. The examples confused the LLM, leading to broken code

**Error Pattern:**
```
TypeError: call_tools_parallel() missing required argument
```

---

## Root Cause

The parallel execution examples were **too prominent** in the code generation guidelines:

**Before:**
```
5. **PARALLEL EXECUTION OPTIMIZATION** (CRITICAL FOR PERFORMANCE!):
   - When making MULTIPLE INDEPENDENT tool calls, use call_tools_parallel() for dramatic speedup
   - Example: Translating 3 texts → 3x faster!
   ...
```

This caused the LLM to try using parallel execution even when:
- It wasn't needed
- The syntax was unclear
- Imports were missing

---

## Fix Applied

### 1. Removed from Code Generation Guidelines

**Removed:**
- Section "5. PARALLEL EXECUTION OPTIMIZATION"
- Parallel execution import suggestion
- Two complex parallel execution examples

**Result:** Code generation now focuses on **simple, sequential** tool calls that always work.

---

### 2. Simplified Overseer Prompt

**Before:**
```
3a. **Parallel Execution Optimization** (CRITICAL FOR PERFORMANCE!)
   - Identify tool calls that can run in PARALLEL
   - Group independent operations
   [30 lines of examples and patterns]
```

**After:**
```
3. **Implementation Plan**
   - Recommended algorithm or approach
   - Data structures to use
   - Key functions and their signatures
   - Which LLM tools should be called and when
   - Execution order (which operations must be sequential)
```

**Result:** Overseer focuses on **clear specifications** without complex parallel optimization.

---

### 3. Made Parallel Execution OPTIONAL

Parallel execution is now an **advanced feature** that users must:
1. Explicitly request in their prompt
2. Manually implement when needed
3. Use only when they understand the tradeoffs

**Documentation:** See `PARALLEL_EXECUTION_OPTIMIZATION.md` for manual usage.

---

## Status

✅ **Fixed:** Code generation no longer attempts parallel execution automatically
✅ **Working:** Standard sequential tool calls work reliably
✅ **Available:** Parallel execution still available for advanced users

---

## When to Use Parallel Execution (Manual)

### ✅ Good Use Cases (Manual Implementation)

When you **explicitly** need performance optimization:

```python
# Manually implement when you have 5+ independent operations
from node_runtime import call_tools_parallel

results = call_tools_parallel([
    ("translate", "Hello to French"),
    ("translate", "Hello to Spanish"),
    ("translate", "Hello to German")
])
```

### ❌ Don't Use (Let Code Generator Handle)

For normal workflows:
```python
# ✅ GOOD - Simple, reliable, auto-generated
text = call_tool("content_generator", "Write an article")
```

---

## Migration Guide

If you have workflows using parallel execution that are now breaking:

### Option 1: Remove Parallel Execution (Recommended)

Convert to sequential calls:

**Before:**
```python
from node_runtime import call_tools_parallel

results = call_tools_parallel([
    ("content_generator", "joke"),
    ("content_generator", "poem")
])
joke, poem = results
```

**After:**
```python
from node_runtime import call_tool

joke = call_tool("content_generator", "Write a joke")
poem = call_tool("content_generator", "Write a poem")
```

**Impact:** Slower (sequential) but more reliable.

---

### Option 2: Fix Imports Manually

If you must keep parallel execution:

```python
import json
import sys
from pathlib import Path

# CRITICAL: Add path setup
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import parallel function
from node_runtime import call_tool, call_tools_parallel

def main():
    input_data = json.load(sys.stdin)

    # Correct parallel usage
    results = call_tools_parallel([
        ("content_generator", "Write a joke"),
        ("content_generator", "Write a poem")
    ])

    joke, poem = results
    print(json.dumps({"joke": joke, "poem": poem}))

if __name__ == "__main__":
    main()
```

---

## Testing

After the fix, code generation should **never** produce:
- Missing imports for `call_tools_parallel`
- Incorrect parallel call syntax
- `TypeError: missing argument` errors

**Verification:**
```bash
cd code_evolver
python chat_cli.py
```

Try: "Generate a joke about cats"

**Expected:** Simple sequential code with `call_tool()`, no parallel execution.

---

## Summary

**Problem:** Parallel execution examples confused code generator → test failures
**Solution:** Made parallel execution optional/manual → reliable code generation
**Result:** Standard workflows work correctly, advanced users can still optimize manually

**Key Principle:** **Simplicity First** - Optimize only when needed, not by default.
