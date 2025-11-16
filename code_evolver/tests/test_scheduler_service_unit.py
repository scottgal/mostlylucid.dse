#!/usr/bin/env python3
"""
Comprehensive unit tests for SchedulerService.

Tests scheduler lifecycle, job management, and execution.
"""

import unittest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.scheduler_service import SchedulerService
from src.scheduler_db import SchedulerDB


class TestSchedulerServiceLifecycle(unittest.TestCase):
    """Test scheduler service lifecycle operations."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Patch the default db path
        self.patcher = patch('src.scheduler_service.SchedulerDB')
        mock_db_class = self.patcher.start()
        mock_db_class.return_value = SchedulerDB(self.temp_db.name)

        # Reset singleton
        SchedulerService._instance = None
        self.scheduler = SchedulerService()

    def tearDown(self):
        """Clean up."""
        if hasattr(self.scheduler, 'scheduler') and self.scheduler._running:
            self.scheduler.stop()

        self.patcher.stop()

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_singleton_pattern(self):
        """Test that only one instance is created."""
        scheduler1 = SchedulerService()
        scheduler2 = SchedulerService()

        self.assertIs(scheduler1, scheduler2)

    def test_set_tool_executor(self):
        """Test setting the tool executor."""
        executor = Mock()
        self.scheduler.set_tool_executor(executor)

        self.assertEqual(self.scheduler._tool_executor, executor)

    def test_start_without_executor_raises(self):
        """Test starting scheduler without executor raises error."""
        with self.assertRaises(RuntimeError):
            self.scheduler.start()

    def test_start_and_stop(self):
        """Test starting and stopping the scheduler."""
        executor = Mock()
        self.scheduler.set_tool_executor(executor)

        self.scheduler.start()
        self.assertTrue(self.scheduler.is_running)
        self.assertTrue(self.scheduler.scheduler.running)

        self.scheduler.stop()
        self.assertFalse(self.scheduler.is_running)

    def test_double_start(self):
        """Test that starting twice doesn't cause issues."""
        executor = Mock()
        self.scheduler.set_tool_executor(executor)

        self.scheduler.start()
        self.scheduler.start()  # Should just warn

        self.assertTrue(self.scheduler.is_running)

        self.scheduler.stop()

    def test_stop_when_not_running(self):
        """Test stopping when not running."""
        # Should not raise
        self.scheduler.stop()


class TestSchedulerServiceScheduleManagement(unittest.TestCase):
    """Test schedule creation and management."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Patch the default db path
        self.patcher = patch('src.scheduler_service.SchedulerDB')
        mock_db_class = self.patcher.start()
        mock_db_class.return_value = SchedulerDB(self.temp_db.name)

        # Reset singleton
        SchedulerService._instance = None
        self.scheduler = SchedulerService()

        # Set up executor
        self.executor = Mock(return_value={'success': True, 'result': 'OK'})
        self.scheduler.set_tool_executor(self.executor)
        self.scheduler.start()

    def tearDown(self):
        """Clean up."""
        if self.scheduler._running:
            self.scheduler.stop()

        self.patcher.stop()

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_create_schedule(self):
        """Test creating a schedule."""
        schedule = self.scheduler.create_schedule(
            name='Test Schedule',
            description='every 5 minutes',
            cron_expression='*/5 * * * *',
            tool_name='test_tool',
            tool_inputs={'param': 'value'}
        )

        self.assertIsNotNone(schedule)
        self.assertIn('id', schedule)
        self.assertEqual(schedule['name'], 'Test Schedule')
        self.assertEqual(schedule['status'], 'active')

        # Verify it's in APScheduler
        job = self.scheduler.scheduler.get_job(schedule['id'])
        self.assertIsNotNone(job)

    def test_create_schedule_with_invalid_cron(self):
        """Test creating schedule with invalid CRON expression."""
        with self.assertRaises(ValueError):
            self.scheduler.create_schedule(
                name='Bad Schedule',
                description='invalid',
                cron_expression='not a valid cron',
                tool_name='test_tool',
                tool_inputs={}
            )

    def test_list_schedules(self):
        """Test listing schedules."""
        # Create multiple schedules
        for i in range(3):
            self.scheduler.create_schedule(
                name=f'Schedule {i}',
                description='test',
                cron_expression='* * * * *',
                tool_name='test_tool',
                tool_inputs={}
            )

        schedules = self.scheduler.list_schedules()
        self.assertEqual(len(schedules), 3)

    def test_list_schedules_by_status(self):
        """Test filtering schedules by status."""
        # Create and pause one
        schedule = self.scheduler.create_schedule(
            name='Paused Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.scheduler.pause_schedule(schedule['id'])

        active = self.scheduler.list_schedules(status='active')
        paused = self.scheduler.list_schedules(status='paused')

        self.assertEqual(len(paused), 1)

    def test_get_schedule(self):
        """Test getting a specific schedule."""
        created = self.scheduler.create_schedule(
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        retrieved = self.scheduler.get_schedule(created['id'])

        self.assertEqual(retrieved['id'], created['id'])
        self.assertEqual(retrieved['name'], created['name'])

    def test_pause_schedule(self):
        """Test pausing a schedule."""
        schedule = self.scheduler.create_schedule(
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.scheduler.pause_schedule(schedule['id'])

        # Should be removed from APScheduler
        job = self.scheduler.scheduler.get_job(schedule['id'])
        self.assertIsNone(job)

        # Should be paused in DB
        retrieved = self.scheduler.get_schedule(schedule['id'])
        self.assertEqual(retrieved['status'], 'paused')

    def test_resume_schedule(self):
        """Test resuming a paused schedule."""
        schedule = self.scheduler.create_schedule(
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.scheduler.pause_schedule(schedule['id'])
        self.scheduler.resume_schedule(schedule['id'])

        # Should be back in APScheduler
        job = self.scheduler.scheduler.get_job(schedule['id'])
        self.assertIsNotNone(job)

        # Should be active in DB
        retrieved = self.scheduler.get_schedule(schedule['id'])
        self.assertEqual(retrieved['status'], 'active')

    def test_delete_schedule(self):
        """Test deleting a schedule."""
        schedule = self.scheduler.create_schedule(
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.scheduler.delete_schedule(schedule['id'])

        # Should be removed from APScheduler
        job = self.scheduler.scheduler.get_job(schedule['id'])
        self.assertIsNone(job)

        # Should be gone from DB
        retrieved = self.scheduler.get_schedule(schedule['id'])
        self.assertIsNone(retrieved)

    def test_pause_nonexistent_schedule(self):
        """Test pausing a schedule that doesn't exist."""
        with self.assertRaises(ValueError):
            self.scheduler.pause_schedule('nonexistent')

    def test_resume_nonexistent_schedule(self):
        """Test resuming a schedule that doesn't exist."""
        with self.assertRaises(ValueError):
            self.scheduler.resume_schedule('nonexistent')

    def test_delete_nonexistent_schedule(self):
        """Test deleting a schedule that doesn't exist."""
        with self.assertRaises(ValueError):
            self.scheduler.delete_schedule('nonexistent')


