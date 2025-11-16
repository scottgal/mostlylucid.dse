# Tool Failure Tracking & Self-Recovery System

## Overview

Automatically handles tool failures by:
1. **Marking failures** - Records when tools fail for specific scenarios
2. **Demoting broken tools** - Reduces quality scores and adds negative tags
3. **Self-recovery** - Automatically tries alternative tools
4. **Learning** - System gets smarter about which tools work where

## Components

### 1. Mark Tool Failure (`mark_tool_failure`)

Records when a tool fails for a specific scenario.

**Input:**
```json
{
  "tool_id": "python_code_analyzer",
  "scenario": "analyze javascript code",
  "error_message": "UnsupportedLanguageError",
  "severity": "high"  // low, medium, high
}
```

**What It Does:**
- Stores failure in RAG with semantic embedding
- Demotes tool quality score (0.01 - 0.10 based on severity)
- Adds negative tags (e.g., "not-for-javascript")
- Tracks total failures per tool

**Demotion Rules:**
- Low severity: -0.01 quality
- Medium severity: -0.05 quality
- High severity: -0.10 quality
- 5+ failures: additional -0.05
- 10+ failures: additional -0.10

### 2. Resilient Tool Call (`resilient_tool_call`)

Self-recovering tool execution with automatic fallback.

**Input:**
```json
{
  "scenario": "translate english to french",
  "input": {"text": "Hello", "target": "fr"},
  "tags": ["translation"],
  "max_attempts": 5
}
```

**How It Works:**
1. Finds best tool for scenario (semantic search + quality score)
2. Tries the tool
3. If it fails:
   - Marks the failure
   - Excludes that tool
   - Finds next best tool
   - Retries
4. Repeats until success or max_attempts reached

**Tool Ranking:**
```
final_score = (semantic_similarity - failure_demotion) * quality_score
```

**Failure Demotion:**
- If tool has similar past failures: -0.3 to similarity
- Ensures failed tools rank lower for similar scenarios

## Usage

### Manual Failure Marking

```python
from node_runtime import call_tool
import json

# Try to use a tool
try:
    result = call_tool("csv_parser", json.dumps({"data": json_data}))
except Exception as e:
    # Mark the failure
    call_tool("mark_tool_failure", json.dumps({
        "tool_id": "csv_parser",
        "scenario": "parse JSON data",
        "error_message": str(e),
        "severity": "high"  # This tool only works for CSV!
    }))
```

### Resilient Execution (Recommended)

```python
from node_runtime import call_tool_resilient

# Automatic fallback to alternatives
result = call_tool_resilient(
    scenario="translate english to french",
    input_data={"text": "Hello", "target": "fr"},
    tags=["translation"],
    max_attempts=5
)

# What happens:
# 1. Tries: nmt_translator → FAILS (API key missing)
# 2. Tries: google_translate → FAILS (Network timeout)
# 3. Tries: offline_translator → SUCCESS!
```

### Integration with Workflows

```python
# Replace brittle calls with resilient ones
def process_data(data):
    try:
        # Old way: Brittle, fails if tool is broken
        # result = call_tool("data_processor", data)

        # New way: Resilient, tries alternatives
        result = call_tool_resilient(
            "process and validate data",
            {"data": data},
            tags=["processing", "validation"],
            max_attempts=3
        )
        return result
    except Exception as e:
        # Only fails if ALL tools fail
        handle_total_failure(e)
```

## Example: Full Workflow

```python
# Scenario: User wants to translate text

# Step 1: Try resilient call
result = call_tool_resilient(
    scenario="translate english text to french",
    input_data={"text": "Hello, how are you?", "target": "french"},
    tags=["translation"],
    max_attempts=5
)

# What happens internally:

# Attempt 1: nmt_translator (score: 0.92)
# → call_tool("nmt_translator", ...)
# → ERROR: API key missing
# → mark_tool_failure("nmt_translator", "translate english text to french", "API key missing", "medium")
#    - Demotes quality: 0.85 → 0.80
#    - Adds tags: ["not-for-translate", "not-for-english"]

# Attempt 2: google_translate (score: 0.85)
# → call_tool("google_translate", ...)
# → ERROR: Network timeout
# → mark_tool_failure("google_translate", "translate english text to french", "Network timeout", "low")
#    - Demotes quality: 0.90 → 0.89

# Attempt 3: offline_translator (score: 0.78)
# → call_tool("offline_translator", ...)
# → SUCCESS: "Bonjour, comment allez-vous?"

# Return:
{
  "success": true,
  "result": "Bonjour, comment allez-vous?",
  "tool_id": "offline_translator",
  "attempts": [
    {"attempt": 1, "tool_id": "nmt_translator", "success": false, ...},
    {"attempt": 2, "tool_id": "google_translate", "success": false, ...},
    {"attempt": 3, "tool_id": "offline_translator", "success": true}
  ]
}
```

