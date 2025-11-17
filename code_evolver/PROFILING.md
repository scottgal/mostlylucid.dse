# PyInstrument Profiling System

## Overview

The mostlylucid DiSE now includes comprehensive PyInstrument-based profiling for performance analysis and optimization. Profiling helps identify bottlenecks, compare tool versions, evaluate workflow alternatives, and make data-driven optimization decisions.

## Features

- **Line-level profiling** - See exactly which lines are slow
- **Call stack analysis** - Understand function call hierarchies
- **Multiple output formats** - Text, HTML, JSON, and Speedscope
- **Version comparison** - Compare performance across tool versions
- **Optimization integration** - Feeds into the optimization pipeline
- **Zero overhead when disabled** - No performance impact in production

## Installation

```bash
pip install -r requirements.txt
```

This installs `pyinstrument>=4.6.0` along with other dependencies.

## Quick Start

### Enable Profiling

```bash
# Enable profiling globally
export CODE_EVOLVER_PROFILE=1

# Run your code
python chat_cli.py
```

Profiles are saved to `./profiles/` by default.

### Custom Output Directory

```bash
export PROFILE_OUTPUT_DIR=/path/to/profiles
```

## Usage Patterns

### 1. Context Manager (Recommended)

```python
from code_evolver.src.profiling import ProfileContext

with ProfileContext("operation_name", metadata={"version": "1.0"}):
    # Code to profile
    result = expensive_operation()
```

### 2. Decorator

```python
from code_evolver.src.profiling import profile_function

@profile_function(name="my_function", metadata={"category": "llm"})
def my_function(x, y):
    return x + y
```

### 3. Manual Control

```python
from code_evolver.src.profiling import Profiler

profiler = Profiler(name="custom_operation", metadata={"tool": "pyinstrument"})
profiler.start()

# Your code here
result = do_work()

profile_data = profiler.stop()  # Automatically saved
```

## Integration Points

The profiling system is integrated into key components:

### 1. LLM Calls (70-90% of latency)

```python
# In ollama_client.py
with ProfileContext(f"LLM.generate.{model_key}", metadata={
    "model": model,
    "prompt_length": len(prompt)
}):
    result = self.generate(...)
```

**Reveals:**
- Network vs inference time
- JSON parsing overhead
- Token counting cost
- Model-specific performance

### 2. Node Execution

```python
# In node_runner.py
with ProfileContext(f"NodeRunner.run_node.{node_id}", metadata={
    "node_id": node_id,
    "timeout_ms": timeout_ms
}):
    stdout, stderr, metrics = self.run_node(...)
```

**Reveals:**
- Subprocess overhead
- Python startup time
- PYTHONPATH setup cost
- Process communication latency

### 3. Optimization Pipeline

```python
# In optimization_pipeline.py
with ProfileContext(f"OptimizationPipeline.optimize_artifact.{level}", metadata={
    "artifact_id": artifact.artifact_id,
    "optimization_level": level
}):
    result = self.optimize_artifact(...)
```

**Reveals:**
- Cost/benefit of each optimization tier
- RAG lookup overhead
- Recursive optimization cost
- Cloud API latency

## Profile Registry

The global registry collects profiles for comparison and analysis:

```python
from code_evolver.src.profiling import get_global_registry

registry = get_global_registry()

# Get all profiles for an operation
profiles = registry.get_profiles("LLM.generate.generator")

# Compare versions
comparison = registry.compare_profiles(
    name="operation_name",
    version1="1.0",
    version2="2.0"
)

if comparison["recommendation"] == "upgrade":
    print(f"Version 2.0 is {comparison['improvement_pct']:.1f}% faster!")

# Export summary
summary = registry.export_summary(output_path="profiles/summary.json")
```

## Version Comparison Example

```python
# Profile v1.0 of a tool
with ProfileContext("tool_execution", metadata={"version": "1.0"}):
    result_v1 = execute_tool_v1()

# Profile v2.0 of the same tool
with ProfileContext("tool_execution", metadata={"version": "2.0"}):
    result_v2 = execute_tool_v2()

# Compare
registry = get_global_registry()
comparison = registry.compare_profiles("tool_execution", "1.0", "2.0")

print(f"Improvement: {comparison['improvement_pct']:.1f}%")
print(f"Recommendation: {comparison['recommendation']}")
```

## Output Formats

### Text Report (Console)

```
  _     ._   __/__   _ _  _  _ _/_   Recorded: 12:34:56  Samples:  142
 /_//_/// /_\ / //_// / //_'/ //     Duration: 5.234     CPU time: 4.891
/   _/                      v4.6.0

Program: chat_cli.py

5.234 <module>  chat_cli.py:1
├─ 4.789 OllamaClient.generate  ollama_client.py:214
│  ├─ 4.123 requests.post  requests/api.py:112
│  │  └─ 4.098 Session.request  requests/sessions.py:587
│  └─ 0.321 json.loads  json/__init__.py:293
└─ 0.234 NodeRunner.run_node  node_runner.py:55
```

### HTML Report (Interactive)

- Flame graph visualization
- Collapsible call trees
- Search and filter
- Timeline view

### JSON (Machine-Readable)

```json
{
  "name": "LLM.generate.generator",
  "duration_ms": 5234.5,
  "timestamp": "2025-01-15T12:34:56",
  "metadata": {
    "model": "qwen2.5-coder:14b",
    "prompt_length": 1024
  },
  "profile_json": {
    "root_frame": {
      "function": "generate",
      "file_path": "ollama_client.py",
      "line_no": 214,
      "time": 5.234,
      "children": [...]
    }
  }
}
```

## Tool-Driven Profiling

Tools can specify profiling requirements in their YAML definitions:

