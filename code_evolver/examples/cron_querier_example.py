#!/usr/bin/env python3
"""
Cron Querier Example.

Demonstrates natural language querying of scheduled tasks using the
cron_querier tool combined with RAG semantic search.
"""
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_example_tasks():
    """Create some example tasks for demonstration."""
    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Sample task functions
    def weekly_report():
        return {"status": "success", "report": "weekly_data.pdf"}

    def nightly_backup():
        return {"status": "success", "backup_size_mb": 1024}

    def poll_events():
        return {"events": 5}

    def cleanup_logs():
        return {"deleted_files": 127}

    # Create diverse tasks
    tasks = [
        ("weekly_bugcatcher_report", "Generate weekly bugcatcher analysis",
         "every monday at 9am", weekly_report, "reports"),

        ("weekly_analytics_report", "Generate weekly analytics summary",
         "every sunday at noon", weekly_report, "reports"),

        ("nightly_database_backup", "Backup production database to S3",
         "daily at 2am", nightly_backup, "backups"),

        ("nightly_file_backup", "Backup file system to external storage",
         "daily at 3am", nightly_backup, "backups"),

        ("api_event_poller", "Poll external API for new events",
         "every 5 minutes", poll_events, "monitoring"),

        ("health_check_monitor", "Check service health status",
         "every 10 minutes", poll_events, "monitoring"),

        ("cleanup_old_logs", "Delete logs older than 30 days",
         "daily at 4am", cleanup_logs, "maintenance"),

        ("cleanup_temp_files", "Remove temporary files",
         "every sunday at midnight", cleanup_logs, "maintenance"),
    ]

    created = []
    for name, desc, schedule, func, group in tasks:
        task_id = task_manager.create_task(
            name=name,
            description=desc,
            schedule=schedule,
            func=func,
            func_name=func.__name__,
            metadata={"group": group}
        )
        created.append(task_id)
        logger.info(f"Created: {name}")

    return created


def example_1_simple_queries():
    """
    Example 1: Simple Natural Language Queries.

    Shows pattern matching for common query types.
    """
    print("\n" + "="*60)
    print("Example 1: Simple Natural Language Queries")
    print("="*60 + "\n")

    from tools.executable.cron_querier import query_scheduled_tasks

    queries = [
        "backup jobs running tonight",
        "weekly reports",
        "monitoring tasks that run every 5 minutes",
        "maintenance jobs",
        "tasks running tomorrow morning"
    ]

    for query in queries:
        print(f"Query: '{query}'")
        parsed = query_scheduled_tasks(query)

        print(f"  Search query: {parsed['search_query']}")
        print(f"  Filters: {parsed['filters']}")
        if parsed.get('time_window'):
            tw = parsed['time_window']
            print(f"  Time window: {tw['window_minutes']} minutes")
        print(f"  Parsed by: {parsed['parsed_method']}")
        print()


def example_2_time_window_queries():
    """
    Example 2: Time Window Queries.

    Shows how time windows are parsed from natural language.
    """
    print("\n" + "="*60)
    print("Example 2: Time Window Queries")
    print("="*60 + "\n")

    from tools.executable.cron_querier import query_scheduled_tasks

    # Use a fixed time for consistent examples
    current_time = "2025-01-16T14:30:00"  # Thursday 2:30pm

    queries = [
        "tasks running in the next 3 hours",
        "tasks running tonight",
        "tasks running tomorrow",
        "tasks running this weekend"
    ]

    for query in queries:
        print(f"Query: '{query}'")
        print(f"Current time: {current_time}")

        parsed = query_scheduled_tasks(query, current_time=current_time)

        if parsed.get('time_window'):
            tw = parsed['time_window']
            print(f"  Start: {tw['start']}")
            print(f"  End: {tw['end']}")
            print(f"  Duration: {tw['window_minutes']} minutes")
        else:
            print("  No time window specified")
        print()


def example_3_combined_queries():
    """
    Example 3: Combined Filter Queries.

    Shows queries with multiple filters combined.
    """
    print("\n" + "="*60)
    print("Example 3: Combined Filter Queries")
    print("="*60 + "\n")

    from tools.executable.cron_querier import query_scheduled_tasks

    queries = [
        "weekly reports on monday morning",
        "backup jobs running at night",
        "monitoring tasks that run every 5 minutes",
        "maintenance jobs this weekend"
    ]

    for query in queries:
        print(f"Query: '{query}'")
        parsed = query_scheduled_tasks(query)

        filters = parsed.get('filters', {})
        print(f"  Filters:")
        for key, value in filters.items():
            print(f"    {key}: {value}")

        if parsed.get('day_names'):
            print(f"  Day names: {parsed['day_names']}")

        print()


