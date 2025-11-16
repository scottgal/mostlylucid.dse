#!/usr/bin/env python3
"""
Comprehensive unit tests for SchedulerDB.

Tests all database operations, edge cases, and error handling.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.scheduler_db import SchedulerDB


class TestSchedulerDBBasics(unittest.TestCase):
    """Test basic CRUD operations."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = SchedulerDB(self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_database_initialization(self):
        """Test that database and tables are created."""
        self.assertTrue(os.path.exists(self.temp_db.name))

        # Check tables exist
        import sqlite3
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        self.assertIn('schedules', tables)
        self.assertIn('executions', tables)

        conn.close()

    def test_create_schedule(self):
        """Test creating a schedule."""
        schedule = self.db.create_schedule(
            schedule_id='test_001',
            name='Test Schedule',
            description='every 5 minutes',
            cron_expression='*/5 * * * *',
            tool_name='test_tool',
            tool_inputs={'param': 'value'}
        )

        self.assertIsNotNone(schedule)
        self.assertEqual(schedule['id'], 'test_001')
        self.assertEqual(schedule['name'], 'Test Schedule')
        self.assertEqual(schedule['cron_expression'], '*/5 * * * *')
        self.assertEqual(schedule['status'], 'active')
        self.assertEqual(schedule['tool_inputs'], {'param': 'value'})
        self.assertEqual(schedule['run_count'], 0)

    def test_create_schedule_with_next_run(self):
        """Test creating a schedule with next_run time."""
        next_run = '2025-01-01T12:00:00'
        schedule = self.db.create_schedule(
            schedule_id='test_002',
            name='Test Schedule',
            description='daily',
            cron_expression='0 0 * * *',
            tool_name='test_tool',
            tool_inputs={},
            next_run=next_run
        )

        self.assertEqual(schedule['next_run'], next_run)

    def test_get_schedule(self):
        """Test retrieving a schedule by ID."""
        self.db.create_schedule(
            schedule_id='test_003',
            name='Test Schedule',
            description='hourly',
            cron_expression='0 * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        schedule = self.db.get_schedule('test_003')

        self.assertIsNotNone(schedule)
        self.assertEqual(schedule['id'], 'test_003')
        self.assertEqual(schedule['name'], 'Test Schedule')

    def test_get_nonexistent_schedule(self):
        """Test retrieving a schedule that doesn't exist."""
        schedule = self.db.get_schedule('nonexistent')
        self.assertIsNone(schedule)

    def test_list_schedules(self):
        """Test listing all schedules."""
        # Create multiple schedules
        for i in range(5):
            self.db.create_schedule(
                schedule_id=f'test_{i:03d}',
                name=f'Schedule {i}',
                description='test',
                cron_expression='* * * * *',
                tool_name='test_tool',
                tool_inputs={}
            )

        schedules = self.db.list_schedules()
        self.assertEqual(len(schedules), 5)

    def test_list_schedules_with_status_filter(self):
        """Test filtering schedules by status."""
        # Create schedules with different statuses
        self.db.create_schedule(
            schedule_id='active_1',
            name='Active 1',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.db.create_schedule(
            schedule_id='active_2',
            name='Active 2',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Pause one
        self.db.update_schedule_status('active_2', 'paused')

        active_schedules = self.db.list_schedules(status='active')
        paused_schedules = self.db.list_schedules(status='paused')

        self.assertEqual(len(active_schedules), 1)
        self.assertEqual(len(paused_schedules), 1)
        self.assertEqual(active_schedules[0]['id'], 'active_1')
        self.assertEqual(paused_schedules[0]['id'], 'active_2')

    def test_list_schedules_with_pagination(self):
        """Test pagination of schedule listings."""
        # Create 10 schedules
        for i in range(10):
            self.db.create_schedule(
                schedule_id=f'test_{i:03d}',
                name=f'Schedule {i}',
                description='test',
                cron_expression='* * * * *',
                tool_name='test_tool',
                tool_inputs={}
            )

        # Get first 5
        page1 = self.db.list_schedules(limit=5, offset=0)
        self.assertEqual(len(page1), 5)

        # Get next 5
        page2 = self.db.list_schedules(limit=5, offset=5)
        self.assertEqual(len(page2), 5)

        # Ensure no overlap
        page1_ids = {s['id'] for s in page1}
        page2_ids = {s['id'] for s in page2}
        self.assertEqual(len(page1_ids & page2_ids), 0)

    def test_update_schedule_status(self):
        """Test updating schedule status."""
        self.db.create_schedule(
            schedule_id='test_004',
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Update to paused
        success = self.db.update_schedule_status('test_004', 'paused')
        self.assertTrue(success)

        schedule = self.db.get_schedule('test_004')
        self.assertEqual(schedule['status'], 'paused')

        # Update to error
        success = self.db.update_schedule_status('test_004', 'error')
        self.assertTrue(success)

        schedule = self.db.get_schedule('test_004')
        self.assertEqual(schedule['status'], 'error')

    def test_update_schedule_run_times(self):
        """Test updating last_run and next_run times."""
        self.db.create_schedule(
            schedule_id='test_005',
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        last_run = '2025-01-01T10:00:00'
        next_run = '2025-01-01T11:00:00'

        self.db.update_schedule_status(
            'test_005',
            'active',
            last_run=last_run,
            next_run=next_run
        )

        schedule = self.db.get_schedule('test_005')
        self.assertEqual(schedule['last_run'], last_run)
        self.assertEqual(schedule['next_run'], next_run)

    def test_update_nonexistent_schedule(self):
        """Test updating a schedule that doesn't exist."""
        success = self.db.update_schedule_status('nonexistent', 'paused')
        self.assertFalse(success)

    def test_increment_run_count(self):
        """Test incrementing schedule run count."""
        self.db.create_schedule(
            schedule_id='test_006',
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Initial count should be 0
        schedule = self.db.get_schedule('test_006')
        self.assertEqual(schedule['run_count'], 0)

        # Increment 5 times
        for i in range(5):
            self.db.increment_run_count('test_006')

        schedule = self.db.get_schedule('test_006')
        self.assertEqual(schedule['run_count'], 5)

    def test_delete_schedule(self):
        """Test deleting a schedule."""
        self.db.create_schedule(
            schedule_id='test_007',
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Create an execution for the schedule
        exec_id = self.db.create_execution('test_007')
        self.assertIsNotNone(exec_id)

        # Delete schedule
        success = self.db.delete_schedule('test_007')
        self.assertTrue(success)

        # Verify it's gone
        schedule = self.db.get_schedule('test_007')
        self.assertIsNone(schedule)

        # Verify executions are also deleted (cascade)
        history = self.db.get_execution_history('test_007')
        self.assertEqual(len(history), 0)

    def test_delete_nonexistent_schedule(self):
        """Test deleting a schedule that doesn't exist."""
        success = self.db.delete_schedule('nonexistent')
        self.assertFalse(success)


class TestSchedulerDBExecutions(unittest.TestCase):
    """Test execution tracking operations."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = SchedulerDB(self.temp_db.name)

        # Create a test schedule
        self.db.create_schedule(
            schedule_id='test_schedule',
            name='Test Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_create_execution(self):
        """Test creating an execution record."""
        exec_id = self.db.create_execution('test_schedule')

        self.assertIsNotNone(exec_id)
        self.assertIsInstance(exec_id, int)
        self.assertGreater(exec_id, 0)

    def test_create_execution_with_status(self):
        """Test creating an execution with specific status."""
        exec_id = self.db.create_execution('test_schedule', status='success')

        history = self.db.get_execution_history('test_schedule')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'success')

    def test_update_execution_with_success(self):
        """Test updating execution with success result."""
        exec_id = self.db.create_execution('test_schedule')

        result = {'output': 'success', 'value': 42}
        self.db.update_execution(exec_id, 'success', result=result)

        history = self.db.get_execution_history('test_schedule')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'success')
        self.assertEqual(history[0]['result'], result)
        self.assertIsNotNone(history[0]['finished_at'])

    def test_update_execution_with_failure(self):
        """Test updating execution with failure."""
        exec_id = self.db.create_execution('test_schedule')

        error = 'Tool execution failed: timeout'
        self.db.update_execution(exec_id, 'failed', error=error)

        history = self.db.get_execution_history('test_schedule')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'failed')
        self.assertEqual(history[0]['error'], error)

    def test_get_execution_history(self):
        """Test retrieving execution history."""
        # Create multiple executions
        for i in range(5):
            exec_id = self.db.create_execution('test_schedule')
            self.db.update_execution(
                exec_id,
                'success',
                result={'iteration': i}
            )

        history = self.db.get_execution_history('test_schedule')
        self.assertEqual(len(history), 5)

        # Should be ordered by most recent first
        self.assertEqual(history[0]['result']['iteration'], 4)

    def test_get_execution_history_with_limit(self):
        """Test limiting execution history results."""
        # Create 10 executions
        for i in range(10):
            exec_id = self.db.create_execution('test_schedule')
            self.db.update_execution(exec_id, 'success')

        history = self.db.get_execution_history('test_schedule', limit=5)
        self.assertEqual(len(history), 5)

    def test_get_execution_history_for_nonexistent_schedule(self):
        """Test getting history for schedule that doesn't exist."""
        history = self.db.get_execution_history('nonexistent')
        self.assertEqual(len(history), 0)


class TestSchedulerDBEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = SchedulerDB(self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_empty_tool_inputs(self):
        """Test schedule with empty tool inputs."""
        schedule = self.db.create_schedule(
            schedule_id='empty_inputs',
            name='Empty Inputs',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.assertEqual(schedule['tool_inputs'], {})

    def test_complex_tool_inputs(self):
        """Test schedule with complex nested tool inputs."""
        complex_inputs = {
            'string': 'value',
            'number': 42,
            'boolean': True,
            'null': None,
            'array': [1, 2, 3],
            'nested': {
                'deep': {
                    'value': 'test'
                }
            }
        }

        schedule = self.db.create_schedule(
            schedule_id='complex_inputs',
            name='Complex Inputs',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs=complex_inputs
        )

        self.assertEqual(schedule['tool_inputs'], complex_inputs)

    def test_unicode_in_fields(self):
        """Test handling of Unicode characters."""
        schedule = self.db.create_schedule(
            schedule_id='unicode_test',
            name='Test 测试 🚀',
            description='every hour 每小时',
            cron_expression='0 * * * *',
            tool_name='test_tool',
            tool_inputs={'message': 'Hello 世界 👋'}
        )

        self.assertEqual(schedule['name'], 'Test 测试 🚀')
        self.assertEqual(schedule['tool_inputs']['message'], 'Hello 世界 👋')

    def test_very_long_description(self):
        """Test handling of very long descriptions."""
        long_description = 'x' * 10000

        schedule = self.db.create_schedule(
            schedule_id='long_desc',
            name='Long Description',
            description=long_description,
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        self.assertEqual(len(schedule['description']), 10000)

    def test_duplicate_schedule_id(self):
        """Test creating schedule with duplicate ID."""
        self.db.create_schedule(
            schedule_id='duplicate',
            name='First',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Should raise IntegrityError
        with self.assertRaises(Exception):
            self.db.create_schedule(
                schedule_id='duplicate',
                name='Second',
                description='test',
                cron_expression='* * * * *',
                tool_name='test_tool',
                tool_inputs={}
            )

    def test_concurrent_read_operations(self):
        """Test multiple concurrent read operations."""
        import threading

        # Create some schedules
        for i in range(10):
            self.db.create_schedule(
                schedule_id=f'test_{i}',
                name=f'Schedule {i}',
                description='test',
                cron_expression='* * * * *',
                tool_name='test_tool',
                tool_inputs={}
            )

        results = []

        def read_schedules():
            schedules = self.db.list_schedules()
            results.append(len(schedules))

        # Launch 10 concurrent reads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=read_schedules)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All reads should get same count
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(results[0], 10)

    def test_null_values(self):
        """Test handling of null values in optional fields."""
        schedule = self.db.create_schedule(
            schedule_id='null_test',
            name='Null Test',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={},
            next_run=None
        )

        self.assertIsNone(schedule['next_run'])
        self.assertIsNone(schedule['last_run'])


class TestSchedulerDBPerformance(unittest.TestCase):
    """Test performance characteristics."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = SchedulerDB(self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_bulk_insert_performance(self):
        """Test inserting many schedules."""
        import time

        start = time.time()

        # Insert 100 schedules
        for i in range(100):
            self.db.create_schedule(
                schedule_id=f'bulk_{i:04d}',
                name=f'Bulk Schedule {i}',
                description='test',
                cron_expression='* * * * *',
                tool_name='test_tool',
                tool_inputs={'index': i}
            )

        duration = time.time() - start

        # Should complete in reasonable time (< 5 seconds)
        self.assertLess(duration, 5.0)

        # Verify all inserted
        schedules = self.db.list_schedules(limit=200)
        self.assertEqual(len(schedules), 100)

    def test_large_execution_history(self):
        """Test performance with large execution history."""
        import time

        self.db.create_schedule(
            schedule_id='perf_test',
            name='Performance Test',
            description='test',
            cron_expression='* * * * *',
            tool_name='test_tool',
            tool_inputs={}
        )

        # Create 1000 executions
        for i in range(1000):
            exec_id = self.db.create_execution('perf_test')
            self.db.update_execution(exec_id, 'success', result={'i': i})

        # Query should still be fast
        start = time.time()
        history = self.db.get_execution_history('perf_test', limit=50)
        duration = time.time() - start

        self.assertLess(duration, 0.5)  # Should be < 500ms
        self.assertEqual(len(history), 50)


if __name__ == '__main__':
    unittest.main(verbosity=2)
