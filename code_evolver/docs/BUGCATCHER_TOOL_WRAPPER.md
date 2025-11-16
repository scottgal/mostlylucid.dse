# BugCatcher Tool Wrapper

The BugCatcher Tool Wrapper allows you to wrap any tool call with exception monitoring and context tracking. This is especially useful for debugging workflows and evolving tools when issues arise.

## Overview

BugCatcher can wrap any tool execution to automatically:
- Track tool inputs and outputs
- Capture execution time
- Monitor for exceptions
- Associate context with failures
- Mark tools as 'debug' level for evolution

## Usage Methods

### 1. Decorator Pattern

Use the `@with_bugcatcher` decorator to wrap tool functions:

```python
from src.bugcatcher_wrapper import with_bugcatcher

@with_bugcatcher('my_analysis_tool', debug_level=True)
def analyze_data(data, threshold=0.5):
    """Analyze data and return results."""
    # Tool implementation
    results = perform_analysis(data, threshold)
    return results

# Tool is automatically monitored
result = analyze_data(my_data, threshold=0.7)
```

**Options:**
- `tool_name`: Name of the tool (required)
- `debug_level`: Mark as debug level (default: True)
- `capture_inputs`: Capture input arguments (default: True)
- `capture_outputs`: Capture output values (default: True)

### 2. Context Manager Pattern

Use `ToolExecutionWrapper` as a context manager:

```python
from src.bugcatcher_wrapper import ToolExecutionWrapper

with ToolExecutionWrapper(
    'data_processor',
    workflow_id='wf_123',
    step_id='step_5',
    debug_level=True
) as wrapper:
    # Your tool code
    result = process_data(input_data)

    # Optionally track output
    wrapper.track_output(result)
```

**Benefits:**
- Explicit control over monitoring scope
- Can track multiple outputs
- Clear workflow/step association

### 3. Functional Pattern

Use `wrap_tool_call()` to wrap function calls:

```python
from src.bugcatcher_wrapper import wrap_tool_call

result = wrap_tool_call(
    'llm_generator',
    generate_text,
    args=(prompt, model),
    kwargs={'max_tokens': 100},
    workflow_id='wf_123',
    step_id='step_2',
    debug_level=True
)
```

**Use Cases:**
- Dynamic tool invocation
- Wrapping third-party functions
- Runtime tool selection

### 4. Debug Convenience Function

Use `debug_wrap_tool()` for quick debug wrapping:

```python
from src.bugcatcher_wrapper import debug_wrap_tool

# Automatically uses debug_level=True
result = debug_wrap_tool(
    'vector_search',
    search_function,
    query,
    top_k=10
)
```

## Debug Level

Tools marked with `debug_level=True` are:
- Available for debugging workflow issues
- Captured with full context for evolution
- Easily identifiable in Loki logs
- Candidates for optimization/evolution

### Query Debug Tools in Grafana

```logql
# All debug-level tool executions
{job="code_evolver_bugcatcher"} |= "debug_level"

# Debug tools that failed
{job="code_evolver_bugcatcher"} |= "debug_level" |= "failed"

# Specific debug tool
{job="code_evolver_bugcatcher", tool_name="my_tool"} |= "debug_level"
```

## Integration with Workflows

### Automatic Workflow Integration

BugCatcher already integrates with WorkflowTracker, but you can add explicit tool wrapping for additional context:

```python
from src.workflow_tracker import WorkflowTracker
from src.bugcatcher_wrapper import ToolExecutionWrapper

tracker = WorkflowTracker('wf_1', 'Data Pipeline')
step = tracker.add_step('step_1', 'data_validator', 'Validate input data')

tracker.start_step('step_1')

# Wrap tool execution with additional monitoring
with ToolExecutionWrapper(
    'data_validator',
    workflow_id='wf_1',
    step_id='step_1',
    debug_level=True
) as wrapper:
    try:
        result = validate_data(input_data)
        wrapper.track_output(result)
        tracker.complete_step('step_1', str(result))
    except Exception as e:
        tracker.fail_step('step_1', str(e))
        raise
```

### Wrapping Existing Tools

Wrap existing tool functions without modifying them:

```python
from src.bugcatcher_wrapper import with_bugcatcher

# Original tool function
def existing_tool(arg1, arg2):
    return arg1 + arg2

# Wrap it for monitoring
monitored_tool = with_bugcatcher('existing_tool', debug_level=True)(existing_tool)

# Use monitored version
result = monitored_tool(10, 20)
```

## Evolution and Debugging

### Using BugCatcher for Tool Evolution

When a tool fails in a workflow:

1. **Identify the failure** in Grafana:
   ```logql
   {job="code_evolver_bugcatcher", tool_name="my_tool", severity="error"}
   ```

