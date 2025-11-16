# Scheduler Quick Start Examples

**Real-world examples to get you started fast**

## Table of Contents

1. [5-Minute Quick Start](#5-minute-quick-start)
2. [Common Patterns](#common-patterns)
3. [Copy-Paste Examples](#copy-paste-examples)
4. [Troubleshooting Recipes](#troubleshooting-recipes)

---

## 5-Minute Quick Start

### Step 1: Verify Installation

```bash
cd code_evolver
python chat_cli.py
```

Look for: `OK Scheduler service started`

### Step 2: Create Your First Schedule

```bash
/schedule create "every 5 minutes" basic_calculator '{"operation": "add", "a": 5, "b": 3"}'
```

You should see:
```
CRON expression: */5 * * * *
Schedule created successfully!
  ID: schedule_abc123def
  Name: basic_calculator - every 5 minutes
  CRON: */5 * * * *
  Next run: 2025-01-16T14:05:00
```

### Step 3: Verify It's Running

```bash
/schedule list
```

### Step 4: Trigger It Manually

```bash
/schedule trigger schedule_abc123def
```

You should see:
```
Schedule executed successfully!
  Execution ID: 1
  Result: {"result": 8, "operation": "add"}
```

### Step 5: View History

```bash
/schedule history schedule_abc123def
```

**Congratulations!** You've created and run your first scheduled task.

---

## Common Patterns

### Pattern 1: Hourly Data Backup

**Use case:** Back up important data every hour

```bash
/schedule create "every hour" backup_tool '{
  "source": "/data/important",
  "destination": "/backups",
  "compression": true
}'
```

**Monitor:**
```bash
# Check if it's running
/schedule list active

# See backup history
/schedule history <schedule_id>
```

---

### Pattern 2: Daily Report at 9am

**Use case:** Generate and email a report every morning

```bash
/schedule create "every day at 9am" report_generator '{
  "report_type": "daily_summary",
  "format": "pdf",
  "recipients": ["manager@company.com", "team@company.com"],
  "include_charts": true
}'
```

**Test it first:**
```bash
# Run it manually to verify it works
/schedule trigger <schedule_id>

# Check the output
/schedule history <schedule_id>
```

---

### Pattern 3: System Health Check Every 15 Minutes

**Use case:** Monitor system health and alert on issues

```bash
/schedule create "every 15 minutes" health_check '{
  "services": ["web_server", "database", "redis", "email_service"],
  "alert_email": "ops@company.com",
  "alert_threshold": 2
}'
```

**Verify it's working:**
```bash
# Let it run for an hour, then check
/schedule history <schedule_id>

# Should see 4 successful runs (60 minutes / 15 minutes = 4)
```

---

### Pattern 4: Weekly Cleanup Every Monday

**Use case:** Clean up old files every Monday at midnight

```bash
/schedule create "every Monday at midnight" cleanup_tool '{
  "directories": ["/tmp", "/cache", "/logs"],
  "older_than_days": 30,
  "dry_run": false
}'
```

**Safety tip:** Test with dry_run first!
```bash
# Create with dry_run=true
/schedule create "every Monday at midnight" cleanup_tool '{
  "directories": ["/tmp"],
  "older_than_days": 30,
  "dry_run": true
}'

# Trigger manually
/schedule trigger <schedule_id>

# Check what would be deleted
/schedule history <schedule_id>

# If OK, update to dry_run=false and resume
```

---

### Pattern 5: Frequent Monitoring with Pause/Resume

**Use case:** Monitor during business hours only

```bash
# Create schedule
/schedule create "every 10 minutes" monitor_tool '{
  "check_types": ["uptime", "response_time", "error_rate"]
}'

# At end of day, pause it
/schedule pause <schedule_id>

# Next morning, resume it
/schedule resume <schedule_id>
```

**Automation idea:** Create start/end of day schedules:
```bash
# Start monitoring at 8am
/schedule create "every day at 8am" start_monitoring '{}'

# Stop monitoring at 6pm
/schedule create "every day at 6pm" stop_monitoring '{}'
```

---

## Copy-Paste Examples

### Example 1: Database Backup (Hourly)

```bash
/schedule create "every hour" database_backup '{
  "database": "production",
  "output_dir": "/backups/db",
  "retention_days": 7,
  "notify_email": "dba@company.com"
}'
```

---

### Example 2: Log Rotation (Daily at 2am)

```bash
/schedule create "every day at 2am" log_rotator '{
  "log_dirs": ["/var/log/app", "/var/log/nginx"],
  "max_size_mb": 100,
  "max_age_days": 30,
  "compress": true
}'
```

---

### Example 3: API Health Check (Every 5 Minutes)

```bash
/schedule create "every 5 minutes" api_health_check '{
  "endpoints": [
    "https://api.example.com/health",
    "https://api.example.com/status"
  ],
  "timeout_seconds": 10,
  "alert_on_failure": true,
  "alert_webhook": "https://slack.com/webhook/..."
}'
```

---

### Example 4: File Sync (Every 30 Minutes)

```bash
/schedule create "every 30 minutes" file_sync '{
  "source": {
    "type": "local",
    "path": "/data/incoming"
  },
  "destination": {
    "type": "s3",
    "bucket": "my-bucket",
    "prefix": "uploads/"
  },
  "delete_source_after_upload": false,
  "file_pattern": "*.json"
}'
```

---

### Example 5: Weekly Report (Monday 9am)

```bash
/schedule create "every Monday at 9am" weekly_report '{
  "report_name": "Weekly Analytics",
  "data_sources": ["database", "google_analytics", "stripe"],
  "format": "pdf",
  "email_to": [
    "ceo@company.com",
    "cto@company.com",
    "team@company.com"
  ],
  "include_graphs": true,
  "date_range": "last_7_days"
}'
```

---

### Example 6: Data Processing Pipeline (Every 2 Hours)

```bash
/schedule create "every 2 hours" data_processor '{
  "input_source": "s3://raw-data-bucket/incoming",
  "output_destination": "s3://processed-data-bucket/clean",
  "processing_steps": [
    "validate",
    "clean",
    "transform",
    "aggregate"
  ],
  "error_handling": "log_and_continue",
  "notification_email": "data-team@company.com"
}'
```

---

### Example 7: Certificate Expiry Check (Daily)

```bash
/schedule create "every day at noon" cert_checker '{
  "domains": [
    "example.com",
    "api.example.com",
    "cdn.example.com"
  ],
  "warn_days_before_expiry": 30,
  "critical_days_before_expiry": 7,
  "alert_email": "security@company.com"
}'
```

---

### Example 8: Cache Warming (Every 6 Hours)

```bash
/schedule create "every 6 hours" cache_warmer '{
  "cache_type": "redis",
  "endpoints_to_warm": [
    "/api/popular-products",
    "/api/categories",
    "/api/homepage-data"
  ],
  "concurrent_requests": 5
}'
```

---

### Example 9: Metrics Collection (Every Minute)

```bash
/schedule create "every minute" metrics_collector '{
  "metrics": [
    "cpu_usage",
    "memory_usage",
    "disk_io",
    "network_io",
    "active_connections"
  ],
  "write_to": "influxdb",
  "tags": {
    "environment": "production",
    "server": "web-01"
  }
}'
```

---

### Example 10: Image Processing Queue (Every 15 Minutes)

```bash
/schedule create "every 15 minutes" image_processor '{
  "queue_source": "sqs://image-processing-queue",
  "max_batch_size": 50,
  "operations": [
    "resize",
    "optimize",
    "generate_thumbnails"
  ],
  "output_format": "webp",
  "s3_destination": "processed-images-bucket"
}'
```

---

## Troubleshooting Recipes

### Recipe 1: Schedule Created But Not Running

**Symptoms:**
- Schedule shows in `/schedule list`
- Status is "active"
- But executions never happen

**Debug steps:**

```bash
# 1. Check the next run time
/schedule list
# Look at "Next Run" column - is it in the future?

# 2. Trigger manually to test
/schedule trigger <schedule_id>
# Does it work?

# 3. Check execution history
/schedule history <schedule_id>
# Any errors?

# 4. Verify CRON expression
# If "Next Run" seems wrong, the CRON might be incorrect
```

**Fix:**
```bash
# Delete and recreate with corrected CRON
/schedule delete <schedule_id>
/schedule create "corrected description" tool_name '{"params": "values"}'
```

---

### Recipe 2: Tool Works Manually But Fails in Schedule

**Symptoms:**
- `/tool run tool_name params` works
- But `/schedule trigger <id>` fails

**Debug steps:**

```bash
# 1. Check the exact error
/schedule history <schedule_id>
# Note the error message

# 2. Verify inputs are identical
/schedule list
# Compare the tool_inputs with what works manually

# 3. Check for environment issues
# Does the tool need files/resources that exist when you run manually
# but not when scheduler runs?
```

**Common causes:**
- Missing file paths (use absolute paths, not relative)
- Environment variables not set
- Permission issues
- Tool expects interactive input

---

### Recipe 3: Too Many Failed Executions

**Symptoms:**
- Schedule shows "error" status
- History shows repeated failures

**Fix:**

```bash
# 1. Pause the schedule immediately
/schedule pause <schedule_id>

# 2. Investigate the error
/schedule history <schedule_id>

# 3. Fix the underlying issue
# - Update tool
# - Fix permissions
# - Update parameters

# 4. Test manually
/schedule trigger <schedule_id>

# 5. When fixed, resume
/schedule resume <schedule_id>
```

---

### Recipe 4: Delete All Schedules (Nuclear Option)

**Warning:** This deletes EVERYTHING!

```bash
# List all schedules and save IDs
/schedule list > schedules_backup.txt

# Delete each one
/schedule delete schedule_id_1
/schedule delete schedule_id_2
# ...

# Or delete the database file
# (Exit CLI first!)
rm scheduler.db
# Restart CLI - fresh database created
```

---

### Recipe 5: Migrate Schedules to Another System

**Export schedules:**

```bash
# 1. List all schedules
/schedule list > schedules.txt

# 2. For each schedule, get full details
/schedule get <schedule_id>

# 3. Save the command to recreate:
# /schedule create "description" tool '{"params": "values"}'

# 4. Copy scheduler.db file
cp scheduler.db scheduler_backup.db

# 5. Move scheduler.db to new system
# 6. Start CLI on new system - schedules auto-load
```

---

### Recipe 6: Monitor Schedule Health

**Create a monitoring schedule that checks other schedules:**

```bash
# 1. Create a monitoring tool that:
# - Lists all schedules
# - Checks their last execution
# - Alerts if any haven't run in expected time

# 2. Schedule it:
/schedule create "every hour" schedule_monitor '{
  "alert_if_not_run_hours": 2,
  "alert_email": "ops@company.com"
}'
```

---

### Recipe 7: Rate Limiting (Don't Overload)

**Problem:** Running a schedule too frequently overloads system

**Solutions:**

```bash
# Option 1: Increase interval
/schedule delete <old_schedule_id>
/schedule create "every 10 minutes" tool '{}' # instead of every minute

# Option 2: Pause during peak hours
# Pause at 8am (peak starts)
/schedule pause <schedule_id>

# Resume at 6pm (peak ends)
/schedule resume <schedule_id>

# Option 3: Create separate schedules for peak/off-peak
/schedule create "every 30 minutes" tool '{}' # Peak hours version
/schedule create "every 5 minutes" tool_2 '{}' # Off-peak version
# Manually enable/disable as needed
```

---

## Best Practices

### 1. Start with Manual Testing

```bash
# DON'T create schedules immediately
# DO test the tool first:
/tool run my_tool '{"param": "value"}'

# THEN create the schedule
/schedule create "every hour" my_tool '{"param": "value"}'
```

---

### 2. Use Descriptive Names

```bash
# BAD
/schedule create "every hour" tool '{}'

# GOOD
/schedule create "every hour" hourly_backup_production_db '{
  "database": "production",
  "backup_location": "/backups"
}'
```

---

### 3. Monitor Execution History

```bash
# Set a reminder to check weekly
/schedule history <important_schedule_id>

# Look for patterns:
# - All success? Great!
# - Occasional failures? Investigate
# - All failures? Pause and fix
```

---

### 4. Document Your Schedules

Keep a file like `schedules_inventory.md`:

```markdown
# Production Schedules

## Database Backups
- Schedule ID: schedule_abc123
- Frequency: Every 2 hours
- Tool: database_backup
- Purpose: Backup production DB to S3
- Owner: DBA team

## Log Rotation
- Schedule ID: schedule_def456
- Frequency: Daily at 2am
- Tool: log_rotator
- Purpose: Rotate and compress logs
- Owner: DevOps team
```

---

### 5. Use Version Control for Inputs

Store tool inputs in files:

```bash
# backup_config.json
{
  "database": "production",
  "destination": "/backups",
  "retention_days": 7
}

# Then reference it:
/schedule create "every hour" backup_tool "$(cat backup_config.json)"
```

---

## Next Steps

1. **Read the full guide:** [CLAUDE_DESKTOP_SCHEDULER_GUIDE.md](CLAUDE_DESKTOP_SCHEDULER_GUIDE.md)
2. **Understand the internals:** [SCHEDULER_README.md](SCHEDULER_README.md)
3. **Run the tests:** See the tests in `code_evolver/tests/`
4. **Experiment:** Create test schedules and learn by doing

**Happy Scheduling!** 🎉
