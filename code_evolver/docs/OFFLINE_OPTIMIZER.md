># Offline Optimizer Feature

The Offline Optimizer is a comprehensive system for monitoring, scheduling, and optimizing background tasks without interfering with active user workflows.

## Overview

The Offline Optimizer consists of three main components:

1. **Enhanced PerfCatcher** - Rolling buffer with threshold-based Loki dumps
2. **Priority-Aware Task Scheduler** - Multi-level priority queue system
3. **Scheduled Tasks System** - Cron-like scheduling with natural language support

## Component 1: Enhanced PerfCatcher

### Features

- **Rolling Buffer**: Maintains a 30-second rolling buffer of all tool requests
- **Threshold Monitoring**: Tracks performance variance per tool
- **Automatic Dumping**: Dumps entire buffer to Loki when thresholds are exceeded
- **Custom Thresholds**: Per-tool threshold configuration

### Configuration

Environment variables:
```bash
PERFCATCHER_ENABLED=true                    # Enable/disable (default: true)
PERFCATCHER_VARIANCE_THRESHOLD=0.2          # 20% variance threshold
PERFCATCHER_WINDOW_SIZE=100                 # Baseline window size
PERFCATCHER_MIN_SAMPLES=10                  # Min samples before checking
PERFCATCHER_BUFFER_DURATION=30              # Rolling buffer duration (seconds)
```

### Usage

```python
from src.tool_interceptors import get_global_interceptor_chain

chain = get_global_interceptor_chain()
perfcatcher = None
for interceptor in chain.interceptors:
    if isinstance(interceptor, PerfCatcherInterceptor):
        perfcatcher = interceptor
        break

# Set custom threshold for a tool
perfcatcher.set_tool_threshold('expensive_tool', 0.15)  # 15%

# Get buffer statistics
stats = perfcatcher.get_buffer_stats()
print(f"Buffer size: {stats['buffer_size']} requests")
print(f"Duration: {stats['duration_s']:.1f}s")

# Get tool performance statistics
tool_stats = perfcatcher.get_tool_stats('my_tool')
print(f"Mean: {tool_stats['mean_ms']:.2f}ms")
print(f"P95: {tool_stats['p95_ms']:.2f}ms")
```

### Buffer Dump Format

When a threshold is exceeded, PerfCatcher dumps the entire rolling buffer to Loki:

```json
{
  "type": "perfcatcher_buffer_dump",
  "triggered_by": "slow_tool",
  "trigger_variance": 0.35,
  "trigger_timestamp": "2025-01-16T10:30:00",
  "buffer_size": 45,
  "buffer_duration_s": 30,
  "requests": [
    {
      "tool_name": "example_tool",
      "execution_time_ms": 123.45,
      "timestamp": 1705401000.123,
      "timestamp_iso": "2025-01-16T10:29:30",
      "workflow_id": "workflow_123",
      "step_id": "step_5",
      "result_summary": "Success: processed 100 items"
    },
    // ... more requests
  ]
}
```

Loki labels:
- `job`: `code_evolver_offline_optimizer`
- `type`: `buffer_dump`
- `triggered_by`: Tool name that triggered the dump
- `severity`: `high` or `medium` based on variance level

### Querying Buffer Dumps

```bash
# Query Loki for buffer dumps
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="code_evolver_offline_optimizer"}' \
  --data-urlencode 'start=1h' \
  --data-urlencode 'limit=100'
```

## Component 2: Priority-Aware Task Scheduler

### Priority Levels

```python
class TaskPriority(Enum):
    CRITICAL = 0     # System-critical tasks
    HIGH = 10        # User workflows, builders
    NORMAL = 50      # Regular operations
    LOW = 90         # Background tasks
    BACKGROUND = 100 # Lowest priority
```

### Features

- **Multi-level Queues**: Separate queues for each priority level
- **Fair Scheduling**: FIFO within priority levels
- **Workflow Awareness**: Pauses background tasks when workflows are active
- **Background Throttling**: Configurable delays between background tasks
- **Thread-Safe**: Concurrent execution with multiple workers

### Configuration

```python
from src.task_scheduler import PriorityTaskScheduler

scheduler = PriorityTaskScheduler(
    num_workers=2,                    # Worker threads
    max_queue_size=1000,              # Max queued tasks
    background_throttle_ms=100        # Min delay between background tasks
)
scheduler.start()
```

### Usage

