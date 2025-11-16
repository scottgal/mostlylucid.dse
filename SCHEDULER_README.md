# Scheduler System

A comprehensive scheduling system for Code Evolver that enables scheduled tasks, workflows, and polling with natural language CRON conversion.

## Features

- **Natural Language Scheduling**: Convert plain English like "every 20 minutes" or "at 6pm each evening" to CRON expressions using LLM
- **Persistent Storage**: SQLite database for schedules and execution history
- **Background Service**: APScheduler-based service that runs alongside the CLI
- **CLI Commands**: Full command-line interface for schedule management
- **System-Wide Scope**: Singleton service accessible across all workflows and tools
- **Thread-Safe**: Concurrent read/write operations supported
- **Execution History**: Track all schedule executions with results and errors

## Architecture

### Components

1. **SchedulerDB** (`src/scheduler_db.py`)
   - SQLite persistence layer
   - Manages schedules and execution history
   - Thread-safe operations with context managers

2. **SchedulerService** (`src/scheduler_service.py`)
   - APScheduler background service
   - Singleton pattern for system-wide access
   - CRON-based job scheduling
   - Tool execution integration

3. **CRON Converter** (`tools/llm/cron_converter.yaml`)
   - LLM tool for natural language to CRON conversion
   - Uses fast, efficient model (speed.tier_1)
   - Examples: "every 20 minutes" → "*/20 * * * *"

4. **Schedule Manager** (`tools/executable/schedule_manager.yaml`)
   - Executable tool for CRUD operations
   - System-scoped for global access
   - Operations: create, list, get, pause, resume, delete, trigger, history

5. **CLI Integration** (`chat_cli.py`)
   - `/schedule` command family
   - Auto-start on CLI initialization
   - Clean shutdown on exit

### Database Schema

**schedules table:**
- `id` (TEXT PRIMARY KEY): Unique schedule identifier
- `name` (TEXT): Human-readable name
- `description` (TEXT): Natural language description
- `cron_expression` (TEXT): CRON schedule expression
- `tool_name` (TEXT): Tool to execute
- `tool_inputs` (TEXT): JSON-encoded tool parameters
- `status` (TEXT): active, paused, or error
- `created_at` (TEXT): ISO timestamp
- `last_run` (TEXT): Last execution time
- `next_run` (TEXT): Next scheduled execution
- `run_count` (INTEGER): Number of executions

**executions table:**
- `id` (INTEGER PRIMARY KEY): Execution record ID
- `schedule_id` (TEXT): Foreign key to schedule
- `started_at` (TEXT): Execution start time
- `finished_at` (TEXT): Execution completion time
- `status` (TEXT): running, success, or failed
- `result` (TEXT): JSON-encoded result
- `error` (TEXT): Error message if failed

## Usage

### CLI Commands

```bash
# Create a new schedule
/schedule create "every 20 minutes" basic_calculator '{"operation": "add", "a": 5, "b": 3}'

# List all schedules
/schedule list

# List active schedules only
/schedule list active

# Trigger a schedule immediately
/schedule trigger schedule_abc123

# View execution history
/schedule history schedule_abc123

# Pause a schedule
/schedule pause schedule_abc123

# Resume a paused schedule
/schedule resume schedule_abc123

# Delete a schedule
/schedule delete schedule_abc123
```

### Natural Language Examples

The system automatically converts natural language to CRON:

- "every 5 minutes" → `*/5 * * * *`
- "every hour" → `0 * * * *`
- "every day at midnight" → `0 0 * * *`
- "every day at 6pm" → `0 18 * * *`
- "at 6pm each evening" → `0 18 * * *`
- "every weekday at 8:30am" → `30 8 * * 1-5`
- "every Monday at 9am" → `0 9 * * 1`
- "twice a day" → `0 0,12 * * *`
- "every 2 hours" → `0 */2 * * *`

### Programmatic Usage

