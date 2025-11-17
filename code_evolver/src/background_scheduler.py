"""
Background Scheduler Loop.

Monitors scheduled tasks and executes them at the appropriate times
with low priority to avoid interfering with user workflows.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional

from .scheduled_tasks import get_global_task_manager, ScheduledTask
from .task_scheduler import get_global_scheduler, TaskPriority

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Background scheduler that monitors and executes scheduled tasks.

    Features:
    - Runs in a background thread
    - Checks for due tasks periodically
    - Executes tasks with LOW/BACKGROUND priority
    - Pauses when high-priority workflows are active
    - Tracks execution statistics
    """

    def __init__(
        self,
        check_interval_seconds: int = 30,
        max_concurrent_tasks: int = 1
    ):
        """
        Initialize background scheduler.

        Args:
            check_interval_seconds: How often to check for due tasks
            max_concurrent_tasks: Max concurrent background tasks
        """
        self.check_interval = check_interval_seconds
        self.max_concurrent = max_concurrent_tasks

        # Get managers
        self.task_manager = get_global_task_manager()
        self.scheduler = get_global_scheduler()

        # Background thread
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._shutdown_event = threading.Event()

        # Statistics
        self._stats = {
            'checks_performed': 0,
            'tasks_executed': 0,
            'tasks_failed': 0,
            'tasks_skipped_due_to_workflows': 0,
            'started_at': None
        }
        self._stats_lock = threading.Lock()

        # Currently executing task IDs
        self._executing_tasks = set()
        self._executing_lock = threading.Lock()

    def start(self):
        """Start the background scheduler."""
        if self._running:
            logger.warning("Background scheduler already running")
            return

        self._running = True
        self._shutdown_event.clear()

        # Start background thread
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            name="BackgroundScheduler",
            daemon=True
        )
        self._thread.start()

        with self._stats_lock:
            self._stats['started_at'] = datetime.now().isoformat()

        logger.info(
            f"Background scheduler started "
            f"(check interval: {self.check_interval}s)"
        )

    def stop(self, wait: bool = True, timeout: Optional[float] = None):
        """
        Stop the background scheduler.

        Args:
            wait: Wait for thread to finish
            timeout: Timeout for waiting (seconds)
        """
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        if wait and self._thread:
            self._thread.join(timeout=timeout)

        logger.info("Background scheduler stopped")

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        with self._stats_lock:
            stats = self._stats.copy()

        with self._executing_lock:
            stats['currently_executing'] = len(self._executing_tasks)

        return stats

    def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.debug("Background scheduler loop started")

        while self._running:
            try:
                # Wait for next check interval (or shutdown)
                if self._shutdown_event.wait(timeout=self.check_interval):
                    break  # Shutdown requested

                # Perform check
                self._check_and_execute_tasks()

                with self._stats_lock:
                    self._stats['checks_performed'] += 1

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(5)  # Back off on error

        logger.debug("Background scheduler loop stopped")

    def _check_and_execute_tasks(self):
        """Check for due tasks and execute them."""
        # Check if we have capacity
        with self._executing_lock:
            if len(self._executing_tasks) >= self.max_concurrent:
                logger.debug("Max concurrent background tasks reached, skipping check")
                return

        # Check if high-priority workflows are active
        if self.scheduler.has_active_workflows():
            logger.debug("Active workflows detected, pausing background task execution")
            with self._stats_lock:
                self._stats['tasks_skipped_due_to_workflows'] += 1
            return

        # Get tasks that are due
        due_tasks = self.task_manager.get_tasks_due_now(
            window_minutes=1  # Look 1 minute ahead
        )

        if not due_tasks:
            return

        logger.info(f"Found {len(due_tasks)} due tasks")

        # Execute each task
        for task in due_tasks:
            # Check if already executing
            with self._executing_lock:
                if task.task_id in self._executing_tasks:
                    continue

                if len(self._executing_tasks) >= self.max_concurrent:
                    break

                self._executing_tasks.add(task.task_id)

            # Submit task to scheduler with background priority
            try:
                self.scheduler.submit(
                    func=self._execute_scheduled_task,
                    args=(task,),
                    priority=TaskPriority.BACKGROUND,
                    name=f"scheduled_{task.name}",
                    metadata={
                        'type': 'scheduled_task',
                        'task_id': task.task_id,
                        'cron_expression': task.cron_expression
                    }
                )

                logger.info(
                    f"Submitted scheduled task: {task.name} "
                    f"(cron: {task.cron_expression})"
                )

            except Exception as e:
                logger.error(f"Failed to submit task {task.name}: {e}")
                with self._executing_lock:
                    self._executing_tasks.discard(task.task_id)

    def _execute_scheduled_task(self, task: ScheduledTask):
        """
        Execute a scheduled task.

        Args:
            task: Task to execute
        """
        logger.info(f"Executing scheduled task: {task.name}")

        try:
            # Execute task function
            if task.func:
                result = task.func(*task.args, **task.kwargs)
                result_str = str(result)[:500] if result else "Success"

                # Mark as successful
                self.task_manager.mark_task_run(
                    task_id=task.task_id,
                    success=True,
                    result=result_str
                )

                with self._stats_lock:
                    self._stats['tasks_executed'] += 1

                logger.info(f"Scheduled task completed: {task.name}")

            else:
                error_msg = f"No function defined for task {task.name}"
                logger.warning(error_msg)
                self.task_manager.mark_task_run(
                    task_id=task.task_id,
                    success=False,
                    error=error_msg
                )

                with self._stats_lock:
                    self._stats['tasks_failed'] += 1

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(
                f"Scheduled task failed: {task.name} - {error_msg}",
                exc_info=True
            )

            # Mark as failed
            self.task_manager.mark_task_run(
                task_id=task.task_id,
                success=False,
                error=error_msg
            )

            with self._stats_lock:
                self._stats['tasks_failed'] += 1

        finally:
            # Remove from executing set
            with self._executing_lock:
                self._executing_tasks.discard(task.task_id)


# Global instance
_global_background_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = threading.Lock()


def get_global_background_scheduler() -> BackgroundScheduler:
    """
    Get or create the global background scheduler.

    Returns:
        Global background scheduler instance
    """
    global _global_background_scheduler

    with _scheduler_lock:
        if _global_background_scheduler is None:
            _global_background_scheduler = BackgroundScheduler(
                check_interval_seconds=30,  # Check every 30 seconds
                max_concurrent_tasks=1  # Only run one background task at a time
            )

        return _global_background_scheduler


def start_background_scheduler():
    """Start the global background scheduler."""
    scheduler = get_global_background_scheduler()
    scheduler.start()


def stop_background_scheduler(wait: bool = True, timeout: Optional[float] = None):
    """
    Stop the global background scheduler.

    Args:
        wait: Wait for scheduler to finish
        timeout: Timeout for waiting (seconds)
    """
    global _global_background_scheduler

    if _global_background_scheduler:
        _global_background_scheduler.stop(wait=wait, timeout=timeout)
