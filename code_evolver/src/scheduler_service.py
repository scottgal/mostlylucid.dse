"""
Background scheduler service using APScheduler.

Executes scheduled tasks using CRON expressions and manages the job lifecycle.
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError

from src.scheduler_db import SchedulerDB

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background service for executing scheduled tasks."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one scheduler instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the scheduler service."""
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.db = SchedulerDB()
        self._tool_executor: Optional[Callable] = None
        self._running = False

        # Configure APScheduler
        executors = {
            'default': ThreadPoolExecutor(max_workers=10)
        }

        job_defaults = {
            'coalesce': True,  # Combine multiple missed executions into one
            'max_instances': 1,  # Only one instance of a job at a time
            'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
        }

        self.scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        logger.info("Scheduler service initialized")

    def set_tool_executor(self, executor: Callable):
        """Set the tool execution function.

        Args:
            executor: Callable that takes (tool_name, tool_inputs) and executes the tool
        """
        self._tool_executor = executor
        logger.info("Tool executor configured for scheduler")

    def start(self):
        """Start the scheduler service and load existing schedules."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        if self._tool_executor is None:
            raise RuntimeError("Tool executor must be set before starting scheduler")

        # Start APScheduler
        self.scheduler.start()
        self._running = True

        # Load and activate existing schedules from database
        self._load_schedules()

        logger.info("Scheduler service started")

    def stop(self):
        """Stop the scheduler service."""
        if not self._running:
            return

        self.scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Scheduler service stopped")

    def _load_schedules(self):
        """Load active schedules from database and add them to APScheduler."""
        active_schedules = self.db.list_schedules(status='active')

        for schedule in active_schedules:
            try:
                self._add_job(schedule)
                logger.info(f"Loaded schedule: {schedule['name']} ({schedule['id']})")
            except Exception as e:
                logger.error(f"Failed to load schedule {schedule['id']}: {e}")
                # Mark schedule as error
                self.db.update_schedule_status(schedule['id'], 'error')

    def create_schedule(
        self,
        name: str,
        description: str,
        cron_expression: str,
        tool_name: str,
        tool_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create and activate a new schedule.

        Args:
            name: Human-readable name for the schedule
            description: Natural language description (e.g., "every 20 minutes")
            cron_expression: CRON expression for scheduling
            tool_name: Name of the tool to execute
            tool_inputs: Dictionary of tool input parameters

        Returns:
            Dictionary containing the created schedule

        Raises:
            ValueError: If CRON expression is invalid
        """
        # Validate CRON expression
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
        except Exception as e:
            raise ValueError(f"Invalid CRON expression: {e}")

        # Generate unique ID
        schedule_id = f"schedule_{uuid.uuid4().hex[:12]}"

        # Calculate next run time
        next_run = trigger.get_next_fire_time(None, datetime.utcnow())
        next_run_str = next_run.isoformat() if next_run else None

        # Create in database
        schedule = self.db.create_schedule(
            schedule_id=schedule_id,
            name=name,
            description=description,
            cron_expression=cron_expression,
            tool_name=tool_name,
            tool_inputs=tool_inputs,
            next_run=next_run_str
        )

        # Add to APScheduler if running
        if self._running:
            try:
                self._add_job(schedule)
                logger.info(f"Created and activated schedule: {name} ({schedule_id})")
            except Exception as e:
                logger.error(f"Failed to activate schedule {schedule_id}: {e}")
                self.db.update_schedule_status(schedule_id, 'error')
                raise

        return schedule

    def _add_job(self, schedule: Dict[str, Any]):
        """Add a schedule to APScheduler.

        Args:
            schedule: Schedule dictionary from database
        """
        trigger = CronTrigger.from_crontab(schedule['cron_expression'])

        self.scheduler.add_job(
            func=self._execute_schedule,
            trigger=trigger,
            id=schedule['id'],
            name=schedule['name'],
            args=[schedule['id']],
            replace_existing=True
        )

    def _execute_schedule(self, schedule_id: str):
        """Execute a scheduled task.

        Args:
            schedule_id: ID of the schedule to execute
        """
        execution_id = None

        try:
            # Get schedule from database
            schedule = self.db.get_schedule(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found in database")
                return

            # Create execution record
            execution_id = self.db.create_execution(schedule_id, status='running')

            logger.info(f"Executing schedule: {schedule['name']} (execution #{execution_id})")

            # Execute the tool
            result = self._tool_executor(
                schedule['tool_name'],
                schedule['tool_inputs']
            )

            # Update execution with success
            self.db.update_execution(execution_id, status='success', result=result)

            # Update schedule last run time
            now = datetime.utcnow().isoformat()
            job = self.scheduler.get_job(schedule_id)
            next_run = job.next_run_time.isoformat() if job and job.next_run_time else None

            self.db.update_schedule_status(
                schedule_id,
                status='active',
                last_run=now,
                next_run=next_run
            )
            self.db.increment_run_count(schedule_id)

            logger.info(f"Schedule {schedule['name']} executed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Schedule execution failed: {error_msg}", exc_info=True)

            # Update execution with failure
            if execution_id:
                self.db.update_execution(execution_id, status='failed', error=error_msg)

            # Update schedule status to error
            self.db.update_schedule_status(schedule_id, status='error')

    def trigger_now(self, schedule_id: str) -> Dict[str, Any]:
        """Execute a schedule immediately (outside of its normal schedule).

        Args:
            schedule_id: ID of the schedule to execute

        Returns:
            Execution result dictionary

        Raises:
            ValueError: If schedule not found
        """
        schedule = self.db.get_schedule(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        # Execute synchronously
        execution_id = self.db.create_execution(schedule_id, status='running')

        try:
            logger.info(f"Manually triggering schedule: {schedule['name']}")

            result = self._tool_executor(
                schedule['tool_name'],
                schedule['tool_inputs']
            )

            self.db.update_execution(execution_id, status='success', result=result)
            logger.info(f"Manual execution successful: {schedule['name']}")

            return {
                'execution_id': execution_id,
                'status': 'success',
                'result': result
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Manual execution failed: {error_msg}", exc_info=True)
            self.db.update_execution(execution_id, status='failed', error=error_msg)

            return {
                'execution_id': execution_id,
                'status': 'failed',
                'error': error_msg
            }

    def pause_schedule(self, schedule_id: str):
        """Pause a schedule (stop it from running but keep it in database).

        Args:
            schedule_id: ID of the schedule to pause

        Raises:
            ValueError: If schedule not found
        """
        schedule = self.db.get_schedule(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        # Remove from APScheduler
        try:
            self.scheduler.remove_job(schedule_id)
        except JobLookupError:
            pass  # Job already removed

        # Update status in database
        self.db.update_schedule_status(schedule_id, 'paused')
        logger.info(f"Paused schedule: {schedule['name']}")

    def resume_schedule(self, schedule_id: str):
        """Resume a paused schedule.

        Args:
            schedule_id: ID of the schedule to resume

        Raises:
            ValueError: If schedule not found
        """
        schedule = self.db.get_schedule(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        # Add back to APScheduler
        self._add_job(schedule)

        # Update status in database
        self.db.update_schedule_status(schedule_id, 'active')
        logger.info(f"Resumed schedule: {schedule['name']}")

    def delete_schedule(self, schedule_id: str):
        """Delete a schedule permanently.

        Args:
            schedule_id: ID of the schedule to delete

        Raises:
            ValueError: If schedule not found
        """
        schedule = self.db.get_schedule(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        # Remove from APScheduler
        try:
            self.scheduler.remove_job(schedule_id)
        except JobLookupError:
            pass  # Job already removed

        # Delete from database
        self.db.delete_schedule(schedule_id)
        logger.info(f"Deleted schedule: {schedule['name']}")

    def list_schedules(self, status: Optional[str] = None) -> list:
        """List all schedules.

        Args:
            status: Optional status filter ('active', 'paused', 'error')

        Returns:
            List of schedule dictionaries
        """
        return self.db.list_schedules(status=status)

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific schedule by ID.

        Args:
            schedule_id: ID of the schedule

        Returns:
            Schedule dictionary or None if not found
        """
        return self.db.get_schedule(schedule_id)

    def get_execution_history(self, schedule_id: str, limit: int = 50) -> list:
        """Get execution history for a schedule.

        Args:
            schedule_id: ID of the schedule
            limit: Maximum number of results

        Returns:
            List of execution dictionaries
        """
        return self.db.get_execution_history(schedule_id, limit)

    @property
    def is_running(self) -> bool:
        """Check if the scheduler service is running."""
        return self._running
