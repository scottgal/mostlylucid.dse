"""
BugCatcher Tool Wrapper - Wrap any tool call with exception monitoring.

This module provides decorators and wrappers to add BugCatcher monitoring
to any tool execution. Marked as 'debug' level for use in workflow debugging
and evolution.
"""
import logging
import functools
import time
from typing import Any, Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def with_bugcatcher(
    tool_name: str,
    debug_level: bool = True,
    capture_inputs: bool = True,
    capture_outputs: bool = True
):
    """
    Decorator to wrap a tool function with BugCatcher monitoring.

    This captures:
    - Tool inputs (if enabled)
    - Tool outputs (if enabled)
    - Execution time
    - Any exceptions raised

    Args:
        tool_name: Name of the tool being wrapped
        debug_level: Mark as debug level (for evolution/debugging)
        capture_inputs: Whether to capture input arguments
        capture_outputs: Whether to capture output values

    Returns:
        Decorated function

    Usage:
        @with_bugcatcher('my_tool', debug_level=True)
        def my_tool(arg1, arg2):
            return do_something(arg1, arg2)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get BugCatcher instance
            try:
                from .bugcatcher import get_bugcatcher
                bugcatcher = get_bugcatcher()
            except (ImportError, Exception) as e:
                logger.debug(f"BugCatcher not available: {e}")
                # Execute without monitoring
                return func(*args, **kwargs)

            # Generate request ID
            request_id = f"{tool_name}_{int(time.time() * 1000)}"

            # Build context
            context = {
                'tool_name': tool_name,
                'debug_level': debug_level,
                'timestamp': datetime.now().isoformat()
            }

            # Capture inputs if enabled
            if capture_inputs:
                try:
                    context['inputs'] = {
                        'args': str(args)[:500],  # Truncate to prevent huge logs
                        'kwargs': str(kwargs)[:500]
                    }
                except Exception as e:
                    logger.debug(f"Failed to capture inputs: {e}")

            # Track request
            bugcatcher.track_request(request_id, context)

            # Execute tool
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Track output if enabled
                if capture_outputs:
                    bugcatcher.track_output(
                        request_id,
                        result,
                        output_type='tool_result'
                    )

                # Update context with success
                context['duration_ms'] = duration_ms
                context['status'] = 'success'
                bugcatcher.track_request(request_id, context)

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                # Capture exception with full context
                bugcatcher.capture_exception(
                    e,
                    request_id=request_id,
                    additional_context={
                        'duration_ms': duration_ms,
                        'debug_level': debug_level,
                        'status': 'failed'
                    }
                )

                # Re-raise exception
                raise

        return wrapper
    return decorator


class ToolExecutionWrapper:
    """
    Wrapper class for tool execution with BugCatcher monitoring.

    Provides a more explicit API for wrapping tool calls.
    """

    def __init__(
        self,
        tool_name: str,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        debug_level: bool = True
    ):
        """
        Initialize tool wrapper.

        Args:
            tool_name: Name of the tool
            workflow_id: Workflow ID (if part of a workflow)
            step_id: Step ID (if part of a workflow)
            debug_level: Mark as debug level
        """
        self.tool_name = tool_name
        self.workflow_id = workflow_id
        self.step_id = step_id
        self.debug_level = debug_level
        self.request_id = f"{tool_name}_{int(time.time() * 1000)}"

        # Get BugCatcher instance
        try:
            from .bugcatcher import get_bugcatcher
            self.bugcatcher = get_bugcatcher()
        except (ImportError, Exception) as e:
            logger.debug(f"BugCatcher not available: {e}")
            self.bugcatcher = None

    def __enter__(self):
        """Enter context - start tracking."""
        if self.bugcatcher:
            context = {
                'tool_name': self.tool_name,
                'debug_level': self.debug_level,
                'timestamp': datetime.now().isoformat()
            }

            if self.workflow_id:
                context['workflow_id'] = self.workflow_id
            if self.step_id:
                context['step_id'] = self.step_id

            self.bugcatcher.track_request(self.request_id, context)

        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Exit context - capture exception if raised."""
        duration_ms = int((time.time() - self.start_time) * 1000)

        if self.bugcatcher:
            if exc_value:
                # Capture exception
                self.bugcatcher.capture_exception(
                    exc_value,
                    request_id=self.request_id,
                    additional_context={
                        'duration_ms': duration_ms,
                        'debug_level': self.debug_level,
                        'status': 'failed'
                    }
                )

        return False  # Don't suppress exception

    def track_output(self, output: Any):
        """
        Track output from the tool.

        Args:
            output: Output value to track
        """
        if self.bugcatcher:
            self.bugcatcher.track_output(
                self.request_id,
                output,
                output_type='tool_result'
            )


def wrap_tool_call(
    tool_name: str,
    tool_func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    workflow_id: Optional[str] = None,
    step_id: Optional[str] = None,
    debug_level: bool = True
) -> Any:
    """
    Wrap a tool call with BugCatcher monitoring.

    This is a functional API for wrapping tool calls without decorators.

    Args:
        tool_name: Name of the tool
        tool_func: Tool function to execute
        args: Positional arguments for the tool
        kwargs: Keyword arguments for the tool
        workflow_id: Workflow ID (if applicable)
        step_id: Step ID (if applicable)
        debug_level: Mark as debug level

    Returns:
        Result of tool execution

    Raises:
        Any exception raised by the tool (after capturing to BugCatcher)

    Usage:
        result = wrap_tool_call(
            'my_tool',
            my_tool_function,
            args=(arg1, arg2),
            kwargs={'option': value},
            workflow_id='wf_1',
            debug_level=True
        )
    """
    kwargs = kwargs or {}

    with ToolExecutionWrapper(
        tool_name,
        workflow_id=workflow_id,
        step_id=step_id,
        debug_level=debug_level
    ) as wrapper:
        result = tool_func(*args, **kwargs)
        wrapper.track_output(result)
        return result


# Convenience function for debug-level tool wrapping
def debug_wrap_tool(
    tool_name: str,
    tool_func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    Debug-level wrapper for tool execution.

    Convenience function that always uses debug_level=True.

    Args:
        tool_name: Name of the tool
        tool_func: Tool function to execute
        *args: Positional arguments for the tool
        **kwargs: Keyword arguments for the tool

    Returns:
        Result of tool execution

    Usage:
        result = debug_wrap_tool('my_tool', my_function, arg1, arg2, option=value)
    """
    return wrap_tool_call(
        tool_name,
        tool_func,
        args=args,
        kwargs=kwargs,
        debug_level=True
    )
