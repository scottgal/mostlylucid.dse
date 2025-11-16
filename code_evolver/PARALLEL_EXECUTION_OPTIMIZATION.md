# Parallel Execution Optimization

## Overview

The overseer now actively identifies opportunities for **parallel execution** of tool calls, which can dramatically reduce workflow latency.

## Performance Impact

**Before (Sequential):**
```
Joke generation:   2000ms  ──┐
Poem generation:   2000ms    │─► Total: 6000ms
Article generation: 2000ms  ──┘
```

**After (Parallel):**
```
Joke generation:   2000ms  ─┐
Poem generation:   2000ms   ├─► Total: 2000ms (3x faster!)
Article generation: 2000ms  ─┘
```

**3x speedup** for 3 independent operations!

---

## How It Works

### 1. Overseer Analysis

The overseer's specification now includes a **"Parallel Execution Optimization"** section that:

- Identifies tool calls with no dependencies
- Groups independent operations together
- Specifies execution order and dependencies
- Recommends `call_tools_parallel()` when applicable

**Example Overseer Output:**

```
3a. **Parallel Execution Optimization**

Independent Operations (can run in parallel):
- Translate "Hello" to French
- Translate "Goodbye" to Spanish
- Translate "Thank you" to German

Recommendation: Use call_tools_parallel() for 3x speedup!

Sequential Operations (must wait):
1. Generate initial content
2. WAIT for step 1 → Proofread content
3. WAIT for step 2 → Format content
```

---

### 2. Code Generation with Parallel Calls

The code generator receives the parallel execution plan and generates code using `call_tools_parallel()`:

**Generated Code:**
```python
from node_runtime import call_tools_parallel

# Run all translations in parallel (3x faster!)
results = call_tools_parallel([
    ("nmt_translator", "Translate to french: Hello"),
    ("nmt_translator", "Translate to spanish: Goodbye"),
    ("nmt_translator", "Translate to german: Thank you")
])

french, spanish, german = results
```

---

## Usage Examples

### Example 1: Multi-Language Translation

**Task:** "Translate 'Hello', 'Goodbye', 'Thank you' to French, Spanish, and German"

**Sequential (OLD):** 9 tool calls × 2000ms = **18,000ms**

**Parallel (NEW):** 9 tool calls in parallel = **2,000ms** (9x faster!)

```python
from node_runtime import call_tools_parallel

texts = ["Hello", "Goodbye", "Thank you"]
languages = ["french", "spanish", "german"]

# Build parallel calls
parallel_calls = []
for text in texts:
    for lang in languages:
        parallel_calls.append((
            "nmt_translator",
            f"Translate to {lang}: {text}"
        ))

# Execute all 9 translations in parallel
results = call_tools_parallel(parallel_calls)  # 2000ms total!
```

---

### Example 2: Multiple Content Types

**Task:** "Generate a joke, poem, and article about technology"

**Sequential (OLD):** 3 × 3000ms = **9,000ms**

**Parallel (NEW):** **3,000ms** (3x faster!)

```python
from node_runtime import call_tools_parallel

results = call_tools_parallel([
    ("content_generator", "Write a funny joke about technology"),
    ("content_generator", "Write a short poem about technology"),
    ("content_generator", "Write a brief article about technology")
])

joke, poem, article = results
```

---

### Example 3: Batch Data Processing

**Task:** "Summarize 5 different articles"

**Sequential (OLD):** 5 × 4000ms = **20,000ms**

**Parallel (NEW):** **4,000ms** (5x faster!)

```python
from node_runtime import call_tools_parallel

articles = [article1, article2, article3, article4, article5]

# Summarize all articles in parallel
parallel_calls = [
    ("content_generator", f"Summarize this article: {article}")
    for article in articles
]

summaries = call_tools_parallel(parallel_calls)  # 4000ms total!
```

---

## When to Use Parallel Execution

### ✅ **Good Use Cases:**

1. **Multiple translations** of different texts
2. **Multiple content generations** (joke + poem + article)
3. **Batch processing** (summarize 10 articles)
4. **Multi-step independent operations** (fetch data from 3 APIs)
5. **A/B testing** (generate 2 versions simultaneously)

### ❌ **Bad Use Cases (Sequential Required):**

1. **Dependent operations:**
   ```python
   # ❌ Can't parallelize - step 2 needs step 1's output
   content = call_tool("content_generator", "Write an article")
   proof = call_tool("proofreader", content)  # Depends on content!
   ```

2. **Single operation:**
   ```python
   # ❌ Only one operation - no benefit
   joke = call_tool("content_generator", "Tell a joke")
   ```

3. **Shared state:**
   ```python
   # ❌ Can't parallelize - all modify same counter
   for i in range(5):
       counter += process_item(i)
   ```

---

## Implementation Details

### Function Signature

