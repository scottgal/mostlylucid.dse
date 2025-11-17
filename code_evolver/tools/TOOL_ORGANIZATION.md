# Tool Organization

This directory contains tools organized by their primary purpose and artifact type.

## Directory Structure

```
tools/
├── optimization/     - Code and workflow optimization tools
├── fixer/           - Bug fixing and error correction tools
├── perf/            - Performance testing, profiling, and benchmarking tools
├── debug/           - Debugging, validation, and static analysis tools
├── custom/          - Custom workflow tools (git, github, http_server, etc.)
├── executable/      - General-purpose executable tools
├── llm/             - LLM-based tools for generation and analysis
└── openapi/         - OpenAPI/API-related tools
```

## Tool Categories

### 1. Optimization Tools (`optimization/`)

Tools focused on improving code performance, resource usage, and efficiency.

**Tools:**
- `code_optimizer.yaml` - Comprehensive code optimization with hierarchical optimization levels
- `performance_optimizer.yaml` - LLM-based performance optimization
- `rag_cluster_optimizer.yaml` - RAG memory optimization and clustering
- `optimize_cluster.yaml` - Cluster optimization for distributed systems

**Use cases:**
- Optimize code for speed and memory
- Improve algorithm complexity
- Refactor for better performance
- System-level optimization

### 2. Fixer Tools (`fixer/`)

Tools that automatically detect and fix bugs, errors, and code issues.

**Tools:**
- `circular_import_fixer.py/yaml` - Detects and fixes circular import issues
- `module_not_found_fixer.py/yaml` - Resolves missing module imports
- `find_code_fix_pattern.py/yaml` - Finds reusable fix patterns
- `store_code_fix_pattern.py/yaml` - Stores fix patterns for reuse

**Use cases:**
- Fix import errors automatically
- Resolve circular dependencies
- Apply known fix patterns
- Build a library of code fixes

### 3. Performance Tools (`perf/`)

Tools for performance testing, profiling, benchmarking, and load testing.

**Tools:**
- `timeit_optimizer.py/yaml` - **NEW** Performance benchmarking with automatic mocking
- `performance_regression_evaluator.py/yaml` - **NEW** LLM-based regression assessment
- `comprehensive_tool_profiler.py/yaml` - **NEW** Complete profiling orchestrator
- `pyinstrument_profiler.yaml` - Python code profiler
- `performance_profiler.yaml` - LLM-based performance profiling
- `behave_test_generator.py/yaml` - BDD test generator
- `locust_load_tester.py/yaml` - Load testing tool
- `create_behave_spec.py/yaml` - Create BDD specifications
- `create_locust_spec.py/yaml` - Create load test specifications

**Use cases:**
- Benchmark tool performance with mocking
- Evaluate performance regressions intelligently
- Profile complete tools (performance + static analysis + RAG)
- Generate performance tests
- Load testing and stress testing
- Track performance metrics in RAG
- Prevent false-positive regression rejections

### 4. Debug Tools (`debug/`)

Tools for debugging, validation, static analysis, and code quality checks.

**Tools:**
- `bugcatcher.yaml` - General bug detection
- `call_tool_validator.py/yaml` - Validates tool call correctness
- `dependency_analyzer.py/yaml` - Analyzes code dependencies
- `json_output_validator.py/yaml` - Validates JSON output
- `python_syntax_validator.py/yaml` - Python syntax checker
- `mypy_type_checker.yaml` - Type checking with mypy
- `isort_import_checker.yaml` - Import sorting validation
- `run_static_analysis.py/yaml` - Static code analysis
- `parse_static_analysis.py/yaml` - Parse static analysis results
- `node_runtime_import_validator.py/yaml` - Node.js import validation

**Use cases:**
- Validate code correctness
- Type checking and linting
- Dependency analysis
- Static analysis
- Code quality checks

## Featured Tools

### Timeit Optimizer

The **Timeit Performance Optimizer** (`perf/timeit_optimizer.py`) is a comprehensive performance testing tool that:

### Key Features

1. **Auto-generates benchmark scripts** - Creates self-contained Python scripts for testing
2. **Runs 3 benchmark iterations** - Selects the best result to account for system variance
3. **Tracks execution time** - Millisecond-precision timing using `time.perf_counter()`
4. **Monitors memory usage** - KB-level memory tracking using `tracemalloc`
5. **Automatic mocking** - Mocks tool calls and external services to isolate performance
6. **RAG integration** - Updates tool metadata with performance metrics

### Usage Examples

#### Generate a performance test script:

```bash
echo '{
  "command": "generate",
  "tool_code": "def process(data): return [x*2 for x in data]",
  "tool_id": "data_processor",
  "test_input": {"data": [1,2,3,4,5]}
}' | python code_evolver/tools/perf/timeit_optimizer.py generate
```

