# Chat Tools Guide - Profiling & Optimization

This guide shows how to use the profiling and optimization tools from the chat window.

## Quick Start

Just ask in natural language! The system will automatically invoke the appropriate tools.

### Performance Profiling

**Ask any of these:**
- "Profile this code and tell me where it's slow"
- "Get performance metrics for this function"
- "Why is this code taking so long?"
- "What's the bottleneck in this script?"
- "Analyze the performance of the LLM generation"

**Example:**
```
You: Profile this code:

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(30)
```

**Response:**
```
## Performance Profile: fibonacci

**Duration**: 342.56ms
**Status**: ✓ Success

### Top Bottlenecks
1. fibonacci - 0.342s
   Issue: Exponential time complexity O(2^n)
   Fix: Use memoization or iterative approach

### Recommendations
- [HIGH] Long execution time - Exponential recursion
  Fix: Add @lru_cache decorator or use dynamic programming
```

### Code Optimization

**Ask any of these:**
- "Optimize this code"
- "Make this function faster"
- "Use cloud optimization for this code"
- "Optimize this thoroughly, it's in the critical path"

**Example:**
```
You: Optimize this code:

def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates
```

**Response:**
```
## Optimization Report

### Baseline Performance
- Duration: 125.34ms
- Bottlenecks: Nested loops O(n²), repeated list lookups

### Optimization Level: LOCAL
- Strategy: Use set for O(1) lookups, collections.Counter for duplicates
- Changes:
  1. Replaced nested loops with single pass
  2. Used set operations
  3. Eliminated redundant checks

### Optimized Code
```python
from collections import Counter

def find_duplicates(items):
    counts = Counter(items)
    return [item for item, count in counts.items() if count > 1]
```

### Performance Comparison
- Before: 125.34ms
- After: 2.15ms
- Improvement: 98.3%
- Recommendation: ACCEPT ✓

### Breaking Changes
- None
```

## Optimization Levels

The Code Optimizer uses a three-tier hierarchy:

### 1. LOCAL (Default)
- **Cost**: Free
- **Time**: ~30 seconds
- **Model**: qwen2.5-coder:14b
- **Improvement**: 10-20%
- **Best for**: Quick wins, obvious inefficiencies

**Automatically tries:**
- Remove redundancy
- Fix O(n²) loops
- Use better data structures (sets vs lists)
- Add caching
- Optimize string operations

### 2. CLOUD
- **Cost**: ~$0.50
- **Time**: ~60 seconds
- **Model**: GPT-4 or Claude
- **Improvement**: 20-40%
- **Triggers**:
  - Local improvement < 15%
  - Code has high reuse count (> 100)
  - User explicitly requests it

**Advanced optimizations:**
- Async/await for I/O
- Multiprocessing for CPU-bound
- Data structure redesign
- Memory layout optimization

### 3. DEEP
- **Cost**: ~$5.00
- **Time**: ~5 minutes
- **Model**: Claude Sonnet 200K
- **Improvement**: 50%+
- **Triggers**:
  - Workflow or system-level optimization
  - Cloud improvement < 25%
  - Architectural changes needed

**System-level changes:**
- Analyze entire call graph
- Architectural redesign
- Tool/library replacements
- Breaking changes if necessary

## How to Request Specific Levels

```
# Default (LOCAL)
"Optimize this code"

# Cloud optimization
"Use cloud optimization for this code"
"This is critical, optimize it thoroughly"

# Deep analysis
"Do a deep system analysis of this workflow"
"Optimize this entire module, architecture changes OK"
```

## Version Comparison

Compare two implementations:

```
You: Compare the performance of these two approaches:

Version 1:
def sum_squares(n):
    return sum([i**2 for i in range(n)])

Version 2:
def sum_squares(n):
    return sum(i**2 for i in range(n))
```

**Response:**
```
## Performance Comparison

### Version 1 (List Comprehension)
- Duration: 45.23ms
- Memory: 8.5 MB

### Version 2 (Generator Expression)
- Duration: 32.18ms
- Memory: 0.1 MB

### Result
Version 2 is 28.9% faster and uses 98.8% less memory
Recommendation: UPGRADE ✓

Why: Generator expressions don't create intermediate list
```

## Automatic Test Updating

When code is optimized, tests are automatically updated:

```
You: Optimize this code and update the tests

def calculate_average(numbers):
    return sum(numbers) / len(numbers)
```

**The optimizer will:**
1. ✓ Profile baseline code
2. ✓ Optimize the function
3. ✓ Find existing tests (test_calculate_average)
4. ✓ Update tests if behavior changed
5. ✓ Add performance regression test
6. ✓ Run all tests to verify
7. ✓ Accept only if all tests pass

**Output includes:**
```python
# Updated test
def test_calculate_average():
    assert calculate_average([1, 2, 3]) == 2.0

    # Performance regression test
    import time
    start = time.time()
    result = calculate_average(range(10000))
    duration = time.time() - start
    assert duration < 0.01  # Should complete in < 10ms
```

## Cost Management

The system tracks optimization costs and has built-in limits:

- **Daily budget**: $50 (configurable)
- **Per-optimization limit**: $5
- **Automatic fallback**: Switches to LOCAL if budget exceeded
- **Warning at 80%**: Notifies when approaching limit

