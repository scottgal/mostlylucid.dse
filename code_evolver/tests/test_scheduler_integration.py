#!/usr/bin/env python3
"""
Integration tests for the complete scheduler system.

Tests end-to-end workflows including CLI, tools, and database.
"""

import unittest
import tempfile
import os
import json
import subprocess
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.scheduler_service import SchedulerService
from src.scheduler_db import SchedulerDB


class TestSchedulerCLIIntegration(unittest.TestCase):
    """Test schedule_manager.py CLI tool."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        os.environ['SCHEDULER_DB_PATH'] = self.temp_db.name

        self.script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'tools', 'executable', 'schedule_manager.py'
        )

    def tearDown(self):
        """Clean up."""
        if 'SCHEDULER_DB_PATH' in os.environ:
            del os.environ['SCHEDULER_DB_PATH']

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def run_cli(self, operation, params):
        """Helper to run CLI command."""
        result = subprocess.run(
            [sys.executable, self.script_path, operation, json.dumps(params)],
            capture_output=True,
            text=True
        )
        return result

    def test_cli_list_empty(self):
        """Test listing schedules when none exist."""
        result = self.run_cli('list', {})

        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['schedules']), 0)

    def test_cli_create_schedule(self):
        """Test creating a schedule via CLI."""
        params = {
            'name': 'CLI Test Schedule',
            'description': 'every 10 minutes',
            'cron_expression': '*/10 * * * *',
            'tool_name': 'test_tool',
            'tool_inputs': {'param': 'value'}
        }

        result = self.run_cli('create', params)

        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertTrue(data['success'])
        self.assertIn('id', data['data'])

    def test_cli_create_invalid_cron(self):
        """Test creating schedule with invalid CRON."""
        params = {
            'name': 'Bad Schedule',
            'description': 'invalid',
            'cron_expression': 'not a cron',
            'tool_name': 'test_tool',
            'tool_inputs': {}
        }

        result = self.run_cli('create', params)

        self.assertEqual(result.returncode, 0)  # Script doesn't exit with error
        data = json.loads(result.stdout)
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_cli_full_workflow(self):
        """Test complete create-list-get-trigger-delete workflow."""
        # Create
        create_params = {
            'name': 'Full Workflow Test',
            'description': 'hourly',
            'cron_expression': '0 * * * *',
            'tool_name': 'test_tool',
            'tool_inputs': {}
        }

        result = self.run_cli('create', create_params)
        data = json.loads(result.stdout)
        schedule_id = data['data']['id']

        # List
        result = self.run_cli('list', {})
        data = json.loads(result.stdout)
        self.assertEqual(len(data['data']['schedules']), 1)

        # Get
        result = self.run_cli('get', {'schedule_id': schedule_id})
        data = json.loads(result.stdout)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], 'Full Workflow Test')

        # Pause
        result = self.run_cli('pause', {'schedule_id': schedule_id})
        data = json.loads(result.stdout)
        self.assertTrue(data['success'])

        # Resume
        result = self.run_cli('resume', {'schedule_id': schedule_id})
        data = json.loads(result.stdout)
        self.assertTrue(data['success'])

        # Delete
        result = self.run_cli('delete', {'schedule_id': schedule_id})
        data = json.loads(result.stdout)
        self.assertTrue(data['success'])

        # Verify deleted
        result = self.run_cli('list', {})
        data = json.loads(result.stdout)
        self.assertEqual(len(data['data']['schedules']), 0)


class TestSchedulerEndToEnd(unittest.TestCase):
    """End-to-end integration tests."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Create fresh singleton
        SchedulerService._instance = None

        # Mock the DB path
        from unittest.mock import patch
        self.patcher = patch('src.scheduler_service.SchedulerDB')
        mock_db_class = self.patcher.start()
        mock_db_class.return_value = SchedulerDB(self.temp_db.name)

        self.scheduler = SchedulerService()
        self.tool_calls = []

        def mock_executor(tool_name, tool_inputs):
            self.tool_calls.append({
                'tool_name': tool_name,
                'tool_inputs': tool_inputs
            })
            return {'success': True, 'result': f'Executed {tool_name}'}

        self.scheduler.set_tool_executor(mock_executor)
        self.scheduler.start()

    def tearDown(self):
        """Clean up."""
        if self.scheduler._running:
            self.scheduler.stop()

        self.patcher.stop()

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_complete_schedule_lifecycle(self):
        """Test complete lifecycle: create, execute, track, delete."""
        # Create schedule
        schedule = self.scheduler.create_schedule(
            name='Lifecycle Test',
            description='every 5 minutes',
            cron_expression='*/5 * * * *',
            tool_name='lifecycle_tool',
            tool_inputs={'test': 'data'}
        )

        schedule_id = schedule['id']

        # Verify it exists
        schedules = self.scheduler.list_schedules()
        self.assertEqual(len(schedules), 1)

        # Execute it manually
        result = self.scheduler.trigger_now(schedule_id)
        self.assertEqual(result['status'], 'success')

        # Verify tool was called
        self.assertEqual(len(self.tool_calls), 1)
        self.assertEqual(self.tool_calls[0]['tool_name'], 'lifecycle_tool')

        # Check execution history
        history = self.scheduler.get_execution_history(schedule_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'success')

        # Pause it
        self.scheduler.pause_schedule(schedule_id)
        paused = self.scheduler.get_schedule(schedule_id)
        self.assertEqual(paused['status'], 'paused')

        # Resume it
        self.scheduler.resume_schedule(schedule_id)
        resumed = self.scheduler.get_schedule(schedule_id)
        self.assertEqual(resumed['status'], 'active')

        # Delete it
        self.scheduler.delete_schedule(schedule_id)
        deleted = self.scheduler.get_schedule(schedule_id)
        self.assertIsNone(deleted)

    def test_multiple_schedules_different_tools(self):
        """Test managing multiple schedules for different tools."""
        tools = ['tool_a', 'tool_b', 'tool_c']

        schedule_ids = []
        for tool in tools:
            schedule = self.scheduler.create_schedule(
                name=f'{tool} Schedule',
                description='test',
                cron_expression='* * * * *',
                tool_name=tool,
                tool_inputs={'tool': tool}
            )
            schedule_ids.append(schedule['id'])

        # Verify all created
        schedules = self.scheduler.list_schedules()
        self.assertEqual(len(schedules), 3)

        # Trigger each
        for schedule_id in schedule_ids:
            result = self.scheduler.trigger_now(schedule_id)
            self.assertEqual(result['status'], 'success')

        # Verify all tools were called
        self.assertEqual(len(self.tool_calls), 3)
        called_tools = {call['tool_name'] for call in self.tool_calls}
        self.assertEqual(called_tools, set(tools))

    def test_schedule_with_complex_inputs(self):
        """Test schedule with complex nested inputs."""
        complex_inputs = {
            'config': {
                'mode': 'production',
                'features': ['a', 'b', 'c'],
                'limits': {
                    'max_size': 1000,
                    'timeout': 30
                }
            },
            'targets': ['target1', 'target2']
        }

        schedule = self.scheduler.create_schedule(
            name='Complex Inputs Test',
            description='test',
            cron_expression='0 * * * *',
            tool_name='complex_tool',
            tool_inputs=complex_inputs
        )

        # Trigger and verify inputs are preserved
        result = self.scheduler.trigger_now(schedule['id'])
        self.assertEqual(result['status'], 'success')

        self.assertEqual(self.tool_calls[0]['tool_inputs'], complex_inputs)

    def test_persistence_across_restarts(self):
        """Test that schedules persist across service restarts."""
        # Create schedule
        schedule = self.scheduler.create_schedule(
            name='Persistent Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='persist_tool',
            tool_inputs={}
        )

        schedule_id = schedule['id']

        # Stop scheduler
        self.scheduler.stop()

        # Create new instance (simulates restart)
        SchedulerService._instance = None
        new_scheduler = SchedulerService()
        new_scheduler.set_tool_executor(lambda t, i: {'success': True})
        new_scheduler.start()

        # Schedule should be loaded
        loaded = new_scheduler.get_schedule(schedule_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['name'], 'Persistent Schedule')

        # Should be in APScheduler
        job = new_scheduler.scheduler.get_job(schedule_id)
        self.assertIsNotNone(job)

        new_scheduler.stop()

    def test_execution_error_handling(self):
        """Test that execution errors are properly recorded."""
        # Set up failing executor
        def failing_executor(tool_name, tool_inputs):
            raise ValueError('Intentional failure for testing')

        self.scheduler._tool_executor = failing_executor

        schedule = self.scheduler.create_schedule(
            name='Failing Schedule',
            description='test',
            cron_expression='* * * * *',
            tool_name='failing_tool',
            tool_inputs={}
        )

        # Trigger and expect failure
        result = self.scheduler.trigger_now(schedule['id'])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('error', result)

        # Check it's recorded in history
        history = self.scheduler.get_execution_history(schedule['id'])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'failed')
        self.assertIsNotNone(history[0]['error'])

        # Schedule status should be error
        schedule = self.scheduler.get_schedule(schedule['id'])
        self.assertEqual(schedule['status'], 'error')

    def test_concurrent_schedule_execution(self):
        """Test that multiple schedules can be triggered concurrently."""
        import threading

        # Create multiple schedules
        schedule_ids = []
        for i in range(5):
            schedule = self.scheduler.create_schedule(
                name=f'Concurrent {i}',
                description='test',
                cron_expression='* * * * *',
                tool_name=f'tool_{i}',
                tool_inputs={'index': i}
            )
            schedule_ids.append(schedule['id'])

        results = []

        def trigger(sid):
            result = self.scheduler.trigger_now(sid)
            results.append(result)

        # Trigger all concurrently
        threads = []
        for sid in schedule_ids:
            t = threading.Thread(target=trigger, args=(sid,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should succeed
        self.assertEqual(len(results), 5)
        self.assertTrue(all(r['status'] == 'success' for r in results))

        # All should be recorded
        for sid in schedule_ids:
            history = self.scheduler.get_execution_history(sid)
            self.assertEqual(len(history), 1)


class TestSchedulerRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        SchedulerService._instance = None

        from unittest.mock import patch
        self.patcher = patch('src.scheduler_service.SchedulerDB')
        mock_db_class = self.patcher.start()
        mock_db_class.return_value = SchedulerDB(self.temp_db.name)

        self.scheduler = SchedulerService()
        self.executions = []

        def mock_executor(tool_name, tool_inputs):
            import time
            time.sleep(0.1)  # Simulate work
            self.executions.append({
                'tool': tool_name,
                'inputs': tool_inputs,
                'timestamp': time.time()
            })
            return {'success': True, 'processed': True}

        self.scheduler.set_tool_executor(mock_executor)
        self.scheduler.start()

    def tearDown(self):
        """Clean up."""
        if self.scheduler._running:
            self.scheduler.stop()

        self.patcher.stop()

        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_daily_backup_scenario(self):
        """Simulate daily backup schedule."""
        schedule = self.scheduler.create_schedule(
            name='Daily Backup',
            description='every day at 2am',
            cron_expression='0 2 * * *',
            tool_name='backup_tool',
            tool_inputs={
                'source': '/data',
                'destination': '/backups',
                'compression': 'gzip'
            }
        )

        # Manually trigger (simulating the 2am run)
        result = self.scheduler.trigger_now(schedule['id'])
        self.assertEqual(result['status'], 'success')

        # Verify backup tool was called with correct params
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(self.executions[0]['tool'], 'backup_tool')
        self.assertEqual(self.executions[0]['inputs']['source'], '/data')

    def test_hourly_monitoring_scenario(self):
        """Simulate hourly system monitoring."""
        schedule = self.scheduler.create_schedule(
            name='Hourly Health Check',
            description='every hour',
            cron_expression='0 * * * *',
            tool_name='health_check_tool',
            tool_inputs={
                'services': ['web', 'db', 'cache'],
                'alert_on_failure': True
            }
        )

        # Simulate multiple hourly runs
        for _ in range(3):
            result = self.scheduler.trigger_now(schedule['id'])
            self.assertEqual(result['status'], 'success')

        # Verify all runs are recorded
        history = self.scheduler.get_execution_history(schedule['id'])
        self.assertEqual(len(history), 3)

        # Verify run count
        updated = self.scheduler.get_schedule(schedule['id'])
        self.assertEqual(updated['run_count'], 3)

    def test_report_generation_scenario(self):
        """Simulate weekly report generation."""
        schedule = self.scheduler.create_schedule(
            name='Weekly Report',
            description='every Monday at 9am',
            cron_expression='0 9 * * 1',
            tool_name='report_generator',
            tool_inputs={
                'report_type': 'weekly_summary',
                'recipients': ['admin@example.com'],
                'format': 'pdf'
            }
        )

        result = self.scheduler.trigger_now(schedule['id'])
        self.assertEqual(result['status'], 'success')

        # Verify report was generated
        self.assertEqual(self.executions[0]['inputs']['report_type'], 'weekly_summary')


if __name__ == '__main__':
    unittest.main(verbosity=2)