#### Run a benchmark:

```bash
echo '{
  "command": "benchmark",
  "tool_code": "def add(a, b): return a + b",
  "tool_id": "simple_adder",
  "test_input": {"a": 5, "b": 3}
}' | python code_evolver/tools/perf/timeit_optimizer.py benchmark
```

#### Update RAG metadata:

```bash
echo '{
  "command": "update_rag",
  "tool_id": "data_processor",
  "best_run": {
    "execution_time_ms": 0.023,
    "memory_usage_kb": 128.5,
    "calls_to_mocked_tools": [],
    "test_run_number": 2,
    "timestamp": "2025-11-17 18:30:00"
  }
}' | python code_evolver/tools/perf/timeit_optimizer.py update_rag
```

### Generated Test Scripts

The tool generates **4B-class** (fully self-contained) test scripts that:

- Include all necessary imports
- Embed the tool code under test
- Set up mocking for dependencies
- Include test input data
- Run 3 benchmark iterations
- Output JSON results to stdout
- Can be executed standalone

Example generated script:

```python
#!/usr/bin/env python3
"""Auto-generated performance test for tool: my_tool"""
import json
import sys
import time
import tracemalloc
from unittest.mock import Mock, patch

# Tool code under test
def my_function(input_data):
    return process(input_data)

# Mock setup (if needed)
external_api = Mock(return_value={'status': 'ok'})

# Run 3 benchmark iterations
# Select best run (lowest execution time)
# Output JSON with metrics
```

### Mocking Strategy

The optimizer automatically detects and mocks:

1. **Tool calls** - Pattern matching for `call_tool`, `execute_tool`, etc.
2. **HTTP clients** - `requests`, `httpx`, `urllib`
3. **LLM APIs** - `ollama`, `openai`, `anthropic`
4. **External services** - Database calls, file I/O, etc.

All mocked calls return successful responses to isolate the tool's performance.

### Performance Metrics

For each benchmark run, the tool tracks:

- **Execution time** - Milliseconds with high precision
- **Memory usage** - Peak memory allocation in KB
- **Run number** - 1, 2, or 3
- **Timestamp** - When the test was run
- **Mocked dependencies** - List of mocked tools/services

### RAG Integration

After successful benchmarking, the tool updates the tool registry at `./code_evolver/tools/index.json`:

```json
{
  "tool_id": "my_tool",
  "metadata": {
    "performance": {
      "execution_time_ms": 0.023,
      "memory_usage_kb": 128.5,
      "last_benchmarked": "2025-11-17 18:30:00",
      "test_runs": 3
    }
  }
}
```

This enables:
- Performance regression detection
- Tool selection optimization (prefer faster tools)
- Performance trend tracking
- Optimization target identification

### Performance Regression Evaluator

The **Performance Regression Evaluator** (`perf/performance_regression_evaluator.py`) prevents getting locked into never accepting performance regressions by using LLM-based assessment.

**Key Problem Solved:**
Traditional regression testing blocks ANY performance degradation, even when justified. This tool uses a 4B-class LLM to evaluate whether regressions are reasonable given requirement changes.

**Key Features:**

1. **LLM-Based Assessment** - Uses qwen2.5-coder:3b to evaluate regression reasonableness
2. **Static Analysis Integration** - Analyzes complexity, security, correctness, code quality
3. **0-100 Scoring** - Quantifies regression acceptability
4. **Smart Recommendations** - ACCEPT (80-100), REVIEW (31-79), REJECT (0-30)
5. **Context-Aware** - Considers feature additions, security improvements, complexity changes

**How It Works:**

The LLM is prompted with:
```
Given these changes since the last test, is the performance change
reasonable for the requirement changes?

Performance: 50% slower
Requirement Change: Added schema validation and security scanning
Feature Additions: ["Schema validation", "Security scanning"]
Security Issues: 2 → 0

Answer with score 0-100 and reasoning.
```

LLM Response:
```json
{
  "score": 85,
  "reasoning": "The 50% regression is reasonable. Security improvements justify the cost.",
  "recommendation": "ACCEPT",
  "confidence": "high"
}
```

**Common Scenarios:**

| Scenario | Typical Score | Outcome |
|----------|---------------|---------|
| Security improvement | 75-90 | ACCEPT |
| Feature addition | 60-80 | ACCEPT (if <30% regression) |
| Bug fix | 50-70 | REVIEW |
| Optimization failure | 10-25 | REJECT |
| No changes | 5-15 | REJECT (investigate) |

**Static Analysis Components:**

- **Complexity** - Radon cyclomatic complexity (fallback: line counting)
- **Security** - Bandit security scanner (fallback: pattern matching)
- **Correctness** - Python syntax validation
- **Code Quality** - Docstring coverage, documentation ratio