**Check your usage:**
```
You: How much have I spent on optimizations today?
```

## Breaking Changes & Migration

The optimizer detects breaking changes:

- Function signature changed
- Return type changed
- Dependencies added/removed
- Behavior fundamentally different

**If no breaking changes:**
- ✓ Auto-migrates all usage
- ✓ Updates version metadata
- ✓ Tests all affected code

**If breaking changes:**
- ⚠ Lists all breaking changes
- 📋 Provides migration guide
- ❌ Requires manual approval
- 🔄 Keeps rollback option

## Performance Profiling Deep Dive

### What Gets Profiled

The profiler tracks:

1. **Execution time** (line-by-line)
2. **Call stack** (function hierarchy)
3. **I/O vs CPU** time breakdown
4. **Memory allocation**
5. **Blocking operations**

### Output Formats

**Text** (Console):
```
  Duration: 5.234s

5.234 main()
├─ 4.789 llm_generate()
│  ├─ 4.123 requests.post()
│  └─ 0.321 json.loads()
└─ 0.234 save_results()
```

**HTML** (Interactive):
- Flame graph visualization
- Collapsible call trees
- Search and filter
- Timeline view

### Environment Control

**Enable profiling:**
```bash
export CODE_EVOLVER_PROFILE=1
python chat_cli.py
```

**Custom output directory:**
```bash
export PROFILE_OUTPUT_DIR=/path/to/profiles
```

**In code:**
```python
from src.profiling import ProfileContext

with ProfileContext("my_operation"):
    # Your code here
    result = expensive_operation()
```

## Advanced Usage

### 1. Profile Specific Sections

```
You: Profile just the data processing part of this code, not the I/O
```

### 2. Compare Across Versions

```
You: Compare performance of tool version 1.0 vs 2.0
```

The optimizer uses the ProfileRegistry:
```python
comparison = registry.compare_profiles("operation", "1.0", "2.0")
# Shows: improvement_pct, recommendation (upgrade/keep)
```

### 3. Continuous Profiling

For frequently used code:
- Auto-profiles executions > 5 seconds
- Accumulates performance data
- Triggers optimization when performance degrades > 15%
- Uses real usage data (not synthetic benchmarks)

### 4. Hot-Swap Profiling

For production systems:
1. System runs normal version
2. Periodically injects profiler-hooked version
3. Collects performance data
4. Swaps back to normal version
5. Analyzes data in background
6. Suggests optimizations based on real usage

## Integration with Evolution System

The profiling data feeds into the evolution system:

1. **Auto-Evolver**: Monitors performance, triggers if quality drops > 15%
2. **Hierarchical Evolver**: Uses profile data to improve plans
3. **Optimization Pipeline**: Decides LOCAL vs CLOUD vs DEEP
4. **RAG Memory**: Stores successful optimizations for reuse
5. **Tools Manager**: Updates tool versions based on performance

## Troubleshooting

### "Profiling is disabled"

Enable it:
```bash
export CODE_EVOLVER_PROFILE=1
```

### "No bottlenecks found"

Code might be too fast. Try:
- Larger input size
- Multiple iterations
- Longer operation

### "Optimization made it slower"

This is caught automatically:
- Improvement < 10%: REJECTED
- Original code kept
- No changes applied

### "Tests failed after optimization"

Optimizer will:
1. Attempt to fix failing tests
2. If can't fix: ROLLBACK
3. Keep original code
4. Report why optimization failed

## Best Practices

### 1. Provide Context

```
Good: "Optimize this function, it's called 1000 times per request"
Better: "This is in the critical path, optimize thoroughly"
```

### 2. Include Test Data

```
Good: "Optimize this function"
Better: "Optimize this function, it processes lists of 10,000 items"
```

### 3. Specify Constraints

```
"Optimize this but keep the API the same"
"Make this faster, breaking changes are OK"
"Optimize for memory, not just speed"
```

### 4. Start Local, Escalate if Needed

```
First: "Optimize this code"  # Tries LOCAL (free)
If not enough: "Use cloud optimization"  # Escalates to CLOUD
```

## Examples Gallery

### Example 1: LLM Call Optimization

```
You: Profile the LLM generation in ollama_client.py

Response:
- Network time: 4.1s (87%)
- JSON parsing: 0.3s (6%)
- Other: 0.3s (7%)

Recommendations:
- Use connection pooling
- Batch multiple requests
- Consider async for parallel calls
```

### Example 2: Data Processing

```
You: Optimize this CSV processing

Before: 15.3s (reading line by line)
After: 0.8s (using pandas.read_csv)
Improvement: 94.8%
```

### Example 3: Recursive Algorithm

```
You: This recursive function is slow

Before: fibonacci(35) = 2.1s
After: fibonacci(35) = 0.0001s
Optimization: Added @lru_cache
Improvement: 99.995%
```

## Summary

**To profile code:**
- Just ask: "Profile this code"
- Or: "Why is this slow?"

**To optimize code:**
- Ask: "Optimize this code"
- Specify level: "Use cloud optimization"

**System handles:**
- ✓ Profiling
- ✓ Bottleneck analysis
- ✓ Optimization (LOCAL → CLOUD → DEEP)
- ✓ Test updating
- ✓ Validation
- ✓ Version management
- ✓ Migration
- ✓ Cost tracking

**You just chat naturally!** 🚀
