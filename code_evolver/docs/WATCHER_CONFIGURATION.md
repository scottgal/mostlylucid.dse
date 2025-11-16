# Watcher Configuration Guide

Comprehensive guide to configuring BugCatcher and PerfCatcher in all deployment scenarios.

## Table of Contents

- [BugCatcher Configuration](#bugcatcher-configuration)
- [PerfCatcher Configuration](#perfcatcher-configuration)
- [Fix Template Store Configuration](#fix-template-store-configuration)
- [Deployment Scenarios](#deployment-scenarios)
- [Environment Variables Reference](#environment-variables-reference)
- [Troubleshooting](#troubleshooting)

---

## BugCatcher Configuration

BugCatcher can be configured through environment variables, config.yaml, or programmatically.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BUGCATCHER_ENABLED` | `true` | Enable/disable BugCatcher globally |
| `BUGCATCHER_LOKI_URL` | `http://localhost:3100` | Loki instance URL |
| `BUGCATCHER_LOKI_ENABLED` | `true` | Enable Loki integration |
| `BUGCATCHER_CACHE_SIZE` | `100` | LRU cache size for request context |
| `BUGCATCHER_LOG_FILE` | `bugcatcher.log` | Local log file path |
| `BUGCATCHER_FILE_LOGGING` | `true` | Enable file logging |
| `BUGCATCHER_MIN_SEVERITY` | `WARNING` | Minimum severity to capture |
| `BUGCATCHER_TRACK_OUTPUTS` | `false` | Track tool outputs (adds overhead) |

### Config.yaml Configuration

```yaml
bugcatcher:
  enabled: true

  # Loki integration
  loki:
    url: "http://localhost:3100"
    enabled: true
    batch_size: 10        # Batch logs for performance
    timeout: 5            # Request timeout in seconds

  # LRU cache for request context
  cache:
    max_size: 100         # Maximum cached requests

  # File logging (fallback when Loki unavailable)
  file_logging:
    enabled: true
    file: "bugcatcher.log"

  # What to track
  tracking:
    exceptions: true
    logged_errors: true
    workflow_failures: true
    tool_failures: true
    llm_errors: true
    outputs: false        # Disable by default (adds overhead)

  # Minimum severity level
  min_severity: "WARNING"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

  # Auto-install hooks
  auto_install_hooks: true
```

### Programmatic Configuration

```python
from src.bugcatcher import BugCatcher

# Create custom BugCatcher instance
bugcatcher = BugCatcher(
    loki_url="http://localhost:3100",
    loki_enabled=True,
    cache_size=200,
    log_to_file=True,
    log_file="custom_bugcatcher.log",
    track_outputs=False
)

# Track request
bugcatcher.track_request('request_1', {
    'workflow_id': 'wf_1',
    'step_id': 'step_1',
    'tool_name': 'my_tool'
})

# Capture exception
try:
    # Your code
    pass
except Exception as e:
    bugcatcher.capture_exception(
        e,
        request_id='request_1',
        severity=ExceptionSeverity.ERROR
    )
```

### Loki Backend Configuration

BugCatcher uses a batched Loki backend for efficient logging:

```python
# Configure Loki backend
bugcatcher = BugCatcher(
    loki_url="http://loki.company.com:3100",
    loki_enabled=True
)

# Loki backend auto-batches logs
# Batch size: 10 (default)
# Flushes on shutdown automatically
```

To manually flush pending logs:

```python
from src.bugcatcher_setup import flush_bugcatcher

# Before shutdown
flush_bugcatcher()
```

### Cache Configuration

The LRU cache stores request context for exception correlation:

```python
bugcatcher = BugCatcher(cache_size=100)  # Store last 100 requests

# Cache automatically evicts oldest entries
# Access pattern: track_request → capture_exception
# Cache key: request_id
```

**Cache sizing guidelines:**
- **Small systems** (< 10 concurrent requests): 50-100
- **Medium systems** (10-50 concurrent requests): 100-500
- **Large systems** (> 50 concurrent requests): 500-1000

---

## PerfCatcher Configuration

PerfCatcher monitors tool performance and detects variance.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PERFCATCHER_ENABLED` | `true` | Enable/disable PerfCatcher globally |
| `PERFCATCHER_VARIANCE_THRESHOLD` | `0.2` | Variance threshold (20%) |
| `PERFCATCHER_WINDOW_SIZE` | `100` | Rolling window size for baseline |
| `PERFCATCHER_LOKI_URL` | `http://localhost:3100` | Loki instance URL |
| `PERFCATCHER_LOKI_ENABLED` | `true` | Enable Loki integration |
| `PERFCATCHER_HIGH_VARIANCE_THRESHOLD` | `1.0` | High variance threshold (100%) |

### Config.yaml Configuration

```yaml
perfcatcher:
  enabled: true

  # Variance thresholds
  variance_threshold: 0.2        # 20% - log when variance exceeds this
  high_variance_threshold: 1.0   # 100% - mark as high severity

  # Rolling window for baseline
  window_size: 100               # Track last 100 executions per tool

  # Loki integration
  loki:
    url: "http://localhost:3100"
    enabled: true
    batch_size: 10

  # What to track
  tracking:
    execution_time: true
    variance: true
    slow_calls: true               # Calls > 1000ms
    fast_calls: false              # Don't log fast successful calls
```

### Programmatic Configuration

```python
from src.tool_interceptors import PerfCatcherInterceptor

# Access via interceptor
interceptor = PerfCatcherInterceptor()

# Configure thresholds
interceptor.variance_threshold = 0.3  # 30%
interceptor.window_size = 50

# Performance data is tracked automatically
# Access via: interceptor.performance_data['tool_name']
```

### Variance Detection

PerfCatcher uses a rolling baseline to detect variance:

```
variance = |current_time - mean_time| / mean_time

if variance > threshold:
    log_variance_event()
```

**Threshold guidelines:**
- **Strict** (0.1-0.2): Catch small variations, more sensitive
- **Normal** (0.2-0.5): Balance between noise and detection
- **Relaxed** (0.5-1.0): Only catch significant variations

### Window Sizing

The window size determines how many executions to track for baseline:

- **Small window** (20-50): Quick adaptation to changes, more sensitive
- **Medium window** (50-200): Balanced, recommended for most cases
- **Large window** (200-500): Stable baseline, less sensitive to spikes

---

## Fix Template Store Configuration

Fix Template Store saves successful fixes with optional vector search.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FIX_TEMPLATE_STORAGE_PATH` | `./fix_templates` | Path to store templates |
| `FIX_TEMPLATE_USE_QDRANT` | `true` | Enable Qdrant vector search |
| `FIX_TEMPLATE_QDRANT_URL` | `http://localhost:6333` | Qdrant instance URL |
| `FIX_TEMPLATE_COLLECTION` | `fix_templates` | Qdrant collection name |

### Config.yaml Configuration

```yaml
fix_template_store:
  storage_path: "./fix_templates"

  # Qdrant vector search (optional)
  qdrant:
    enabled: true
    url: "http://localhost:6333"
    collection_name: "fix_templates"
    vector_size: 768  # nomic-embed-text

  # Fallback to rule-based matching if Qdrant unavailable
  fallback_to_rules: true
```

### Programmatic Configuration

```python
from src.fix_template_store import FixTemplateStore

# Create store
store = FixTemplateStore(
    storage_path="./fix_templates",
    use_qdrant=True,
    qdrant_url="http://localhost:6333",
    collection_name="fix_templates"
)

# Save fix template
template = store.save_fix_template(
    problem_type='bug',
    tool_name='my_tool',
    problem_description='ValueError: invalid input',
    problem_data={'exception_type': 'ValueError'},
    fix_description='Add input validation',
    fix_implementation='if not valid: raise ValueError()',
    conditions={'exception_type': 'ValueError'}
)

# Find similar fixes
problem = {
    'type': 'bug',
    'exception_type': 'ValueError'
}
matches = store.find_similar_fixes(problem, top_k=5)
```

### Storage Formats

Fix templates are stored in two locations:

1. **Filesystem** (JSON files):
   ```
   ./fix_templates/
   ├── bug_my_tool_abc12345.json
   ├── perf_slow_tool_def67890.json
   └── ...
   ```

2. **Qdrant** (vector embeddings):
   - Collection: `fix_templates`
   - Vectors: 768 dimensions (nomic-embed-text)
   - Metadata: template_id, problem_type, tool_name

### Qdrant Integration

If Qdrant is enabled, templates are searchable by similarity:

```python
# Vector similarity search
matches = store.find_similar_fixes(problem, top_k=5)

# Fallback to rule-based if Qdrant unavailable
# Automatic fallback, no configuration needed
```

**Qdrant setup:**
```bash
# Start Qdrant
docker-compose -f docker-compose.localdev.yml up -d qdrant

# Verify connection
curl http://localhost:6333/collections
```

---

## Deployment Scenarios

### Local Development

**Goal:** Full monitoring with visualization

```yaml
# config.yaml
bugcatcher:
  enabled: true
  loki:
    url: "http://localhost:3100"
    enabled: true
  file_logging:
    enabled: true

perfcatcher:
  enabled: true
  variance_threshold: 0.2

fix_template_store:
  qdrant:
    enabled: true
```

**Docker setup:**
```bash
# Start full stack
docker-compose -f docker-compose.localdev.yml up -d

# Access Grafana: http://localhost:3000
# Access Loki: http://localhost:3100
# Access Qdrant: http://localhost:6333
```

### Testing / CI

**Goal:** Monitoring enabled, no external dependencies

```yaml
# config.yaml
bugcatcher:
  enabled: true
  loki:
    enabled: false  # No Loki in tests
  file_logging:
    enabled: true
    file: "test_bugcatcher.log"

perfcatcher:
  enabled: true
  loki:
    enabled: false

fix_template_store:
  qdrant:
    enabled: false  # No Qdrant in tests
  fallback_to_rules: true
```

**Environment variables:**
```bash
# Disable external services
export BUGCATCHER_LOKI_ENABLED=false
export PERFCATCHER_LOKI_ENABLED=false
export FIX_TEMPLATE_USE_QDRANT=false
```

### Production

**Goal:** Monitoring with remote services

```yaml
# config.yaml
bugcatcher:
  enabled: true
  loki:
    url: "http://loki.prod.company.com:3100"
    enabled: true
    batch_size: 50  # Larger batches for performance
  cache:
    max_size: 500  # Larger cache for high throughput

perfcatcher:
  enabled: true
  variance_threshold: 0.3  # Less sensitive in prod
  window_size: 200  # Stable baseline

fix_template_store:
  storage_path: "/var/lib/code_evolver/fix_templates"
  qdrant:
    enabled: true
    url: "http://qdrant.prod.company.com:6333"
```

**Best practices:**
- Use remote Loki/Qdrant instances
- Increase batch sizes for performance
- Monitor BugCatcher/PerfCatcher themselves
- Set up alerts in Grafana for critical errors

### Disabled (No Monitoring)

**Goal:** Turn off all monitoring

```bash
# Environment variables
export BUGCATCHER_ENABLED=false
export PERFCATCHER_ENABLED=false
```

Or in code:
```python
bugcatcher.enabled = False
perfcatcher.enabled = False
```

---

## Environment Variables Reference

### Complete List

```bash
# BugCatcher
export BUGCATCHER_ENABLED=true
export BUGCATCHER_LOKI_URL=http://localhost:3100
export BUGCATCHER_LOKI_ENABLED=true
export BUGCATCHER_CACHE_SIZE=100
export BUGCATCHER_LOG_FILE=bugcatcher.log
export BUGCATCHER_FILE_LOGGING=true
export BUGCATCHER_MIN_SEVERITY=WARNING
export BUGCATCHER_TRACK_OUTPUTS=false

# PerfCatcher
export PERFCATCHER_ENABLED=true
export PERFCATCHER_VARIANCE_THRESHOLD=0.2
export PERFCATCHER_WINDOW_SIZE=100
export PERFCATCHER_LOKI_URL=http://localhost:3100
export PERFCATCHER_LOKI_ENABLED=true
export PERFCATCHER_HIGH_VARIANCE_THRESHOLD=1.0

# Fix Template Store
export FIX_TEMPLATE_STORAGE_PATH=./fix_templates
export FIX_TEMPLATE_USE_QDRANT=true
export FIX_TEMPLATE_QDRANT_URL=http://localhost:6333
export FIX_TEMPLATE_COLLECTION=fix_templates
```

### Precedence

Configuration precedence (highest to lowest):
1. **Environment variables** - Override everything
2. **Programmatic configuration** - Explicit in code
3. **config.yaml** - Default configuration file
4. **Built-in defaults** - Hardcoded in source

Example:
```bash
# config.yaml sets cache_size: 100
# Environment variable overrides it
export BUGCATCHER_CACHE_SIZE=500

# Result: cache_size = 500
```

---

## Troubleshooting

### BugCatcher not capturing exceptions

**Symptoms:** Exceptions occur but aren't logged

**Checks:**
1. Verify BugCatcher is enabled:
   ```python
   from src.bugcatcher import get_bugcatcher
   bc = get_bugcatcher()
   assert bc.enabled is True
   ```

2. Check request tracking:
   ```python
   stats = bc.get_stats()
   print(f"Cache size: {stats['cache_size']}")
   print(f"Exceptions: {stats['total_exceptions']}")
   ```

3. Verify Loki connection:
   ```bash
   curl http://localhost:3100/ready
   ```

4. Check file logs:
   ```bash
   tail -f bugcatcher.log
   ```

### PerfCatcher not detecting variance

**Symptoms:** Performance varies but no logs

**Checks:**
1. Verify PerfCatcher is enabled:
   ```bash
   echo $PERFCATCHER_ENABLED  # Should be 'true'
   ```

2. Check variance threshold:
   ```python
   from src.tool_interceptors import get_global_interceptor_chain
   chain = get_global_interceptor_chain()
   perf_interceptor = chain.get_interceptor_by_type(PerfCatcherInterceptor)
   print(f"Threshold: {perf_interceptor.variance_threshold}")
   ```

3. Ensure enough baseline data:
   - Need at least 10 executions before variance detection
   - Check: `len(perf_interceptor.performance_data['tool_name'])`

4. Verify variance calculation:
   ```python
   data = perf_interceptor.performance_data['tool_name']
   if len(data) > 1:
       import statistics
       mean = statistics.mean(data)
       current = data[-1]
       variance = abs(current - mean) / mean
       print(f"Variance: {variance:.2%}")
   ```

### Loki connection issues

**Symptoms:** "Connection refused" or "Failed to send to Loki"

**Solutions:**
1. Verify Loki is running:
   ```bash
   docker ps | grep loki
   ```

2. Check Loki URL:
   ```bash
   curl http://localhost:3100/ready
   # Should return "ready"
   ```

3. Check network connectivity:
   ```bash
   # If using Docker network
   docker network inspect code_evolver_network
   ```

4. Use file logging as fallback:
   ```yaml
   bugcatcher:
     loki:
       enabled: false  # Temporarily disable
     file_logging:
       enabled: true
   ```

### Qdrant integration issues

**Symptoms:** "Failed to initialize Qdrant" or templates not searchable

**Solutions:**
1. Verify Qdrant is running:
   ```bash
   curl http://localhost:6333/collections
   ```

2. Check collection exists:
   ```bash
   curl http://localhost:6333/collections/fix_templates
   ```

3. Fallback to rule-based matching:
   ```yaml
   fix_template_store:
     qdrant:
       enabled: false
     fallback_to_rules: true
   ```

4. Verify vector size:
   ```python
   # nomic-embed-text uses 768 dimensions
   from src.fix_template_store import FixTemplateStore
   store = FixTemplateStore(use_qdrant=True)
   # Should auto-configure to 768
   ```

### High memory usage

**Symptoms:** BugCatcher/PerfCatcher using too much memory

**Solutions:**
1. Reduce cache size:
   ```yaml
   bugcatcher:
     cache:
       max_size: 50  # Reduce from 100
   ```

2. Reduce performance window:
   ```yaml
   perfcatcher:
     window_size: 50  # Reduce from 100
   ```

3. Disable output tracking:
   ```yaml
   bugcatcher:
     tracking:
       outputs: false
   ```

4. Increase batch sizes (reduce memory overhead):
   ```yaml
   bugcatcher:
     loki:
       batch_size: 50  # Increase from 10
   ```

### Performance overhead

**Symptoms:** Monitoring slowing down application

**Solutions:**
1. Disable output tracking:
   ```yaml
   bugcatcher:
     tracking:
       outputs: false  # Significant overhead
   ```

2. Increase Loki batch size:
   ```yaml
   bugcatcher:
     loki:
       batch_size: 50  # Fewer network calls
   ```

3. Increase variance threshold:
   ```yaml
   perfcatcher:
     variance_threshold: 0.5  # Less frequent logging
   ```

4. Disable in specific scenarios:
   ```python
   # Disable for specific tools
   if tool_name in ['high_frequency_tool']:
       bugcatcher.enabled = False
   ```

---

## Best Practices

### 1. Start Conservative

Begin with monitoring disabled or relaxed:
```yaml
bugcatcher:
  enabled: false

perfcatcher:
  enabled: false
```

Enable gradually:
```yaml
# Stage 1: Enable with high thresholds
perfcatcher:
  enabled: true
  variance_threshold: 1.0

# Stage 2: Lower thresholds
perfcatcher:
  variance_threshold: 0.5

# Stage 3: Production thresholds
perfcatcher:
  variance_threshold: 0.2
```

### 2. Monitor the Monitors

Set up alerts for BugCatcher/PerfCatcher health:
```yaml
# Grafana alert
alert: BugCatcher Cache Full
expr: bugcatcher_cache_size >= bugcatcher_cache_max_size
```

### 3. Use File Logging as Fallback

Always enable file logging:
```yaml
bugcatcher:
  loki:
    enabled: true
  file_logging:
    enabled: true  # Fallback if Loki fails
```

### 4. Tune for Your Workload

**High throughput:**
- Large caches (500-1000)
- Large batches (50-100)
- Relaxed thresholds (0.3-0.5)

**Low throughput:**
- Small caches (50-100)
- Small batches (10-20)
- Strict thresholds (0.1-0.2)

### 5. Review and Adjust

Regularly review:
- Exception patterns in Grafana
- Performance variance trends
- Template application counts
- System overhead metrics

Adjust configuration based on findings.

---

## Examples

### Example 1: Strict Development Setup

```yaml
# config.yaml - catch everything
bugcatcher:
  enabled: true
  min_severity: "DEBUG"
  tracking:
    exceptions: true
    logged_errors: true
    workflow_failures: true
    tool_failures: true
    llm_errors: true

perfcatcher:
  enabled: true
  variance_threshold: 0.1  # Very strict
```

### Example 2: Production Setup

```yaml
# config.yaml - balanced for production
bugcatcher:
  enabled: true
  min_severity: "WARNING"
  loki:
    url: "http://loki-prod:3100"
    batch_size: 50
  cache:
    max_size: 500

perfcatcher:
  enabled: true
  variance_threshold: 0.3
  window_size: 200
```

### Example 3: Testing Setup

```bash
# .env.test - no external dependencies
BUGCATCHER_ENABLED=true
BUGCATCHER_LOKI_ENABLED=false
BUGCATCHER_FILE_LOGGING=true

PERFCATCHER_ENABLED=true
PERFCATCHER_LOKI_ENABLED=false

FIX_TEMPLATE_USE_QDRANT=false
```

---

For more information, see:
- [BugCatcher Documentation](./BUGCATCHER.md)
- [Tool Interceptors Documentation](./TOOL_INTERCEPTORS.md)
- [Monitoring Overview](./MONITORING_OVERVIEW.md)
- [Docker Setup Guide](../DOCKER_SETUP.md)