```python
from src.task_scheduler import get_global_scheduler, TaskPriority

scheduler = get_global_scheduler()

# Submit high-priority workflow task
task_id = scheduler.submit(
    func=process_workflow_step,
    args=(step_data,),
    priority=TaskPriority.HIGH,
    name="workflow_step_1",
    metadata={"workflow_id": "wf_123"}
)

# Submit background task
bg_task_id = scheduler.submit(
    func=cleanup_old_data,
    priority=TaskPriority.BACKGROUND,
    name="cleanup_task"
)

# Mark workflow as active (pauses background tasks)
scheduler.mark_workflow_active("wf_123")

# ... workflow executes ...

# Mark workflow as inactive (resumes background tasks)
scheduler.mark_workflow_inactive("wf_123")

# Get task status
task = scheduler.get_task(task_id)
print(f"Status: {task.status}")
print(f"Duration: {task.duration_ms}ms")

# Get scheduler statistics
stats = scheduler.get_stats()
print(f"Tasks completed: {stats['tasks_completed']}")
print(f"High priority: {stats['high_priority_tasks']}")
print(f"Background: {stats['background_tasks']}")
```

### Background Task Behavior

Background tasks are automatically throttled when:
1. High-priority workflows are active
2. Minimum throttle delay hasn't elapsed

This ensures workflows get maximum system resources.

## Component 3: Scheduled Tasks System

### Features

- **Natural Language Scheduling**: Convert English to cron expressions
- **RAG Storage**: Semantic search for scheduled tasks
- **Execution Tracking**: Last run, success/failure tracking
- **Auto-disable on Errors**: Disables after 5 consecutive failures
- **Persistent Storage**: JSON backup + RAG semantic storage

### Natural Language Examples

```python
from src.scheduled_tasks import get_global_task_manager

task_manager = get_global_task_manager()

# Natural language descriptions
schedules = [
    "every 5 minutes",
    "every hour",
    "every day at 2pm",
    "every sunday at noon",
    "every monday at midnight",
    "every week",
    "every month"
]

# Converted to cron automatically
# "every sunday at noon" -> "0 12 * * 0"
```

### Creating Scheduled Tasks

```python
# Define task function
def poll_api():
    response = requests.get("https://api.example.com/events")
    return response.json()

# Create scheduled task
task_id = task_manager.create_task(
    name="event_poller",
    description="Poll external API for new events",
    schedule="every 5 minutes",  # Natural language
    func=poll_api,
    func_name="poll_api",  # For persistence
    metadata={
        "api_endpoint": "https://api.example.com/events",
        "timeout": 30
    }
)

# Or use cron expression directly
task_id = task_manager.create_task(
    name="nightly_backup",
    description="Backup database to S3",
    schedule="0 2 * * *",  # 2am daily
    func=backup_database,
    func_name="backup_database"
)
```

### Managing Scheduled Tasks

```python
# List all tasks
tasks = task_manager.list_tasks(enabled_only=True)
for task in tasks:
    print(f"{task.name}: {task.cron_expression}")
    print(f"  Next run: {task.get_next_run_time()}")
    print(f"  Run count: {task.run_count}")
    print(f"  Errors: {task.error_count}")

# Get tasks due now
due_tasks = task_manager.get_tasks_due_now()

# Get tasks due in next 20 minutes
upcoming = task_manager.get_tasks_due_now(window_minutes=20)

# Mark task as executed
task_manager.mark_task_run(
    task_id=task_id,
    success=True,
    result="Processed 100 events"
)

# Mark task as failed
task_manager.mark_task_run(
    task_id=task_id,
    success=False,
    error="API timeout"
)

# Delete task
task_manager.delete_task(task_id)
```

### Task Storage

Tasks are stored in two places:

1. **JSON File**: `./data/scheduled_tasks/tasks.json`
   - Persistent backup
   - Fast loading on startup

2. **RAG Memory**: Semantic embeddings for search
   - Stored as `PLAN` artifacts
   - Searchable by description and schedule
   - Tags: `['scheduled_task', 'cron', expression]`

### RAG Integration

```python
# Tasks are automatically stored in RAG with semantic embeddings
# This allows natural language queries like:

from src import create_rag_memory

rag = create_rag_memory(config_manager, ollama_client)

# Find similar tasks
similar = rag.find_similar(
    artifact_type=ArtifactType.PLAN,
    query="tasks that run daily",
    tags=['scheduled_task'],
    limit=10
)

# Search by cron pattern
weekly_tasks = rag.find_by_tags(['scheduled_task', '* * * * 0'])
```

## Component 4: Background Scheduler Loop

### Features

- **Automatic Monitoring**: Checks for due tasks every 30 seconds
- **Workflow-Aware**: Pauses when user workflows are active
- **Low Priority Execution**: Uses BACKGROUND priority
- **Concurrent Limit**: Max 1 background task at a time (configurable)
- **Statistics Tracking**: Execution counts, failures, skipped tasks

