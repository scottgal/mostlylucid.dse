#!/usr/bin/env python3
"""
Simple test for the scheduler database and core functionality.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Test just the database layer (no complex imports)
from src.scheduler_db import SchedulerDB

def test_database():
    """Test database operations."""
    print("Testing scheduler database...")

    db = SchedulerDB('/tmp/test_scheduler.db')

    # Create a test schedule
    schedule = db.create_schedule(
        schedule_id='test_001',
        name='Test Schedule',
        description='every 5 minutes',
        cron_expression='*/5 * * * *',
        tool_name='basic_calculator',
        tool_inputs={'operation': 'add', 'a': 2, 'b': 3},
        next_run='2025-01-01T00:00:00'
    )

    print(f"  ✓ Created schedule: {schedule['id']}")
    assert schedule['name'] == 'Test Schedule'
    assert schedule['cron_expression'] == '*/5 * * * *'

    # List schedules
    schedules = db.list_schedules()
    print(f"  ✓ Listed schedules: {len(schedules)} found")
    assert len(schedules) >= 1

    # Get specific schedule
    retrieved = db.get_schedule('test_001')
    print(f"  ✓ Retrieved schedule: {retrieved['name']}")
    assert retrieved['id'] == 'test_001'

    # Create execution
    exec_id = db.create_execution('test_001')
    print(f"  ✓ Created execution: {exec_id}")
    assert exec_id > 0

    # Update execution
    db.update_execution(exec_id, 'success', result={'result': 5})
    print(f"  ✓ Updated execution with result")

    # Get history
    history = db.get_execution_history('test_001')
    print(f"  ✓ Got execution history: {len(history)} records")
    assert len(history) == 1
    assert history[0]['status'] == 'success'
    assert history[0]['result']['result'] == 5

    # Update status
    success = db.update_schedule_status('test_001', 'paused')
    print(f"  ✓ Updated schedule status: {success}")
    assert success

    # Increment run count
    db.increment_run_count('test_001')
    updated = db.get_schedule('test_001')
    print(f"  ✓ Incremented run count: {updated['run_count']}")
    assert updated['run_count'] == 1

    # Cleanup
    deleted = db.delete_schedule('test_001')
    print(f"  ✓ Deleted schedule: {deleted}")
    assert deleted

    print("\n✓ All database tests passed!\n")


def test_cron_validation():
    """Test CRON expression validation via APScheduler."""
    print("Testing CRON validation...")

    try:
        from apscheduler.triggers.cron import CronTrigger

        # Valid CRON expressions
        valid_crons = [
            '*/5 * * * *',      # Every 5 minutes
            '0 * * * *',        # Every hour
            '0 0 * * *',        # Every day at midnight
            '0 18 * * *',       # Every day at 6pm
            '30 8 * * 1-5',     # Weekdays at 8:30am
            '0 0,12 * * *',     # Twice a day
        ]

        for cron in valid_crons:
            trigger = CronTrigger.from_crontab(cron)
            print(f"  ✓ Valid CRON: {cron}")

        # Invalid CRON should raise exception
        try:
            trigger = CronTrigger.from_crontab('invalid cron')
            print("  ❌ Should have raised exception for invalid CRON")
            sys.exit(1)
        except:
            print(f"  ✓ Invalid CRON correctly rejected")

        print("\n✓ CRON validation tests passed!\n")

    except ImportError:
        print("  ⚠ APScheduler not available, skipping CRON validation")


if __name__ == '__main__':
    print("="*60)
    print("Scheduler Database Test Suite")
    print("="*60)
    print()

    try:
        test_database()
        test_cron_validation()

        print("="*60)
        print("ALL TESTS PASSED!")
        print("="*60)

        # Cleanup test database
        import os
        if os.path.exists('/tmp/test_scheduler.db'):
            os.remove('/tmp/test_scheduler.db')
            print("\nCleaned up test database")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
