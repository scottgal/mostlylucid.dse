# Tool Interceptors - Automatic Monitoring

Tool Interceptors provide automatic wrapping of **every tool call** with monitoring, debugging, and performance tracking. BugCatcher and PerfCatcher are applied automatically at the outermost level, catching exceptions both in and out.

## Overview

The interceptor system wraps all tool executions with a chain of interceptors:

```
Tool Call
  ↓
BugCatcher (outermost - catches everything)
  ↓
PerfCatcher (performance monitoring)
  ↓
[Your Custom Interceptors]
  ↓
Actual Tool Execution
  ↓
[Your Custom Interceptors] (on exit)
  ↓
PerfCatcher (track timing)
  ↓
BugCatcher (track output/exceptions)
  ↓
Return Result
```

## BugCatcher Interceptor

**Automatically enabled on every tool call** - catches all exceptions both entering and exiting tools.

### Features

- **Automatic wrapping**: No code changes needed
- **Exception capture**: Catches exceptions in and out
- **Full context**: Tracks workflow, step, inputs, outputs
- **LRU caching**: Associates exceptions with request context
- **Environment control**: Can disable via `BUGCATCHER_ENABLED=false`

### Environment Variables

```bash
# Disable BugCatcher entirely
export BUGCATCHER_ENABLED=false

# Enable (default)
export BUGCATCHER_ENABLED=true
```

### What It Captures

**On Entry:**
- Tool name
- Input arguments (first 500 chars)
- Workflow/step context
- Timestamp

**On Success:**
- Output (if `tracking.outputs` enabled)
- Execution time

**On Exception:**
- Full exception with traceback
- Request context from LRU cache
- Execution time
- All context data

### Usage

No code changes needed! BugCatcher automatically wraps all tools:

```python
# Tool is automatically wrapped
result = some_tool(arg1, arg2)

# If exception occurs, BugCatcher captures it automatically
# with full context from LRU cache
```

## PerfCatcher Interceptor

**Automatically enabled** - monitors tool performance and logs when variance is detected.

### How It Works

1. **Tracks Response Times**: Maintains rolling window of execution times per tool
2. **Calculates Baseline**: Mean and standard deviation from historical data
3. **Detects Variance**: Compares current execution to baseline
4. **Logs Anomalies**: Only logs when outside threshold (not every call)
5. **Captures Window**: Logs window of data when performance degrades

### Configuration

```bash
# Enable/disable (default: true)
export PERFCATCHER_ENABLED=true

# Variance threshold (default: 0.2 = 20%)
export PERFCATCHER_VARIANCE_THRESHOLD=0.2

# Window size for baseline (default: 100 samples)
export PERFCATCHER_WINDOW_SIZE=100

# Minimum samples before checking variance (default: 10)
export PERFCATCHER_MIN_SAMPLES=10
```

### Example

```python
# Tool executes normally
result = my_tool(data)

# PerfCatcher automatically:
# 1. Records execution time
# 2. Compares to rolling baseline
# 3. If variance > 20%, logs to Loki:
#    {
#      "tool_name": "my_tool",
#      "current_time_ms": 1500,
#      "mean_time_ms": 100,
#      "variance": 1.4,  # 140% variance!
#      "variance_threshold": 0.2
#    }
```

### Querying Performance Issues in Grafana

```logql
# All performance variances
{job="code_evolver_perfcatcher"}

# High variance issues
{job="code_evolver_perfcatcher", variance_level="high"}

# Specific tool
{job="code_evolver_perfcatcher", tool_name="llm_generator"}

# Variance over time
rate({job="code_evolver_perfcatcher"}[5m])
```

### Getting Performance Stats

```python
from src.tool_interceptors import get_global_interceptor_chain

chain = get_global_interceptor_chain()

# Find PerfCatcher interceptor
perf_interceptor = None
for interceptor in chain.interceptors:
    if isinstance(interceptor, PerfCatcherInterceptor):
        perf_interceptor = interceptor
        break

# Get stats for a tool
if perf_interceptor:
    stats = perf_interceptor.get_tool_stats('my_tool')
    print(f"Mean: {stats['mean_ms']:.1f}ms")
    print(f"P95: {stats['p95_ms']:.1f}ms")
    print(f"P99: {stats['p99_ms']:.1f}ms")
```

## Integration with Tools Manager

To integrate interceptors into `tools_manager.py`:

```python
from src.tool_interceptors import intercept_tool_call

class ToolsManager:
    def execute_tool(self, tool_id: str, inputs: dict, context: dict = None):
        """Execute a tool with automatic interceptor wrapping."""

        # Get tool
        tool = self.get_tool(tool_id)

        # Execute with interceptors (automatic BugCatcher + PerfCatcher)
        result = intercept_tool_call(
            tool_name=tool_id,
            tool_func=tool.execute,
            kwargs=inputs,
            context=context or {}
        )

        return result
```

## Custom Interceptors

You can create custom interceptors for specific needs:

```python
from src.tool_interceptors import ToolInterceptor, InterceptorPriority

class AuthInterceptor(ToolInterceptor):
    """Check authentication before tool execution."""

    def __init__(self):
        super().__init__(priority=InterceptorPriority.NORMAL)

    def before_execution(self, tool_name, args, kwargs, context):
        """Verify user is authenticated."""
        if not context.get('user_id'):
            raise PermissionError("Authentication required")
        return context

    def after_execution(self, tool_name, result, context):
        """Log access."""
        logger.info(f"User {context['user_id']} executed {tool_name}")
        return result

# Add to global chain
from src.tool_interceptors import get_global_interceptor_chain

chain = get_global_interceptor_chain()
chain.add_interceptor(AuthInterceptor())
```

