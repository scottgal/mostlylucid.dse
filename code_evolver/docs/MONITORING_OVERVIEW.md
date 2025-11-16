# Code Evolver Monitoring System

Complete overview of the global monitoring system for Code Evolver, including BugCatcher, PerfCatcher, and tool interceptors.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Every Tool Call                              │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │            Interceptor Chain (Automatic)                │    │
│  │                                                          │    │
│  │  BugCatcher (FIRST - Outermost)                         │    │
│  │    ├─ Track request context (LRU cache)                 │    │
│  │    ├─ Capture exceptions IN and OUT                     │    │
│  │    └─ Log to Loki with full context                     │    │
│  │                     ↓                                    │    │
│  │  PerfCatcher (HIGH Priority)                            │    │
│  │    ├─ Record execution time                             │    │
│  │    ├─ Compare to rolling baseline                       │    │
│  │    └─ Log if variance > threshold                       │    │
│  │                     ↓                                    │    │
│  │  [Your Custom Interceptors]                             │    │
│  │                     ↓                                    │    │
│  │  Tool Execution                                          │    │
│  │                     ↓                                    │    │
│  │  [Results bubble back through chain]                    │    │
│  └────────────────────────────────────────────────────────┘    │
│                           ↓                                      │
│                    Loki / Grafana                                │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. BugCatcher

**Purpose**: Global exception monitoring with full context capture

**What It Does**:
- Wraps every tool call automatically
- Tracks request context in LRU cache (default: 100 entries)
- Captures exceptions with full context
- Logs to Grafana Loki
- **Focuses on failure**: Only logs comprehensive data when exceptions occur

**Key Features**:
- Automatic wrapping (no code changes needed)
- Exception capture on entry and exit
- Request/response correlation via LRU cache
- Workflow/step context association
- File logging fallback

**Control**:
```bash
# Disable entirely
export BUGCATCHER_ENABLED=false

# Configure in config.yaml
bugcatcher:
  enabled: true
  tracking:
    outputs: false  # Only capture at failure, not all requests
```

**Documentation**: [docs/BUGCATCHER.md](BUGCATCHER.md)

### 2. PerfCatcher

**Purpose**: Performance monitoring with variance detection

**What It Does**:
- Tracks execution time for every tool call
- Maintains rolling baseline (default: 100 samples)
- Calculates mean and standard deviation
- **Only logs when variance exceeds threshold** (default: 20%)
- Captures window of data when performance degrades

**Key Features**:
- Constantly updating baseline
- Variance-based alerting
- Threshold configurable per environment
- Minimal overhead (in-memory only)
- Logs anomalies to Loki via BugCatcher

**Control**:
```bash
# Configure thresholds
export PERFCATCHER_VARIANCE_THRESHOLD=0.2  # 20%
export PERFCATCHER_WINDOW_SIZE=100
export PERFCATCHER_MIN_SAMPLES=10

# Disable
export PERFCATCHER_ENABLED=false
```

**Documentation**: [docs/TOOL_INTERCEPTORS.md](TOOL_INTERCEPTORS.md)

### 3. Tool Interceptors

**Purpose**: Automatic wrapping framework for all tool executions

**What It Does**:
- Provides priority-based interceptor chain
- Executes interceptors in order (outermost to innermost)
- Handles exceptions at each layer
- Supports custom interceptors

**Priority Levels**:
- `FIRST (0)`: BugCatcher - must be outermost
- `HIGH (10)`: PerfCatcher - performance critical
- `NORMAL (50)`: Custom business logic
- `LOW (90)`: Logging, metrics
- `LAST (100)`: Innermost wrappers

**Documentation**: [docs/TOOL_INTERCEPTORS.md](TOOL_INTERCEPTORS.md)

### 4. Tool Wrappers (Optional)

**Purpose**: Manual wrapping for specific tools

**What It Does**:
- Decorator-based wrapping
- Context manager pattern
- Functional wrapping
- Debug-level marking for evolution

**Use When**:
- Need explicit control
- Want debug-level marking
- Testing specific tools
- Wrapping external functions

**Documentation**: [docs/BUGCATCHER_TOOL_WRAPPER.md](BUGCATCHER_TOOL_WRAPPER.md)

## Data Flow

### Normal Execution (No Errors)

