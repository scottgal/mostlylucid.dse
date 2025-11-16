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
        window_minutes: int = 0,
        use_rag_hint: bool = True
    ) -> List[ScheduledTask]:
        """
        Get all tasks that should run now (or within a time window).

        Can optionally use RAG semantic search as a hint to narrow down
        candidates before checking exact cron times.

        Args:
            current_time: Current time (defaults to now)
            window_minutes: Look ahead window in minutes
            use_rag_hint: Use RAG to find candidate tasks (faster for large task sets)

        Returns:
            List of tasks that should run
        """
        current_time = current_time or datetime.now()
        end_time = current_time + timedelta(minutes=window_minutes)

        # Optional: Use RAG to find candidates based on semantic time hints
        candidate_tasks = None
        if use_rag_hint and self.rag and window_minutes > 0:
            candidate_tasks = self._find_tasks_by_time_window_rag(
                current_time,
                window_minutes
            )

        # Check all tasks (or just candidates from RAG)
        due_tasks = []
        with self._tasks_lock:
            tasks_to_check = candidate_tasks if candidate_tasks else self._tasks.values()

            for task in tasks_to_check:
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

    def search_tasks(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ScheduledTask]:
        """
        Search for tasks using semantic RAG search.

        Args:
            query: Natural language query (e.g., "weekly reports", "morning tasks")
            filters: Optional filters (group, frequency, time_of_day)

        Returns:
            List of matching tasks

        Examples:
            - search_tasks("weekly reports")
            - search_tasks("backup jobs", {"time_of_day": "night"})
            - search_tasks("monitoring tasks", {"frequency": "every_5_minutes"})
        """
        if not self.rag:
            logger.warning("RAG not available, falling back to simple search")
            return self._simple_search(query, filters)

        try:
            from .rag_memory import ArtifactType

            # Build tag filters
            tags = ['scheduled_task']
            if filters:
                if 'group' in filters:
                    tags.append(filters['group'])
                if 'frequency' in filters:
                    tags.append(filters['frequency'])
                if 'time_of_day' in filters:
                    tags.append(filters['time_of_day'])

            # Search RAG
            similar = self.rag.find_similar(
                artifact_type=ArtifactType.PLAN,
                query=query,
                tags=tags if len(tags) > 1 else ['scheduled_task'],
                limit=20,
                min_similarity=0.3
            )

            # Extract task IDs from RAG results
            task_ids = []
            for artifact in similar:
                task_id = artifact.get('metadata', {}).get('task_id')
                if task_id:
                    task_ids.append(task_id)

            # Get actual tasks
            tasks = []
            with self._tasks_lock:
                for task_id in task_ids:
                    task = self._tasks.get(task_id)
                    if task:
                        tasks.append(task)

            return tasks

        except Exception as e:
            logger.warning(f"RAG search failed: {e}, falling back to simple search")
            return self._simple_search(query, filters)

    def _find_tasks_by_time_window_rag(
        self,
        current_time: datetime,
        window_minutes: int
    ) -> List[ScheduledTask]:
        """
        Use RAG to find tasks likely to run in the time window.

        This is a hint/optimization - still need to check exact cron times.
        """
        if not self.rag:
            return list(self._tasks.values())

        try:
            # Determine time of day for semantic search
            hour = current_time.hour
            if 0 <= hour < 6:
                time_hint = "night"
            elif 6 <= hour < 12:
                time_hint = "morning"
            elif 12 <= hour < 18:
                time_hint = "afternoon"
            else:
                time_hint = "evening"

            # Get day name
            day_name = current_time.strftime("%A")

            # Search for tasks matching this time window
            query = f"tasks running in the {time_hint} on {day_name}"

            # Use semantic search to find candidates
            candidates = self.search_tasks(
                query,
                filters={"time_of_day": time_hint}
            )

            # Also include tasks that run very frequently (every minute, every 5 minutes)
            frequent = self.search_tasks(
                "frequent monitoring polling tasks",
                filters={"frequency": "every_5_minutes"}
            )

            # Combine and deduplicate
            all_candidates = {t.task_id: t for t in candidates + frequent}
            return list(all_candidates.values())

        except Exception as e:
            logger.warning(f"RAG time window search failed: {e}")
            return list(self._tasks.values())

    def _simple_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ScheduledTask]:
        """Simple keyword-based search fallback."""
        query_lower = query.lower()
        results = []

        with self._tasks_lock:
            for task in self._tasks.values():
                # Check name and description
                if query_lower in task.name.lower() or query_lower in task.description.lower():
                    results.append(task)
                    continue

                # Check filters
                if filters:
                    matches = True
                    for key, value in filters.items():
                        if key in task.metadata and task.metadata[key] != value:
                            matches = False
                            break
                    if matches:
                        results.append(task)

        return results

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

    def query_tasks_natural_language(
        self,
        query: str,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Query tasks using natural language.

        This is a high-level interface that:
        1. Parses the natural language query into structured filters
        2. Searches RAG for matching tasks
        3. If time window specified, also checks for tasks due in that window

        Args:
            query: Natural language query
            current_time: Reference time (defaults to now)

        Returns:
            Dict with parsed query, matched tasks, and due tasks

        Examples:
            - query_tasks_natural_language("backup jobs running tonight")
            - query_tasks_natural_language("all tasks in the next 3 hours")
            - query_tasks_natural_language("weekly reports on monday morning")
        """
        from tools.executable.cron_querier import query_scheduled_tasks

        current_time = current_time or datetime.now()

        # Parse the query
        parsed = query_scheduled_tasks(
            query,
            current_time=current_time.isoformat(),
            llm_client=self.ollama_client
        )

        # Search for matching tasks
        matched_tasks = []
        if parsed.get('filters') or parsed.get('search_query'):
            matched_tasks = self.search_tasks(
                parsed['search_query'],
                parsed.get('filters')
            )

        # Get tasks due in time window if specified
        due_tasks = []
        if parsed.get('time_window'):
            window_minutes = parsed['time_window']['window_minutes']
            due_tasks = self.get_tasks_due_now(
                current_time=current_time,
                window_minutes=window_minutes
            )

        # Combine and deduplicate
        if due_tasks and matched_tasks:
            # Intersection: tasks that match filters AND are due
            task_ids_matched = {t.task_id for t in matched_tasks}
            combined = [t for t in due_tasks if t.task_id in task_ids_matched]
        elif due_tasks:
            combined = due_tasks
        else:
            combined = matched_tasks

        return {
            'query': query,
            'parsed': parsed,
            'matched_tasks': matched_tasks,
            'due_tasks': due_tasks,
            'combined_results': combined,
            'result_count': len(combined)
        }

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
        """Store task in RAG with rich cron embedding."""
        if not self.rag:
            return

        try:
            # Deconstruct cron expression for rich semantic embedding
            from tools.executable.cron_deconstructor import deconstruct_cron

            cron_meta = deconstruct_cron(
                cron_expression=task.cron_expression,
                tool_name=task.func_name,
                description=task.description,
                metadata=task.metadata,
                llm_client=self.ollama_client
            )

            # Create rich content for embedding combining all semantic fields
            # This format makes semantic search much more effective
            content_parts = [
                f"Task: {task.name}",
                f"Description: {cron_meta['description']}",
                f"Tool: {cron_meta['tool']}",
                f"Group: {cron_meta['group']}",
                f"Frequency: {cron_meta['frequency']}",
            ]

            if cron_meta['time_of_day']:
                content_parts.append(f"Time of Day: {cron_meta['time_of_day']}")

            if cron_meta['day_names']:
                content_parts.append(f"Days: {', '.join(cron_meta['day_names'])}")

            content_parts.append(f"Cron: {task.cron_expression}")
            content_parts.append(f"Next Runs: {', '.join(cron_meta['next_runs'][:2])}")

            # Add semantic tags for better embedding
            if cron_meta['semantic_tags']:
                content_parts.append(f"Tags: {', '.join(cron_meta['semantic_tags'])}")

            content = "\n".join(content_parts)

            # Store as a PLAN artifact (using existing RAG system)
            from .rag_memory import ArtifactType

            # Enhanced tags including semantic tags
            tags = ['scheduled_task', cron_meta['frequency'], cron_meta['group']]
            if cron_meta['time_of_day']:
                tags.append(cron_meta['time_of_day'])
            tags.extend(cron_meta['semantic_tags'][:5])  # Top 5 semantic tags
            tags.append(f"cron_{task.cron_expression}")

            # Enhanced metadata with cron deconstruction
            metadata = {
                'task_id': task.task_id,
                'cron_expression': task.cron_expression,
                'cron_metadata': cron_meta,  # Full deconstructed data
                'next_run': task.get_next_run_time().isoformat(),
                'enabled': task.enabled,
                'group': cron_meta['group'],
                'frequency': cron_meta['frequency'],
                'time_of_day': cron_meta['time_of_day']
            }

            artifact_id = self.rag.store_artifact(
                artifact_type=ArtifactType.PLAN,
                name=task.name,
                description=cron_meta['description'],  # Use generated description
                content=content,
                tags=tags,
                metadata=metadata
            )

            logger.debug(
                f"Stored task in RAG: {task.name} "
                f"(artifact: {artifact_id}, group: {cron_meta['group']}, "
                f"frequency: {cron_meta['frequency']})"
            )

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