### Usage

The background scheduler starts automatically when the CLI initializes:

```python
# Starts automatically in ChatCLI.__init__()
from src.background_scheduler import start_background_scheduler

start_background_scheduler()
```

### Configuration

```python
from src.background_scheduler import BackgroundScheduler

scheduler = BackgroundScheduler(
    check_interval_seconds=30,    # Check every 30s
    max_concurrent_tasks=1        # Max concurrent background tasks
)
scheduler.start()

# Get statistics
stats = scheduler.get_stats()
print(f"Checks performed: {stats['checks_performed']}")
print(f"Tasks executed: {stats['tasks_executed']}")
print(f"Tasks failed: {stats['tasks_failed']}")
print(f"Skipped due to workflows: {stats['tasks_skipped_due_to_workflows']}")
```

## Integration with Existing Systems

### CLI Integration

The Offline Optimizer is automatically initialized when the CLI starts:

```python
# In ChatCLI.__init__():
from src.background_scheduler import start_background_scheduler

start_background_scheduler()
# Background task scheduler started
```

### Workflow Integration

Mark workflows as active/inactive to control background task execution:

```python
from src.task_scheduler import get_global_scheduler

scheduler = get_global_scheduler()

# Before starting workflow
scheduler.mark_workflow_active(workflow_id)

try:
    # Execute workflow steps (HIGH priority)
    for step in workflow.steps:
        scheduler.submit(
            func=execute_step,
            args=(step,),
            priority=TaskPriority.HIGH,
            metadata={"workflow_id": workflow_id}
        )
finally:
    # After workflow completes
    scheduler.mark_workflow_inactive(workflow_id)
```

### Tool Interceptor Integration

PerfCatcher is automatically applied to all tool calls via the interceptor chain:

```python
# Automatic - no code changes needed!
# All tool calls are automatically monitored

from src.tools_manager import ToolsManager

tools = ToolsManager(config, ollama_client, rag)
result = tools.execute_tool("my_tool", {"arg": "value"})

# PerfCatcher automatically:
# - Records execution time
# - Adds to rolling buffer
# - Checks variance
# - Dumps buffer to Loki if threshold exceeded
```

## Use Cases

### 1. Event Polling

```python
task_manager.create_task(
    name="github_webhook_poller",
    description="Poll GitHub webhooks for new events",
    schedule="every 2 minutes",
    func=poll_github_webhooks,
    metadata={"repo": "myorg/myrepo"}
)
```

### 2. Periodic Reports

```python
task_manager.create_task(
    name="weekly_analytics",
    description="Generate and email weekly analytics report",
    schedule="every sunday at 9am",
    func=generate_analytics_report,
    metadata={"recipients": ["team@example.com"]}
)
```

### 3. Data Cleanup

```python
task_manager.create_task(
    name="cleanup_old_logs",
    description="Delete logs older than 30 days",
    schedule="0 3 * * *",  # 3am daily
    func=cleanup_old_logs,
    metadata={"retention_days": 30}
)
```

### 4. Performance Monitoring

```python
# Set custom thresholds for critical tools
perfcatcher.set_tool_threshold('database_query', 0.10)  # 10% variance
perfcatcher.set_tool_threshold('api_call', 0.25)        # 25% variance

# Buffer dumps will be sent to Loki when thresholds exceeded
# Query Loki to analyze performance patterns offline
```

## Dependencies

Required packages (already in `requirements.txt`):
- `croniter>=2.0.0` - Cron expression parsing and scheduling

## File Structure

```
code_evolver/
├── src/
│   ├── tool_interceptors.py         # Enhanced PerfCatcher
│   ├── task_scheduler.py             # Priority-aware scheduler
│   ├── scheduled_tasks.py            # Scheduled task management
│   └── background_scheduler.py       # Background monitoring loop
├── tools/executable/
│   └── schedule_task.yaml            # Scheduled task tool definition
├── examples/
│   └── offline_optimizer_example.py  # Complete examples
├── docs/
│   └── OFFLINE_OPTIMIZER.md          # This file
└── data/
    └── scheduled_tasks/
        └── tasks.json                # Persistent task storage
```

## Monitoring and Debugging

### Check PerfCatcher Buffer

```python
from src.tool_interceptors import get_global_interceptor_chain

chain = get_global_interceptor_chain()
for interceptor in chain.interceptors:
    if hasattr(interceptor, 'get_buffer_stats'):
        stats = interceptor.get_buffer_stats()
        print(f"Buffer: {stats['buffer_size']} requests, {stats['duration_s']:.1f}s")
```