## Interceptor Priority

Interceptors execute in priority order (lower number = outer wrapper):

| Priority | Value | Use Case |
|----------|-------|----------|
| FIRST | 0 | BugCatcher (must be outermost) |
| HIGH | 10 | PerfCatcher, critical monitoring |
| NORMAL | 50 | Auth, validation, business logic |
| LOW | 90 | Logging, metrics |
| LAST | 100 | Innermost wrappers |

## Disabling Interceptors

### Disable BugCatcher

```bash
export BUGCATCHER_ENABLED=false
```

### Disable PerfCatcher

```bash
export PERFCATCHER_ENABLED=false
```

### Disable All Interceptors

```python
from src.tool_interceptors import get_global_interceptor_chain

chain = get_global_interceptor_chain()
chain.interceptors.clear()
```

### Disable Specific Interceptor

```python
from src.tool_interceptors import get_global_interceptor_chain, BugCatcherInterceptor

chain = get_global_interceptor_chain()
chain.remove_interceptor(BugCatcherInterceptor)
```

## Exception Suppression

Interceptors can suppress exceptions (use with caution):

```python
class ErrorRecoveryInterceptor(ToolInterceptor):
    def on_exception(self, tool_name, exception, context):
        """Attempt to recover from certain errors."""
        if isinstance(exception, RetryableError):
            # Log and suppress
            logger.warning(f"Retryable error in {tool_name}: {exception}")
            return True  # Suppress exception
        return False  # Re-raise
```

## Performance Impact

### BugCatcher
- **Overhead**: ~1-2ms per tool call
- **Impact**: Minimal (batched Loki writes)
- **When**: Always active (unless disabled)

### PerfCatcher
- **Overhead**: ~0.5ms per tool call
- **Impact**: Minimal (in-memory stats)
- **When**: Only logs when variance detected

### Combined
- **Total Overhead**: ~2-3ms per tool call
- **Acceptable For**: Most use cases
- **Too Much For**: Extreme performance scenarios (disable via env vars)

## Use Cases

### Debugging Production Issues

```bash
# Enable both interceptors
export BUGCATCHER_ENABLED=true
export PERFCATCHER_ENABLED=true

# Run workflow
python chat_cli.py

# Exceptions automatically logged to Loki
# Performance variances automatically detected
```

### Performance Regression Testing

```bash
# Lower variance threshold to catch small regressions
export PERFCATCHER_VARIANCE_THRESHOLD=0.1  # 10%

# Increase window size for more stable baseline
export PERFCATCHER_WINDOW_SIZE=500
```

### Development (Verbose Monitoring)

```yaml
# config.yaml
bugcatcher:
  tracking:
    outputs: true  # Log all outputs (not just exceptions)
```

### Production (Minimal Overhead)

```bash
# Disable output tracking
# Only capture exceptions and high-variance performance
export PERFCATCHER_VARIANCE_THRESHOLD=0.5  # 50%
```

## Best Practices

1. **Always keep BugCatcher enabled** in production - low overhead, high value
2. **Adjust PerfCatcher threshold** based on your tolerance for variance
3. **Monitor Loki storage** - performance logs can accumulate
4. **Review variance patterns** regularly to identify optimization opportunities
5. **Use custom interceptors** for domain-specific concerns (auth, billing, etc.)
6. **Don't suppress exceptions** unless you have a good recovery strategy

## Troubleshooting

### Interceptors Not Running

Check that tools are being executed through `intercept_tool_call()`:

```python
# Wrong - bypasses interceptors
result = tool.execute(inputs)

# Right - applies interceptors
result = intercept_tool_call('tool_name', tool.execute, kwargs=inputs)
```

### High Overhead

Reduce overhead by:
1. Disabling output tracking: `bugcatcher.tracking.outputs: false`
2. Increasing PerfCatcher threshold: `PERFCATCHER_VARIANCE_THRESHOLD=0.5`
3. Reducing window size: `PERFCATCHER_WINDOW_SIZE=50`

### Too Many Performance Alerts

Increase variance threshold:
```bash
export PERFCATCHER_VARIANCE_THRESHOLD=0.3  # 30%
```

### Missing Performance Data

Ensure minimum samples reached:
```bash
export PERFCATCHER_MIN_SAMPLES=5  # Lower threshold
```

## Future Enhancements

- **Distributed Tracing**: Add trace IDs across tools
- **Cost Tracking**: Monitor LLM token costs
- **Rate Limiting**: Automatic throttling for expensive tools
- **Circuit Breaker**: Disable failing tools automatically
- **A/B Testing**: Compare tool versions automatically

## Summary

Tool Interceptors provide:
- **Automatic Wrapping**: Every tool call monitored by default
- **Exception Capture**: BugCatcher catches all exceptions in/out
- **Performance Monitoring**: PerfCatcher detects variance automatically
- **Low Overhead**: 2-3ms per call with batching
- **Environment Control**: Disable via env vars
- **Extensible**: Add custom interceptors easily

This is the foundation for robust, production-ready tool execution with comprehensive monitoring and debugging capabilities.
