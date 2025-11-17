# Performance Testing & Regression Evaluation Workflow Guide

Complete guide for using the performance testing tools to benchmark, analyze, and evaluate tool performance with intelligent regression assessment.

## Overview

Three integrated tools work together to provide comprehensive tool profiling:

1. **timeit_optimizer.py** - Performance benchmarking with automatic mocking
2. **performance_regression_evaluator.py** - LLM-based regression assessment with static analysis
3. **comprehensive_tool_profiler.py** - Orchestrates the complete workflow

## Quick Start

### Initial Tool Profiling (No Old Version)

```bash
echo '{
  "tool_code": "def add(a, b):\n    return a + b",
  "test_input": {"a": 5, "b": 3},
  "requirement": "Add two numbers together"
}' | python code_evolver/tools/perf/comprehensive_tool_profiler.py simple_adder
```

**What it does:**
1. ✅ Runs performance benchmark (3 iterations)
2. ✅ Analyzes code (complexity, security, correctness)
3. ⏭️  Skips regression evaluation (no old version)
4. ✅ Tags tool in RAG with all metadata

### Tool Update with Regression Check

```bash
echo '{
  "tool_code": "def add(a, b):\n    # Added validation\n    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):\n        raise TypeError(\"Arguments must be numbers\")\n    return a + b",
  "test_input": {"a": 5, "b": 3},
  "requirement": "Add two numbers with type validation",
  "old_version_data": {
    "code": "def add(a, b):\n    return a + b",
    "version": "1.0.0",
    "requirement": "Add two numbers together",
    "metadata": {
      "performance": {
        "execution_time_ms": 0.005,
        "memory_usage_kb": 0.1
      },
      "static_analysis": {
        "security": {"total_issues": 0}
      }
    }
  }
}' | python code_evolver/tools/perf/comprehensive_tool_profiler.py simple_adder
```

**What it does:**
1. ✅ Runs performance benchmark on new version
2. ✅ Analyzes new code
3. ✅ Compares with old version using LLM
4. ✅ LLM evaluates: "Is 20% slowdown reasonable for type validation?"
5. ✅ Returns score (0-100) and recommendation (ACCEPT/REJECT/REVIEW)
6. ✅ If accepted, updates RAG

## Tool Details

### 1. Timeit Optimizer

**Purpose:** Performance benchmarking with automatic dependency mocking

**Commands:**
- `generate` - Create standalone test script
- `benchmark` - Run 3 iterations and collect metrics
- `update_rag` - Store performance data in RAG

**Example - Generate test script:**
```bash
echo '{
  "command": "generate",
  "tool_code": "def multiply(a, b):\n    return a * b",
  "tool_id": "multiplier",
  "test_input": {"a": 10, "b": 20}
}' | python code_evolver/tools/perf/timeit_optimizer.py generate
```

**Output:**
```json
{
  "test_script": "#!/usr/bin/env python3\n# Auto-generated test...",
  "tool_id": "multiplier"
}
```

**Example - Run benchmark:**
```bash
echo '{
  "command": "benchmark",
  "tool_code": "def multiply(a, b):\n    return a * b",
  "tool_id": "multiplier",
  "test_input": {"a": 10, "b": 20}
}' | python code_evolver/tools/perf/timeit_optimizer.py benchmark
```

**Output:**
```json
{
  "success": true,
  "best_run": {
    "execution_time_ms": 0.0058,
    "memory_usage_kb": 0.140625,
    "test_run_number": 1
  },
  "all_runs": [...]
}
```

**Key Features:**
- Runs 3 iterations, selects best
- High-precision timing (ms)
- Memory tracking (KB)
- Auto-mocks tool calls and external APIs
- Generates standalone 4B-class test scripts

### 2. Performance Regression Evaluator

**Purpose:** LLM-based assessment of performance changes with static analysis

**Commands:**
- `evaluate` - Assess regression reasonableness
- `analyze` - Run static analysis only

**Example - Analyze code:**
```bash
echo '{
  "command": "analyze",
  "code": "def process(data):\n    return [x*2 for x in data]"
}' | python code_evolver/tools/perf/performance_regression_evaluator.py analyze
```

**Output:**
```json
{
  "success": true,
  "analysis": {
    "complexity": {
      "average_complexity": 1.2,
      "grade": "A"
    },
    "security": {
      "total_issues": 0
    },
    "correctness": {
      "syntax_valid": true
    },
    "code_quality": {
      "documentation_ratio": 0.5,
      "function_count": 1
    }
  }
}
```

**Example - Evaluate regression:**
```bash
echo '{
  "command": "evaluate",
  "old_metrics": {
    "execution_time_ms": 5.0,
    "memory_usage_kb": 1024,
    "timestamp": "2025-11-17T10:00:00",
    "version": "1.0.0",
    "security_issues": 2
  },
  "new_metrics": {
    "execution_time_ms": 7.5,
    "memory_usage_kb": 1280,
    "timestamp": "2025-11-17T12:00:00",
    "version": "1.1.0",
    "security_issues": 0
  },
  "requirement_change": {
    "previous_requirement": "Parse JSON",
    "new_requirement": "Parse JSON with validation",
    "change_summary": "Added schema validation and security checks",
    "feature_additions": ["Schema validation", "Security scanning"],
    "feature_removals": [],
    "breaking_changes": []
  },
  "old_code": "def parse(data): return json.loads(data)",
  "new_code": "def parse(data): validate(data); return json.loads(data)"
}' | python code_evolver/tools/perf/performance_regression_evaluator.py evaluate
```