2. **Review captured context**:
   - Input arguments
   - Output values (if any)
   - Exception traceback
   - Execution time
   - Workflow context

3. **Create improved version**:
   ```python
   @with_bugcatcher('my_tool_v2', debug_level=True)
   def my_tool_v2(input_data):
       # Improved implementation based on failure analysis
       validated_input = validate(input_data)
       return process(validated_input)
   ```

4. **Compare performance**:
   ```logql
   # Compare v1 vs v2 failure rates
   rate({job="code_evolver_bugcatcher", tool_name="my_tool"}[1h])
   rate({job="code_evolver_bugcatcher", tool_name="my_tool_v2"}[1h])
   ```

### Auto-Repair Integration

BugCatcher data can feed into auto-repair systems:

```python
from src.bugcatcher_wrapper import wrap_tool_call

def auto_repair_tool_call(tool_name, tool_func, *args, **kwargs):
    """Execute tool with auto-repair on failure."""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            return wrap_tool_call(
                f"{tool_name}_attempt_{attempt}",
                tool_func,
                args=args,
                kwargs=kwargs,
                debug_level=True
            )
        except Exception as e:
            if attempt < max_retries - 1:
                # Analyze failure and adjust parameters
                kwargs = adjust_parameters_based_on_error(e, kwargs)
            else:
                raise
```

## Performance Considerations

### Overhead

BugCatcher tool wrapping has minimal overhead:
- ~1-5ms per wrapped call
- Batched Loki writes
- Async-friendly design

### Selective Wrapping

Wrap tools selectively based on:
- **Critical tools**: Always wrap
- **Unstable tools**: Wrap during development
- **Performance-sensitive**: Wrap only in debug mode

```python
import os

DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

if DEBUG_MODE:
    @with_bugcatcher('performance_tool', debug_level=True)
    def performance_tool(data):
        return process(data)
else:
    def performance_tool(data):
        return process(data)
```

## Best Practices

1. **Always use debug_level=True** for tools under development
2. **Wrap tool boundaries**, not internal functions
3. **Capture meaningful context** (workflow_id, step_id)
4. **Review BugCatcher data** regularly to identify patterns
5. **Evolve tools** based on captured failures
6. **Remove debug wrapping** for stable, production tools

## Future: PerfCatcher Integration

The same wrapper pattern will support PerfCatcher:

```python
from src.bugcatcher_wrapper import with_bugcatcher
from src.perfcatcher_wrapper import with_perfcatcher  # Future

@with_bugcatcher('my_tool', debug_level=True)
@with_perfcatcher('my_tool', track_memory=True)  # Future
def my_tool(data):
    return process(data)
```

## Examples

### Example 1: Wrapping LLM Call

```python
from src.bugcatcher_wrapper import wrap_tool_call

result = wrap_tool_call(
    'llm_code_generator',
    llm_client.generate,
    args=(model, prompt),
    kwargs={'max_tokens': 2000, 'temperature': 0.7},
    workflow_id='code_gen_wf',
    step_id='generate_step',
    debug_level=True
)
```

### Example 2: Wrapping Database Query

```python
from src.bugcatcher_wrapper import ToolExecutionWrapper

with ToolExecutionWrapper('db_query', debug_level=True) as wrapper:
    results = db.query("SELECT * FROM users WHERE active = true")
    wrapper.track_output(f"Returned {len(results)} rows")
```

### Example 3: Wrapping File Operation

```python
from src.bugcatcher_wrapper import debug_wrap_tool

def read_config(file_path):
    with open(file_path) as f:
        return json.load(f)

# Wrap with debug monitoring
config = debug_wrap_tool('config_reader', read_config, 'config.json')
```

## Troubleshooting

### BugCatcher Not Available

If BugCatcher is not initialized, the wrapper gracefully degrades:

```python
# This works even if BugCatcher is disabled
@with_bugcatcher('my_tool')
def my_tool():
    return "result"  # Executes normally without monitoring
```

### Logs Not Appearing

Check that:
1. BugCatcher is enabled: `bugcatcher.enabled: true`
2. Loki is running: `docker ps | grep loki`
3. `debug_level` is being captured: Search for `"debug_level": true`

### Performance Impact

If wrapping causes performance issues:
1. Disable output capture: `capture_outputs=False`
2. Disable input capture: `capture_inputs=False`
3. Use selective wrapping (only in debug mode)

## Summary

The BugCatcher Tool Wrapper provides:
- **Flexible APIs**: Decorator, context manager, and functional patterns
- **Debug marking**: Identify tools for evolution/debugging
- **Full context capture**: Inputs, outputs, exceptions, timing
- **Workflow integration**: Associate tools with workflows/steps
- **Minimal overhead**: Lightweight, async-friendly design

Use it to wrap any tool and gain comprehensive monitoring for debugging and evolution!