```
Tool Call
  ↓
BugCatcher: Track request in LRU cache
  ↓
PerfCatcher: Record start time
  ↓
Tool Executes Successfully
  ↓
PerfCatcher: Calculate duration, compare to baseline
  ↓
  If variance > threshold:
    └─> Log to Loki (performance variance)
  ↓
BugCatcher: (No action - no exception)
  ↓
Return Result
```

**Loki Logs**: Only if performance variance detected

### Exception Execution

```
Tool Call
  ↓
BugCatcher: Track request in LRU cache
  ↓
PerfCatcher: Record start time
  ↓
Tool Raises Exception
  ↓
PerfCatcher: Record duration
  ↓
BugCatcher:
  ├─ Get request context from LRU cache
  ├─ Capture exception with traceback
  ├─ Add execution time, workflow/step context
  └─> Log to Loki (full exception data)
  ↓
Re-raise Exception
```

**Loki Logs**: Full exception context with all cached data

## Storage Backends

### Loki (Primary)

- **Purpose**: Centralized log aggregation
- **Port**: 3100
- **Retention**: 7 days (configurable)
- **Storage**: Filesystem (local dev), S3 (production)

### Qdrant (Vector DB)

- **Purpose**: RAG memory for tool context
- **Port**: 6333 (REST), 6334 (gRPC)
- **Storage**: Docker volume

### Grafana (Visualization)

- **Purpose**: Log querying and dashboards
- **Port**: 3000
- **Login**: admin/admin

### File Logs (Fallback)

- **BugCatcher**: `bugcatcher.log`
- **Code Evolver**: `code_evolver.log`

## Quick Start

### 1. Start Infrastructure

```bash
# Start Loki, Qdrant, Grafana
cd code_evolver
docker-compose -f docker-compose.localdev.yml up -d

# Verify services
docker-compose -f docker-compose.localdev.yml ps
```

### 2. Run Code Evolver

```bash
# BugCatcher and PerfCatcher auto-initialize
python chat_cli.py
```

### 3. View Logs in Grafana

1. Open: http://localhost:3000
2. Login: admin / admin
3. Explore → Loki
4. Query examples:

```logql
# All BugCatcher exceptions
{job="code_evolver_bugcatcher", severity="error"}

# Performance variances
{job="code_evolver_perfcatcher"}

# Specific tool
{job="code_evolver_bugcatcher", tool_name="llm_generator"}

# Specific workflow
{job="code_evolver_bugcatcher", workflow_id="wf_123"}
```

## Configuration

### config.yaml

```yaml
bugcatcher:
  enabled: true
  loki:
    url: "http://localhost:3100"
    enabled: true
    batch_size: 10
  cache:
    max_size: 100  # LRU cache size
  tracking:
    exceptions: true
    outputs: false  # Only capture at failure
```

### Environment Variables

```bash
# BugCatcher
export BUGCATCHER_ENABLED=true

# PerfCatcher
export PERFCATCHER_ENABLED=true
export PERFCATCHER_VARIANCE_THRESHOLD=0.2
export PERFCATCHER_WINDOW_SIZE=100
export PERFCATCHER_MIN_SAMPLES=10
```

## Use Cases

### Debugging Production Issues

**Problem**: Tool failing intermittently in production

**Solution**:
1. Enable BugCatcher (already enabled by default)
2. Wait for failure
3. Query Loki for exceptions:
   ```logql
   {job="code_evolver_bugcatcher", tool_name="problem_tool"}
   ```
4. Review full context: inputs, workflow, stack trace
5. Reproduce locally with captured context

### Performance Regression Detection

**Problem**: Tool performance degraded after deployment

**Solution**:
1. Lower PerfCatcher threshold:
   ```bash
   export PERFCATCHER_VARIANCE_THRESHOLD=0.1  # 10%
   ```
2. Run workflows
3. PerfCatcher automatically logs variances
4. Query Loki:
   ```logql
   {job="code_evolver_perfcatcher", tool_name="slow_tool"}
   ```
5. Compare `current_time_ms` vs `mean_time_ms`
6. Investigate regression

### Auto-Repair Integration

**Problem**: Need to automatically evolve failing tools

**Solution**:
1. BugCatcher captures all failures with context
2. Auto-repair system queries Loki for patterns
3. Identifies common failure modes
4. Generates improved tool versions
5. Tests with captured contexts
6. Deploys improved version
7. PerfCatcher validates performance

### Workflow Debugging

**Problem**: Complex workflow failing unpredictably

