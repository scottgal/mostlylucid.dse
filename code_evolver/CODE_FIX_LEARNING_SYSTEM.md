# Code Fix Learning System

## Overview

A self-learning system that stores code errors and their fixes as reusable patterns. The system learns from every fix and can automatically apply proven solutions when similar errors occur.

## Key Features

✅ **Store fixes as separate nodes** - Multiple solutions for same problem
✅ **Rank by usage count** - Most successful fixes ranked higher
✅ **Semantic search** - Find similar errors even with different wording
✅ **Full debug info** - Stack traces, variables, context all stored
✅ **Tool-specific tracking** - Link fixes to specific tools
✅ **Temporal decay** - Recent fixes weighted higher than old ones (coming soon)

## Architecture

### Two Core Tools

**1. store_code_fix_pattern** - Stores a fix pattern
**2. find_code_fix_pattern** - Searches for similar fixes

### Storage Strategy

Each fix is stored as a **separate RAG artifact**, even for the same error.

Why? Because:
- Same error can have multiple valid solutions
- Different approaches work better in different contexts
- Usage tracking shows which fixes actually work

### Ranking Algorithm

```python
rank_score = (usage_count × 10) + similarity + quality_score
```

**Priority order:**
1. **Usage count** (most proven) - A fix used 10 times beats a perfect match used 0 times
2. **Similarity** - How closely it matches your error
3. **Quality score** - Confidence in the fix (starts at 0.95)

## Usage Examples

### Example 1: Store a Fix

```bash
cd code_evolver
cat > fix.json << 'EOF'
{
  "error_message": "Syntax Error: f-string: single } is not allowed",
  "broken_code": "f\"Status: {status}\"",
  "fixed_code": "f\"Status: {{status}}\"",
  "fix_description": "Literal braces in f-strings must be doubled",
  "error_type": "syntax",
  "language": "python",
  "context": {
    "tool_id": "standalone_exe_compiler",
    "function": "generate_standalone_wrapper",
    "file": "standalone_exe_compiler.py",
    "line": 73
  },
  "debug_info": {
    "stack_trace": "File 'standalone_exe_compiler.py', line 73, in generate_standalone_wrapper",
    "local_vars": {"status": "healthy", "port": 8080},
    "timestamp": "2025-01-16T10:30:00Z"
  }
}
EOF

cat fix.json | python tools/executable/store_code_fix_pattern.py
```

**Result:**
```json
{
  "success": true,
  "pattern_id": "fix_pattern_51852d82e561",
  "error_type": "syntax",
  "tags": ["code-fix-pattern", "syntax", "python", "syntax-error", "tool:standalone_exe_compiler"],
  "message": "Stored code fix pattern: fix_pattern_51852d82e561"
}
```

### Example 2: Find Similar Fixes

```bash
cat > search.json << 'EOF'
{
  "error_message": "SyntaxError: f-string: single } not allowed",
  "broken_code": "f\"Hello {name}\"",
  "error_type": "syntax"
}
EOF

cat search.json | python tools/executable/find_code_fix_pattern.py
```

**Result:**
```json
{
  "success": true,
  "found": true,
  "pattern_count": 2,
  "best_match": {
    "pattern_id": "fix_pattern_51852d82e561",
    "similarity": 0.98,
    "usage_count": 15,
    "rank_score": 150.98,
    "error_message": "SyntaxError: f-string: single } is not allowed",
    "broken_code": "f\"Status: {status}\"",
    "fixed_code": "f\"Status: {{status}}\"",
    "fix_description": "Literal braces must be doubled",
    "debug_info": {...},
    "context": {"tool_id": "standalone_exe_compiler"}
  },
  "all_patterns": [
    {...fix #1 - used 15 times...},
    {...fix #2 - used 5 times...}
  ]
}
```

## Integration with Fix Cycle

### Automated Fix Workflow

```python
from node_runtime import call_tool
import json
import traceback

def execute_with_learned_fixes(code, tool_id=None):
    """
    Execute code and auto-apply learned fixes if errors occur
    """
    try:
        result = exec(code)
        return result

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()

        # 1. Search for similar fix patterns
        search_result = call_tool("find_code_fix_pattern", json.dumps({
            "error_message": error_msg,
            "broken_code": code,
            "error_type": type(e).__name__.lower()
        }))

        search_data = json.loads(search_result)

        if search_data['found']:
            # 2. Try each fix in order of rank
            for pattern in search_data['all_patterns']:
                try:
                    # Apply transformation
                    fixed_code = apply_fix_transformation(
                        code,
                        pattern['broken_code'],
                        pattern['fixed_code']
                    )

                    # Test the fix
                    result = exec(fixed_code)

                    # SUCCESS! Increment usage count
                    rag.increment_usage(pattern['pattern_id'])

                    print(f"✓ Auto-fixed using pattern {pattern['pattern_id']}")
                    print(f"  Fix has been successfully applied {pattern['usage_count'] + 1} times")

                    return result

                except:
                    # This fix didn't work, try next one
                    continue

        # 3. No fix worked - use LLM
        print("No learned fix worked. Using LLM...")
        fixed_code = llm_fix_code(code, error_msg, tb)

        try:
            result = exec(fixed_code)

            # 4. Store this new fix for future use
            call_tool("store_code_fix_pattern", json.dumps({
                "error_message": error_msg,
                "broken_code": code,
                "fixed_code": fixed_code,
                "fix_description": "LLM-generated fix",
                "error_type": type(e).__name__.lower(),
                "context": {"tool_id": tool_id} if tool_id else {},
                "debug_info": {
                    "stack_trace": tb,
                    "exception_type": type(e).__name__
                }
            }))

            print(f"✓ Fixed with LLM and stored pattern for future use")
            return result

        except Exception as fix_error:
            raise Exception(f"Fix failed: {fix_error}")
```

