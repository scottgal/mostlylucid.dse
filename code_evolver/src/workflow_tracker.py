"""
Workflow tracking and visualization for multi-step AI workflows.
Tracks tool invocations, timing, and displays progress in real-time.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep:
    """Represents a single step in a workflow."""

    def __init__(
        self,
        step_id: str,
        tool_name: str,
        description: str,
        inputs: Optional[Dict[str, Any]] = None
    ):
        self.step_id = step_id
        self.tool_name = tool_name
        # Truncate long descriptions for display (keep full version in metadata)
        if len(description) > 100:
            self.description = description[:97] + "..."
            self.full_description = description
        else:
            self.description = description
            self.full_description = description
        self.inputs = inputs or {}
        self.status = StepStatus.PENDING
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.output: Optional[str] = None
        self.error: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def start(self):
        """Mark step as started."""
        self.status = StepStatus.RUNNING
        self.start_time = time.time()

    def complete(self, output: str, metadata: Optional[Dict[str, Any]] = None):
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.end_time = time.time()
        self.output = output
        if metadata:
            self.metadata.update(metadata)

    def fail(self, error: str):
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.end_time = time.time()
        self.error = error

    def skip(self, reason: str):
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED
        self.metadata["skip_reason"] = reason

    @property
    def duration_ms(self) -> int:
        """Get step duration in milliseconds."""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "output_length": len(self.output) if self.output else 0,
            "error": self.error,
            "metadata": self.metadata
        }


class WorkflowTracker:
    """Tracks multi-step workflow execution."""

    def __init__(
        self,
        workflow_id: str,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ):
        self.workflow_id = workflow_id
        self.description = description
        self.context = context or {}
        self.steps: List[WorkflowStep] = []
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.current_step: Optional[WorkflowStep] = None

        # Track workflow start in BugCatcher
        self._track_workflow_start()

    def add_step(
        self,
        step_id: str,
        tool_name: str,
        description: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> WorkflowStep:
        """Add a new step to the workflow."""
        step = WorkflowStep(step_id, tool_name, description, inputs)
        self.steps.append(step)

        # Track step addition in BugCatcher
        self._track_step_added(step)

        return step

    def start_step(self, step_id: str) -> WorkflowStep:
        """Start executing a step."""
        step = self.get_step(step_id)
        if step:
            step.start()
            self.current_step = step

            # Track step start in BugCatcher
            self._track_step_start(step)

        return step

    def complete_step(
        self,
        step_id: str,
        output: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Mark a step as completed."""
        step = self.get_step(step_id)
        if step:
            step.complete(output, metadata)
            if self.current_step == step:
                self.current_step = None

            # Track step completion in BugCatcher
            self._track_step_complete(step)

    def fail_step(self, step_id: str, error: str):
        """Mark a step as failed."""
        step = self.get_step(step_id)
        if step:
            step.fail(error)
            if self.current_step == step:
                self.current_step = None

            # Track step failure in BugCatcher
            self._track_step_failure(step)

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def finish(self):
        """Mark workflow as finished."""
        self.end_time = time.time()

    @property
    def total_duration_ms(self) -> int:
        """Get total workflow duration in milliseconds."""
        end = self.end_time or time.time()
        return int((end - self.start_time) * 1000)

    @property
    def completed_steps(self) -> int:
        """Count completed steps."""
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def failed_steps(self) -> int:
        """Count failed steps."""
        return sum(1 for s in self.steps if s.status == StepStatus.FAILED)

    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return all(
            s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED]
            for s in self.steps
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary."""
        return {
            "workflow_id": self.workflow_id,
            "description": self.description,
            "context": self.context,
            "total_steps": len(self.steps),
            "completed": self.completed_steps,
            "failed": self.failed_steps,
            "duration_ms": self.total_duration_ms,
            "is_complete": self.is_complete,
            "steps": [s.to_dict() for s in self.steps]
        }

    def format_text_display(self) -> str:
        """Format workflow as text display."""
        lines = []
        lines.append(f"Workflow: {self.description}")
        lines.append(f"ID: {self.workflow_id}")

        # Workflow chain visualization (completed steps only)
        completed = [s for s in self.steps if s.status == StepStatus.COMPLETED]
        if completed:
            # Extract tool names, truncate if too long
            tool_names = []
            for step in completed:
                tool_name = step.tool_name
                # Shorten common prefixes
                if tool_name.startswith("llm: "):
                    tool_name = tool_name[5:]  # Remove "llm: " prefix
                elif tool_name.startswith("test: "):
                    tool_name = tool_name[6:]  # Remove "test: " prefix
                elif tool_name.startswith("rag: "):
                    tool_name = tool_name[5:]  # Remove "rag: " prefix
                elif tool_name.startswith("optimize: "):
                    tool_name = tool_name[10:]  # Remove "optimize: " prefix
                elif tool_name.startswith("run: "):
                    tool_name = tool_name[5:]  # Remove "run: " prefix

                # Truncate long tool names
                if len(tool_name) > 25:
                    tool_name = tool_name[:22] + "..."

                tool_names.append(tool_name)

            # Create chain visualization
            chain = " -> ".join(tool_names)
            lines.append(f"\nWorkflow Chain:")
            lines.append(f"  {chain}")

        # Context
        if self.context:
            lines.append("\nContext:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")

        # Steps
        lines.append(f"\nSteps ({self.completed_steps}/{len(self.steps)} completed):")
        for i, step in enumerate(self.steps, 1):
            status_symbol = {
                StepStatus.PENDING: "[ ]",
                StepStatus.RUNNING: "[>]",
                StepStatus.COMPLETED: "[OK]",
                StepStatus.FAILED: "[FAIL]",
                StepStatus.SKIPPED: "[-]"
            }.get(step.status, "[?]")

            duration_str = f"{step.duration_ms}ms" if step.duration_ms > 0 else ""
            lines.append(f"  {i}. {status_symbol} {step.tool_name}: {step.description} {duration_str}")

            if step.error:
                lines.append(f"      Error: {step.error[:100]}")

        # Total time
        lines.append(f"\nTotal time: {self.total_duration_ms}ms")

        return "\n".join(lines)

    # =========================================================================
    # BugCatcher Integration Methods
    # =========================================================================

    def _get_bugcatcher(self):
        """Get BugCatcher instance if available."""
        try:
            from .bugcatcher import get_bugcatcher
            return get_bugcatcher()
        except (ImportError, Exception) as e:
            # BugCatcher not available or disabled
            logger.debug(f"BugCatcher not available: {e}")
            return None

    def _track_workflow_start(self):
        """Track workflow start in BugCatcher."""
        bugcatcher = self._get_bugcatcher()
        if bugcatcher:
            bugcatcher.track_request(
                self.workflow_id,
                {
                    'workflow_id': self.workflow_id,
                    'description': self.description,
                    'context': self.context,
                    'event': 'workflow_start',
                    'timestamp': datetime.now().isoformat()
                }
            )

    def _track_step_added(self, step: WorkflowStep):
        """Track step addition in BugCatcher."""
        bugcatcher = self._get_bugcatcher()
        if bugcatcher:
            request_id = f"{self.workflow_id}:{step.step_id}"
            bugcatcher.track_request(
                request_id,
                {
                    'workflow_id': self.workflow_id,
                    'step_id': step.step_id,
                    'tool_name': step.tool_name,
                    'description': step.description,
                    'event': 'step_added',
                    'timestamp': datetime.now().isoformat()
                }
            )

    def _track_step_start(self, step: WorkflowStep):
        """Track step start in BugCatcher."""
        bugcatcher = self._get_bugcatcher()
        if bugcatcher:
            request_id = f"{self.workflow_id}:{step.step_id}"
            bugcatcher.track_request(
                request_id,
                {
                    'workflow_id': self.workflow_id,
                    'step_id': step.step_id,
                    'tool_name': step.tool_name,
                    'description': step.description,
                    'event': 'step_start',
                    'timestamp': datetime.now().isoformat()
                }
            )

    def _track_step_complete(self, step: WorkflowStep):
        """Track step completion in BugCatcher."""
        # Track output for correlation with future exceptions
        bugcatcher = self._get_bugcatcher()
        if bugcatcher and step.output:
            request_id = f"{self.workflow_id}:{step.step_id}"
            bugcatcher.track_output(
                request_id,
                step.output,
                output_type='step_output'
            )

    def _track_step_failure(self, step: WorkflowStep):
        """Track step failure in BugCatcher."""
        bugcatcher = self._get_bugcatcher()
        if bugcatcher and step.error:
            # Create a synthetic exception for the failure
            try:
                raise RuntimeError(step.error)
            except RuntimeError as e:
                request_id = f"{self.workflow_id}:{step.step_id}"
                bugcatcher.capture_exception(
                    e,
                    request_id=request_id,
                    additional_context={
                        'workflow_id': self.workflow_id,
                        'step_id': step.step_id,
                        'tool_name': step.tool_name,
                        'description': step.description,
                        'duration_ms': step.duration_ms,
                        'event': 'step_failure'
                    }
                )