**Output:**
```json
{
  "success": true,
  "evaluation": {
    "score": 85,
    "reasoning": "The 50% performance regression is reasonable. Schema validation and security scanning are important features that justify the performance cost. Security issues were reduced from 2 to 0.",
    "recommendation": "ACCEPT",
    "confidence": "high"
  }
}
```

**Key Features:**
- Uses 4B LLM (qwen2.5-coder:3b)
- Scores 0-100 (0=reject, 100=accept)
- Combines static analysis with LLM reasoning
- Considers feature additions, security improvements, complexity changes
- Prevents false-positive regression rejections

### 3. Comprehensive Tool Profiler

**Purpose:** Orchestrates complete profiling workflow

**Example:**
```bash
echo '{
  "tool_code": "def add(a, b): return a + b",
  "test_input": {"a": 5, "b": 3},
  "requirement": "Add two numbers"
}' | python code_evolver/tools/perf/comprehensive_tool_profiler.py simple_adder
```

**Output:**
```json
{
  "tool_id": "simple_adder",
  "status": "completed",
  "workflow_steps": [
    {"step": "benchmark", "status": "completed"},
    {"step": "static_analysis", "status": "completed"},
    {"step": "regression_evaluation", "status": "skipped"},
    {"step": "rag_update", "status": "completed"}
  ],
  "metadata": {
    "performance": {...},
    "static_analysis": {...},
    "source": "...",
    "requirement": "..."
  }
}
```

**Exit Codes:**
- `0` - Success, tool accepted
- `1` - Failure (benchmark failed)
- `2` - Review required (human decision needed)

## Workflow Integration

### Code Generation Workflow

```
1. LLM generates tool code
   ↓
2. Run unit tests (pytest)
   ↓ (if tests pass)
3. Run comprehensive_tool_profiler
   ↓
4. Store in RAG with metadata:
   - Performance metrics
   - Static analysis findings
   - Source code
   - Requirement specification
```

### Code Mutation Workflow

```
1. Load old version from RAG
   ↓
2. LLM mutates code (add features, fix bugs, etc.)
   ↓
3. Run unit tests (pytest)
   ↓ (if tests pass)
4. Run comprehensive_tool_profiler with old_version_data
   ↓
5. LLM evaluates regression:
   - ACCEPT (score >= 80) → Update RAG
   - REJECT (score <= 30) → Revert or re-try
   - REVIEW (score 31-79) → Human decision
   ↓ (if accepted)
6. Save new version to RAG
```

### Optimization Workflow

```
1. Run comprehensive_tool_profiler on current code
   ↓
2. If performance is inadequate:
   ↓
3. Use code_optimizer to improve performance
   ↓
4. Run comprehensive_tool_profiler again
   ↓
5. Compare old vs new:
   - If faster and tests pass → ACCEPT
   - If slower → REJECT (optimization failed)
   - If marginally faster → REVIEW
```

## RAG Metadata Schema

Tools are tagged in RAG with comprehensive metadata:

```json
{
  "tool_id": "example_tool",
  "version": "1.1.0",
  "metadata": {
    "performance": {
      "execution_time_ms": 7.8,
      "memory_usage_kb": 1280,
      "last_benchmarked": "2025-11-17T12:00:00",
      "test_runs": 3,
      "test_script": "#!/usr/bin/env python3...",
      "regression_evaluation": {
        "score": 85,
        "recommendation": "ACCEPT",
        "reasoning": "...",
        "confidence": "high"
      }
    },
    "static_analysis": {
      "complexity": {
        "average_complexity": 3.2,
        "grade": "B"
      },
      "security": {
        "total_issues": 0,
        "severity_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
      },
      "correctness": {
        "syntax_valid": true
      },
      "code_quality": {
        "documentation_ratio": 0.75,
        "function_count": 4
      }
    },
    "source": "<complete source code>",
    "requirement": "<requirement specification>",
    "documentation": "<auto-generated docs>",
    "last_updated": "2025-11-17T12:30:00"
  }
}
```

## Decision Logic

### Regression Evaluation Scoring

**0-30 (REJECT):**
- Large regression (>50%) with no meaningful changes
- Performance degraded but no features added
- Security issues increased
- Optimization attempt that made things worse

**31-79 (REVIEW - Human Decision):**
- Moderate regression (20-50%) with some changes
- Conflicting signals (complexity better but performance worse)
- Low confidence from LLM
- Significant changes but unclear if regression is justified

**80-100 (ACCEPT):**
- Performance improved
- Minor regression (<10%) with feature additions
- Security improvements justify performance cost
- Complexity reduced significantly

