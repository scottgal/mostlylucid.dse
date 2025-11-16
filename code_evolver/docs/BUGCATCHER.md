# BugCatcher - Global Exception Monitoring

BugCatcher is a global exception monitoring tool for Code Evolver that automatically tracks and logs all exceptions across workflows, providing centralized observability via Grafana Loki.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Docker Setup](#docker-setup)
- [Grafana Dashboard](#grafana-dashboard)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## Overview

BugCatcher sits at the front of every workflow and automatically:
- Captures exceptions from workflow steps
- Tracks logged errors and exceptions
- Maintains request context via LRU cache
- Logs all exceptions to Grafana Loki
- Provides file-based logging fallback

## Features

### Exception Tracking
- **Global Exception Hook**: Captures all uncaught exceptions
- **Logging Handler**: Captures exceptions that are logged
- **Workflow Integration**: Automatically tracks workflow and step failures
- **Request Context**: Associates exceptions with workflow/step context via LRU cache

### Storage Backends
- **Loki**: Primary backend - centralized log aggregation
- **File Logging**: Fallback backend - local file storage

### Low Overhead
- **Batching**: Minimizes network requests to Loki
- **Bounded Memory**: LRU cache prevents unbounded growth
- **Graceful Degradation**: Works even if Loki is unavailable
- **Configurable**: Can be disabled without code changes

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Code Evolver Workflows                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Step 1   │ -> │ Step 2   │ -> │ Step 3   │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                      │
│       └───────────────┼───────────────┘                      │
│                       │                                      │
│                       v                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              BugCatcher                              │   │
│  │  ┌──────────────┐    ┌──────────────┐               │   │
│  │  │ LRU Cache    │    │ Exception    │               │   │
│  │  │ (Request     │    │ Capture      │               │   │
│  │  │  Context)    │    │              │               │   │
│  │  └──────────────┘    └──────┬───────┘               │   │
│  │                              │                        │   │
│  │                              v                        │   │
│  │  ┌──────────────────────────────────────┐            │   │
│  │  │         Logging Backends             │            │   │
│  │  │  ┌────────────┐    ┌──────────────┐  │            │   │
│  │  │  │   Loki     │    │   File Log   │  │            │   │
│  │  │  │  Backend   │    │   Backend    │  │            │   │
│  │  │  └─────┬──────┘    └──────────────┘  │            │   │
│  │  └────────┼─────────────────────────────┘            │   │
│  └───────────┼──────────────────────────────────────────┘   │
└──────────────┼──────────────────────────────────────────────┘
               │
               v
  ┌────────────────────────┐
  │   Grafana Loki         │
  │   (Docker Container)   │
  └────────────────────────┘
               │
               v
  ┌────────────────────────┐
  │   Grafana Dashboard    │
  │   (Visualization)      │
  └────────────────────────┘
```

## Quick Start

### 1. Start Local Development Environment

```bash
# Start Loki, Qdrant, and Grafana
cd code_evolver
docker-compose -f docker-compose.localdev.yml up -d

# Verify services are running
docker-compose -f docker-compose.localdev.yml ps
```

### 2. Configure BugCatcher

BugCatcher is configured in `config.yaml`:

```yaml
bugcatcher:
  enabled: true
  loki:
    url: "http://localhost:3100"
    enabled: true
  cache:
    max_size: 100
  file_logging:
    enabled: true
    file: "bugcatcher.log"
```

### 3. Run Code Evolver

BugCatcher automatically initializes when Code Evolver starts (if enabled):

```bash
python chat_cli.py
```

### 4. View Logs in Grafana

1. Open Grafana: http://localhost:3000
2. Login: admin / admin
3. Navigate to Explore
4. Select Loki datasource
5. Query: `{job="code_evolver_bugcatcher"}`

## Configuration

### Configuration Options

```yaml
bugcatcher:
  # Enable/disable BugCatcher
  enabled: true

  # Loki configuration
  loki:
    url: "http://localhost:3100"  # Loki push endpoint
    enabled: true                  # Enable Loki logging
    batch_size: 10                 # Number of logs to batch
    timeout: 5                     # Request timeout (seconds)

  # Request context cache
  cache:
    max_size: 100                  # Maximum cache entries

  # File logging (fallback)
  file_logging:
    enabled: true                  # Enable file logging
    file: "bugcatcher.log"         # Log file path

  # What to track
  tracking:
    exceptions: true               # Track raised exceptions
    logged_errors: true            # Track logged errors
    workflow_failures: true        # Track workflow failures
    tool_failures: true            # Track tool failures
    llm_errors: true               # Track LLM errors

  # Minimum severity to capture
  min_severity: "WARNING"          # DEBUG, INFO, WARNING, ERROR, CRITICAL

  # Auto-install exception hooks
  auto_install_hooks: true         # Install global exception hooks
```

### Environment Variables

BugCatcher respects the following environment variables:

- `BUGCATCHER_ENABLED`: Override `bugcatcher.enabled` setting
- `LOKI_URL`: Override Loki URL
- `BUGCATCHER_LOG_FILE`: Override log file path

## Usage

### Automatic Usage

BugCatcher automatically tracks all workflow steps:

```python
# No code changes needed - BugCatcher is automatic!
# Just run your workflows as normal
```

### Manual Exception Tracking

```python
from src.bugcatcher import get_bugcatcher

bugcatcher = get_bugcatcher()

# Track a request
bugcatcher.track_request('request_123', {
    'workflow_id': 'wf_1',
    'step_id': 'step_1',
    'tool_name': 'my_tool'
})

# Capture an exception
try:
    # Your code
    result = risky_operation()
except Exception as e:
    bugcatcher.capture_exception(
        e,
        request_id='request_123',
        additional_context={'operation': 'risky_operation'}
    )
```

### Context Manager

```python
from src.bugcatcher import track_request

# Automatically track and capture exceptions
with track_request('request_123', workflow_id='wf_1', step_id='step_1'):
    # Your code - exceptions automatically captured
    result = my_function()
```

### Getting Statistics

```python
from src.bugcatcher import get_bugcatcher

bugcatcher = get_bugcatcher()
stats = bugcatcher.get_stats()

print(f"Total exceptions: {stats['total_exceptions']}")
print(f"Cache size: {stats['cache_size']}")
print(f"Loki enabled: {stats['loki_enabled']}")
```

### Flushing Logs

```python
from src.bugcatcher_setup import flush_bugcatcher

# Flush pending logs before shutdown
flush_bugcatcher()
```

## Docker Setup

### docker-compose.localdev.yml

The local development environment includes:

- **Loki**: Log aggregation (port 3100)
- **Qdrant**: Vector database (ports 6333, 6334)
- **Grafana**: Visualization dashboard (port 3000)

```bash
# Start all services
docker-compose -f docker-compose.localdev.yml up -d

# View logs
docker-compose -f docker-compose.localdev.yml logs -f loki

# Stop all services
docker-compose -f docker-compose.localdev.yml down

# Stop and remove volumes
docker-compose -f docker-compose.localdev.yml down -v
```

### Service URLs

- Loki: http://localhost:3100
- Qdrant: http://localhost:6333
- Qdrant Dashboard: http://localhost:6333/dashboard
- Grafana: http://localhost:3000

### Persistent Data

All services use Docker volumes for persistence:

- `code_evolver_loki_data`: Loki logs and indexes
- `code_evolver_qdrant_storage`: Qdrant vector data
- `code_evolver_grafana_data`: Grafana dashboards and settings

## Grafana Dashboard

### Setting Up Grafana

1. **Access Grafana**: http://localhost:3000
2. **Login**: admin / admin (change on first login)
3. **Loki datasource**: Auto-provisioned as default

### Querying Logs

Example LogQL queries:

```logql
# All BugCatcher logs
{job="code_evolver_bugcatcher"}

# Only errors
{job="code_evolver_bugcatcher", severity="error"}

# Specific workflow
{job="code_evolver_bugcatcher", workflow_id="wf_123"}

# Specific exception type
{job="code_evolver_bugcatcher", exception_type="ValueError"}

# Time range with rate
rate({job="code_evolver_bugcatcher"}[5m])
```

### Creating Dashboards

1. Navigate to Dashboards > New Dashboard
2. Add Panel
3. Select Loki datasource
4. Enter LogQL query
5. Configure visualization
6. Save dashboard

### Recommended Panels

- **Exception Rate**: `rate({job="code_evolver_bugcatcher"}[1m])`
- **Exceptions by Type**: Group by `exception_type` label
- **Exceptions by Workflow**: Group by `workflow_id` label
- **Recent Exceptions**: Table view with time, severity, message

## API Reference

### BugCatcher Class

```python
class BugCatcher:
    def __init__(
        self,
        loki_url: str = "http://localhost:3100",
        loki_enabled: bool = True,
        cache_size: int = 100,
        log_to_file: bool = True,
        log_file: str = "bugcatcher.log"
    )

    def track_request(
        self,
        request_id: str,
        context: Dict[str, Any]
    )

    def capture_exception(
        self,
        exception: Exception,
        request_id: Optional[str] = None,
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        additional_context: Optional[Dict[str, Any]] = None
    )

    def get_stats(self) -> Dict[str, Any]

    def flush(self)
```

### Helper Functions

```python
# Get singleton instance
def get_bugcatcher() -> BugCatcher

# Setup with config
def setup_bugcatcher_logging(**kwargs) -> BugCatcher

# Initialize from config dict
def initialize_bugcatcher_from_config(config: Dict[str, Any]) -> Optional[BugCatcher]

# Check Loki connection
def check_loki_connection(loki_url: str, timeout: int) -> bool

# Flush pending logs
def flush_bugcatcher()
```

## Troubleshooting

### Logs Not Appearing in Loki

**Symptoms**: Exceptions are captured but not visible in Grafana

**Solutions**:
1. Check Loki is running: `docker ps | grep loki`
2. Verify Loki URL in config: `bugcatcher.loki.url`
3. Check `loki_enabled` is `true`
4. Flush logs manually: `bugcatcher.flush()`
5. Check Loki logs: `docker logs code_evolver_loki`

### Connection Refused

**Symptoms**: "Connection refused" errors when logging

**Solutions**:
1. Start Loki: `docker-compose -f docker-compose.localdev.yml up -d loki`
2. Check port mapping: `docker port code_evolver_loki`
3. Verify URL is correct: `http://localhost:3100` (not `https`)
4. Check firewall settings

### High Memory Usage

**Symptoms**: BugCatcher consuming excessive memory

**Solutions**:
1. Reduce cache size in config: `bugcatcher.cache.max_size`
2. Reduce batch size: `bugcatcher.loki.batch_size`
3. Enable more frequent flushing
4. Check for exception loops (fix the underlying issue)

### Exceptions Not Being Captured

**Symptoms**: Known exceptions not appearing in logs

**Solutions**:
1. Verify BugCatcher is enabled: `bugcatcher.enabled: true`
2. Check auto-install hooks: `bugcatcher.auto_install_hooks: true`
3. Verify severity level: Check `bugcatcher.min_severity`
4. Check tracking settings: Ensure relevant tracking is enabled
5. Manually capture: Use `bugcatcher.capture_exception()`

### Grafana Not Showing Data

**Symptoms**: Grafana connected but no data visible

**Solutions**:
1. Check time range (default is last 6 hours)
2. Verify query: `{job="code_evolver_bugcatcher"}`
3. Check Loki datasource is default
4. Refresh datasource: Settings > Data Sources > Loki > Test
5. Check Loki has data: `curl http://localhost:3100/loki/api/v1/labels`

## Best Practices

1. **Always flush before shutdown**: Call `flush_bugcatcher()` in cleanup code
2. **Monitor cache size**: Keep cache size appropriate for your workload
3. **Use appropriate severity levels**: Don't capture DEBUG in production
4. **Set up alerting**: Configure Grafana alerts for critical exceptions
5. **Regular log review**: Periodically review exception patterns
6. **Clean up old logs**: Configure Loki retention (default: 7 days)
7. **Test Loki availability**: Use `check_loki_connection()` on startup

## Integration with Other Tools

### Workflow Tracker

BugCatcher automatically integrates with WorkflowTracker:

```python
from src.workflow_tracker import WorkflowTracker

tracker = WorkflowTracker('wf_1', 'My Workflow')

# BugCatcher automatically tracks this workflow
step = tracker.add_step('step_1', 'my_tool', 'Do something')
tracker.start_step('step_1')

# If step fails, BugCatcher captures the exception
tracker.fail_step('step_1', 'Something went wrong')
```

### Status Manager

BugCatcher complements StatusManager for real-time monitoring:

- **StatusManager**: Real-time in-memory status updates
- **BugCatcher**: Historical exception logging and aggregation

### Profiling

Use BugCatcher with Profiling for comprehensive observability:

- **Profiling**: Performance metrics (timing, memory)
- **BugCatcher**: Exception and error tracking

## Advanced Topics

### Custom Exception Severity

```python
from src.bugcatcher import ExceptionSeverity, get_bugcatcher

bugcatcher = get_bugcatcher()

# Capture with custom severity
try:
    result = operation()
except KnownIssueException as e:
    # Log as warning instead of error
    bugcatcher.capture_exception(e, severity=ExceptionSeverity.WARNING)
```

### Custom Loki Labels

Loki labels are automatically generated from context:

- `job`: Always "code_evolver_bugcatcher"
- `severity`: Exception severity level
- `exception_type`: Exception class name
- `workflow_id`: Workflow ID (if available)
- `tool_name`: Tool name (if available)

### Batching and Performance

BugCatcher batches logs to minimize network overhead:

- Default batch size: 10 logs
- Batch sent when full or on flush
- Adjust via `bugcatcher.loki.batch_size`

### File Logging Format

File logs use Python's standard logging format:

```
2024-01-15 10:30:45,123 - bugcatcher - ERROR - BugCatcher captured ValueError: Invalid input
```

## Contributing

To contribute to BugCatcher:

1. Add tests in `tests/test_bugcatcher.py`
2. Update documentation in `docs/BUGCATCHER.md`
3. Follow existing code style
4. Ensure all tests pass

## License

BugCatcher is part of Code Evolver and uses the same license.
