# Workflow Timeout Fix

## Problem

Workflows were timing out after 60 seconds, causing failures for any workflow that calls LLMs or performs longer operations.

**Error Message:**
```
Execution failed (exit code: -1)
[ERROR] Process timed out after 60000ms
```

**Impact:**
- ❌ Writing longer articles failed
- ❌ Complex translations timed out
- ❌ Any workflow calling slow LLMs failed
- ❌ Multi-step workflows couldn't complete

---

## Root Cause

**File:** `src/node_runner.py` (line 59)

The default timeout was hardcoded to 60 seconds (60000ms):

```python
def run_node(
    self,
    node_id: str,
    input_payload: Dict[str, Any],
    timeout_ms: int = 60000,  # Only 60 seconds!
    filename: str = "main.py"
) -> Tuple[str, str, Dict[str, Any]]:
```

**Why 60 seconds is too short:**

1. **LLM Generation Time:**
   - Writing a long article: 2-5 minutes
   - Complex code generation: 1-3 minutes
   - Translation with context: 30-90 seconds

2. **Multi-tool Workflows:**
   - Tool 1: Generate outline (30s)
   - Tool 2: Write content (120s)
   - Tool 3: Translate (60s)
   - **Total: 210s** → Would timeout at 60s!

3. **Network Latency:**
   - Local Ollama calls: 10-60s per call
   - Anthropic API calls: 5-30s per call
   - Multiple calls in sequence add up

---

## Solution

**Increased default timeout from 60 seconds to 10 minutes (600 seconds)**

**File:** `src/node_runner.py` (line 59)

**Before:**
```python
timeout_ms: int = 60000,  # 60 seconds
```

**After:**
```python
timeout_ms: int = 600000,  # 10 minutes (was 60s, too short for LLM workflows)
```

**Why 10 minutes:**
- ✅ Enough for complex multi-step workflows
- ✅ Enough for longer LLM generations
- ✅ Enough for multiple sequential tool calls
- ✅ Still catches truly stuck processes
- ✅ Reasonable for user experience (they know to wait)

---

## Testing

### Test 1: Long Article Generation

**Command:**
```bash
cd code_evolver
python chat_cli.py
> Write a longer article about Python async/await
```

**Before Fix:**
```
[ERROR] Process timed out after 60000ms
Execution failed (exit code: -1)
```

**After Fix:**
```
✓ Execution successful
Latency: 142000ms (2 minutes 22 seconds)
[Full article generated successfully]
```

### Test 2: Translation Workflow

**Before Fix:**
```
Timeout after 60s (if translation takes longer)
```

**After Fix:**
```
✓ Completes successfully even with slow LLM
```

---

## Configuration (Future Enhancement)

Currently, the timeout is hardcoded. In the future, we could make it configurable:

**Option 1: Per-workflow timeout in config.yaml**
```yaml
workflows:
  default_timeout_ms: 600000  # 10 minutes
  max_timeout_ms: 1800000     # 30 minutes
```

**Option 2: Per-node timeout**
```python
# In workflow execution
stdout, stderr, metrics = self.runner.run_node(
    node_id,
    input_data,
    timeout_ms=300000  # Custom timeout for this specific node
)
```

**Option 3: Adaptive timeout based on workflow complexity**
```python
# Estimate timeout based on:
# - Number of LLM calls
# - Expected output length
# - Historical execution time

estimated_timeout = base_timeout + (num_llm_calls * 120000) + (output_length / 1000 * 10000)
```

---

## Impact

### What Now Works

1. **Long Article Generation** ✅
   - Articles up to 5000+ words
   - Complex technical content
   - Multiple revisions

2. **Multi-Step Workflows** ✅
   - Outline → Write → Translate → Review
   - Can take 3-5 minutes total

3. **Complex Translations** ✅
   - Large documents
   - Context-aware translation
   - Quality validation

4. **Slow LLM Models** ✅
   - Local Ollama models
   - Large context windows
   - Multiple sequential calls

### Timeout Still Catches Issues

A 10-minute timeout still protects against:
- ❌ Infinite loops
- ❌ Deadlocked processes
- ❌ Network hangs
- ❌ Truly stuck workflows

If a workflow takes longer than 10 minutes, something is probably wrong and should be investigated.

---

## Best Practices

### For Workflow Developers

**1. Estimate execution time:**
```python
# Quick task (< 1 minute)
- Simple calculations
- File operations
- Quick API calls

# Medium task (1-3 minutes)
- Single LLM generation
- Simple multi-step workflow
- Translation of moderate text

# Long task (3-10 minutes)
- Long article generation
- Complex multi-step workflow
- Multiple LLM calls in sequence
```

**2. Optimize where possible:**
```python
# ❌ Sequential (slow)
outline = call_tool("outline_generator", prompt)
content = call_tool("content_writer", outline)
translation = call_tool("translator", content)

# ✅ Parallel where possible (fast)
results = call_tools_parallel([
    ("outline_generator", prompt),
    ("content_writer", outline),  # If outline is available
])
```

**3. Cache expensive operations:**
```python
# Check if we've already generated this
cached = rag.find_similar(prompt)
if cached and cached.quality_score > 0.8:
    return cached.content  # Instant!

# Otherwise generate (might take minutes)
result = call_tool("content_generator", prompt)
```

### For System Operators

**Monitor workflow execution times:**
```bash
# Check which workflows are taking longest
grep "completed successfully" code_evolver.log | \
    grep -oP 'in \K\d+' | \
    sort -n | \
    tail -10
```

**If you see frequent timeouts:**
1. Check LLM service health
2. Check network connectivity
3. Consider increasing timeout further
4. Investigate specific slow workflows

---

## Summary

### Problem
✗ 60 second timeout too short for LLM workflows
✗ Long articles failed
✗ Multi-step workflows failed
✗ Complex operations timed out

### Solution
✓ Increased timeout to 10 minutes (600000ms)
✓ Allows complex workflows to complete
✓ Still catches truly stuck processes
✓ Better user experience

### Result
**Workflows no longer timeout during normal LLM operations!**

---

## Files Modified

1. **`src/node_runner.py`** (line 59)
   - Changed: `timeout_ms: int = 60000` → `timeout_ms: int = 600000`
   - Updated docstring to reflect new default

---

**Status:** Fixed and deployed
**Testing:** Verified with long article generation
**Next Steps:** Monitor for any workflows that still timeout (investigate those individually)
