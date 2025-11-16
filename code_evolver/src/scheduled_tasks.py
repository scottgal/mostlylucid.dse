"""
Scheduled Tasks System with RAG Storage.

Provides cron-like scheduled task management with:
- Natural language to cron conversion
- RAG storage for task schedules with semantic search
- Last-run tracking and error handling
- Priority-aware execution (background priority)
"""
import json
import logging
import os
import threading
import time
import uuid
from croniter import croniter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """
    Represents a scheduled task.
    """
    task_id: str
    name: str
    description: str
    cron_expression: str
    func: Optional[Callable] = None
    func_name: Optional[str] = None  # For serialization
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_result: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int = 0
    error_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate cron expression."""
        if not self.task_id:
            self.task_id = f"sched_{uuid.uuid4().hex[:12]}"

        # Validate cron expression
        try:
            croniter(self.cron_expression)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{self.cron_expression}': {e}")

    def should_run_now(self, current_time: Optional[datetime] = None) -> bool:
        """
        Check if task should run now.

        Args:
            current_time: Current time (defaults to now)

        Returns:
            True if task should run
        """
        if not self.enabled:
            return False

        current_time = current_time or datetime.now()

        # Get next run time based on last run (or creation time)
        base_time = self.last_run or self.created_at
        cron = croniter(self.cron_expression, base_time)
        next_run = cron.get_next(datetime)

        # Should run if current time >= next run time
        return current_time >= next_run

    def get_next_run_time(self, base_time: Optional[datetime] = None) -> datetime:
        """
        Get next scheduled run time.

        Args:
            base_time: Base time (defaults to last_run or now)

        Returns:
            Next run time
        """
        base_time = base_time or self.last_run or datetime.now()
        cron = croniter(self.cron_expression, base_time)
        return cron.get_next(datetime)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'cron_expression': self.cron_expression,
            'func_name': self.func_name,
            'args': self.args,
            'kwargs': self.kwargs,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'last_result': self.last_result,
            'last_error': self.last_error,
            'run_count': self.run_count,
            'error_count': self.error_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledTask':
        """Create from dictionary."""
        return cls(
            task_id=data['task_id'],
            name=data['name'],
            description=data['description'],
            cron_expression=data['cron_expression'],
            func_name=data.get('func_name'),
            args=tuple(data.get('args', [])),
            kwargs=data.get('kwargs', {}),
            enabled=data.get('enabled', True),
            last_run=datetime.fromisoformat(data['last_run']) if data.get('last_run') else None,
            last_result=data.get('last_result'),
            last_error=data.get('last_error'),
            run_count=data.get('run_count', 0),
            error_count=data.get('error_count', 0),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {})
        )


class CronConverter:
    """
    Converts natural language time descriptions to cron expressions.

    Uses an LLM to parse English descriptions like "every sunday at noon"
    into cron expressions like "0 12 * * 0".
    """

    def __init__(self, llm_client=None, model: str = "llama3.2"):
        """
        Initialize cron converter.

        Args:
            llm_client: LLM client (uses Ollama by default)
            model: Model to use for conversion (medium-sized)
        """
        self.llm_client = llm_client
        self.model = model

    def english_to_cron(self, description: str) -> Tuple[str, str]:
        """
        Convert English description to cron expression.

        Args:
            description: Natural language description (e.g., "every sunday at noon")

        Returns:
            Tuple of (cron_expression, explanation)

        Raises:
            ValueError: If conversion fails
        """
        # Check for common patterns first (fast path)
        cron = self._check_common_patterns(description.lower())
        if cron:
            return cron, f"Common pattern: {description}"

        # Use LLM for complex descriptions
        if self.llm_client:
            return self._llm_convert(description)

        # Fallback: simple pattern matching
        return self._fallback_convert(description)

    def _check_common_patterns(self, description: str) -> Optional[str]:
        """Check for common cron patterns."""
        patterns = {
            'every minute': '* * * * *',
            'every hour': '0 * * * *',
            'every day': '0 0 * * *',
            'daily': '0 0 * * *',
            'every week': '0 0 * * 0',
            'weekly': '0 0 * * 0',
            'every month': '0 0 1 * *',
            'monthly': '0 0 1 * *',
            'every sunday': '0 0 * * 0',
            'every monday': '0 0 * * 1',
            'every tuesday': '0 0 * * 2',
            'every wednesday': '0 0 * * 3',
            'every thursday': '0 0 * * 4',
            'every friday': '0 0 * * 5',
            'every saturday': '0 0 * * 6',
        }

        # Check exact matches
        for pattern, cron in patterns.items():
            if pattern in description:
                # Check for time specifications
                if 'noon' in description or '12pm' in description:
                    return cron.replace('0 0', '0 12')
                elif 'midnight' in description or '12am' in description:
                    return cron
                elif description == pattern:
                    return cron

        return None

    def _llm_convert(self, description: str) -> Tuple[str, str]:
        """Use LLM to convert description to cron."""
        prompt = f"""Convert the following natural language time description to a cron expression.