def example_4_full_integration():
    """
    Example 4: Full Integration with Task Manager.

    Shows how to use natural language queries with the task manager.
    """
    print("\n" + "="*60)
    print("Example 4: Full Integration with Task Manager")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Create example tasks
    print("Setting up example tasks...")
    setup_example_tasks()
    print()

    # Example queries
    queries = [
        "all backup jobs",
        "weekly reports",
        "tasks running every 5 minutes",
        "maintenance jobs"
    ]

    for query in queries:
        print(f"Query: '{query}'")

        # Use the high-level natural language interface
        result = task_manager.query_tasks_natural_language(query)

        print(f"  Found {result['result_count']} tasks:")
        for task in result['combined_results']:
            print(f"    - {task.name}")
            print(f"      Schedule: {task.cron_expression}")
            print(f"      Description: {task.description}")
        print()


def example_5_time_window_with_filters():
    """
    Example 5: Time Windows Combined with Filters.

    Shows the most powerful queries combining time and filters.
    """
    print("\n" + "="*60)
    print("Example 5: Time Windows + Filters")
    print("="*60 + "\n")

    from src.scheduled_tasks import get_global_task_manager

    task_manager = get_global_task_manager()

    # Example: "backup jobs running tonight"
    query = "backup jobs running tonight"
    print(f"Query: '{query}'")

    result = task_manager.query_tasks_natural_language(query)

    print(f"\nParsed query:")
    print(f"  Search terms: {result['parsed']['search_query']}")
    print(f"  Filters: {result['parsed']['filters']}")
    print(f"  Time window: {result['parsed']['time_window']['window_minutes']} minutes")

    print(f"\nMatched tasks (by filters): {len(result['matched_tasks'])}")
    for task in result['matched_tasks']:
        print(f"  - {task.name}")

    print(f"\nDue tasks (by time window): {len(result['due_tasks'])}")
    for task in result['due_tasks']:
        next_run = task.get_next_run_time()
        print(f"  - {task.name} (next: {next_run.strftime('%H:%M')})")

    print(f"\nCombined results (both filters AND time): {len(result['combined_results'])}")
    for task in result['combined_results']:
        print(f"  - {task.name}")


def example_6_llm_enhanced_parsing():
    """
    Example 6: LLM-Enhanced Query Parsing.

    Shows complex queries that benefit from LLM parsing.
    """
    print("\n" + "="*60)
    print("Example 6: LLM-Enhanced Query Parsing")
    print("="*60 + "\n")

    from tools.executable.cron_querier import query_scheduled_tasks

    # These queries might work better with LLM parsing
    complex_queries = [
        "show me all the things that run between now and dinner time",
        "what backup operations happen overnight",
        "which reports are generated at the start of the week",
        "find monitoring tasks that check things frequently"
    ]

    print("Note: These complex queries benefit from LLM parsing")
    print("      (requires Ollama client available)\n")

    for query in complex_queries:
        print(f"Query: '{query}'")
        parsed = query_scheduled_tasks(query)

        print(f"  Method: {parsed['parsed_method']}")
        print(f"  Search: {parsed['search_query']}")
        print(f"  Filters: {parsed.get('filters', {})}")
        print()


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CRON QUERIER EXAMPLES")
    print("="*60)

    try:
        example_1_simple_queries()
        example_2_time_window_queries()
        example_3_combined_queries()
        example_4_full_integration()
        example_5_time_window_with_filters()
        example_6_llm_enhanced_parsing()

        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60 + "\n")

        print("\nKey Features Demonstrated:")
        print("✓ Natural language query parsing")
        print("✓ Time window extraction (next N hours, tonight, tomorrow, etc.)")
        print("✓ Filter extraction (group, frequency, time_of_day)")
        print("✓ Combined queries (filters + time windows)")
        print("✓ Integration with task manager")
        print("✓ Both simple pattern matching and LLM-enhanced parsing")
        print("\nExample Queries That Work:")
        print("• 'backup jobs running tonight'")
        print("• 'all tasks in the next 3 hours'")
        print("• 'weekly reports on monday morning'")
        print("• 'monitoring tasks that run every 5 minutes'")
        print("• 'maintenance jobs this weekend'")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
