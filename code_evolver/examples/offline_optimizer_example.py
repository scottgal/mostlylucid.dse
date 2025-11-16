#!/usr/bin/env python3
"""
Offline Optimizer Example.

Demonstrates the complete Offline Optimizer feature including:
- PerfCatcher rolling buffer and threshold monitoring
- Priority-aware task scheduler
- Scheduled tasks with natural language descriptions
- Background task execution with workflow awareness
"""
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_perfcatcher_monitoring():
    """
    Example 1: PerfCatcher with Rolling Buffer.

    Shows how PerfCatcher monitors tool performance and dumps
    the rolling buffer to Loki when thresholds are exceeded.
    """
    print("\n" + "="*60)
    print("Example 1: PerfCatcher Rolling Buffer Monitoring")
    print("="*60 + "\n")

    from src.tool_interceptors import get_global_interceptor_chain

    # Get PerfCatcher from global chain
    chain = get_global_interceptor_chain()
    perfcatcher = None
    for interceptor in chain.interceptors:
        if interceptor.__class__.__name__ == 'PerfCatcherInterceptor':
            perfcatcher = interceptor
            break

    if not perfcatcher:
        print("PerfCatcher not available")
        return

    # Set a custom threshold for a specific tool
    perfcatcher.set_tool_threshold('example_tool', 0.15)  # 15% variance

    # Simulate tool execution with varying performance
    def slow_operation():
        time.sleep(0.1)  # Simulate work
        return "result"

    def fast_operation():
        time.sleep(0.01)  # Much faster
        return "result"

    # Execute several operations to build baseline
    print("Building performance baseline...")
    for i in range(15):
        chain.intercept_tool_call(
            'example_tool',
            slow_operation if i < 10 else fast_operation
        )

    # Get buffer stats
    stats = perfcatcher.get_buffer_stats()
    print(f"\nBuffer Statistics:")
    print(f"  Size: {stats['buffer_size']} requests")
    print(f"  Duration: {stats['duration_s']:.1f}s")
    print(f"  Oldest: {stats.get('oldest_entry', 'N/A')}")
    print(f"  Newest: {stats.get('newest_entry', 'N/A')}")

    # Get tool stats
    tool_stats = perfcatcher.get_tool_stats('example_tool')
    if tool_stats:
        print(f"\nTool Performance Statistics:")
        print(f"  Mean: {tool_stats['mean_ms']:.2f}ms")
        print(f"  Median: {tool_stats['median_ms']:.2f}ms")
        print(f"  StdDev: {tool_stats['stdev_ms']:.2f}ms")
        print(f"  Min/Max: {tool_stats['min_ms']:.2f}ms / {tool_stats['max_ms']:.2f}ms")

    print("\nNote: When variance exceeds threshold, entire buffer is dumped to Loki")
    print("Check Loki with job='code_evolver_offline_optimizer' for buffer dumps")


def example_2_priority_scheduler():
    """
    Example 2: Priority-Aware Task Scheduler.

    Shows how high-priority workflows take precedence over
    background tasks.
    """
    print("\n" + "="*60)
    print("Example 2: Priority-Aware Task Scheduler")
    print("="*60 + "\n")

    from src.task_scheduler import get_global_scheduler, TaskPriority

    scheduler = get_global_scheduler()

    # Define example tasks
    def high_priority_work():
        logger.info("Executing HIGH priority workflow task")
        time.sleep(0.5)
        return "workflow_result"

    def background_work():
        logger.info("Executing BACKGROUND priority task")
        time.sleep(0.2)
        return "background_result"

    # Submit tasks with different priorities
    print("Submitting tasks with different priorities...")

    # Mark a workflow as active
    scheduler.mark_workflow_active("test_workflow_123")

    # Submit high-priority workflow tasks
    high_task_1 = scheduler.submit(
        high_priority_work,
        priority=TaskPriority.HIGH,
        name="workflow_step_1"
    )

    high_task_2 = scheduler.submit(
        high_priority_work,
        priority=TaskPriority.HIGH,
        name="workflow_step_2"
    )

    # Submit background tasks
    bg_task_1 = scheduler.submit(
        background_work,
        priority=TaskPriority.BACKGROUND,
        name="background_cleanup"
    )

    bg_task_2 = scheduler.submit(
        background_work,
        priority=TaskPriority.BACKGROUND,
        name="background_optimization"
    )

    # Wait a bit for execution
    time.sleep(2)

    # Get stats
    stats = scheduler.get_stats()
    print(f"\nScheduler Statistics:")
    print(f"  Tasks Submitted: {stats['tasks_submitted']}")
    print(f"  Tasks Completed: {stats['tasks_completed']}")
    print(f"  High Priority Tasks: {stats['high_priority_tasks']}")
    print(f"  Background Tasks: {stats['background_tasks']}")
    print(f"  Active Tasks: {stats['active_tasks']}")
    print(f"  Queue Size: {stats['queue_size']}")

    # Mark workflow as inactive
    scheduler.mark_workflow_inactive("test_workflow_123")

    print("\nNote: Background tasks are throttled when workflows are active")