Description: "{description}"

Respond ONLY with a JSON object in this exact format:
{{
  "cron": "the cron expression (5 fields: minute hour day month weekday)",
  "explanation": "brief explanation of when this runs"
}}

Cron format reminder:
- minute (0-59)
- hour (0-23)
- day of month (1-31)
- month (1-12)
- day of week (0-6, 0=Sunday)

Examples:
- "every day at 2pm" -> {{"cron": "0 14 * * *", "explanation": "Runs at 2pm every day"}}
- "every sunday at noon" -> {{"cron": "0 12 * * 0", "explanation": "Runs at noon every Sunday"}}
- "every 5 minutes" -> {{"cron": "*/5 * * * *", "explanation": "Runs every 5 minutes"}}

Now convert: "{description}"
"""

        try:
            response = self.llm_client.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.1}  # Low temperature for consistency
            )

            # Parse JSON response
            response_text = response.get('response', '').strip()

            # Extract JSON from response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                cron_expr = result['cron']
                explanation = result['explanation']

                # Validate cron expression
                croniter(cron_expr)

                return cron_expr, explanation
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            logger.warning(f"LLM cron conversion failed: {e}")
            return self._fallback_convert(description)

    def _fallback_convert(self, description: str) -> Tuple[str, str]:
        """Fallback conversion for simple patterns."""
        description = description.lower()

        # Try to extract time
        hour = 0
        if 'noon' in description or '12pm' in description:
            hour = 12
        elif 'midnight' in description or '12am' in description:
            hour = 0

        # Check for day of week
        days = {
            'sunday': 0, 'monday': 1, 'tuesday': 2, 'wednesday': 3,
            'thursday': 4, 'friday': 5, 'saturday': 6
        }

        for day_name, day_num in days.items():
            if day_name in description:
                cron = f"0 {hour} * * {day_num}"
                return cron, f"Runs at {hour}:00 every {day_name.capitalize()}"

        # Default to daily at specified hour
        cron = f"0 {hour} * * *"
        return cron, f"Runs daily at {hour}:00"


class ScheduledTaskManager:
    """
    Manages scheduled tasks with RAG storage.

    Features:
    - Store tasks in RAG with semantic search
    - Track execution history and errors
    - Query tasks by time windows using cron embeddings
    - Natural language schedule descriptions
    """

    def __init__(
        self,
        rag_memory=None,
        ollama_client=None,
        storage_path: str = "./data/scheduled_tasks"
    ):
        """
        Initialize scheduled task manager.

        Args:
            rag_memory: RAG memory instance for semantic storage
            ollama_client: Ollama client for embeddings and cron conversion
            storage_path: Path for task storage (JSON backup)
        """
        self.rag = rag_memory
        self.ollama_client = ollama_client
        self.storage_path = storage_path

        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)

        # Task registry (in-memory cache)
        self._tasks: Dict[str, ScheduledTask] = {}
        self._tasks_lock = threading.Lock()

        # Cron converter
        self.cron_converter = CronConverter(
            llm_client=ollama_client,
            model=os.getenv('CRON_CONVERTER_MODEL', 'llama3.2')
        )

        # Load tasks from storage
        self._load_tasks()

        logger.info(f"ScheduledTaskManager initialized with {len(self._tasks)} tasks")

    def create_task(
        self,
        name: str,
        description: str,
        schedule: str,
        func: Optional[Callable] = None,
        func_name: Optional[str] = None,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new scheduled task.

        Args:
            name: Task name
            description: Task description
            schedule: Cron expression OR natural language description
            func: Function to execute
            func_name: Function name (for persistence)
            args: Function arguments
            kwargs: Function keyword arguments
            metadata: Additional metadata

        Returns:
            Task ID

        Raises:
            ValueError: If schedule is invalid
        """
        kwargs = kwargs or {}
        metadata = metadata or {}

        # Convert schedule to cron if needed
        cron_expression = schedule
        if not self._is_valid_cron(schedule):
            cron_expression, explanation = self.cron_converter.english_to_cron(schedule)
            logger.info(f"Converted '{schedule}' to cron: {cron_expression} ({explanation})")
            metadata['schedule_description'] = schedule
            metadata['cron_explanation'] = explanation

        # Create task
        task = ScheduledTask(
            task_id=f"sched_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            cron_expression=cron_expression,
            func=func,
            func_name=func_name or (func.__name__ if func else None),
            args=args,
            kwargs=kwargs,
            metadata=metadata
        )

        # Store in registry
        with self._tasks_lock:
            self._tasks[task.task_id] = task

        # Store in RAG for semantic search
        if self.rag:
            self._store_task_in_rag(task)

        # Save to disk
        self._save_tasks()

        logger.info(f"Created scheduled task: {name} (cron: {cron_expression}, id: {task.task_id})")
        return task.task_id

    def get_tasks_due_now(
        self,
        current_time: Optional[datetime] = None,
        window_minutes: int = 0
    ) -> List[ScheduledTask]:
        """
        Get all tasks that should run now (or within a time window).

        Args:
            current_time: Current time (defaults to now)
            window_minutes: Look ahead window in minutes

        Returns:
            List of tasks that should run
        """
        current_time = current_time or datetime.now()
        end_time = current_time + timedelta(minutes=window_minutes)

        due_tasks = []
        with self._tasks_lock:
            for task in self._tasks.values():
                if not task.enabled:
                    continue

                # Check if task should run now
                if task.should_run_now(current_time):
                    due_tasks.append(task)
                    continue

                # If window specified, check if task will run within window
                if window_minutes > 0:
                    next_run = task.get_next_run_time()
                    if next_run <= end_time:
                        due_tasks.append(task)

        return due_tasks

    def mark_task_run(
        self,
        task_id: str,
        success: bool = True,
        result: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Mark a task as having run.

        Updates last_run timestamp and execution statistics.

        Args:
            task_id: Task ID
            success: Whether execution succeeded
            result: Execution result
            error: Error message if failed
        """
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Task not found: {task_id}")
                return

            task.last_run = datetime.now()
            task.run_count += 1
            task.updated_at = datetime.now()

            if success:
                task.last_result = result
                task.last_error = None
            else:
                task.last_error = error
                task.error_count += 1

            # Disable task if too many consecutive errors
            if task.error_count >= 5:
                logger.warning(f"Disabling task {task.name} after {task.error_count} errors")
                task.enabled = False

        # Update RAG entry
        if self.rag:
            self._update_task_in_rag(task)

        # Save to disk
        self._save_tasks()

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID."""
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def list_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """
        List all tasks.

        Args:
            enabled_only: Only return enabled tasks

        Returns:
            List of tasks
        """
        with self._tasks_lock:
            tasks = list(self._tasks.values())

        if enabled_only:
            tasks = [t for t in tasks if t.enabled]

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                return False

            del self._tasks[task_id]

        # Remove from RAG
        if self.rag:
            # RAG removal logic here
            pass

        # Save to disk
        self._save_tasks()

        logger.info(f"Deleted scheduled task: {task_id}")
        return True

    def _is_valid_cron(self, expression: str) -> bool:
        """Check if string is a valid cron expression."""
        try:
            croniter(expression)
            return True
        except:
            return False

    def _store_task_in_rag(self, task: ScheduledTask):
        """Store task in RAG with cron embedding."""
        if not self.rag:
            return

        try:
            # Create content for embedding
            # Include cron pattern in a way that can be semantically searched
            content = f"""
Task: {task.name}
Description: {task.description}
Schedule: {task.cron_expression}
Schedule Description: {task.metadata.get('schedule_description', 'cron expression')}
When: {task.metadata.get('cron_explanation', 'see cron expression')}
Next Run: {task.get_next_run_time().isoformat()}
"""

            # Store as a PLAN artifact (using existing RAG system)
            from .rag_memory import ArtifactType

            artifact_id = self.rag.store_artifact(
                artifact_type=ArtifactType.PLAN,
                name=task.name,
                description=task.description,
                content=content,
                tags=['scheduled_task', 'cron', task.cron_expression],
                metadata={
                    'task_id': task.task_id,
                    'cron_expression': task.cron_expression,
                    'next_run': task.get_next_run_time().isoformat(),
                    'enabled': task.enabled
                }
            )

            logger.debug(f"Stored task in RAG: {task.name} (artifact: {artifact_id})")

        except Exception as e:
            logger.warning(f"Failed to store task in RAG: {e}")

    def _update_task_in_rag(self, task: ScheduledTask):
        """Update task in RAG (re-store with updated info)."""
        self._store_task_in_rag(task)

    def _load_tasks(self):
        """Load tasks from disk storage."""
        tasks_file = os.path.join(self.storage_path, 'tasks.json')
        if not os.path.exists(tasks_file):
            return

        try:
            with open(tasks_file, 'r') as f:
                data = json.load(f)

            for task_data in data.get('tasks', []):
                task = ScheduledTask.from_dict(task_data)
                self._tasks[task.task_id] = task

            logger.info(f"Loaded {len(self._tasks)} scheduled tasks from disk")

        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

    def _save_tasks(self):
        """Save tasks to disk storage."""
        tasks_file = os.path.join(self.storage_path, 'tasks.json')

        try:
            with self._tasks_lock:
                data = {
                    'version': '1.0',
                    'updated_at': datetime.now().isoformat(),
                    'tasks': [task.to_dict() for task in self._tasks.values()]
                }

            with open(tasks_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")


# Global instance
_global_task_manager: Optional[ScheduledTaskManager] = None
_manager_lock = threading.Lock()


def get_global_task_manager() -> ScheduledTaskManager:
    """
    Get or create the global scheduled task manager.

    Returns:
        Global task manager instance
    """
    global _global_task_manager

    with _manager_lock:
        if _global_task_manager is None:
            # Initialize with RAG and Ollama if available
            try:
                from . import create_rag_memory, ConfigManager, OllamaClient

                config = ConfigManager()
                ollama = OllamaClient(config_manager=config)
                rag = create_rag_memory(config_manager=config, ollama_client=ollama)

                _global_task_manager = ScheduledTaskManager(
                    rag_memory=rag,
                    ollama_client=ollama
                )
            except Exception as e:
                logger.warning(f"Failed to initialize with RAG/Ollama: {e}")
                _global_task_manager = ScheduledTaskManager()

        return _global_task_manager