### Tool-Specific Auto-Fix

```python
# When a tool breaks, store fix linked to that tool
def fix_and_store(tool_id, error, broken_code, fixed_code):
    call_tool("store_code_fix_pattern", json.dumps({
        "error_message": str(error),
        "broken_code": broken_code,
        "fixed_code": fixed_code,
        "fix_description": f"Auto-fixed error in {tool_id}",
        "context": {
            "tool_id": tool_id,  # Link to specific tool
            "auto_applied": False,  # Not yet auto-applied
            "mutation_compatible": True  # Can apply after mutations
        }
    }))

# When same error happens in same tool again
def auto_fix_tool_error(tool_id, error, broken_code):
    # Search for tool-specific fixes
    result = call_tool("find_code_fix_pattern", json.dumps({
        "error_message": str(error),
        "broken_code": broken_code,
        "tags": [f"tool:{tool_id}"]  # Filter by tool
    }))

    fixes = json.loads(result)

    if fixes['found']:
        # Automatically apply highest-ranked fix for this tool
        best_fix = fixes['best_match']

        # Check if fix is mutation-compatible
        if best_fix['context'].get('mutation_compatible', False):
            return apply_fix_after_mutation(
                broken_code,
                best_fix['broken_code'],
                best_fix['fixed_code']
            )
```

## Multiple Fixes for Same Error

Example: `TypeError: str + int`

**Fix #1:** Convert int to str
```python
# Usage count: 50
result = str(value1) + value2
```

**Fix #2:** Convert str to int
```python
# Usage count: 5
result = value1 + int(value2)
```

**Fix #3:** Use f-string
```python
# Usage count: 100  ← HIGHEST RANK
result = f"{value1}{value2}"
```

The system will recommend Fix #3 first (most proven), but all three are available.

## Planned Features

### 1. Temporal Decay

Older fixes gradually get lower weight:

```python
# Age-based weighting
age_days = (now - pattern['timestamp']).days
decay_factor = 1.0 / (1 + age_days / 30)  # 50% decay after 30 days

adjusted_score = (usage_count * 10 * decay_factor) + similarity
```

This ensures:
- Recent fixes rank higher
- Outdated solutions fade out
- System stays current

### 2. Mutation-Aware Fixes

When a tool is evolved/mutated, fixes should still work:

```python
# Store fix with structural pattern, not exact code
{
  "pattern_type": "brace_escaping",
  "broken_pattern": "f\"...{variable}...\"",
  "fixed_pattern": "f\"...{{variable}}...\"",
  "applies_to": ["f-strings", "format strings"],
  "mutation_safe": true
}
```

### 3. Cross-Tool Learning

If a fix works in tool A, suggest it for similar errors in tool B:

```python
# When fix succeeds, tag it for related tools
if fix_successful:
    similar_tools = find_similar_tools(tool_id)
    for similar_tool in similar_tools:
        tag_pattern(pattern_id, f"suggested_for:{similar_tool}")
```

## Benefits

### For the System
- ✅ **Faster fixes** - Apply proven solutions instantly
- ✅ **Learn from mistakes** - Never repeat the same error twice
- ✅ **Build knowledge** - Accumulate fix library over time
- ✅ **Self-improving** - Gets smarter with every fix

### For Users
- ✅ **Automatic fixes** - Most errors fixed without intervention
- ✅ **Transparent** - See which fix was applied and why
- ✅ **Trustworthy** - Highest-ranked fixes proven by usage
- ✅ **Educational** - Learn from past fixes

## Testing

### Test 1: Store and Retrieve

```bash
# Store a fix
cat > test_fix.json << 'EOF'
{
  "error_message": "NameError: name 'x' is not defined",
  "broken_code": "print(x)",
  "fixed_code": "x = 0\nprint(x)",
  "fix_description": "Variable used before definition",
  "error_type": "runtime"
}
EOF
cat test_fix.json | python tools/executable/store_code_fix_pattern.py

# Search for it
cat > test_search.json << 'EOF'
{
  "error_message": "NameError: name 'y' is not defined"
}
EOF
cat test_search.json | python tools/executable/find_code_fix_pattern.py
```

### Test 2: Multiple Fixes Ranking

```bash
# Store 3 different fixes for same error
# Fix 1 - use 10 times (rank: 100)
# Fix 2 - use 5 times (rank: 50)
# Fix 3 - use 20 times (rank: 200) ← Should rank highest

# Search should return Fix 3 first
```

## Summary

**Status:** ✅ WORKING

**Files Created:**
- `tools/executable/store_code_fix_pattern.py` + `.yaml`
- `tools/executable/find_code_fix_pattern.py` + `.yaml`

**Features Implemented:**
- ✅ Store fixes as separate nodes
- ✅ Full debug info capture
- ✅ Rank by usage + similarity
- ✅ Tool-specific tracking
- ✅ Semantic search
- ✅ Multiple fixes per error

**Next Steps:**
- ⏳ Implement temporal decay
- ⏳ Add mutation-aware pattern matching
- ⏳ Auto-fix integration in evolve_tool
- ⏳ Cross-tool learning