### Comprehensive Tool Profiler

The **Comprehensive Tool Profiler** (`perf/comprehensive_tool_profiler.py`) orchestrates the complete profiling workflow.

**Workflow Steps:**

1. **Benchmark Performance** → Uses timeit_optimizer
2. **Run Static Analysis** → Uses performance_regression_evaluator
3. **Evaluate Regression** → LLM assessment (if old version exists)
4. **Build Metadata** → Combine all metrics
5. **Update RAG** → Store in tools/index.json

**Complete RAG Metadata:**

```json
{
  "tool_id": "my_tool",
  "metadata": {
    "performance": {
      "execution_time_ms": 7.8,
      "memory_usage_kb": 1280,
      "regression_evaluation": {
        "score": 85,
        "recommendation": "ACCEPT",
        "reasoning": "Security improvements justify cost"
      }
    },
    "static_analysis": {
      "complexity": {"average_complexity": 3.2, "grade": "B"},
      "security": {"total_issues": 0},
      "correctness": {"syntax_valid": true},
      "code_quality": {"documentation_ratio": 0.75}
    },
    "source": "<source code>",
    "requirement": "<requirement spec>",
    "documentation": "<auto-generated docs>"
  }
}
```

**Exit Codes:**
- `0` - Success (tool accepted)
- `1` - Failure (benchmark/tests failed)
- `2` - Review Required (human decision needed)

**Usage:**

```bash
# Initial profiling (no old version)
echo '{
  "tool_code": "def add(a, b): return a + b",
  "test_input": {"a": 5, "b": 3},
  "requirement": "Add two numbers"
}' | python comprehensive_tool_profiler.py simple_adder

# With regression check (has old version)
echo '{
  "tool_code": "def add(a, b): validate(a, b); return a + b",
  "test_input": {"a": 5, "b": 3},
  "requirement": "Add two numbers with validation",
  "old_version_data": {...}
}' | python comprehensive_tool_profiler.py simple_adder
```

See `PERFORMANCE_WORKFLOW_GUIDE.md` for complete documentation.

## Workflow Integration

### Using Timeit Optimizer in Workflows

```yaml
workflow:
  steps:
    - id: "benchmark_tool"
      tool: "timeit_optimizer"
      action: "benchmark"
      inputs:
        tool_code: "{{ generated_code }}"
        tool_id: "{{ tool_name }}"
        test_input: "{{ sample_input }}"
      outputs:
        - best_run
        - performance_metrics

    - id: "update_metadata"
      tool: "timeit_optimizer"
      action: "update_rag"
      condition: "benchmark succeeded"
      inputs:
        tool_id: "{{ tool_name }}"
        best_run: "{{ benchmark_tool.best_run }}"
```

### Optimization Workflow Pattern

A typical optimization workflow:

1. **Generate code** - Create initial tool implementation
2. **Generate tests** - Create unit tests for the tool
3. **Run tests** - Verify correctness
4. **Benchmark** - Run performance benchmarks (3 iterations)
5. **Optimize** - Use code_optimizer if performance is inadequate
6. **Re-benchmark** - Verify optimization improved performance
7. **Update RAG** - Store performance metrics for future reference

## Best Practices

### When to Use Each Category

- **optimization/** - When you need to improve existing code performance
- **fixer/** - When you have known errors or issues to correct
- **perf/** - When you need to measure, test, or benchmark performance
- **debug/** - When you need to validate, analyze, or debug code

### Performance Testing Best Practices

1. **Always benchmark after fixes** - Only benchmark fully working code
2. **Use representative inputs** - Test with realistic data
3. **Mock dependencies** - Isolate tool performance from external factors
4. **Run multiple iterations** - Account for system variance (3 runs minimum)
5. **Update RAG only on success** - Store metrics only for working code
6. **Keep test scripts** - Save generated scripts for debugging
7. **Track trends** - Monitor performance over time

### Tool Organization Guidelines

- Place tools in the most specific category that fits
- Tools can exist in multiple locations (original + category)
- Use artifact_type metadata to aid discovery
- Tag tools comprehensively for search
- Document tool purpose and usage in YAML

## Migration Notes

Existing tools in `executable/` and `llm/` remain in place. The new category folders contain **copies** of relevant tools for easier discovery and organization. This dual-location approach ensures:

- Backward compatibility with existing workflows
- Easier discovery by category
- Clear organization for new tools
- No breaking changes to existing systems

## Future Enhancements

Potential additions to tool categories:

- **security/** - Security scanning and vulnerability detection
- **refactor/** - Code refactoring and restructuring tools
- **migration/** - Code migration and transformation tools
- **documentation/** - Auto-documentation and explanation tools