```python
from src.scheduler_service import SchedulerService

# Get singleton instance
scheduler = SchedulerService()

# Set tool executor (required before starting)
def tool_executor(tool_name, tool_inputs):
    # Execute your tool here
    return {'success': True, 'result': 'Done'}

scheduler.set_tool_executor(tool_executor)

# Start the scheduler
scheduler.start()

# Create a schedule
schedule = scheduler.create_schedule(
    name='Daily Report',
    description='every day at 9am',
    cron_expression='0 9 * * *',
    tool_name='generate_report',
    tool_inputs={'format': 'pdf'}
)

# List schedules
schedules = scheduler.list_schedules(status='active')

# Trigger manually
result = scheduler.trigger_now(schedule['id'])

# View history
history = scheduler.get_execution_history(schedule['id'])

# Stop the scheduler
scheduler.stop()
```

### Database API

```python
from src.scheduler_db import SchedulerDB

# Initialize database
db = SchedulerDB()  # Uses default path: scheduler.db

# Create schedule
schedule = db.create_schedule(
    schedule_id='my_schedule_001',
    name='My Schedule',
    description='every 10 minutes',
    cron_expression='*/10 * * * *',
    tool_name='my_tool',
    tool_inputs={'param': 'value'}
)

# List schedules
schedules = db.list_schedules(status='active')

# Get schedule
schedule = db.get_schedule('my_schedule_001')

# Update status
db.update_schedule_status('my_schedule_001', 'paused')

# Create execution record
exec_id = db.create_execution('my_schedule_001')

# Update execution with results
db.update_execution(
    exec_id,
    status='success',
    result={'output': 'Complete'}
)

# Get execution history
history = db.get_execution_history('my_schedule_001', limit=50)

# Delete schedule
db.delete_schedule('my_schedule_001')
```

## Scope Concept

The scheduler introduces a new **scope** concept for tools:

- **system**: Single instance across entire system (scheduler uses this)
- **workflow**: One instance per workflow
- **tool**: One instance per tool invocation
- **siblings**: Shared across all instances of the same tool type

This is configured in the tool YAML:
```yaml
scope: "system"  # System-wide singleton
```

## Testing

Run the test suite:

```bash
python test_scheduler_simple.py
```

Tests cover:
- Database CRUD operations
- Execution tracking
- CRON validation
- Schedule lifecycle

## Files Created

1. `src/scheduler_db.py` - SQLite persistence layer
2. `src/scheduler_service.py` - APScheduler background service
3. `tools/llm/cron_converter.yaml` - Natural language to CRON converter
4. `tools/executable/schedule_manager.yaml` - Schedule management tool
5. `tools/executable/schedule_manager.py` - Tool implementation
6. `chat_cli.py` - Updated with /schedule commands
7. `requirements.txt` - Updated with APScheduler>=3.10.4
8. `test_scheduler_simple.py` - Test suite
9. `scheduler.db` - SQLite database (created on first run)

## Dependencies

- **APScheduler>=3.10.4**: Job scheduling framework
- **sqlite3**: Built-in Python (no install needed)
- **threading**: Built-in Python (no install needed)

## Future Enhancements

Potential improvements:

1. **Advanced Scheduling**:
   - One-time schedules (specific date/time)
   - Interval-based schedules (every X seconds)
   - Date-based triggers

2. **Workflow Integration**:
   - Schedule entire workflows, not just tools
   - Multi-step scheduled tasks
   - Conditional execution

3. **Monitoring**:
   - Success/failure notifications
   - Slack/email alerts
   - Dashboard for schedule visualization

4. **Advanced Features**:
   - Schedule dependencies (chain schedules)
   - Retry logic for failed executions
   - Parallel execution limits
   - Schedule versioning and rollback

5. **Performance**:
   - Distributed scheduling (multi-node)
   - Priority queues
   - Resource limits per schedule

## Notes

- The scheduler starts automatically when the CLI initializes
- Schedules persist across CLI sessions
- Failed executions are logged with error messages
- The scheduler is thread-safe and supports concurrent operations
- All times are stored in UTC
- The singleton pattern ensures only one scheduler instance runs