### Common Scenarios

| Scenario | Typical Score | Recommendation | Reasoning |
|----------|---------------|----------------|-----------|
| Security improvement | 75-90 | ACCEPT | Security > Speed |
| Feature addition | 60-80 | ACCEPT if <30% regression | Features justify cost |
| Refactoring | 70-85 | ACCEPT if complexity improved | Maintainability matters |
| Bug fix | 50-70 | REVIEW | Depends on bug severity |
| Optimization failure | 10-25 | REJECT | Should improve, not degrade |
| No changes | 5-15 | REJECT | Investigate environment |

## Best Practices

### 1. Always Profile After Changes

Run comprehensive profiling after:
- Initial code generation
- Feature additions
- Bug fixes
- Refactoring
- Optimization attempts

### 2. Provide Meaningful Requirements

Good requirement specifications help the LLM evaluate regressions:

❌ Bad: "Process data"
✅ Good: "Process JSON data with schema validation and security checks"

### 3. Use Representative Test Inputs

Test inputs should exercise main code paths:

❌ Bad: `{"data": []}`
✅ Good: `{"data": [1, 2, 3, 4, 5], "options": {"validate": true}}`

### 4. Track Trends Over Time

Use RAG metadata to:
- Monitor performance trends
- Identify performance regressions early
- Select optimal tools for workflows
- Detect performance degradation patterns

### 5. Don't Optimize Prematurely

Some regressions are acceptable:
- Security improvements
- Feature additions
- Code clarity improvements
- Maintainability enhancements

The LLM evaluation prevents getting locked into never accepting these justified changes.

### 6. Review Flagged Tools

When status = "review_required":
- Examine the LLM reasoning
- Check if requirement changed significantly
- Consider if performance cost is acceptable
- Make informed decision to accept or reject

## Troubleshooting

### Benchmark Fails

**Issue:** `"success": false` in benchmark result

**Solutions:**
1. Check test_input is valid for the tool
2. Verify tool code has no syntax errors
3. Ensure required dependencies are available
4. Check if mocking is interfering with tool logic

### LLM Evaluation Times Out

**Issue:** Evaluation takes >30 seconds

**Solutions:**
1. Use faster 3B-4B model (qwen2.5-coder:3b)
2. Simplify requirement descriptions
3. Reduce code size in old_code/new_code
4. Check ollama is running properly

### Regression Always Rejected

**Issue:** LLM always returns low scores even with good reasons

**Solutions:**
1. Improve requirement change descriptions
2. List feature_additions explicitly
3. Document why changes were necessary
4. Use more detailed change_summary
5. Consider using larger LLM (7B) for better reasoning

### RAG Update Fails

**Issue:** `"rag_update": {"success": false}`

**Solutions:**
1. Verify tools/index.json exists
2. Check file permissions
3. Ensure JSON is valid (not corrupted)
4. Create tools/index.json if missing: `echo '{}' > tools/index.json`

## Examples

### Example 1: Security Improvement

```bash
# Old version (no validation)
old_code = "def parse(data): return json.loads(data)"

# New version (with validation)
new_code = "def parse(data): validate_schema(data); return json.loads(sanitize(data))"

# Performance: 50% slower
# Security issues: 2 → 0
# LLM Score: 85/100
# Recommendation: ACCEPT
# Reasoning: "Security improvements justify performance cost"
```

### Example 2: Feature Addition

```bash
# Old version (basic processing)
old_code = "def process(items): return [x*2 for x in items]"

# New version (with filtering and logging)
new_code = "def process(items): filtered = [x for x in items if x > 0]; log(filtered); return [x*2 for x in filtered]"

# Performance: 25% slower
# Features added: ["Filtering", "Logging"]
# LLM Score: 72/100
# Recommendation: REVIEW
# Reasoning: "Moderate regression for moderate features - review if logging is necessary"
```

### Example 3: Optimization Failure

```bash
# Old version (working)
old_code = "def sort_data(data): return sorted(data)"

# New version (attempted optimization)
new_code = "def sort_data(data): return bubble_sort(data)"  # Worse algorithm!

# Performance: 200% slower
# Features added: []
# LLM Score: 5/100
# Recommendation: REJECT
# Reasoning: "Optimization attempt made performance significantly worse with no benefits"
```

## Summary

The performance workflow tools provide:

1. **Accurate benchmarking** - 3 iterations with mocking
2. **Comprehensive analysis** - Complexity, security, correctness
3. **Intelligent regression evaluation** - LLM-based assessment
4. **Complete metadata** - Stored in RAG for future use
5. **Automated workflow** - From codegen to RAG tagging

This prevents:
- ❌ False positive regressions blocking valid improvements
- ❌ Accepting unjustified performance degradation
- ❌ Missing important quality metrics
- ❌ Losing track of tool evolution

And enables:
- ✅ Confident code evolution
- ✅ Data-driven optimization decisions
- ✅ Comprehensive tool quality tracking
- ✅ Automated acceptance/rejection with human review option