def example_3_scheduled_tasks():
    """
    Example 3: Scheduled Tasks with Natural Language.

    Shows how to create scheduled tasks using natural language
    descriptions that are converted to cron expressions.
    """
    print("\n" + "="*60)
    print("Example 3: Scheduled Tasks with Natural Language")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Define a task function
    def poll_for_updates():
        logger.info("Polling for updates...")
        # Simulate API call
        return {"status": "success", "updates": 3}

    def generate_report():
        logger.info("Generating weekly report...")
        # Simulate report generation
        return {"report_id": "weekly_001", "status": "complete"}

    # Create scheduled tasks with natural language
    print("Creating scheduled tasks...")

    # Example 1: Every 5 minutes (for demo, would normally be longer)
    task1_id = task_manager.create_task(
        name="update_poller",
        description="Poll external API for new updates",
        schedule="every 5 minutes",
        func=poll_for_updates,
        func_name="poll_for_updates",
        metadata={"api_endpoint": "https://api.example.com/updates"}
    )
    print(f"✓ Created task: update_poller (ID: {task1_id})")

    # Example 2: Weekly at specific time
    task2_id = task_manager.create_task(
        name="weekly_report",
        description="Generate and send weekly analytics report",
        schedule="every sunday at noon",
        func=generate_report,
        func_name="generate_report",
        metadata={"report_type": "analytics"}
    )
    print(f"✓ Created task: weekly_report (ID: {task2_id})")

    # Example 3: Using cron expression directly
    task3_id = task_manager.create_task(
        name="nightly_backup",
        description="Backup data to external storage",
        schedule="0 2 * * *",  # 2am daily
        func_name="backup_data",  # Would need to be registered
        metadata={"backup_location": "/backups"}
    )
    print(f"✓ Created task: nightly_backup (ID: {task3_id})")

    # List all tasks
    print(f"\nScheduled Tasks:")
    for task in task_manager.list_tasks(enabled_only=True):
        next_run = task.get_next_run_time()
        print(f"\n  {task.name}:")
        print(f"    Description: {task.description}")
        print(f"    Cron: {task.cron_expression}")
        print(f"    Next Run: {next_run.isoformat()}")
        print(f"    Run Count: {task.run_count}")
        print(f"    Errors: {task.error_count}")

    # Check for tasks due now (in demo, won't be any)
    due_tasks = task_manager.get_tasks_due_now()
    print(f"\nTasks Due Now: {len(due_tasks)}")

    print("\nNote: Background scheduler checks every 30s and executes due tasks")
    print("Tasks run with BACKGROUND priority to avoid interfering with workflows")


def example_4_complete_workflow():
    """
    Example 4: Complete Workflow with Priority Management.

    Demonstrates how workflows and background tasks interact.
    """
    print("\n" + "="*60)
    print("Example 4: Complete Workflow with Priority Management")
    print("="*60 + "\n")

    from src.task_scheduler import get_global_scheduler, TaskPriority
    from src.scheduled_tasks import get_global_task_manager

    scheduler = get_global_scheduler()
    task_manager = get_global_task_manager()

    # Simulate a user workflow
    def workflow_step(step_num):
        logger.info(f"Executing workflow step {step_num}")
        time.sleep(0.3)
        return f"step_{step_num}_complete"

    # Mark workflow as active
    workflow_id = "user_workflow_456"
    scheduler.mark_workflow_active(workflow_id)
    print(f"Started workflow: {workflow_id}")

    # Submit workflow steps as high-priority
    print("\nSubmitting high-priority workflow steps...")
    for i in range(3):
        scheduler.submit(
            lambda n=i: workflow_step(n+1),
            priority=TaskPriority.HIGH,
            name=f"workflow_step_{i+1}",
            metadata={"workflow_id": workflow_id}
        )

    # Background scheduler will see active workflow and pause background tasks
    print("\nBackground tasks will be paused while workflow is active...")
    time.sleep(1)

    # Complete workflow
    scheduler.mark_workflow_inactive(workflow_id)
    print(f"\nCompleted workflow: {workflow_id}")

    # Now background tasks can resume
    print("Background tasks can now resume execution")

    # Get final stats
    stats = scheduler.get_stats()
    print(f"\nFinal Statistics:")
    print(f"  Total Tasks: {stats['tasks_submitted']}")
    print(f"  Completed: {stats['tasks_completed']}")
    print(f"  Active: {stats['active_tasks']}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("OFFLINE OPTIMIZER FEATURE EXAMPLES")
    print("="*60)

    try:
        # Run examples
        example_1_perfcatcher_monitoring()
        time.sleep(1)

        example_2_priority_scheduler()
        time.sleep(1)

        example_3_scheduled_tasks()
        time.sleep(1)

        example_4_complete_workflow()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