```yaml
name: "Slow Tool"
type: "executable"
metadata:
  speed_tier: "slow"  # Profile more thoroughly
  profile_breakdown:
    - "network_time"
    - "parsing_time"
    - "execution_time"
```

The profiling system uses these hints to:
1. Enable detailed profiling for slow tools
2. Track specific metrics defined in `profile_breakdown`
3. Compare against expected latency budgets
4. Trigger optimization when performance degrades

## Optimization Workflow

```
1. Profile current version
   ↓
2. Identify bottlenecks (LLM, I/O, CPU)
   ↓
3. Optimization pipeline suggests alternatives
   ↓
4. Profile alternative implementations
   ↓
5. Compare versions (ProfileRegistry)
   ↓
6. Auto-upgrade if improvement > 10%
   ↓
7. Update tool version metadata
   ↓
8. Trigger code migration (if no breaking changes)
```

## Performance Insights

### What PyInstrument Reveals

**LLM Operations:**
- 70-90% of total latency
- Network time vs inference time
- JSON serialization overhead
- Token counting cost

**Node Execution:**
- Subprocess overhead (50-200ms)
- Python interpreter startup
- Module import time
- Process communication

**RAG Operations:**
- Embedding generation (30-50% of RAG time)
- Vector search latency
- Database query overhead
- Result ranking time

**Workflow Distribution:**
- Parallelization efficiency
- Task scheduling overhead
- Inter-process communication
- Resource contention

**Optimization Pipeline:**
- Local vs cloud vs deep costs
- RAG context retrieval time
- Recursive optimization overhead
- Cost/benefit analysis

## Testing

Run the profiling tests:

```bash
# Run all profiling tests
python -m pytest code_evolver/tests/test_profiling.py -v

# Run with profiling enabled
CODE_EVOLVER_PROFILE=1 python -m pytest code_evolver/tests/test_profiling.py -v

# Run specific test
python -m pytest code_evolver/tests/test_profiling.py::TestProfiler::test_profiler_basic_timing -v
```

## Best Practices

### 1. Use Meaningful Names

```python
# Good
with ProfileContext("LLM.generate.code_reviewer"):
    ...

# Bad
with ProfileContext("function1"):
    ...
```

### 2. Include Rich Metadata

```python
metadata = {
    "version": "2.1.0",
    "model": "qwen2.5-coder:14b",
    "prompt_length": len(prompt),
    "temperature": 0.7,
    "tool_type": "code_generator"
}
```

### 3. Profile at Multiple Levels

- **Function-level**: Individual operations
- **Component-level**: Entire subsystems
- **System-level**: End-to-end workflows

### 4. Compare Apples to Apples

When comparing versions:
- Use same input data
- Run on same hardware
- Average multiple runs
- Account for warm-up time

### 5. Don't Profile Everything

Only profile:
- Suspected bottlenecks
- Critical path operations
- Operations being optimized
- Periodic health checks

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODE_EVOLVER_PROFILE` | `0` | Enable/disable profiling (`1` = on) |
| `PROFILE_OUTPUT_DIR` | `./profiles` | Directory for profile output |
| `CODE_EVOLVER_DEBUG` | `1` | Enable debug logging |

## Advanced Features

### Custom Profile Analysis

```python
from code_evolver.src.profiling import Profiler

profiler = Profiler(name="custom_analysis")
profiler.start()

# Your code
result = expensive_operation()

profile_data = profiler.stop(save=False)

# Custom analysis
if profile_data.duration_ms > 1000:
    print(f"WARNING: Operation took {profile_data.duration_ms}ms")
    print(profile_data.profile_text)
```

### Batch Profiling

```python
operations = ["op1", "op2", "op3"]

for op in operations:
    with ProfileContext(op, metadata={"batch": "test_run"}):
        execute_operation(op)

# Compare all operations
registry = get_global_registry()
summary = registry.export_summary()

for op_name, stats in summary["profiles_by_operation"].items():
    print(f"{op_name}: {stats['avg_duration_ms']:.2f}ms")
```

## Troubleshooting

### PyInstrument Not Installed

If you see this warning:
```
PyInstrument profiling is enabled but pyinstrument is not installed.
Install with: pip install pyinstrument
```

Run:
```bash
pip install pyinstrument>=4.6.0
```

### No Profiles Generated

Check:
1. `CODE_EVOLVER_PROFILE=1` is set
2. `PROFILE_OUTPUT_DIR` is writable
3. Profiled code actually executed
4. No exceptions during profiling

### Large Profile Files

Profiles can be large (1-10MB). To reduce size:
- Profile smaller code sections
- Use `save=False` for temporary profiling
- Clean up old profiles regularly

## Future Enhancements

- [ ] Automatic profiling for slow operations (>5s)
- [ ] Integration with Qdrant cluster detection
- [ ] Tool RAG optimization based on profiles
- [ ] Workflow-level profiling and optimization
- [ ] Real-time profiling dashboard
- [ ] Distributed profiling across endpoints
- [ ] Profile-based cost modeling

## See Also

- `code_evolver/src/profiling.py` - Core implementation
- `code_evolver/tools/executable/pyinstrument_profiler.yaml` - Tool definition
- `code_evolver/tests/test_profiling.py` - Test suite
- [PyInstrument Documentation](https://github.com/joerick/pyinstrument)

## Contributing

When adding new components:

1. **Identify critical paths** - What's slow?
2. **Add ProfileContext** - Wrap expensive operations
3. **Include metadata** - Version, type, parameters
4. **Test profiling** - Verify profiles are generated
5. **Document findings** - Update this doc with insights

## Questions?

See the main README or open an issue on GitHub.