### Check Task Scheduler

```python
from src.task_scheduler import get_global_scheduler

scheduler = get_global_scheduler()
stats = scheduler.get_stats()
print(f"Tasks: {stats['tasks_submitted']} submitted, {stats['tasks_completed']} completed")
print(f"Queue: {stats['queue_size']} pending")
```

### Check Scheduled Tasks

```python
from src.scheduled_tasks import get_global_task_manager

task_manager = get_global_task_manager()
tasks = task_manager.list_tasks()
print(f"Scheduled tasks: {len(tasks)}")

for task in tasks:
    print(f"\n{task.name}:")
    print(f"  Enabled: {task.enabled}")
    print(f"  Cron: {task.cron_expression}")
    print(f"  Last run: {task.last_run}")
    print(f"  Run count: {task.run_count}")
    print(f"  Errors: {task.error_count}")
```

### Check Background Scheduler

```python
from src.background_scheduler import get_global_background_scheduler

bg_scheduler = get_global_background_scheduler()
stats = bg_scheduler.get_stats()
print(f"Checks: {stats['checks_performed']}")
print(f"Executed: {stats['tasks_executed']}")
print(f"Failed: {stats['tasks_failed']}")
print(f"Skipped (workflows active): {stats['tasks_skipped_due_to_workflows']}")
```

### Query Loki for Performance Data

```bash
# Get buffer dumps from last hour
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="code_evolver_offline_optimizer",type="buffer_dump"}' \
  --data-urlencode 'start=1h' \
  --data-urlencode 'limit=100' | jq

# Get high-severity dumps only
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="code_evolver_offline_optimizer",severity="high"}' \
  --data-urlencode 'start=24h' | jq
```

## Best Practices

1. **Set Appropriate Thresholds**
   - Use lower thresholds (10-15%) for critical tools
   - Use higher thresholds (25-30%) for variable-performance tools

2. **Use Natural Language for Schedules**
   - Easier to read and maintain
   - Automatic conversion to cron
   - Explanation stored in metadata

3. **Monitor Task Errors**
   - Check error counts regularly
   - Investigate disabled tasks
   - Set up alerts for consecutive failures

4. **Mark Workflows Active**
   - Always mark user workflows as active
   - Ensures background tasks don't interfere
   - Maximizes workflow performance

5. **Review Buffer Dumps**
   - Periodically check Loki for patterns
   - Identify slow tools and optimize
   - Use for offline analysis and improvement

6. **Limit Concurrent Background Tasks**
   - Keep max_concurrent_tasks low (1-2)
   - Prevents resource contention
   - Ensures workflows get priority

## Troubleshooting

### Background Tasks Not Running

```python
# Check if background scheduler is started
from src.background_scheduler import get_global_background_scheduler

bg = get_global_background_scheduler()
if not bg._running:
    bg.start()

# Check for active workflows blocking background tasks
from src.task_scheduler import get_global_scheduler

scheduler = get_global_scheduler()
if scheduler.has_active_workflows():
    print("Workflows active - background tasks paused")
```

### Tasks Not Executing

```python
# Check task is enabled
task = task_manager.get_task(task_id)
if not task.enabled:
    print(f"Task disabled (errors: {task.error_count})")

# Check cron expression
from croniter import croniter
cron = croniter(task.cron_expression)
next_run = cron.get_next(datetime)
print(f"Next run: {next_run}")

# Check if function is defined
if task.func is None:
    print("No function defined for task")
```

### Buffer Not Dumping

```python
# Check PerfCatcher is enabled
perfcatcher = get_perfcatcher_interceptor()
if not perfcatcher.enabled:
    print("PerfCatcher disabled")

# Check variance threshold
threshold = perfcatcher.variance_threshold
print(f"Threshold: {threshold:.1%}")

# Check if BugCatcher/Loki is available
if not perfcatcher.bugcatcher:
    print("BugCatcher not available")
elif not hasattr(perfcatcher.bugcatcher, 'loki'):
    print("Loki not available")
```

## Future Enhancements

Potential future improvements:

1. **Distributed Scheduling** - Multi-machine task execution
2. **Task Dependencies** - DAG-based task workflows
3. **Dynamic Thresholds** - Machine learning-based threshold adjustment
4. **Advanced Cron** - Support for @yearly, @monthly, etc.
5. **Task Metrics** - Prometheus integration for monitoring
6. **Web UI** - Visual task management interface
7. **Notification System** - Email/Slack alerts on failures
8. **Task Retry** - Automatic retry with exponential backoff

## License

Part of the Code Evolver project.