**Solution**:
1. BugCatcher tracks entire workflow:
   - Each step with inputs/outputs
   - Timing for each step
   - Exceptions with workflow context
2. Query workflow in Grafana:
   ```logql
   {job="code_evolver_bugcatcher", workflow_id="wf_123"}
   ```
3. Visualize execution timeline
4. Identify failing step
5. Review step context and exception

## Performance Impact

| Component | Overhead | When | Impact |
|-----------|----------|------|--------|
| BugCatcher | 1-2ms | Every tool call | Minimal |
| PerfCatcher | 0.5ms | Every tool call | Minimal |
| Loki Logging | Async | Batched | None |
| **Total** | **2-3ms** | Every call | **Negligible** |

### Optimization Tips

**High-Performance Scenarios**:
```bash
# Disable output tracking
# config.yaml: bugcatcher.tracking.outputs: false

# Increase variance threshold
export PERFCATCHER_VARIANCE_THRESHOLD=0.5  # 50%

# Reduce window size
export PERFCATCHER_WINDOW_SIZE=50
```

**Verbose Debugging**:
```bash
# Enable output tracking
# config.yaml: bugcatcher.tracking.outputs: true

# Lower variance threshold
export PERFCATCHER_VARIANCE_THRESHOLD=0.1  # 10%

# Increase window size
export PERFCATCHER_WINDOW_SIZE=500
```

## Best Practices

1. **Always keep BugCatcher enabled** - low cost, high value
2. **Adjust PerfCatcher threshold** per environment (tight in dev, loose in prod)
3. **Monitor Loki storage** - set retention policies
4. **Review variance patterns** weekly to identify optimization opportunities
5. **Use workflow_id/step_id** for context in all tool calls
6. **Query Loki regularly** to understand system behavior
7. **Set up Grafana alerts** for critical exceptions
8. **Flush BugCatcher** before shutdown: `flush_bugcatcher()`

## Troubleshooting

### Logs Not Appearing

1. Check Loki is running: `docker ps | grep loki`
2. Check configuration: `bugcatcher.loki.enabled: true`
3. Verify URL: `http://localhost:3100`
4. Test connection: `curl http://localhost:3100/ready`
5. Check batching: Logs may be batched (wait or flush)

### High Memory Usage

1. Reduce cache size: `bugcatcher.cache.max_size: 50`
2. Disable output tracking: `bugcatcher.tracking.outputs: false`
3. Reduce PerfCatcher window: `PERFCATCHER_WINDOW_SIZE=50`

### Too Many Performance Alerts

1. Increase threshold: `PERFCATCHER_VARIANCE_THRESHOLD=0.5`
2. Increase min samples: `PERFCATCHER_MIN_SAMPLES=20`
3. Review if alerts indicate real issues

### Missing Context

1. Ensure workflow_id/step_id in context
2. Check LRU cache size (may be evicting)
3. Enable output tracking temporarily for debugging

## Documentation

- **[BUGCATCHER.md](BUGCATCHER.md)**: Complete BugCatcher guide
- **[BUGCATCHER_TOOL_WRAPPER.md](BUGCATCHER_TOOL_WRAPPER.md)**: Manual tool wrapping
- **[TOOL_INTERCEPTORS.md](TOOL_INTERCEPTORS.md)**: Automatic interceptors
- **[DOCKER_SETUP.md](../DOCKER_SETUP.md)**: Docker environment setup

## Future Enhancements

- [ ] Distributed tracing with trace IDs
- [ ] Cost tracking for LLM calls
- [ ] Rate limiting interceptor
- [ ] Circuit breaker for failing tools
- [ ] A/B testing interceptor
- [ ] Custom Grafana dashboards
- [ ] Alerting rules
- [ ] Slack/email notifications
- [ ] Automatic tool version rollback

## Summary

The Code Evolver monitoring system provides:

✅ **Automatic Exception Capture** - BugCatcher wraps every tool call
✅ **Performance Monitoring** - PerfCatcher detects variance automatically
✅ **Full Context** - LRU cache associates failures with requests
✅ **Threshold-Based Logging** - Only logs when issues occur
✅ **Low Overhead** - 2-3ms per tool call
✅ **Environment Control** - Disable via env vars
✅ **Extensible** - Add custom interceptors easily
✅ **Production Ready** - Handles Loki unavailability gracefully

This gives you comprehensive monitoring for debugging, optimization, and auto-repair without any code changes!
