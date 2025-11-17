# Optimized Performance Tracking

## Overview

The Optimized Performance Tracker is a lightweight, high-efficiency system for tracking tool call performance with minimal overhead. It's designed to collect just enough data to characterize tool behavior for RAG-based optimization, while avoiding the performance penalties of comprehensive logging.

## Key Features

### 1. Dual-Mode Operation

**Normal Mode (Default)**
- **Minimal Overhead**: Only captures essential data
  - Tool name
  - Parameters summary (truncated to 200 chars)
  - Start timestamp
  - End timestamp
- **Tiny footprint**: ~50-100 bytes per record
- **Fast**: No expensive operations during execution
- **Background saves**: Async persistence doesn't block execution

**Optimization Mode**
- **Comprehensive Data**: Captures detailed performance metrics
  - Full parameters
  - Memory usage
  - CPU percentage
  - Parent-child relationships
  - Error details
  - Custom metadata
- **Used for**: Periodic optimization runs, performance analysis, debugging

### 2. Per-Tool LRU Limits

Each tool has a configurable limit of performance data points:
- Oldest records automatically evicted when limit reached
- Prevents unbounded memory growth
- Keeps most recent, relevant data
- Configurable via YAML per tool

### 3. Parent-Child Context Aggregation

When a tool calls other tools:
- Child tools automatically tracked
- Parent-child relationships preserved
- Child data aggregated into parent's context
- Enables call graph analysis

### 4. RAG Integration

Performance data is clustered with tool definitions in RAG:
- Minimal perf metadata attached to tool artifacts
- Enables performance-aware tool selection
- No separate embeddings (saves space)
- Auto-updates on each tool call

### 5. Background Persistence

Async saving ensures zero blocking:
- Records batched before writing
- Configurable batch size and flush interval
- Falls back to no-op if storage unavailable
- Graceful shutdown flushes pending data

### 6. Auto-Cleanup

During optimization runs:
- Old performance data automatically deleted
- Prevents data accumulation over time
- Keeps storage footprint small
- Configurable via YAML

## Configuration

### YAML Configuration File

Location: `code_evolver/config/tool_perf_limits.yaml`

```yaml
# Global default for all tools
default_perf_points: 100

# Per-tool overrides
tool_limits:
  # High-frequency tools - keep fewer points
  llm_call: 50
  vector_search: 50

  # Critical tools - keep more data
  workflow_execute: 500
  optimize_code: 1000

  # Disable tracking for specific tool
  noop_tool: 0

  # Unlimited tracking
  critical_tool: -1

# Optimization mode settings
optimization:
  enabled: false  # Set to true for comprehensive tracking
  trigger_threshold: 10000  # Auto-trigger after N calls
  cleanup_on_optimize: true  # Delete old data on optimization

# Storage settings
storage:
  async_save: true  # Background saves
  batch_size: 100  # Records per batch
  flush_interval_seconds: 30  # Force flush interval

# RAG integration
rag:
  enabled: true  # Store perf data in RAG
  cluster_with_tool: true  # Co-locate with tool definition
  embedding_include: false  # Don't create separate embeddings
```

### Environment Variables

- `OPTIMIZED_PERF_TRACKER_ENABLED`: Enable/disable (default: true)
- Can be set to: `true`, `1`, `yes`, `on` (enabled) or `false`, `0`, `no`, `off` (disabled)

## Usage

### Automatic Tracking (Recommended)

All tool calls are automatically tracked via the interceptor chain:

```python
# Just call your tool normally - tracking happens automatically
result = my_tool.execute(params)
```

### Manual Tracking

For custom code or testing:

```python
from optimized_perf_tracker import track_tool_call, end_tool_call

# Start tracking
record_id = track_tool_call("my_tool", {"param1": "value1"})

try:
    # Your tool logic here
    result = do_work()

    # End tracking (success)
    end_tool_call(record_id)

except Exception as e:
    # End tracking (with error)
    end_tool_call(record_id, error=str(e))
    raise
```

### Optimization Mode

