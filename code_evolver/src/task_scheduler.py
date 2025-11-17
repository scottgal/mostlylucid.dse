"""
Task Scheduler with Priority Support.

Provides priority-aware task scheduling where workflows and builders
run at high priority, and background tasks (like scheduled jobs) run
at low priority without interfering with active user workflows.
"""
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from queue import PriorityQueue, Empty

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """
    Priority levels for task execution.

    Lower values = higher priority (executed first).
    """
    CRITICAL = 0  # System-critical tasks
    HIGH = 10      # User workflows, builders
    NORMAL = 50    # Regular operations
    LOW = 90       # Background tasks, scheduled jobs
    BACKGROUND = 100  # Lowest priority background operations


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class PrioritizedTask:
    """
    A task with priority for queue ordering.

    Tasks are ordered by:
    1. Priority (lower number = higher priority)
    2. Submission time (earlier = higher priority within same priority level)
    """
    priority: int = field(compare=True)
    submit_time: float = field(compare=True)
    task: 'Task' = field(compare=False)


@dataclass
class Task:
    """
    Represents a schedulable task.
    """
    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    submit_time: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Any = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize task."""
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:12]}"

    @property
    def duration_ms(self) -> Optional[float]:
        """Get task duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None


class PriorityTaskScheduler:
    """
    Priority-aware task scheduler.

    Features:
    - Multiple priority levels (HIGH for workflows, LOW for background)
    - Fair scheduling within priority levels
    - Thread-safe execution
    - Task cancellation support
    - Execution statistics and monitoring
    """

    def __init__(
        self,
        num_workers: int = 2,
        max_queue_size: int = 1000,
        background_throttle_ms: int = 100
    ):
        """
        Initialize task scheduler.

        Args:
            num_workers: Number of worker threads
            max_queue_size: Maximum task queue size
            background_throttle_ms: Minimum delay between background tasks (ms)
        """
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.background_throttle_ms = background_throttle_ms

        # Priority queue for tasks
        self._task_queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)

        # Task registry
        self._tasks: Dict[str, Task] = {}
        self._tasks_lock = threading.Lock()

        # Worker threads
        self._workers: List[threading.Thread] = []
        self._running = False
        self._shutdown_event = threading.Event()

        # Statistics
        self._stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'total_execution_time_ms': 0,
            'high_priority_tasks': 0,
            'low_priority_tasks': 0,
            'background_tasks': 0
        }
        self._stats_lock = threading.Lock()

        # Track active workflows (for priority boosting)
        self._active_workflows = set()
        self._workflows_lock = threading.Lock()

        # Last background task time (for throttling)
        self._last_background_task_time = 0
        self._background_lock = threading.Lock()

    def start(self):
        """Start the scheduler and worker threads."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._shutdown_event.clear()

        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskScheduler-Worker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)

        logger.info(f"Task scheduler started with {self.num_workers} workers")

    def stop(self, wait: bool = True, timeout: Optional[float] = None):
        """
        Stop the scheduler.

        Args:
            wait: Wait for workers to finish
            timeout: Timeout for waiting (seconds)
        """
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        if wait:
            for worker in self._workers:
                worker.join(timeout=timeout)

        self._workers.clear()
        logger.info("Task scheduler stopped")

    def submit(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit a task for execution.

        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Task priority
            name: Human-readable task name
            metadata: Additional task metadata

        Returns:
            Task ID

        Raises:
            RuntimeError: If scheduler not running or queue full
        """
        if not self._running:
            raise RuntimeError("Scheduler not running")

        kwargs = kwargs or {}
        metadata = metadata or {}

        # Create task
        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            status=TaskStatus.PENDING,
            metadata=metadata
        )

        # Register task
        with self._tasks_lock:
            self._tasks[task.task_id] = task

        # Create prioritized task for queue
        prioritized = PrioritizedTask(
            priority=priority.value,
            submit_time=time.time(),
            task=task
        )

        # Add to queue
        try:
            self._task_queue.put(prioritized, block=False)
            task.status = TaskStatus.QUEUED

            # Update statistics
            with self._stats_lock:
                self._stats['tasks_submitted'] += 1
                if priority == TaskPriority.HIGH:
                    self._stats['high_priority_tasks'] += 1
                elif priority == TaskPriority.LOW:
                    self._stats['low_priority_tasks'] += 1
                elif priority == TaskPriority.BACKGROUND:
                    self._stats['background_tasks'] += 1

            logger.debug(f"Task submitted: {task.name} (priority: {priority.name}, id: {task.task_id})")
            return task.task_id

        except Exception as e:
            with self._tasks_lock:
                del self._tasks[task.task_id]
            raise RuntimeError(f"Failed to queue task: {e}")

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled, False if already running/completed
        """
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED):
                task.status = TaskStatus.CANCELLED
                with self._stats_lock:
                    self._stats['tasks_cancelled'] += 1
                logger.info(f"Task cancelled: {task.name} (id: {task_id})")
                return True

        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.

        Returns:
            Statistics dictionary
        """
        with self._stats_lock:
            stats = self._stats.copy()

        with self._tasks_lock:
            stats['active_tasks'] = len([
                t for t in self._tasks.values()
                if t.status == TaskStatus.RUNNING
            ])
            stats['queued_tasks'] = len([
                t for t in self._tasks.values()
                if t.status == TaskStatus.QUEUED
            ])

        stats['queue_size'] = self._task_queue.qsize()
        stats['workers'] = len(self._workers)
        stats['running'] = self._running

        return stats

    def mark_workflow_active(self, workflow_id: str):
        """
        Mark a workflow as active (boosts task priorities).

        Args:
            workflow_id: Workflow ID
        """
        with self._workflows_lock:
            self._active_workflows.add(workflow_id)

    def mark_workflow_inactive(self, workflow_id: str):
        """
        Mark a workflow as inactive.

        Args:
            workflow_id: Workflow ID
        """
        with self._workflows_lock:
            self._active_workflows.discard(workflow_id)

    def has_active_workflows(self) -> bool:
        """
        Check if there are active workflows.

        Returns:
            True if any workflows are active
        """
        with self._workflows_lock:
            return len(self._active_workflows) > 0

    def _worker_loop(self):
        """Worker thread loop."""
        logger.debug(f"Worker {threading.current_thread().name} started")

        while self._running:
            try:
                # Get next task with timeout
                try:
                    prioritized = self._task_queue.get(timeout=0.5)
                except Empty:
                    continue

                task = prioritized.task

                # Check if cancelled
                if task.status == TaskStatus.CANCELLED:
                    self._task_queue.task_done()
                    continue

                # Throttle background tasks if workflows are active
                if task.priority == TaskPriority.BACKGROUND:
                    if self.has_active_workflows():
                        # Re-queue and yield to higher priority tasks
                        self._task_queue.put(prioritized)
                        self._task_queue.task_done()
                        time.sleep(0.1)
                        continue

                    # Apply throttling
                    with self._background_lock:
                        elapsed = (time.time() - self._last_background_task_time) * 1000
                        if elapsed < self.background_throttle_ms:
                            time.sleep((self.background_throttle_ms - elapsed) / 1000)

                # Execute task
                self._execute_task(task)

                # Update background task time
                if task.priority == TaskPriority.BACKGROUND:
                    with self._background_lock:
                        self._last_background_task_time = time.time()

                self._task_queue.task_done()

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

        logger.debug(f"Worker {threading.current_thread().name} stopped")

    def _execute_task(self, task: Task):
        """
        Execute a task.

        Args:
            task: Task to execute
        """
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()

        logger.debug(f"Executing task: {task.name} (priority: {task.priority.name})")

        try:
            # Execute function
            result = task.func(*task.args, **task.kwargs)

            # Mark success
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()

            # Update statistics
            with self._stats_lock:
                self._stats['tasks_completed'] += 1
                if task.duration_ms:
                    self._stats['total_execution_time_ms'] += task.duration_ms

            logger.debug(
                f"Task completed: {task.name} "
                f"(duration: {task.duration_ms:.1f}ms)"
            )

        except Exception as e:
            # Mark failure
            task.error = e
            task.status = TaskStatus.FAILED
            task.end_time = datetime.now()

            # Update statistics
            with self._stats_lock:
                self._stats['tasks_failed'] += 1

            logger.error(
                f"Task failed: {task.name} (error: {e})",
                exc_info=True
            )


# Global scheduler instance
_global_scheduler: Optional[PriorityTaskScheduler] = None
_scheduler_lock = threading.Lock()


def get_global_scheduler() -> PriorityTaskScheduler:
    """
    Get or create the global task scheduler.

    Returns:
        Global scheduler instance
    """
    global _global_scheduler

    with _scheduler_lock:
        if _global_scheduler is None:
            _global_scheduler = PriorityTaskScheduler(
                num_workers=2,
                background_throttle_ms=100
            )
            _global_scheduler.start()
            logger.info("Global task scheduler initialized")

        return _global_scheduler


def submit_task(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Submit a task to the global scheduler.

    Args:
        func: Function to execute
        args: Positional arguments
        kwargs: Keyword arguments
        priority: Task priority
        name: Human-readable task name
        metadata: Additional task metadata

    Returns:
        Task ID
    """
    scheduler = get_global_scheduler()
    return scheduler.submit(func, args, kwargs, priority, name, metadata)
