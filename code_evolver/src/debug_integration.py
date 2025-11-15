"""
Debug Store Integration with Workflow Tracker

Automatically records workflow execution into the debug store for analysis.
Provides decorators and context managers for easy integration.
"""

import time
import functools
import inspect
import hashlib
from typing import Any, Callable, Dict, Optional
from pathlib import Path

from debug_store import DebugStore, DebugContext
from workflow_tracker import WorkflowTracker, WorkflowStep, StepStatus


class DebugIntegration:
    """
    Integrates debug store with workflow tracking.

    Usage:
        # Initialize
        integration = DebugIntegration(session_id="workflow_run_123")

        # Track workflow
        with integration.track_workflow(tracker):
            # Workflow execution happens here
            pass

        # Or use decorator
        @integration.track_function(context_type="tool")
        def my_function():
            pass

        # Analyze later
        analysis = integration.analyze("tool", "my_function")
    """

    def __init__(
        self,
        session_id: str,
        base_path: str = "debug_data",
        auto_sync_interval: int = 30,
        enable_code_snapshots: bool = True
    ):
        self.store = DebugStore(
            session_id=session_id,
            base_path=base_path,
            auto_sync_interval=auto_sync_interval
        )
        self.enable_code_snapshots = enable_code_snapshots
        self._workflow_stack = []  # Track nested workflows

    def track_workflow(self, tracker: WorkflowTracker):
        """
        Context manager to automatically track workflow execution in debug store.

        Usage:
            tracker = WorkflowTracker("my_workflow", "Does something")
            with integration.track_workflow(tracker):
                # Workflow steps happen here
                pass
        """
        return WorkflowDebugContext(self.store, tracker, self.enable_code_snapshots)

    def track_step(
        self,
        step: WorkflowStep,
        parent_workflow_id: Optional[str] = None,
        code_snapshot: Optional[str] = None,
        variant_id: Optional[str] = None
    ):
        """
        Context manager to track a single workflow step.

        Usage:
            step = WorkflowStep("step_1", "http_fetch", "Fetch data")
            with integration.track_step(step):
                # Step execution
                result = fetch_data()
                step.complete(result)
        """
        return StepDebugContext(
            self.store,
            step,
            parent_workflow_id,
            code_snapshot,
            variant_id
        )

    def track_function(
        self,
        context_type: str = "function",
        capture_args: bool = True,
        capture_result: bool = True,
        variant_id: Optional[str] = None
    ):
        """
        Decorator to automatically track function execution.

        Usage:
            @integration.track_function(context_type="tool")
            def my_tool(input_data):
                return process(input_data)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Prepare request data
                request_data = {}
                if capture_args:
                    # Get function signature
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    request_data = dict(bound_args.arguments)

                # Get code snapshot
                code_snapshot = None
                code_hash = None
                if self.enable_code_snapshots:
                    try:
                        code_snapshot = inspect.getsource(func)
                        code_hash = hashlib.md5(code_snapshot.encode()).hexdigest()
                    except (OSError, TypeError):
                        pass

                # Prepare context
                context_id = func.__name__
                context_name = func.__qualname__

                # Get parent context if in workflow
                parent_context = self._get_current_workflow_id()

                # Track execution
                start_time = time.time()
                error = None
                status = "success"
                response_data = {}

                try:
                    result = func(*args, **kwargs)

                    if capture_result:
                        # Try to serialize result
                        if isinstance(result, (str, int, float, bool, list, dict, type(None))):
                            response_data = {"result": result}
                        else:
                            response_data = {"result_type": type(result).__name__}

                    return result

                except Exception as e:
                    status = "error"
                    error = str(e)
                    raise

                finally:
                    duration_ms = (time.time() - start_time) * 1000

                    # Record in debug store
                    self.store.write_record(
                        context_type=context_type,
                        context_id=context_id,
                        context_name=context_name,
                        request_data=request_data,
                        response_data=response_data,
                        duration_ms=duration_ms,
                        status=status,
                        error=error,
                        parent_context=parent_context,
                        code_snapshot=code_snapshot,
                        code_hash=code_hash,
                        variant_id=variant_id
                    )

            return wrapper
        return decorator

    def _get_current_workflow_id(self) -> Optional[str]:
        """Get the current workflow ID from the stack"""
        return self._workflow_stack[-1] if self._workflow_stack else None

    def _push_workflow(self, workflow_id: str):
        """Push workflow onto stack"""
        self._workflow_stack.append(workflow_id)

    def _pop_workflow(self):
        """Pop workflow from stack"""
        if self._workflow_stack:
            self._workflow_stack.pop()

    def analyze(
        self,
        context_type: str,
        context_id: Optional[str] = None,
        output_path: Optional[str] = None,
        max_tokens: Optional[int] = 50000
    ) -> str:
        """
        Analyze debug data and export for LLM consumption.

        Args:
            context_type: Type of context to analyze
            context_id: Specific context ID (optional)
            output_path: If specified, write to file
            max_tokens: Token budget for output

        Returns:
            Markdown analysis
        """
        from debug_analyzer import DebugAnalyzer

        analyzer = DebugAnalyzer(self.store)
        package = analyzer.analyze_context(
            context_type=context_type,
            context_id=context_id,
            include_variants=True,
            max_samples=10
        )

        markdown = package.to_markdown(max_tokens=max_tokens)

        if output_path:
            analyzer.export_to_file(package, output_path, format="markdown", max_tokens=max_tokens)

        return markdown

    def get_optimization_candidates(self) -> list:
        """Get list of optimization candidates"""
        from debug_analyzer import DebugAnalyzer

        analyzer = DebugAnalyzer(self.store)
        return analyzer.get_optimization_candidates()

    def close(self):
        """Close the debug store"""
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class WorkflowDebugContext:
    """Context manager for tracking entire workflow"""

    def __init__(
        self,
        store: DebugStore,
        tracker: WorkflowTracker,
        enable_code_snapshots: bool = True
    ):
        self.store = store
        self.tracker = tracker
        self.enable_code_snapshots = enable_code_snapshots
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        # Record workflow summary
        workflow_data = {
            "workflow_id": self.tracker.workflow_id,
            "description": self.tracker.description,
            "total_steps": len(self.tracker.steps),
            "completed_steps": sum(1 for s in self.tracker.steps if s.status == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in self.tracker.steps if s.status == StepStatus.FAILED)
        }

        status = "success" if exc_type is None else "error"
        error = str(exc_val) if exc_val else None

        self.store.write_record(
            context_type="workflow",
            context_id=self.tracker.workflow_id,
            context_name=self.tracker.description,
            request_data={"context": self.tracker.context},
            response_data=workflow_data,
            duration_ms=duration_ms,
            status=status,
            error=error,
            metadata={"step_details": [s.to_dict() for s in self.tracker.steps]}
        )

        # Record individual steps
        for step in self.tracker.steps:
            step_status = "success" if step.status == StepStatus.COMPLETED else (
                "error" if step.status == StepStatus.FAILED else "skipped"
            )

            self.store.write_record(
                context_type="step",
                context_id=step.step_id,
                context_name=step.description,
                request_data=step.inputs,
                response_data={"output": step.output} if step.output else {},
                duration_ms=step.duration_ms,
                status=step_status,
                error=step.error,
                parent_context=self.tracker.workflow_id,
                metadata=step.metadata
            )

        return False  # Don't suppress exceptions


class StepDebugContext:
    """Context manager for tracking individual workflow steps"""

    def __init__(
        self,
        store: DebugStore,
        step: WorkflowStep,
        parent_workflow_id: Optional[str] = None,
        code_snapshot: Optional[str] = None,
        variant_id: Optional[str] = None
    ):
        self.store = store
        self.step = step
        self.parent_workflow_id = parent_workflow_id
        self.code_snapshot = code_snapshot
        self.variant_id = variant_id

    def __enter__(self):
        self.step.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self.step.status != StepStatus.FAILED:
            self.step.fail(str(exc_val))

        step_status = "success" if self.step.status == StepStatus.COMPLETED else (
            "error" if self.step.status == StepStatus.FAILED else "skipped"
        )

        code_hash = None
        if self.code_snapshot:
            code_hash = hashlib.md5(self.code_snapshot.encode()).hexdigest()

        self.store.write_record(
            context_type="step",
            context_id=self.step.step_id,
            context_name=self.step.description,
            request_data=self.step.inputs,
            response_data={"output": self.step.output} if self.step.output else {},
            duration_ms=self.step.duration_ms,
            status=step_status,
            error=self.step.error,
            parent_context=self.parent_workflow_id,
            metadata=self.step.metadata,
            code_snapshot=self.code_snapshot,
            code_hash=code_hash,
            variant_id=self.variant_id
        )

        return False  # Don't suppress exceptions


# Global integration instance for easy access
_global_integration: Optional[DebugIntegration] = None


def init_debug_integration(
    session_id: str,
    base_path: str = "debug_data",
    auto_sync_interval: int = 30
) -> DebugIntegration:
    """
    Initialize global debug integration.

    Usage:
        integration = init_debug_integration("my_session")

        @debug_track("tool")
        def my_function():
            pass
    """
    global _global_integration
    _global_integration = DebugIntegration(
        session_id=session_id,
        base_path=base_path,
        auto_sync_interval=auto_sync_interval
    )
    return _global_integration


def get_debug_integration() -> Optional[DebugIntegration]:
    """Get the global debug integration instance"""
    return _global_integration


def debug_track(
    context_type: str = "function",
    capture_args: bool = True,
    capture_result: bool = True,
    variant_id: Optional[str] = None
):
    """
    Convenience decorator using global integration.

    Usage:
        init_debug_integration("my_session")

        @debug_track("tool")
        def my_tool():
            pass
    """
    if _global_integration is None:
        raise RuntimeError("Debug integration not initialized. Call init_debug_integration() first.")

    return _global_integration.track_function(
        context_type=context_type,
        capture_args=capture_args,
        capture_result=capture_result,
        variant_id=variant_id
    )