Enable for detailed analysis:

```python
from optimized_perf_tracker import set_optimization_mode

# Enable optimization mode
set_optimization_mode(True)

# Run your tools - comprehensive data will be collected
run_analysis()

# Disable optimization mode
set_optimization_mode(False)
```

### Get Statistics

```python
from optimized_perf_tracker import get_perf_stats

# Get stats for specific tool
tool_stats = get_perf_stats("my_tool")
print(f"Calls: {tool_stats['count']}")
print(f"Avg duration: {tool_stats['avg_duration_s']:.3f}s")

# Get global stats
all_stats = get_perf_stats()
print(f"Total calls: {all_stats['total_calls']}")
print(f"Tools tracked: {all_stats['tools_tracked']}")
```

### Cleanup Old Data

During optimization runs:

```python
from optimized_perf_tracker import cleanup_perf_data

# Cleanup all old performance data
cleanup_perf_data()
```

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│                 Tool Call                            │
│                     ↓                                │
│         OptimizedPerfTrackerInterceptor              │
│                     ↓                                │
│           before_execution()                         │
│           - Generate record_id                       │
│           - Start tracking                           │
│           - Track parent-child relationship          │
│                     ↓                                │
│            TOOL EXECUTION                           │
│                     ↓                                │
│           after_execution()                          │
│           - End tracking                             │
│           - Add to LRU store                        │
│           - Queue for background save               │
│           - Update RAG metadata                     │
│                     ↓                                │
│         Background Saver Thread                      │
│           - Batch records                           │
│           - Write to disk (JSONL)                   │
│           - One file per tool                       │
└─────────────────────────────────────────────────────┘
```

### Storage Format

Performance data is stored in JSONL format (one JSON object per line):

**Normal Mode Record:**
```json
{
  "tool": "my_tool",
  "timestamp": "2025-01-17T10:30:45.123456",
  "data": {
    "t": "my_tool",
    "p": "{\"param1\": \"value1\"}",
    "s": 1705493445.123,
    "e": 1705493445.456,
    "d": 0.333
  }
}
```

**Optimization Mode Record:**
```json
{
  "tool": "my_tool",
  "timestamp": "2025-01-17T10:30:45.123456",
  "data": {
    "tool": "my_tool",
    "params": {"param1": "value1"},
    "start": 1705493445.123,
    "end": 1705493445.456,
    "duration_ms": 333.0,
    "memory_mb": 125.4,
    "cpu_percent": 45.2,
    "parent_tool": "parent_record_id",
    "child_tools": ["child1_id", "child2_id"],
    "error": null,
    "metadata": {}
  }
}
```

### Memory Management

The LRU store ensures bounded memory usage:

1. Each tool has its own LRU store
2. Store size limited by YAML config
3. Oldest records evicted automatically
4. Thread-safe with locks
5. No cross-tool interference

Example memory usage:
- 100 tools with 100 records each = ~500KB - 1MB total
- 100 tools with 1000 records each = ~5-10MB total

## Integration Points

### Tool Interceptors

The `OptimizedPerfTrackerInterceptor` runs at `InterceptorPriority.HIGH`:
- After `BugCatcherInterceptor` (priority: FIRST)
- Alongside `PerfCatcherInterceptor` (priority: HIGH)
- Both can run concurrently for different purposes

### RAG Memory

Performance metadata is attached to tool artifacts:

```python
# In RAG, tools have embedded performance data
{
  "artifact_id": "tool_my_tool",
  "artifact_type": "function",
  "name": "my_tool",
  "content": "...",
  "metadata": {
    "perf_summary": {
      "avg_duration_ms": 333.0,
      "call_count": 1234,
      "last_updated": "2025-01-17T10:30:45"
    }
  }
}
```

This enables performance-aware retrieval:
- Fast tools can be preferred
- Slow tools can be avoided
- Performance trends visible

## Performance Impact

### Normal Mode Overhead

- **Per call**: ~0.1-0.5ms
- **Memory**: ~50-100 bytes per record
- **Background save**: 0ms (async)
- **Total impact**: <1% for typical tool calls

### Optimization Mode Overhead

- **Per call**: ~1-5ms (depends on metrics collected)
- **Memory**: ~500-1000 bytes per record
- **Impact**: 1-5% for typical tool calls

### When to Use Each Mode

**Normal Mode:**
- Production deployments
- Long-running workflows
- High-frequency tool calls
- When minimizing overhead is critical

**Optimization Mode:**
- Development and testing
- Performance analysis sessions
- Debugging performance issues
- Optimization runs (scheduled or manual)

## Best Practices

### 1. Configure Limits Appropriately

- High-frequency tools: Lower limits (50-100 records)
- Low-frequency tools: Standard limits (100-200 records)
- Critical tools: Higher limits (500-1000 records)
- Debug tools: Very high limits (1000-5000 records)

### 2. Regular Cleanup

Schedule periodic cleanup to prevent accumulation:

```python
# In your optimization scheduler
def run_optimization():
    # Enable optimization mode
    set_optimization_mode(True)

    # Run optimization analysis
    analyze_performance()

    # Cleanup old data
    cleanup_perf_data()

    # Disable optimization mode
    set_optimization_mode(False)
