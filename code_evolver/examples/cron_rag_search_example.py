#!/usr/bin/env python3
"""
Cron RAG Search Example.

Demonstrates how the cron deconstructor creates rich embeddings for
semantic search of scheduled tasks.
"""
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_cron_deconstruction():
    """
    Example 1: Cron Deconstruction.

    Shows how a cron expression is deconstructed into rich metadata.
    """
    print("\n" + "="*60)
    print("Example 1: Cron Expression Deconstruction")
    print("="*60 + "\n")

    from tools.executable.cron_deconstructor import deconstruct_cron

    # Example 1: Weekly report
    cron1 = deconstruct_cron(
        cron_expression="0 9 * * MON",
        tool_name="bugcatcher_logs",
        description="Generate weekly bugcatcher report"
    )

    print("Cron: 0 9 * * MON")
    print(f"Description: {cron1['description']}")
    print(f"Group: {cron1['group']}")
    print(f"Frequency: {cron1['frequency']}")
    print(f"Time of Day: {cron1['time_of_day']}")
    print(f"Day Names: {cron1['day_names']}")
    print(f"Semantic Tags: {cron1['semantic_tags']}")
    print(f"Next Runs: {cron1['next_runs'][:2]}")

    print("\n" + "-"*60 + "\n")

    # Example 2: Frequent polling
    cron2 = deconstruct_cron(
        cron_expression="*/5 * * * *",
        tool_name="poll_api_events",
        description="Poll API for new events"
    )

    print("Cron: */5 * * * *")
    print(f"Description: {cron2['description']}")
    print(f"Group: {cron2['group']}")
    print(f"Frequency: {cron2['frequency']}")
    print(f"Semantic Tags: {cron2['semantic_tags']}")

    print("\n" + "-"*60 + "\n")

    # Example 3: Nightly backup
    cron3 = deconstruct_cron(
        cron_expression="0 2 * * *",
        tool_name="backup_database",
        description="Backup production database to S3"
    )

    print("Cron: 0 2 * * *")
    print(f"Description: {cron3['description']}")
    print(f"Group: {cron3['group']}")
    print(f"Frequency: {cron3['frequency']}")
    print(f"Time of Day: {cron3['time_of_day']}")
    print(f"Semantic Tags: {cron3['semantic_tags']}")


def example_2_semantic_rag_storage():
    """
    Example 2: Semantic RAG Storage.

    Shows how tasks are stored in RAG with rich embeddings.
    """
    print("\n" + "="*60)
    print("Example 2: Semantic RAG Storage")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Create some example tasks
    def weekly_report():
        logger.info("Generating weekly report...")
        return {"status": "success"}

    def nightly_backup():
        logger.info("Running backup...")
        return {"status": "success"}

    def poll_events():
        logger.info("Polling events...")
        return {"count": 5}

    # Create tasks with different schedules
    print("Creating scheduled tasks...")

    task1 = task_manager.create_task(
        name="weekly_bugcatcher_report",
        description="Generate and email weekly bugcatcher analysis",
        schedule="every monday at 9am",
        func=weekly_report,
        func_name="weekly_report",
        metadata={"report_type": "bugcatcher"}
    )
    print(f"✓ Created: weekly_bugcatcher_report")

    task2 = task_manager.create_task(
        name="nightly_database_backup",
        description="Backup production database to S3",
        schedule="daily at 2am",
        func=nightly_backup,
        func_name="nightly_backup",
        metadata={"backup_target": "s3"}
    )
    print(f"✓ Created: nightly_database_backup")

    task3 = task_manager.create_task(
        name="api_event_poller",
        description="Poll external API for new events",
        schedule="every 5 minutes",
        func=poll_events,
        func_name="poll_events"
    )
    print(f"✓ Created: api_event_poller")

    task4 = task_manager.create_task(
        name="weekly_analytics_report",
        description="Generate weekly analytics summary",
        schedule="every sunday at noon",
        func=weekly_report,
        func_name="weekly_report",
        metadata={"report_type": "analytics"}
    )
    print(f"✓ Created: weekly_analytics_report")

    print("\nAll tasks stored in RAG with rich semantic embeddings!")