```python
def call_tools_parallel(tool_calls: list) -> list:
    """
    Call multiple tools in parallel using concurrent execution.

    Args:
        tool_calls: List of tuples or dicts:
                   - Tuple: (tool_name, prompt) or (tool_name, prompt, kwargs)
                   - Dict: {'tool': name, 'prompt': text, 'kwargs': {...}}

    Returns:
        List of results in same order as tool_calls
    """
```

### Tuple Format

```python
results = call_tools_parallel([
    ("content_generator", "Write a joke"),
    ("content_generator", "Write a poem"),
    ("nmt_translator", "Translate to french: Hello", {"target_lang": "fr"})
])
```

### Dict Format

```python
results = call_tools_parallel([
    {"tool": "content_generator", "prompt": "Write a joke"},
    {"tool": "content_generator", "prompt": "Write a poem"},
    {"tool": "nmt_translator", "prompt": "Translate: Hello", "kwargs": {"target_lang": "fr"}}
])
```

---

## Overseer Prompt Updates

The overseer now includes this in all specifications:

```
3a. **Parallel Execution Optimization** (CRITICAL FOR PERFORMANCE!)
   - Identify tool calls that can run in PARALLEL (no dependencies)
   - Group independent operations together
   - Specify dependencies: which operations must wait for others

   PARALLEL EXECUTION PATTERN:
   ✅ GOOD - Run independent calls in parallel
   results = call_tools_parallel([
       ("content_generator", "Write a joke about cats"),
       ("content_generator", "Write a poem about dogs")
   ])

   ❌ BAD - Run sequentially (slow!)
   joke = call_tool("content_generator", "Write a joke about cats")
   poem = call_tool("content_generator", "Write a poem about dogs")  # Waits!
```

---

## Code Generation Updates

The code generator now includes:

**Import Suggestion:**
```python
from node_runtime import call_tools_parallel  # For parallel operations
```

**Example Templates:**
- **Parallel Translation** example (3 texts × 3 languages = 9x speedup)
- **Parallel Content Generation** example (joke + poem + article = 3x speedup)
- **Batch Processing** pattern

---

## Configuration

No configuration needed! The feature works automatically:

1. **Overseer analyzes** task for parallel opportunities
2. **Code generator** uses `call_tools_parallel()` when applicable
3. **Runtime executes** using ThreadPoolExecutor for concurrent calls

---

## Performance Metrics

| Scenario | Sequential | Parallel | Speedup |
|----------|-----------|----------|---------|
| 3 translations | 6000ms | 2000ms | **3x** |
| 5 summaries | 20000ms | 4000ms | **5x** |
| 10 generations | 30000ms | 3000ms | **10x** |
| joke+poem+article | 9000ms | 3000ms | **3x** |

**Key Insight:** Speedup = number of parallel operations (assuming similar execution times)

---

## Future Enhancements

Potential improvements:

1. **Automatic batching:** Group calls automatically when >10 similar operations
2. **Dynamic parallelism:** Adjust thread pool size based on system resources
3. **Retry logic:** Automatic retry for failed parallel calls
4. **Progress tracking:** Show progress for long-running parallel operations
5. **Resource limits:** Cap max parallel calls to prevent overload

---

## Best Practices

### 1. **Always Check Dependencies**

Before parallelizing, verify operations are truly independent:

```python
# ✅ Independent - can parallelize
results = call_tools_parallel([
    ("translate", "Hello to French"),
    ("translate", "Goodbye to Spanish")  # No dependency!
])

# ❌ Dependent - must be sequential
content = call_tool("content_generator", "Write article")
summary = call_tool("summarizer", content)  # Needs content!
```

### 2. **Batch Similar Operations**

Group similar operations for maximum efficiency:

```python
# ✅ Good - all translations together
translations = call_tools_parallel([
    ("translate", text1),
    ("translate", text2),
    ("translate", text3)
])

# ❌ Suboptimal - mixed operations
results = call_tools_parallel([
    ("translate", text1),
    ("summarize", article1),
    ("translate", text2)
])
```

### 3. **Handle Errors Gracefully**

Individual calls can fail - handle errors:

```python
results = call_tools_parallel([
    ("tool1", "prompt1"),
    ("tool2", "prompt2")
])

for i, result in enumerate(results):
    if "error" in str(result).lower():
        print(f"Call {i} failed: {result}")
```

---

## Summary

**Key Benefits:**
- ⚡ **3-10x faster** for multiple independent operations
- 🤖 **Automatic optimization** - overseer identifies opportunities
- 📦 **Simple API** - just use `call_tools_parallel()`
- 🔄 **No config needed** - works out of the box

**When to Use:**
- Multiple independent tool calls
- Batch processing
- Multi-language translation
- Parallel content generation

**Result:** Dramatically faster workflows with minimal code changes!