```

### 3. Monitor Storage Growth

Check storage directory periodically:

```bash
# Check size of perf data
du -sh code_evolver/perf_data/

# Count records per tool
for f in code_evolver/perf_data/*_perf.jsonl; do
    echo "$f: $(wc -l < $f) records"
done
```

### 4. Tune Batch Settings

Adjust based on your workload:

- High-frequency calls: Larger batches, shorter flush interval
- Low-frequency calls: Smaller batches, longer flush interval
- I/O-constrained: Larger batches to reduce write operations

### 5. Test Impact

Measure overhead in your environment:

```python
import time

# Disable tracking
os.environ['OPTIMIZED_PERF_TRACKER_ENABLED'] = 'false'
start = time.time()
run_workload()
baseline = time.time() - start

# Enable tracking
os.environ['OPTIMIZED_PERF_TRACKER_ENABLED'] = 'true'
start = time.time()
run_workload()
with_tracking = time.time() - start

overhead = ((with_tracking - baseline) / baseline) * 100
print(f"Overhead: {overhead:.2f}%")
```

## Future Enhancements

Planned features (not yet implemented):

1. **Auto-trigger optimization** at 10,000 calls
2. **Smart sampling** - track every Nth call to reduce overhead
3. **Compression** - compress old records to save space
4. **Analytics dashboard** - visualize performance trends
5. **Anomaly detection** - alert on performance degradation
6. **Export to Prometheus** - integrate with monitoring stack

## Troubleshooting

### Performance data not being saved

1. Check if tracker is enabled:
   ```python
   from optimized_perf_tracker import get_tracker
   tracker = get_tracker()
   print(f"Enabled: {tracker.enabled}")
   ```

2. Check environment variable:
   ```bash
   echo $OPTIMIZED_PERF_TRACKER_ENABLED
   ```

3. Check storage directory exists and is writable:
   ```bash
   ls -la code_evolver/perf_data/
   ```

### High memory usage

1. Check per-tool limits in YAML
2. Reduce `default_perf_points`
3. Set specific tools to lower limits
4. Disable tracking for high-frequency tools

### Slow performance

1. Verify async_save is enabled
2. Check if optimization mode is accidentally enabled
3. Increase batch_size to reduce I/O
4. Disable tracking for non-critical tools

## Summary

The Optimized Performance Tracker provides:
- ✅ Minimal overhead (< 1% in normal mode)
- ✅ Bounded memory usage (LRU per tool)
- ✅ Automatic tracking (via interceptors)
- ✅ RAG integration (performance-aware retrieval)
- ✅ Background persistence (non-blocking)
- ✅ Flexible configuration (YAML + env vars)
- ✅ Auto-cleanup (prevents data accumulation)

Use it to characterize tool performance without sacrificing execution speed.