class TestSchedulerServiceExecution(unittest.TestCase):
    """Test schedule execution."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Patch the default db path
        self.patcher = patch('src.scheduler_service.SchedulerDB')
        mock_db_class = self.patcher.start()
        mock_db_class.return_value = SchedulerDB(self.temp_db.name)

        # Reset singleton
        SchedulerService._instance = None
        self.scheduler = SchedulerService()

        # Track executions
        self.executions = []

        def executor(tool_name, tool_inputs):
            self.executions.append({
                'tool_name': tool_name,
                'tool_inputs': tool_inputs
            })
            return {'success': True, 'result': 'executed'}

        self.executor = executor
        self.scheduler.set_tool_executor(self.executor)
        self.scheduler.start()

    def tearDown(self):
        """Clean up."""
        if self.scheduler._running:
            self.scheduler.stop()

        self.patcher.stop()

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_trigger_now(self):
        """Test manually triggering a schedule."""
        schedule = self.scheduler.create_schedule(
            name='Test Schedule',
            description='manual trigger',
            cron_expression='0 0 * * *',  # Daily at midnight
            tool_name='test_tool',
            tool_inputs={'param': 'value'}
        )

        result = self.scheduler.trigger_now(schedule['id'])

        self.assertTrue(result['status'] == 'success')
        self.assertIn('execution_id', result)

        # Verify tool was called
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(self.executions[0]['tool_name'], 'test_tool')
        self.assertEqual(self.executions[0]['tool_inputs']['param'], 'value')

    def test_trigger_now_with_failing_tool(self):
        """Test triggering a schedule that fails."""
        def failing_executor(tool_name, tool_inputs):
            raise Exception('Tool failed!')

        self.scheduler._tool_executor = failing_executor

        schedule = self.scheduler.create_schedule(
            name='Failing Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='failing_tool',
            tool_inputs={}
        )

        result = self.scheduler.trigger_now(schedule['id'])

        self.assertEqual(result['status'], 'failed')
        self.assertIn('error', result)

    def test_trigger_nonexistent_schedule(self):
        """Test triggering a schedule that doesn't exist."""
        with self.assertRaises(ValueError):
            self.scheduler.trigger_now('nonexistent')

    def test_get_execution_history(self):
        """Test getting execution history."""
        schedule = self.scheduler.create_schedule(
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Trigger multiple times
        for _ in range(3):
            self.scheduler.trigger_now(schedule['id'])

        history = self.scheduler.get_execution_history(schedule['id'])

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['status'], 'success')

    def test_automatic_execution(self):
        """Test that schedules execute automatically (via APScheduler)."""
        # This test is more complex as it requires waiting for APScheduler
        # We'll test the _execute_schedule method directly instead

        schedule = self.scheduler.create_schedule(
            name='Auto Execute',
            description='test',
            cron_expression='* * * * *',
            tool_name='auto_tool',
            tool_inputs={'auto': True}
        )

        # Manually trigger the execution method
        self.scheduler._execute_schedule(schedule['id'])

        # Verify execution happened
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(self.executions[0]['tool_name'], 'auto_tool')

        # Verify it was recorded
        history = self.scheduler.get_execution_history(schedule['id'])
        self.assertEqual(len(history), 1)

        # Verify run count incremented
        updated = self.scheduler.get_schedule(schedule['id'])
        self.assertEqual(updated['run_count'], 1)


class TestSchedulerServiceEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Patch the default db path
        self.patcher = patch('src.scheduler_service.SchedulerDB')
        mock_db_class = self.patcher.start()
        mock_db_class.return_value = SchedulerDB(self.temp_db.name)

        # Reset singleton
        SchedulerService._instance = None
        self.scheduler = SchedulerService()

    def tearDown(self):
        """Clean up."""
        if hasattr(self.scheduler, 'scheduler') and self.scheduler._running:
            self.scheduler.stop()

        self.patcher.stop()

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_execution_with_unicode(self):
        """Test execution with Unicode characters in inputs."""
        executor = Mock(return_value={'success': True, 'result': '成功'})
        self.scheduler.set_tool_executor(executor)
        self.scheduler.start()

        schedule = self.scheduler.create_schedule(
            name='Unicode Test 测试',
            description='test',
            cron_expression='* * * * *',
            tool_name='unicode_tool',
            tool_inputs={'message': 'Hello 世界 🚀'}
        )

        result = self.scheduler.trigger_now(schedule['id'])
        self.assertEqual(result['status'], 'success')

    def test_execution_with_large_result(self):
        """Test execution with large result data."""
        large_result = {'data': 'x' * 100000}
        executor = Mock(return_value={'success': True, 'result': large_result})
        self.scheduler.set_tool_executor(executor)
        self.scheduler.start()

        schedule = self.scheduler.create_schedule(
            name='Large Result',
            description='test',
            cron_expression='* * * * *',
            tool_name='large_tool',
            tool_inputs={}
        )

        result = self.scheduler.trigger_now(schedule['id'])
        self.assertEqual(result['status'], 'success')

        # Verify it was stored
        history = self.scheduler.get_execution_history(schedule['id'])
        self.assertEqual(len(history[0]['result']['data']), 100000)

    def test_concurrent_triggers(self):
        """Test multiple concurrent manual triggers."""
        executor = Mock(return_value={'success': True, 'result': 'OK'})
        self.scheduler.set_tool_executor(executor)
        self.scheduler.start()

        schedule = self.scheduler.create_schedule(
            name='Concurrent Test',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        results = []

        def trigger():
            result = self.scheduler.trigger_now(schedule['id'])
            results.append(result)

        # Launch 5 concurrent triggers
        threads = []
        for _ in range(5):
            t = threading.Thread(target=trigger)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should succeed
        self.assertEqual(len(results), 5)
        self.assertTrue(all(r['status'] == 'success' for r in results))

        # All should be recorded
        history = self.scheduler.get_execution_history(schedule['id'])
        self.assertEqual(len(history), 5)

    def test_load_existing_schedules_on_start(self):
        """Test that existing schedules are loaded when starting."""
        # Create schedule directly in DB (before starting scheduler)
        db = SchedulerDB(self.temp_db.name)
        db.create_schedule(
            schedule_id='existing_001',
            name='Existing Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Now start scheduler
        executor = Mock(return_value={'success': True})
        self.scheduler.set_tool_executor(executor)
        self.scheduler.start()

        # Should be loaded into APScheduler
        job = self.scheduler.scheduler.get_job('existing_001')
        self.assertIsNotNone(job)

    def test_execution_updates_timestamps(self):
        """Test that execution updates last_run and next_run."""
        executor = Mock(return_value={'success': True})
        self.scheduler.set_tool_executor(executor)
        self.scheduler.start()

        schedule = self.scheduler.create_schedule(
            name='Timestamp Test',
            description='test',
            cron_expression='*/5 * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        initial_last_run = schedule['last_run']
        self.assertIsNone(initial_last_run)

        # Trigger execution
        self.scheduler.trigger_now(schedule['id'])

        # Check updated timestamps
        updated = self.scheduler.get_schedule(schedule['id'])
        self.assertIsNotNone(updated['last_run'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