def example_3_semantic_search():
    """
    Example 3: Semantic Search.

    Shows how to search for tasks using natural language queries.
    """
    print("\n" + "="*60)
    print("Example 3: Semantic Task Search")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Search examples
    print("Query: 'weekly reports'")
    results = task_manager.search_tasks("weekly reports")
    print(f"Found {len(results)} tasks:")
    for task in results:
        print(f"  - {task.name}: {task.description}")

    print("\n" + "-"*60 + "\n")

    print("Query: 'backup jobs'")
    results = task_manager.search_tasks("backup jobs")
    print(f"Found {len(results)} tasks:")
    for task in results:
        print(f"  - {task.name}: {task.description}")

    print("\n" + "-"*60 + "\n")

    print("Query: 'morning tasks'")
    results = task_manager.search_tasks("morning tasks", {"time_of_day": "morning"})
    print(f"Found {len(results)} tasks:")
    for task in results:
        print(f"  - {task.name}: {task.description}")

    print("\n" + "-"*60 + "\n")

    print("Query: 'monitoring' (filtered by frequency)")
    results = task_manager.search_tasks(
        "monitoring polling",
        {"frequency": "every_5_minutes"}
    )
    print(f"Found {len(results)} tasks:")
    for task in results:
        print(f"  - {task.name}: {task.description}")


def example_4_time_window_search():
    """
    Example 4: Time Window Search with RAG Hints.

    Shows how RAG is used to optimize finding tasks due in a time window.
    """
    print("\n" + "="*60)
    print("Example 4: Time Window Search with RAG Hints")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Get tasks due in next 5 minutes
    print("Finding tasks due in next 5 minutes...")
    print("(Using RAG semantic search to narrow candidates before cron checking)")

    due_tasks = task_manager.get_tasks_due_now(
        window_minutes=5,
        use_rag_hint=True  # Use RAG to find candidates first
    )

    print(f"\nFound {len(due_tasks)} tasks due:")
    for task in due_tasks:
        next_run = task.get_next_run_time()
        print(f"\n  {task.name}:")
        print(f"    Cron: {task.cron_expression}")
        print(f"    Next run: {next_run}")

    print("\n" + "-"*60 + "\n")

    # Show how RAG hints work
    print("How RAG hints work:")
    print("1. Determine current time of day (morning, afternoon, evening, night)")
    print("2. Search RAG for tasks with matching time_of_day tag")
    print("3. Also include frequently-running tasks (every N minutes)")
    print("4. Check exact cron times for candidates")
    print("5. Return tasks that are actually due")
    print("\nThis is much faster than checking ALL tasks when you have many scheduled jobs!")


def example_5_grouping_and_organization():
    """
    Example 5: Task Grouping and Organization.

    Shows how tasks are automatically grouped by category.
    """
    print("\n" + "="*60)
    print("Example 5: Task Grouping and Organization")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager
    from collections import defaultdict

    task_manager = get_global_task_manager()

    # Group tasks by category
    tasks_by_group = defaultdict(list)

    for task in task_manager.list_tasks():
        # Get group from metadata (set during RAG storage)
        group = task.metadata.get('group', 'general')
        tasks_by_group[group].append(task)

    # Display grouped tasks
    for group, tasks in sorted(tasks_by_group.items()):
        print(f"\n{group.upper()} ({len(tasks)} tasks):")
        for task in tasks:
            print(f"  - {task.name}")
            print(f"    Schedule: {task.cron_expression}")
            print(f"    Description: {task.description}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CRON RAG SEARCH EXAMPLES")
    print("="*60)

    try:
        example_1_cron_deconstruction()

        example_2_semantic_rag_storage()

        example_3_semantic_search()

        example_4_time_window_search()

        example_5_grouping_and_organization()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")

        print("\nKey Benefits of Cron Deconstruction + RAG:")
        print("✓ Natural language search: 'find weekly reports'")
        print("✓ Automatic grouping: reports, backups, monitoring, etc.")
        print("✓ Time-aware search: 'morning tasks', 'nightly jobs'")
        print("✓ Fast lookups: RAG hints reduce candidates to check")
        print("✓ Rich metadata: frequency, time_of_day, day_names, tags")
        print("✓ Semantic similarity: finds related tasks automatically")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