## Future Tool Selection

Next time someone searches for "translate english to french":

**Tool Rankings:**
1. `offline_translator` - score: 0.78 (no failures for this scenario)
2. `google_translate` - score: 0.71 (0.89 quality * 0.8 demotion for failure)
3. `nmt_translator` - score: 0.48 (0.80 quality * 0.6 demotion for failure)

The system learned that `offline_translator` works best for this scenario!

## Tag Refinement

Tools automatically get more specific tags based on failures:

**Before Failures:**
```yaml
tool_id: python_code_analyzer
tags: ["code", "analyzer", "linter"]
quality: 0.90
```

**After 3 Failures (analyzing JS code):**
```yaml
tool_id: python_code_analyzer
tags: ["code", "analyzer", "linter", "not-for-javascript", "not-for-analyze"]
quality: 0.75  # Demoted
```

**Result:** Won't be recommended for JavaScript analysis anymore!

## Recovery from Demotion

If a tool is fixed or demotion was unwarranted:

```python
from src.rag_memory import RAGMemory

rag = RAGMemory(...)

# Restore quality score
rag.update_quality_score("python_code_analyzer", 0.90)

# Remove negative tags
rag.update_artifact_metadata("python_code_analyzer", {
    "tags": ["code", "analyzer", "linter", "python"]  # Removed not-for-* tags
})
```

## Benefits

1. **Automatic Fault Tolerance**: Workflows don't break when tools fail
2. **Learning System**: Gets smarter about which tools work where
3. **Self-Healing**: Automatically tries alternatives without human intervention
4. **Quality Tracking**: Tool quality scores reflect real-world performance
5. **Tag Accuracy**: Tool metadata becomes more precise over time

## Best Practices

### 1. Use Resilient Calls for Critical Operations

```python
# ✅ Good: Critical operation with fallback
result = call_tool_resilient(
    "translate critical error message",
    {"text": msg, "target": "es"},
    max_attempts=10  # Must succeed!
)

# ❌ Bad: No fallback, breaks on failure
result = call_tool("translator", msg)
```

### 2. Set Appropriate Severity

```python
# High: Tool completely broken for this use case
severity="high"  # -0.10 demotion

# Medium: Tool doesn't work, but might for other scenarios
severity="medium"  # -0.05 demotion

# Low: Minor issue, might work next time
severity="low"  # -0.01 demotion
```

### 3. Use Tag Filters

```python
# Narrow search space for faster recovery
result = call_tool_resilient(
    "translate text",
    input_data,
    tags=["translation", "offline"]  # Only offline translators
)
```

### 4. Monitor Attempts

```python
result_data = json.loads(result)
print(f"Succeeded with {result_data['tool_id']} after {len(result_data['attempts'])} attempts")

# Log for debugging
for attempt in result_data["attempts"]:
    if not attempt["success"]:
        logger.warning(f"Tool {attempt['tool_id']} failed: {attempt.get('error')}")
```

## Integration Points

### chat_cli.py

Workflows automatically use resilient calls:

```python
# In run_workflow():
result = call_tool_resilient(
    scenario=user_request,
    input_data=workflow_input,
    max_attempts=5
)
```

### orchestrator.py

Orchestrator can wrap tool calls:

```python
def execute_with_fallback(tool_id, scenario, input_data):
    try:
        return call_tool(tool_id, input_data)
    except Exception:
        # Fall back to resilient call
        return call_tool_resilient(scenario, input_data)
```

### auto_evolver.py

Evolution can use failure history:

```python
def should_evolve(node_id):
    # Check failure count
    failures = rag.search_by_tags(["tool_failure", node_id])
    if len(failures) > 5:
        return True  # Too many failures, evolve!
```

## Files

- `tools/executable/mark_tool_failure.py` - Failure recording tool
- `tools/executable/mark_tool_failure.yaml` - Tool config
- `tools/executable/resilient_tool_call.py` - Self-recovery tool
- `tools/executable/resilient_tool_call.yaml` - Tool config
- `node_runtime.py` - Added `call_tool_resilient()` function

## Summary

The Tool Failure Tracking system makes your workflows **self-healing**:
- Tools fail → System marks failure
- Next tool tried → Automatically
- System learns → Won't recommend broken tools
- Workflows succeed → At all costs

**Use `call_tool_resilient()` for production workflows!**
