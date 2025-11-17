"""
Background Process Manager
Manages multiple background processes and coordinates with Sentinel AI for interrupt decisions.
"""
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from src.background_process import BackgroundProcess, ProcessStatus


class BackgroundProcessManager:
    """
    Manages multiple background processes.

    Features:
    - Start/stop processes
    - Track running processes
    - Query process status
    - Sentinel AI integration for interrupt decisions
    """

    def __init__(self, sentinel=None, max_concurrent: int = 3):
        """
        Initialize background process manager.

        Args:
            sentinel: SentinelLLM instance for interrupt decisions
            max_concurrent: Maximum number of concurrent processes
        """
        self.sentinel = sentinel
        self.max_concurrent = max_concurrent

        self.processes: Dict[str, BackgroundProcess] = {}
        self._lock = threading.Lock()
        self._next_id = 1

    def start_process(
        self,
        task_fn: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        description: str = "",
        process_id: Optional[str] = None
    ) -> str:
        """
        Start a background process.

        Args:
            task_fn: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            description: Process description
            process_id: Optional custom process ID

        Returns:
            Process ID

        Raises:
            RuntimeError: If max concurrent processes exceeded
        """
        with self._lock:
            # Check concurrent limit
            running_count = sum(
                1 for p in self.processes.values()
                if p.is_running()
            )

            if running_count >= self.max_concurrent:
                raise RuntimeError(
                    f"Maximum concurrent processes ({self.max_concurrent}) exceeded. "
                    f"Wait for some to complete or cancel them."
                )

            # Generate process ID
            if process_id is None:
                process_id = f"bg_{int(time.time())}_{self._next_id}"
                self._next_id += 1

            # Create and start process
            process = BackgroundProcess(
                process_id=process_id,
                task_fn=task_fn,
                args=args,
                kwargs=kwargs,
                description=description
            )

            self.processes[process_id] = process
            process.start()

            return process_id

    def get_process(self, process_id: str) -> Optional[BackgroundProcess]:
        """
        Get a process by ID.

        Args:
            process_id: Process ID

        Returns:
            BackgroundProcess or None if not found
        """
        with self._lock:
            return self.processes.get(process_id)

    def get_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get process status.

        Args:
            process_id: Process ID

        Returns:
            Status dict or None if not found
        """
        process = self.get_process(process_id)
        if process:
            return process.get_info()
        return None

    def get_running_processes(self) -> Dict[str, BackgroundProcess]:
        """
        Get all running processes.

        Returns:
            Dictionary of process_id -> BackgroundProcess
        """
        with self._lock:
            return {
                pid: proc for pid, proc in self.processes.items()
                if proc.is_running()
            }

    def get_all_processes(self) -> Dict[str, BackgroundProcess]:
        """
        Get all processes (running, completed, failed).

        Returns:
            Dictionary of process_id -> BackgroundProcess
        """
        with self._lock:
            return self.processes.copy()

    def has_running_processes(self) -> bool:
        """Check if any processes are currently running"""
        with self._lock:
            return any(p.is_running() for p in self.processes.values())

    def wait_for_process(self, process_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a specific process to complete.

        Args:
            process_id: Process ID
            timeout: Maximum time to wait

        Returns:
            True if completed, False if timeout or not found
        """
        process = self.get_process(process_id)
        if process is None:
            return False

        return process.wait(timeout=timeout)

    def wait_for_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all running processes to complete.

        Args:
            timeout: Maximum time to wait (total, not per-process)

        Returns:
            True if all completed, False if timeout
        """
        start_time = time.time()

        running = self.get_running_processes()

        for process_id, process in running.items():
            if timeout:
                elapsed = time.time() - start_time
                remaining = max(0, timeout - elapsed)

                if remaining <= 0:
                    return False

                if not process.wait(timeout=remaining):
                    return False
            else:
                process.wait()

        return True

    def cancel_process(self, process_id: str) -> bool:
        """
        Cancel a process.

        Args:
            process_id: Process ID

        Returns:
            True if cancelled, False if not found or already finished
        """
        process = self.get_process(process_id)
        if process is None:
            return False

        if not process.is_running():
            return False

        process.cancel()
        return True

    def cancel_all(self):
        """Cancel all running processes"""
        running = self.get_running_processes()

        for process_id in running.keys():
            self.cancel_process(process_id)

    def cleanup_finished(self, max_age_seconds: float = 3600):
        """
        Remove finished processes older than max_age.

        Args:
            max_age_seconds: Maximum age for finished processes
        """
        with self._lock:
            current_time = time.time()
            to_remove = []

            for process_id, process in self.processes.items():
                if not process.is_running():
                    if process.end_time and (current_time - process.end_time) > max_age_seconds:
                        to_remove.append(process_id)

            for process_id in to_remove:
                del self.processes[process_id]

    def get_new_status_updates(self) -> Dict[str, List[Any]]:
        """
        Get new status updates from all processes.

        Returns:
            Dictionary of process_id -> list of new updates
        """
        updates = {}

        with self._lock:
            for process_id, process in self.processes.items():
                new_updates = process.get_new_status_updates()
                if new_updates:
                    updates[process_id] = new_updates

        return updates

    def should_interrupt(self, user_input: str) -> Optional[str]:
        """
        Ask sentinel AI if user input should interrupt any background process.

        Args:
            user_input: User's command/question

        Returns:
            Process ID to interrupt, or None
        """
        if not self.sentinel:
            return None

        running = self.get_running_processes()

        if not running:
            return None

        # Check each running process
        for process_id, process in running.items():
            process_info = process.get_info()

            decision = self.sentinel.should_interrupt_background_process(
                process_info,
                user_input
            )

            if decision.get('should_interrupt', False):
                return process_id

        return None

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all processes.

        Returns:
            Summary statistics
        """
        with self._lock:
            total = len(self.processes)
            running = sum(1 for p in self.processes.values() if p.is_running())
            completed = sum(1 for p in self.processes.values() if p.is_complete())
            failed = sum(1 for p in self.processes.values() if p.is_failed())
            cancelled = sum(1 for p in self.processes.values() if p.status == ProcessStatus.CANCELLED)

            return {
                'total': total,
                'running': running,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled,
                'pending': total - running - completed - failed - cancelled
            }

    def __repr__(self) -> str:
        summary = self.get_summary()
        return (
            f"BackgroundProcessManager("
            f"total={summary['total']}, "
            f"running={summary['running']}, "
            f"completed={summary['completed']}"
            f")"
        )
