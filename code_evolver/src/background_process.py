"""
Background Process
Represents a long-running task that runs in a background thread.
"""
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ProcessStatus(Enum):
    """Status of a background process"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StatusUpdate:
    """A status update from a background process"""
    timestamp: float
    message: str
    progress: float  # 0.0 to 1.0
    details: Optional[Dict[str, Any]] = None


class BackgroundProcess:
    """
    Represents a background process running in a thread.

    Features:
    - Thread-based execution
    - Progress tracking
    - Status updates
    - Cancellation support
    - Result/error capture
    """

    def __init__(
        self,
        process_id: str,
        task_fn: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        description: str = ""
    ):
        """
        Initialize background process.

        Args:
            process_id: Unique identifier
            task_fn: Function to execute
            args: Positional arguments for task_fn
            kwargs: Keyword arguments for task_fn
            description: Human-readable description
        """
        self.process_id = process_id
        self.task_fn = task_fn
        self.args = args
        self.kwargs = kwargs or {}
        self.description = description

        # Status
        self.status = ProcessStatus.PENDING
        self.progress = 0.0
        self.result = None
        self.error = None

        # Thread
        self.thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()

        # Timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Status updates
        self.status_updates: List[StatusUpdate] = []
        self._status_lock = threading.Lock()
        self._unread_updates: List[StatusUpdate] = []

    def start(self):
        """Start the background process in a thread"""
        if self.status != ProcessStatus.PENDING:
            raise RuntimeError(f"Cannot start process in state: {self.status}")

        self.status = ProcessStatus.RUNNING
        self.start_time = time.time()

        self.thread = threading.Thread(
            target=self._run,
            name=f"BackgroundProcess-{self.process_id}",
            daemon=True
        )
        self.thread.start()

    def _run(self):
        """Internal: Execute the task function"""
        try:
            # Inject process reference into kwargs if needed
            if 'process' in self.kwargs or 'background_process' in self.kwargs:
                self.kwargs['background_process'] = self

            # Run task
            self.result = self.task_fn(*self.args, **self.kwargs)

            # Check if cancelled during execution
            if self._cancel_event.is_set():
                self.status = ProcessStatus.CANCELLED
                self.update_status("Cancelled", 1.0)
            else:
                self.status = ProcessStatus.COMPLETED
                self.progress = 1.0
                self.update_status("Completed successfully", 1.0)

        except Exception as e:
            self.status = ProcessStatus.FAILED
            self.error = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            self.update_status(f"Failed: {str(e)}", self.progress)

        finally:
            self.end_time = time.time()

    def update_status(self, message: str, progress: float, details: Optional[Dict[str, Any]] = None):
        """
        Update process status.

        Args:
            message: Status message
            progress: Progress from 0.0 to 1.0
            details: Optional additional details
        """
        with self._status_lock:
            self.progress = max(0.0, min(1.0, progress))  # Clamp to [0, 1]

            update = StatusUpdate(
                timestamp=time.time(),
                message=message,
                progress=progress,
                details=details
            )

            self.status_updates.append(update)
            self._unread_updates.append(update)

    def get_new_status_updates(self) -> List[StatusUpdate]:
        """
        Get new status updates since last check.

        Returns:
            List of unread status updates
        """
        with self._status_lock:
            updates = self._unread_updates.copy()
            self._unread_updates.clear()
            return updates

    def get_all_status_updates(self) -> List[StatusUpdate]:
        """
        Get all status updates.

        Returns:
            List of all status updates
        """
        with self._status_lock:
            return self.status_updates.copy()

    def cancel(self):
        """Request cancellation of the process"""
        if self.status == ProcessStatus.RUNNING:
            self._cancel_event.set()
            self.update_status("Cancellation requested", self.progress)

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested"""
        return self._cancel_event.is_set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for process to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if completed, False if timeout
        """
        if self.thread is None:
            return True

        self.thread.join(timeout=timeout)
        return not self.thread.is_alive()

    def is_running(self) -> bool:
        """Check if process is currently running"""
        return self.status == ProcessStatus.RUNNING

    def is_complete(self) -> bool:
        """Check if process completed successfully"""
        return self.status == ProcessStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if process failed"""
        return self.status == ProcessStatus.FAILED

    def get_duration(self) -> Optional[float]:
        """Get process duration in seconds"""
        if self.start_time is None:
            return None

        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    def get_info(self) -> Dict[str, Any]:
        """
        Get process information.

        Returns:
            Dictionary with process details
        """
        latest_update = None
        if self.status_updates:
            latest_update = self.status_updates[-1]

        return {
            'process_id': self.process_id,
            'description': self.description,
            'status': self.status.value,
            'progress': self.progress,
            'progress_percent': int(self.progress * 100),
            'result': self.result,
            'error': self.error,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.get_duration(),
            'latest_update': {
                'message': latest_update.message,
                'timestamp': latest_update.timestamp,
                'progress': latest_update.progress
            } if latest_update else None,
            'update_count': len(self.status_updates)
        }

    def __repr__(self) -> str:
        return (
            f"BackgroundProcess(id={self.process_id}, "
            f"status={self.status.value}, "
            f"progress={self.progress:.0%})"
        )
