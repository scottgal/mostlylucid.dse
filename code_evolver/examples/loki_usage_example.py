#!/usr/bin/env python3
"""
Example: Using the Loki tool for log aggregation.

This example demonstrates:
1. Creating a Loki manager instance (global or tool-scoped)
2. Starting Loki automatically
3. Pushing logs with custom labels
4. Querying logs by labels and time range
5. Managing multiple named instances
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import ConfigManager, create_loki_manager


def example_global_scope():
    """
    Example 1: Using Loki in global scope.

    Global scope means a single instance shared across the application.
    """
    print("=" * 70)
    print("EXAMPLE 1: Global Scope Loki")
    print("=" * 70)

    # Load configuration
    config = ConfigManager()

    # Create global Loki instance
    loki = create_loki_manager(config, scope='global')

    if not loki:
        print("❌ Loki is disabled in config")
        return

    print(f"✓ Created global Loki manager")
    print(f"  URL: {loki.url}")
    print(f"  Data path: {loki.data_path}")
    print(f"  Scope: {loki.scope}")
    print()

    # Start Loki (will use existing instance if already running)
    print("Starting Loki instance...")
    result = loki.start()
    print(f"  Status: {result['status']}")
    print(f"  Message: {result['message']}")
    print()

    # Check status
    print("Checking Loki status...")
    status = loki.status()
    print(f"  Healthy: {status['instance_info']['healthy']}")
    print(f"  Stats: {status['stats']}")
    print()

    # Push some logs
    print("Pushing logs...")
    logs = [
        {
            'timestamp': datetime.now(),
            'message': 'Application started'
        },
        {
            'timestamp': datetime.now(),
            'message': 'Processing user request'
        },
        {
            'timestamp': datetime.now(),
            'message': 'Request completed successfully'
        }
    ]

    labels = {
        'level': 'info',
        'component': 'example',
        'scope': 'global'
    }

    push_result = loki.push(logs, labels)
    print(f"  Status: {push_result['status']}")
    print(f"  Message: {push_result['message']}")
    print()

    # Flush to ensure logs are sent
    print("Flushing logs...")
    flush_result = loki.flush()
    print(f"  Status: {flush_result['status']}")
    print(f"  Message: {flush_result['message']}")
    print()

    # Wait a bit for logs to be indexed
    time.sleep(2)

    # Query logs
    print("Querying logs...")
    query = '{application="code_evolver",component="example"}'
    query_result = loki.query(query, start_time='5m', limit=10)
    print(f"  Status: {query_result['status']}")
    print(f"  Found {len(query_result['logs'])} logs")

    if query_result['logs']:
        print("\n  Recent logs:")
        for log in query_result['logs'][:5]:
            ts = datetime.fromtimestamp(log['timestamp'] / 1e9)
            print(f"    [{ts.strftime('%H:%M:%S')}] {log['message']}")
    print()


def example_tool_scope():
    """
    Example 2: Using Loki in tool scope.

    Tool scope means instances created on-demand for specific tasks.
    """
    print("=" * 70)
    print("EXAMPLE 2: Tool Scope Loki")
    print("=" * 70)

    config = ConfigManager()

    # Create tool-scoped instance
    loki_tool = create_loki_manager(config, scope='tool')

    if not loki_tool:
        print("❌ Loki is disabled in config")
        return

    print(f"✓ Created tool-scoped Loki manager")
    print(f"  Scope: {loki_tool.scope}")
    print()

    # Push logs specific to this tool
    print("Pushing tool-specific logs...")
    logs = [
        {
            'message': 'Tool started processing'
        },
        {
            'message': 'Tool generated output'
        },
        {
            'message': 'Tool completed successfully'
        }
    ]

    labels = {
        'level': 'debug',
        'tool_name': 'example_tool',
        'scope': 'tool'
    }

    push_result = loki_tool.push(logs, labels)
    print(f"  Status: {push_result['status']}")
    loki_tool.flush()
    print()


def example_named_instances():
    """
    Example 3: Using named Loki instances.

    Named instances allow multiple isolated log streams.
    """
    print("=" * 70)
    print("EXAMPLE 3: Named Loki Instances")
    print("=" * 70)

    config = ConfigManager()

    # Create different named instances
    loki_api = create_loki_manager(config, scope='api_logs')
    loki_worker = create_loki_manager(config, scope='worker_logs')

    if not loki_api or not loki_worker:
        print("❌ Loki is disabled in config")
        return

    print(f"✓ Created named instances:")
    print(f"  - {loki_api.scope}")
    print(f"  - {loki_worker.scope}")
    print()

    # Push logs to API instance
    print("Pushing API logs...")
    loki_api.push(
        logs=[{'message': 'API request received'}],
        labels={'component': 'api', 'endpoint': '/users'}
    )
    loki_api.flush()

    # Push logs to worker instance
    print("Pushing worker logs...")
    loki_worker.push(
        logs=[{'message': 'Background job started'}],
        labels={'component': 'worker', 'job_type': 'data_sync'}
    )
    loki_worker.flush()
    print()


def example_log_querying():
    """
    Example 4: Advanced log querying.

    Demonstrates different query patterns and time ranges.
    """
    print("=" * 70)
    print("EXAMPLE 4: Advanced Log Querying")
    print("=" * 70)

    config = ConfigManager()
    loki = create_loki_manager(config, scope='global')

    if not loki:
        print("❌ Loki is disabled in config")
        return

    # Ensure Loki is running
    loki.start()

    # Push test logs with different levels
    print("Pushing test logs with different levels...")
    for level in ['debug', 'info', 'warning', 'error']:
        loki.push(
            logs=[{
                'message': f'Test message at {level} level',
                'timestamp': datetime.now()
            }],
            labels={'level': level, 'test': 'query_example'}
        )
    loki.flush()
    time.sleep(2)
    print()

    # Query 1: All logs from test
    print("Query 1: All test logs")
    result = loki.query('{test="query_example"}', start_time='5m', limit=100)
    print(f"  Found {len(result['logs'])} logs")
    print()

    # Query 2: Only error logs
    print("Query 2: Only error logs")
    result = loki.query('{test="query_example",level="error"}', start_time='5m')
    print(f"  Found {len(result['logs'])} error logs")
    print()

    # Query 3: Tail recent logs
    print("Query 3: Tail recent logs")
    result = loki.tail(query='{application="code_evolver"}', limit=10)
    print(f"  Found {len(result['logs'])} recent logs")
    if result['logs']:
        print("\n  Most recent:")
        for log in result['logs'][:3]:
            ts = datetime.fromtimestamp(log['timestamp'] / 1e9)
            print(f"    [{ts.strftime('%H:%M:%S')}] {log['message']}")
    print()

    # Query 4: Get available labels
    print("Query 4: Available labels")
    result = loki.get_labels()
    print(f"  Labels: {', '.join(result['labels_list'][:10])}")
    print()


def example_docker_operations():
    """
    Example 5: Docker container operations.

    Demonstrates starting, stopping, and restarting Loki.
    """
    print("=" * 70)
    print("EXAMPLE 5: Docker Container Operations")
    print("=" * 70)

    config = ConfigManager()
    loki = create_loki_manager(config, scope='global')

    if not loki:
        print("❌ Loki is disabled in config")
        return

    # Check initial status
    print("Checking initial status...")
    status = loki.status()
    print(f"  Healthy: {status['instance_info']['healthy']}")
    print()

    # Start if not running
    if not status['instance_info']['healthy']:
        print("Starting Loki...")
        result = loki.start()
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        print()

    # Get instance info
    print("Instance information:")
    info = loki.get_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    print()

    print("✓ Container operations completed")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "LOKI USAGE EXAMPLES" + " " * 29 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        # Run examples
        example_global_scope()
        example_tool_scope()
        example_named_instances()
        example_log_querying()
        example_docker_operations()

        print("=" * 70)
        print("✓ All examples completed successfully!")
        print()
        print("Next steps:")
        print("  1. View logs in Grafana: http://localhost:3000")
        print("  2. Query Loki API: http://localhost:3100")
        print("  3. Check data persistence: ./data/loki")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
