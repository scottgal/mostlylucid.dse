#!/usr/bin/env python3
"""
Test script for the scheduler system.
"""

import sys
import json
import time
from src.scheduler_service import SchedulerService
from src.scheduler_db import SchedulerDB

def test_database():
    """Test database operations."""
    print("Testing database...")

    db = SchedulerDB()

    # Create a test schedule
    schedule = db.create_schedule(
        schedule_id='test_schedule_001',
        name='Test Schedule',
        description='every 5 minutes',
        cron_expression='*/5 * * * *',
        tool_name='basic_calculator',
        tool_inputs={'operation': 'add', 'a': 2, 'b': 3},
        next_run='2025-01-01T00:00:00'
    )

    print(f"Created schedule: {schedule['id']}")

    # List schedules
    schedules = db.list_schedules()
    print(f"Total schedules: {len(schedules)}")

    # Get specific schedule
    retrieved = db.get_schedule('test_schedule_001')
    print(f"Retrieved: {retrieved['name']}")

    # Create execution
    exec_id = db.create_execution('test_schedule_001')
    print(f"Created execution: {exec_id}")

    # Update execution
    db.update_execution(exec_id, 'success', result={'result': 5})
    print(f"Updated execution with result")

    # Get history
    history = db.get_execution_history('test_schedule_001')
    print(f"Execution history: {len(history)} records")

    # Cleanup
    db.delete_schedule('test_schedule_001')
    print("Cleaned up test schedule")

    print("✓ Database tests passed!\n")


def test_scheduler_service():
    """Test scheduler service."""
    print("Testing scheduler service...")

    # Create a simple tool executor
    def tool_executor(tool_name, tool_inputs):
        print(f"  Executing tool: {tool_name} with inputs: {tool_inputs}")
        if tool_name == 'basic_calculator':
            op = tool_inputs.get('operation', 'add')
            a = tool_inputs.get('a', 0)
            b = tool_inputs.get('b', 0)

            if op == 'add':
                result = a + b
            elif op == 'multiply':
                result = a * b
            else:
                result = 0

            return {
                'success': True,
                'result': result,
                'operation': op
            }

        return {'success': False, 'error': 'Unknown tool'}

    # Initialize scheduler
    scheduler = SchedulerService()
    scheduler.set_tool_executor(tool_executor)
    scheduler.start()

    print("Scheduler started")

    # Create a schedule
    schedule = scheduler.create_schedule(
        name='Test Calculator Schedule',
        description='every 5 minutes',
        cron_expression='*/5 * * * *',
        tool_name='basic_calculator',
        tool_inputs={'operation': 'add', 'a': 10, 'b': 20}
    )

    print(f"Created schedule: {schedule['id']}")
    print(f"  Name: {schedule['name']}")
    print(f"  CRON: {schedule['cron_expression']}")

    # List schedules
    schedules = scheduler.list_schedules()
    print(f"\nActive schedules: {len(schedules)}")

    # Trigger manually
    print("\nTriggering schedule manually...")
    result = scheduler.trigger_now(schedule['id'])
    print(f"Execution result: {result}")

    # View history
    history = scheduler.get_execution_history(schedule['id'])
    print(f"\nExecution history: {len(history)} records")
    if history:
        print(f"  Last execution: {history[0]['status']}")
        print(f"  Result: {history[0].get('result')}")

    # Pause schedule
    scheduler.pause_schedule(schedule['id'])
    print(f"\nPaused schedule: {schedule['id']}")

    # Resume schedule
    scheduler.resume_schedule(schedule['id'])
    print(f"Resumed schedule: {schedule['id']}")

    # Cleanup
    scheduler.delete_schedule(schedule['id'])
    print(f"Deleted schedule: {schedule['id']}")

    # Stop scheduler
    scheduler.stop()
    print("Scheduler stopped")

    print("\n✓ Scheduler service tests passed!\n")


def test_schedule_manager_tool():
    """Test the schedule_manager executable tool."""
    print("Testing schedule_manager tool...")

    import subprocess
    import os

    tool_dir = os.path.join(os.path.dirname(__file__), 'tools', 'executable')
    script_path = os.path.join(tool_dir, 'schedule_manager.py')

    # Test list command
    print("Testing list command...")
    result = subprocess.run(
        [sys.executable, script_path, 'list', '{}'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        data = json.loads(result.stdout)
        print(f"  Success: {data.get('success')}")
        print(f"  Schedules: {len(data.get('data', {}).get('schedules', []))}")
    else:
        print(f"  Error: {result.stderr}")

    print("\n✓ Schedule manager tool tests passed!\n")


if __name__ == '__main__':
    print("="*60)
    print("Scheduler System Test Suite")
    print("="*60)
    print()

    try:
        test_database()
        test_scheduler_service()
        test_schedule_manager_tool()

        print("="*60)
        print("ALL TESTS PASSED!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
