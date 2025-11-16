# Code Evolver Scheduler - Claude Desktop User Guide

**Complete guide for using the scheduler system with Claude Desktop**

## Table of Contents

1. [Quick Start](#quick-start)
2. [What is the Scheduler?](#what-is-the-scheduler)
3. [Installation](#installation)
4. [Basic Usage](#basic-usage)
5. [Natural Language Scheduling](#natural-language-scheduling)
6. [Command Reference](#command-reference)
7. [Practical Examples](#practical-examples)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage](#advanced-usage)
10. [FAQ](#faq)

---

## Quick Start

**Get started in 3 steps:**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the CLI
python chat_cli.py

# 3. Create your first schedule
/schedule create "every 20 minutes" basic_calculator '{"operation": "add", "a": 5, "b": 3"}'
```

That's it! Your schedule is now running in the background.

---

## What is the Scheduler?

The Code Evolver Scheduler is a **background task automation system** that:

- **Runs tasks automatically** on a schedule (like cron but easier)
- **Understands natural language** - just say "every 20 minutes" or "daily at 6pm"
- **Persists across sessions** - schedules survive CLI restarts
- **Tracks execution history** - see when tasks ran and their results
- **Integrates with all tools** - schedule any executable or LLM tool

### Use Cases

- **Automated backups**: "Run backup every day at 2am"
- **Monitoring**: "Check system health every 15 minutes"
- **Data processing**: "Process new files every hour"
- **Report generation**: "Generate weekly report every Monday at 9am"
- **Notifications**: "Send status update twice a day"
- **Testing**: "Run test suite every 30 minutes"

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Code Evolver installed
- Working CLI (run `python chat_cli.py` successfully)

### Install Dependencies

```bash
cd code_evolver
pip install -r requirements.txt
```

This installs APScheduler (the scheduling engine) and other dependencies.

### Verify Installation

Start the CLI and look for this message:

```
OK Scheduler service started
```

If you see this, the scheduler is ready to use!

---

## Basic Usage

### Starting the CLI

The scheduler starts automatically when you launch the CLI:

```bash
python chat_cli.py
```

You'll see:
```
OK Scheduler service started
```

The scheduler runs in the background and will:
- Load existing schedules from the database
- Execute scheduled tasks at their specified times
- Continue running until you exit the CLI

### Your First Schedule

Create a simple schedule that runs every 5 minutes:

```bash
/schedule create "every 5 minutes" basic_calculator '{"operation": "add", "a": 10, "b": 20"}'
```

**What happens:**
1. The natural language "every 5 minutes" is converted to CRON: `*/5 * * * *`
2. A schedule is created in the database
3. The schedule is activated in the background scheduler
4. The tool `basic_calculator` will run every 5 minutes with the given inputs

**Response:**
```
CRON expression: */5 * * * *
Schedule created successfully!
  ID: schedule_abc123def
  Name: basic_calculator - every 5 minutes
  CRON: */5 * * * *
  Next run: 2025-01-16T14:05:00
```

### List Your Schedules

See all active schedules:

```bash
/schedule list
```

**Output:**
```
┌─────────────────┬──────────────────┬─────────────────┬─────────────┬───────┬────────┬──────┬──────────────────┐
│ ID              │ Name             │ Description     │ CRON        │ Tool  │ Status │ Runs │ Next Run         │
├─────────────────┼──────────────────┼─────────────────┼─────────────┼───────┼────────┼──────┼──────────────────┤
│ schedule_abc123 │ basic_calculat...│ every 5 minutes │ */5 * * * * │ basic │ active │ 3    │ 2025-01-16 14:05 │
└─────────────────┴──────────────────┴─────────────────┴─────────────┴───────┴────────┴──────┴──────────────────┘
```

### Trigger Manually

Run a schedule immediately (without waiting):

```bash
/schedule trigger schedule_abc123
```

**Response:**
```
Schedule executed successfully!
  Execution ID: 42
  Result: {"result": 30, "operation": "add"}
```

### View Execution History

See past executions of a schedule:

```bash
/schedule history schedule_abc123
```

**Output:**
```
┌────┬─────────────────────┬─────────────────────┬─────────┬────────┐
│ ID │ Started             │ Finished            │ Status  │ Error  │
├────┼─────────────────────┼─────────────────────┼─────────┼────────┤
│ 45 │ 2025-01-16 14:05:00 │ 2025-01-16 14:05:01 │ success │        │
│ 44 │ 2025-01-16 14:00:00 │ 2025-01-16 14:00:01 │ success │        │
│ 43 │ 2025-01-16 13:55:00 │ 2025-01-16 13:55:01 │ success │        │
└────┴─────────────────────┴─────────────────────┴─────────┴────────┘
```

### Pause and Resume

Temporarily stop a schedule without deleting it:

```bash
# Pause
/schedule pause schedule_abc123

# Resume later
/schedule resume schedule_abc123
```

### Delete a Schedule

Permanently remove a schedule:

```bash
/schedule delete schedule_abc123
```

**Warning:** This deletes the schedule AND all its execution history!

---

## Natural Language Scheduling

One of the most powerful features is **natural language to CRON conversion**.

### How It Works

When you create a schedule, the system:
1. Takes your natural language description (e.g., "every 20 minutes")
2. Sends it to a small, fast LLM
3. Gets back a CRON expression (e.g., `*/20 * * * *`)
4. Creates the schedule with that CRON

### Supported Patterns

#### Minute-based
```
"every minute"          → * * * * *
"every 5 minutes"       → */5 * * * *
"every 15 minutes"      → */15 * * * *
"every 20 minutes"      → */20 * * * *
"every 30 minutes"      → */30 * * * *
```

#### Hour-based
```
"every hour"            → 0 * * * *
"every 2 hours"         → 0 */2 * * *
"every 6 hours"         → 0 */6 * * *
```

#### Daily
```
"every day at midnight" → 0 0 * * *
"every day at 6am"      → 0 6 * * *
"every day at 2pm"      → 0 14 * * *
"every day at 6pm"      → 0 18 * * *
"at 6pm each evening"   → 0 18 * * *
"daily at noon"         → 0 12 * * *
```

#### Weekly
```
"every Monday"          → 0 0 * * 1
"every Monday at 9am"   → 0 9 * * 1
"every Friday at 5pm"   → 0 17 * * 5
"every weekday at 8:30am" → 30 8 * * 1-5
"weekdays at 9am"       → 0 9 * * 1-5
```

#### Multiple times per day
```
"twice a day"           → 0 0,12 * * *
"three times a day"     → 0 0,8,16 * * *
"every 4 hours"         → 0 */4 * * *
```

#### Special cases
```
"once an hour"          → 0 * * * *
"hourly"                → 0 * * * *
"daily"                 → 0 0 * * *
"weekly"                → 0 0 * * 0
```

### Tips for Best Results

1. **Be specific**: "every 20 minutes" is better than "often"
2. **Use common phrases**: "daily at 6pm" works better than "6 in the evening every day"
3. **Check the CRON**: The system shows you the CRON expression - verify it's correct
4. **Test manually**: Use `/schedule trigger` to test before waiting for automatic execution

---

## Command Reference

### `/schedule create`

**Create a new schedule**

```bash
/schedule create '<description>' <tool_name> [tool_inputs_json]
```

**Arguments:**
- `description` (required): Natural language schedule (e.g., "every 20 minutes")
- `tool_name` (required): Name of the tool to execute
- `tool_inputs_json` (optional): JSON object with tool parameters

**Examples:**

```bash
# Simple tool, no inputs
/schedule create "every hour" status_check '{}'

# Tool with inputs
/schedule create "every 30 minutes" backup_tool '{"source": "/data", "dest": "/backup"}'

# Complex inputs
/schedule create "daily at 2am" report_generator '{"type": "weekly", "format": "pdf", "recipients": ["admin@example.com"]}'
```

**Returns:**
- Schedule ID
- Name
- CRON expression
- Next run time

---

### `/schedule list`

**List all schedules or filter by status**

```bash
/schedule list [status]
```

**Arguments:**
- `status` (optional): Filter by status - `active`, `paused`, or `error`

**Examples:**

```bash
# All schedules
/schedule list

# Only active
/schedule list active

# Only paused
/schedule list paused

# Only errored
/schedule list error
```

**Returns:**
Table with columns:
- ID
- Name
- Description
- CRON expression
- Tool name
- Status
- Run count
- Next run time

---

### `/schedule trigger`

**Execute a schedule immediately**

```bash
/schedule trigger <schedule_id>
```

**Arguments:**
- `schedule_id` (required): ID of the schedule to run

**Examples:**

```bash
/schedule trigger schedule_abc123
```

**Returns:**
- Execution ID
- Status (success or failed)
- Result data or error message

**Note:** This runs the schedule immediately WITHOUT affecting its regular schedule.

---

### `/schedule pause`

**Pause a schedule (stop automatic execution)**

```bash
/schedule pause <schedule_id>
```

**Arguments:**
- `schedule_id` (required): ID of the schedule to pause

**Examples:**

```bash
/schedule pause schedule_abc123
```

**What happens:**
- Schedule is removed from the active scheduler
- Status changes to "paused"
- Schedule and history remain in database
- Can be resumed later with `/schedule resume`

---

### `/schedule resume`

**Resume a paused schedule**

```bash
/schedule resume <schedule_id>
```

**Arguments:**
- `schedule_id` (required): ID of the schedule to resume

**Examples:**

```bash
/schedule resume schedule_abc123
```

**What happens:**
- Schedule is re-added to the active scheduler
- Status changes to "active"
- Next run time is calculated
- Automatic execution resumes

---

### `/schedule delete`

**Permanently delete a schedule**

```bash
/schedule delete <schedule_id>
```

**Arguments:**
- `schedule_id` (required): ID of the schedule to delete

**Examples:**

```bash
/schedule delete schedule_abc123
```

**Warning:**
- This is PERMANENT
- Schedule AND all execution history are deleted
- Cannot be undone

---

### `/schedule history`

**View execution history for a schedule**

```bash
/schedule history <schedule_id>
```

**Arguments:**
- `schedule_id` (required): ID of the schedule

**Examples:**

```bash
/schedule history schedule_abc123
```

**Returns:**
Table with last 20 executions showing:
- Execution ID
- Started time
- Finished time
- Status (success, failed, running)
- Error message (if failed)

---

## Practical Examples

### Example 1: Daily Backup

**Scenario:** Back up your data every day at 2am

```bash
/schedule create "every day at 2am" backup_tool '{"source": "/data", "destination": "/backups", "compress": true}'
```

**Verify:**
```bash
/schedule list
```

**Test it:**
```bash
/schedule trigger <schedule_id>
```

---

### Example 2: Monitoring System Health

**Scenario:** Check system health every 15 minutes

```bash
/schedule create "every 15 minutes" health_check '{"services": ["web", "db", "cache"], "alert": true}'
```

**Monitor executions:**
```bash
/schedule history <schedule_id>
```

---

### Example 3: Weekly Report Generation

**Scenario:** Generate a weekly report every Monday at 9am

```bash
/schedule create "every Monday at 9am" report_generator '{"report_type": "weekly", "format": "pdf", "email": "team@company.com"}'
```

---

### Example 4: Data Processing Pipeline

**Scenario:** Process new files every hour

```bash
/schedule create "every hour" file_processor '{"input_dir": "/incoming", "output_dir": "/processed", "format": "json"}'
```

**View progress:**
```bash
# See all executions
/schedule history <schedule_id>

# Trigger manual processing
/schedule trigger <schedule_id>
```

---

### Example 5: Temporary Schedule

**Scenario:** Run a task every 5 minutes for testing, then pause it

```bash
# Create
/schedule create "every 5 minutes" test_tool '{}'

# Let it run a few times...

# Check history
/schedule history <schedule_id>

# Pause when done testing
/schedule pause <schedule_id>

# Delete when completely done
/schedule delete <schedule_id>
```

---

### Example 6: Complex Multi-Parameter Tool

**Scenario:** Schedule a complex data sync with many parameters

```bash
/schedule create "every 6 hours" data_sync '{
  "source": {
    "type": "database",
    "host": "db.example.com",
    "database": "production"
  },
  "destination": {
    "type": "s3",
    "bucket": "backups",
    "prefix": "daily/"
  },
  "options": {
    "incremental": true,
    "compression": "gzip",
    "encryption": true
  }
}'
```

---

## Troubleshooting

### Scheduler Not Starting

**Symptom:** No "OK Scheduler service started" message when launching CLI

**Solutions:**

1. Check APScheduler is installed:
   ```bash
   pip install APScheduler>=3.10.4
   ```

2. Check for import errors:
   ```bash
   python -c "from src.scheduler_service import SchedulerService; print('OK')"
   ```

3. Check database permissions:
   ```bash
   # Ensure you can write to the current directory
   touch scheduler.db && rm scheduler.db
   ```

---

### Schedule Not Executing

**Symptom:** Schedule created but tool never runs

**Debugging steps:**

1. **Verify schedule exists:**
   ```bash
   /schedule list
   ```

2. **Check status is "active":**
   - Status should be "active", not "paused" or "error"

3. **Check next run time:**
   - Is it in the future?
   - Is the CRON expression correct?

4. **Test manually:**
   ```bash
   /schedule trigger <schedule_id>
   ```
   - Does it work when triggered manually?

5. **Check execution history:**
   ```bash
   /schedule history <schedule_id>
   ```
   - Are there any error messages?

---

### CRON Expression Wrong

**Symptom:** Natural language converted to wrong CRON

**Solution:**

1. Check what CRON was generated (shown when you create)

2. If wrong, delete and recreate with explicit CRON:
   ```bash
   # Delete wrong one
   /schedule delete <schedule_id>

   # Create with explicit CRON
   # (You can bypass natural language by using a valid CRON directly)
   ```

3. Use [crontab.guru](https://crontab.guru) to verify CRON expressions

---

### Tool Execution Fails

**Symptom:** Schedule runs but tool fails

**Debugging:**

1. **Check execution history:**
   ```bash
   /schedule history <schedule_id>
   ```
   Look at the "Error" column

2. **Test tool directly:**
   ```bash
   /tool run <tool_name> <inputs>
   ```
   Does the tool work when run manually?

3. **Check tool inputs:**
   - Are the JSON parameters correct?
   - Are all required parameters provided?

4. **View detailed error:**
   Check the schedule's execution history for the full error message

---

### Database Issues

**Symptom:** "Database is locked" or similar errors

**Solutions:**

1. **Close other instances:**
   - Only one CLI instance should be running
   - Check for background processes: `ps aux | grep chat_cli`

2. **Reset database** (WARNING: deletes all schedules):
   ```bash
   rm scheduler.db
   # Restart CLI - fresh database will be created
   ```

3. **Check disk space:**
   ```bash
   df -h .
   ```

---

### Schedule Shows "error" Status

**Symptom:** Schedule status is "error"

**What happened:**
- The last execution failed with an error
- The scheduler automatically marked it as "error" status

**Solutions:**

1. **Check execution history:**
   ```bash
   /schedule history <schedule_id>
   ```
   Look for the error message

2. **Fix the underlying issue:**
   - Tool not available?
   - Invalid parameters?
   - Permission issue?

3. **Resume when fixed:**
   ```bash
   /schedule resume <schedule_id>
   ```

---

## Advanced Usage

### Using CRON Expressions Directly

While natural language is convenient, you can use CRON expressions directly for precise control:

```bash
# Every 7 minutes
/schedule create "custom schedule" my_tool '{"param": "value"}'
# Then manually edit the CRON in the database, OR:
```

**CRON Format:**
```
* * * * *
│ │ │ │ │
│ │ │ │ └─ Day of week (0-6, 0=Sunday)
│ │ │ └─── Month (1-12)
│ │ └───── Day of month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

**Special characters:**
- `*` = every
- `*/N` = every N units
- `N,M` = at N and M
- `N-M` = from N to M

---

### Scheduling Workflows (Not Just Tools)

Currently, schedules work with individual tools. For multi-step workflows:

**Workaround:** Create a custom tool that orchestrates the workflow:

1. Create a new executable tool
2. Make it call multiple tools in sequence
3. Schedule that orchestrator tool

---

### Monitoring and Alerts

**Pattern:** Create a monitoring schedule that sends alerts on failure

```bash
/schedule create "every 15 minutes" health_monitor '{"alert_email": "ops@company.com", "services": ["web", "db"]}'
```

Make your `health_monitor` tool:
- Check service health
- Send email only if something fails
- Return success/failure status

---

### Database Maintenance

The schedule database is at `scheduler.db` (SQLite).

**Backup:**
```bash
cp scheduler.db scheduler_backup.db
```

**View schedules manually:**
```bash
sqlite3 scheduler.db "SELECT id, name, status, run_count FROM schedules;"
```

**View execution history:**
```bash
sqlite3 scheduler.db "SELECT * FROM executions ORDER BY started_at DESC LIMIT 10;"
```

---

## FAQ

### Q: Does the scheduler run when the CLI is closed?

**A:** No. The scheduler only runs while the CLI is active. When you close the CLI, all schedules pause. They resume when you restart the CLI.

For 24/7 scheduling, keep the CLI running in a terminal session (use `screen` or `tmux`).

---

### Q: Can I schedule the same tool with different parameters?

**A:** Yes! Create multiple schedules:

```bash
/schedule create "every 30 minutes" backup_tool '{"source": "/data1"}'
/schedule create "every hour" backup_tool '{"source": "/data2"}'
```

---

### Q: What's the maximum number of schedules?

**A:** No hard limit. The system uses SQLite which can handle thousands of schedules efficiently.

---

### Q: Can schedules run in parallel?

**A:** Yes! The scheduler uses a thread pool (10 workers by default) so multiple schedules can run concurrently.

---

### Q: What happens if a schedule runs too long?

**A:**
- APScheduler has a "coalesce" setting that skips missed runs if a schedule is still executing
- Only one instance of each schedule runs at a time
- If execution takes longer than the interval, the next run waits

---

### Q: Can I export/import schedules?

**A:** The database is portable. To move schedules:

1. Copy `scheduler.db` to another machine
2. Start the CLI there
3. Schedules will load automatically

Or use the CLI to recreate schedules programmatically.

---

### Q: How do I see ALL schedules, even deleted ones?

**A:** Deleted schedules are permanently removed. There's no recycle bin.

**Tip:** Before deleting, export important schedules:
```bash
/schedule list > my_schedules.txt
```

---

### Q: Can I schedule based on file changes or events?

**A:** Not currently. The scheduler is time-based only (CRON).

For event-based triggering, you'd need to create a polling schedule:
```bash
/schedule create "every minute" file_watcher '{"path": "/watch/folder"}'
```

---

### Q: What's the shortest interval I can use?

**A:** Technically, every minute (`* * * * *`), but:
- Consider the tool's execution time
- Don't overload the system
- For sub-minute needs, use a tool with its own loop

---

### Q: How do I schedule something to run just once?

**A:** Schedules are recurring. For one-time execution:

1. Create the schedule
2. Let it run once
3. Delete it

Or just use `/tool run` directly.

---

## Support

**Issues or Questions?**

1. Check the [main README](SCHEDULER_README.md) for technical details
2. Review the [test suite](tests/) for usage examples
3. File an issue on GitHub
4. Check logs in the CLI output

**Happy Scheduling!** 🚀
