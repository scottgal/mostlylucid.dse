"""
Tool Execution Interceptors - Automatic wrapping of all tool calls.

This module provides automatic interception of all tool executions
for monitoring, debugging, and performance tracking.

BugCatcher and PerfCatcher are automatically applied to every tool call
at the outermost level, catching exceptions in and out.
"""
import os
import logging
import time
import statistics
from typing import Any, Callable, Dict, Optional, List
from datetime import datetime
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class InterceptorPriority(Enum):
    """Priority levels for interceptor execution order."""
    FIRST = 0      # Execute first (outermost wrapper)
    HIGH = 10
    NORMAL = 50
    LOW = 90
    LAST = 100     # Execute last (innermost wrapper)


class ToolInterceptor:
    """
    Base class for tool execution interceptors.

    Interceptors wrap tool execution to add monitoring, logging,
    performance tracking, etc.
    """

    def __init__(self, priority: InterceptorPriority = InterceptorPriority.NORMAL):
        """
        Initialize interceptor.

        Args:
            priority: Execution priority (lower = outer wrapper)
        """
        self.priority = priority
        self.enabled = True

    def before_execution(
        self,
        tool_name: str,
        args: tuple,
        kwargs: dict,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Called before tool execution.

        Args:
            tool_name: Name of the tool
            args: Positional arguments
            kwargs: Keyword arguments
            context: Execution context (can be modified)

        Returns:
            Updated context
        """
        return context

    def after_execution(
        self,
        tool_name: str,
        result: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Called after successful tool execution.

        Args:
            tool_name: Name of the tool
            result: Tool execution result
            context: Execution context

        Returns:
            Result (can be modified)
        """
        return result

    def on_exception(
        self,
        tool_name: str,
        exception: Exception,
        context: Dict[str, Any]
    ) -> bool:
        """
        Called when tool raises an exception.

        Args:
            tool_name: Name of the tool
            exception: Exception that was raised
            context: Execution context

        Returns:
            True to suppress exception, False to re-raise
        """
        return False  # Don't suppress by default


class BugCatcherInterceptor(ToolInterceptor):
    """
    BugCatcher interceptor for automatic exception monitoring.

    Automatically wraps every tool call, catching exceptions both
    in and out. Can be disabled via BUGCATCHER_ENABLED env var.
    """

    def __init__(self):
        """Initialize BugCatcher interceptor."""
        # Run at highest priority (outermost wrapper)
        super().__init__(priority=InterceptorPriority.FIRST)

        # Check environment variable
        env_enabled = os.getenv('BUGCATCHER_ENABLED', 'true').lower()
        self.enabled = env_enabled in ('true', '1', 'yes', 'on')

        # Get BugCatcher instance
        self.bugcatcher = None
        if self.enabled:
            try:
                from .bugcatcher import get_bugcatcher
                self.bugcatcher = get_bugcatcher()
            except (ImportError, Exception) as e:
                logger.debug(f"BugCatcher not available: {e}")
                self.enabled = False

    def before_execution(
        self,
        tool_name: str,
        args: tuple,
        kwargs: dict,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track tool execution start."""
        if not self.enabled or not self.bugcatcher:
            return context

        # Generate request ID
        request_id = f"{tool_name}_{int(time.time() * 1000000)}"
        context['bugcatcher_request_id'] = request_id

        # Build tracking context
        tracking_context = {
            'tool_name': tool_name,
            'timestamp': datetime.now().isoformat(),
            'args_summary': str(args)[:500],
            'kwargs_summary': str(kwargs)[:500]
        }

        # Add workflow context if available
        if 'workflow_id' in context:
            tracking_context['workflow_id'] = context['workflow_id']
        if 'step_id' in context:
            tracking_context['step_id'] = context['step_id']

        # Track request
        self.bugcatcher.track_request(request_id, tracking_context)

        return context

    def after_execution(
        self,
        tool_name: str,
        result: Any,
        context: Dict[str, Any]
    ) -> Any:
        """Track successful execution."""
        if not self.enabled or not self.bugcatcher:
            return result

        request_id = context.get('bugcatcher_request_id')
        if request_id:
            # Track output (only if output tracking is enabled)
            if hasattr(self.bugcatcher, '_track_outputs') and self.bugcatcher._track_outputs:
                self.bugcatcher.track_output(
                    request_id,
                    result,
                    output_type='tool_result'
                )

        return result

    def on_exception(
        self,
        tool_name: str,
        exception: Exception,
        context: Dict[str, Any]
    ) -> bool:
        """Capture exception with full context."""
        if not self.enabled or not self.bugcatcher:
            return False

        request_id = context.get('bugcatcher_request_id')

        # Capture exception
        self.bugcatcher.capture_exception(
            exception,
            request_id=request_id,
            additional_context={
                'tool_name': tool_name,
                'duration_ms': context.get('execution_time_ms', 0),
                'workflow_id': context.get('workflow_id'),
                'step_id': context.get('step_id'),
                'intercepted_at': 'tool_execution'
            }
        )

        return False  # Don't suppress exception


class PerfCatcherInterceptor(ToolInterceptor):
    """
    PerfCatcher interceptor for performance monitoring.

    Tracks tool performance against thresholds and logs when
    variance is detected. Only captures data when outside threshold.

    Can be configured via environment variables:
    - PERFCATCHER_ENABLED: Enable/disable (default: true)
    - PERFCATCHER_VARIANCE_THRESHOLD: Variance threshold (default: 0.2 = 20%)
    - PERFCATCHER_WINDOW_SIZE: Window size for baseline (default: 100)
    - PERFCATCHER_MIN_SAMPLES: Minimum samples before checking (default: 10)
    """

    def __init__(self):
        """Initialize PerfCatcher interceptor."""
        # Run after BugCatcher but still high priority
        super().__init__(priority=InterceptorPriority.HIGH)

        # Check environment variable
        env_enabled = os.getenv('PERFCATCHER_ENABLED', 'true').lower()
        self.enabled = env_enabled in ('true', '1', 'yes', 'on')

        # Configuration from env vars
        self.variance_threshold = float(os.getenv('PERFCATCHER_VARIANCE_THRESHOLD', '0.2'))
        self.window_size = int(os.getenv('PERFCATCHER_WINDOW_SIZE', '100'))
        self.min_samples = int(os.getenv('PERFCATCHER_MIN_SAMPLES', '10'))

        # Performance tracking per tool
        self.performance_data: Dict[str, deque] = {}

        # Get BugCatcher for logging performance issues
        self.bugcatcher = None
        if self.enabled:
            try:
                from .bugcatcher import get_bugcatcher
                self.bugcatcher = get_bugcatcher()
            except (ImportError, Exception):
                pass

    def before_execution(
        self,
        tool_name: str,
        args: tuple,
        kwargs: dict,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record execution start time."""
        if self.enabled:
            context['perfcatcher_start_time'] = time.time()
        return context

    def after_execution(
        self,
        tool_name: str,
        result: Any,
        context: Dict[str, Any]
    ) -> Any:
        """Track execution time and check for variance."""
        if not self.enabled:
            return result

        # Calculate execution time
        start_time = context.get('perfcatcher_start_time')
        if not start_time:
            return result

        execution_time_ms = (time.time() - start_time) * 1000
        context['execution_time_ms'] = execution_time_ms

        # Initialize deque for this tool if needed
        if tool_name not in self.performance_data:
            self.performance_data[tool_name] = deque(maxlen=self.window_size)

        perf_data = self.performance_data[tool_name]
        perf_data.append(execution_time_ms)

        # Check for variance if we have enough samples
        if len(perf_data) >= self.min_samples:
            self._check_variance(tool_name, execution_time_ms, perf_data, context)

        return result

    def _check_variance(
        self,
        tool_name: str,
        current_time_ms: float,
        perf_data: deque,
        context: Dict[str, Any]
    ):
        """
        Check if current execution time is outside variance threshold.

        Args:
            tool_name: Name of the tool
            current_time_ms: Current execution time
            perf_data: Historical performance data
            context: Execution context
        """
        # Calculate baseline statistics
        mean_time = statistics.mean(perf_data)
        stdev_time = statistics.stdev(perf_data) if len(perf_data) > 1 else 0

        # Calculate variance from mean
        variance = abs(current_time_ms - mean_time) / mean_time if mean_time > 0 else 0

        # Check if outside threshold
        if variance > self.variance_threshold:
            # Log performance issue
            self._log_performance_variance(
                tool_name,
                current_time_ms,
                mean_time,
                stdev_time,
                variance,
                context
            )

    def _log_performance_variance(
        self,
        tool_name: str,
        current_time_ms: float,
        mean_time_ms: float,
        stdev_time_ms: float,
        variance: float,
        context: Dict[str, Any]
    ):
        """
        Log performance variance to BugCatcher/Loki.

        Only logs when outside threshold - captures window of data.

        Args:
            tool_name: Name of the tool
            current_time_ms: Current execution time
            mean_time_ms: Mean execution time
            stdev_time_ms: Standard deviation
            variance: Variance ratio
            context: Execution context
        """
        perf_issue = {
            'tool_name': tool_name,
            'current_time_ms': current_time_ms,
            'mean_time_ms': mean_time_ms,
            'stdev_time_ms': stdev_time_ms,
            'variance': variance,
            'variance_threshold': self.variance_threshold,
            'variance_percent': variance * 100,
            'outside_threshold': True,
            'timestamp': datetime.now().isoformat(),
            'workflow_id': context.get('workflow_id'),
            'step_id': context.get('step_id')
        }

        # Log to standard logger
        logger.warning(
            f"PerfCatcher: {tool_name} performance variance {variance:.1%} "
            f"(current: {current_time_ms:.1f}ms, mean: {mean_time_ms:.1f}ms, "
            f"threshold: {self.variance_threshold:.1%})"
        )

        # Log to Loki via BugCatcher if available
        if self.bugcatcher and hasattr(self.bugcatcher, 'loki'):
            import json

            labels = {
                'job': 'code_evolver_perfcatcher',
                'tool_name': tool_name,
                'variance_level': 'high' if variance > self.variance_threshold * 2 else 'medium'
            }

            if context.get('workflow_id'):
                labels['workflow_id'] = str(context['workflow_id'])

            message = json.dumps(perf_issue, indent=2, default=str)
            self.bugcatcher.loki.push(message, labels)

    def get_tool_stats(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get performance statistics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dict with performance stats, or None if no data
        """
        if tool_name not in self.performance_data:
            return None

        perf_data = list(self.performance_data[tool_name])
        if not perf_data:
            return None

        return {
            'tool_name': tool_name,
            'sample_count': len(perf_data),
            'mean_ms': statistics.mean(perf_data),
            'median_ms': statistics.median(perf_data),
            'stdev_ms': statistics.stdev(perf_data) if len(perf_data) > 1 else 0,
            'min_ms': min(perf_data),
            'max_ms': max(perf_data),
            'p95_ms': statistics.quantiles(perf_data, n=20)[18] if len(perf_data) >= 20 else max(perf_data),
            'p99_ms': statistics.quantiles(perf_data, n=100)[98] if len(perf_data) >= 100 else max(perf_data)
        }


class InterceptorChain:
    """
    Manages chain of tool execution interceptors.

    Interceptors are executed in priority order (lowest priority number = outermost wrapper).
    """

    def __init__(self):
        """Initialize interceptor chain."""
        self.interceptors: List[ToolInterceptor] = []

    def add_interceptor(self, interceptor: ToolInterceptor):
        """
        Add an interceptor to the chain.

        Args:
            interceptor: Interceptor to add
        """
        self.interceptors.append(interceptor)
        # Sort by priority (lowest first = outermost)
        self.interceptors.sort(key=lambda i: i.priority.value)

    def remove_interceptor(self, interceptor_type: type):
        """
        Remove all interceptors of a given type.

        Args:
            interceptor_type: Type of interceptor to remove
        """
        self.interceptors = [
            i for i in self.interceptors
            if not isinstance(i, interceptor_type)
        ]

    def intercept_tool_call(
        self,
        tool_name: str,
        tool_func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        context: Dict[str, Any] = None
    ) -> Any:
        """
        Execute tool with all interceptors applied.

        Interceptors are applied in priority order (outermost to innermost).

        Args:
            tool_name: Name of the tool
            tool_func: Tool function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            context: Execution context

        Returns:
            Tool execution result

        Raises:
            Any exception raised by the tool (after interceptor processing)
        """
        kwargs = kwargs or {}
        context = context or {}

        # Run before_execution for all enabled interceptors
        for interceptor in self.interceptors:
            if interceptor.enabled:
                try:
                    context = interceptor.before_execution(
                        tool_name, args, kwargs, context
                    )
                except Exception as e:
                    logger.error(f"Interceptor {type(interceptor).__name__} before_execution failed: {e}")

        # Execute tool
        try:
            result = tool_func(*args, **kwargs)

            # Run after_execution for all enabled interceptors (reverse order)
            for interceptor in reversed(self.interceptors):
                if interceptor.enabled:
                    try:
                        result = interceptor.after_execution(
                            tool_name, result, context
                        )
                    except Exception as e:
                        logger.error(f"Interceptor {type(interceptor).__name__} after_execution failed: {e}")

            return result

        except Exception as e:
            # Run on_exception for all enabled interceptors
            suppress = False
            for interceptor in self.interceptors:
                if interceptor.enabled:
                    try:
                        if interceptor.on_exception(tool_name, e, context):
                            suppress = True
                    except Exception as interceptor_error:
                        logger.error(
                            f"Interceptor {type(interceptor).__name__} on_exception failed: "
                            f"{interceptor_error}"
                        )

            # Re-raise unless suppressed
            if not suppress:
                raise


# Global interceptor chain
_global_interceptor_chain: Optional[InterceptorChain] = None


def get_global_interceptor_chain() -> InterceptorChain:
    """
    Get the global interceptor chain.

    Initializes with BugCatcher and PerfCatcher if not already initialized.

    Returns:
        Global interceptor chain
    """
    global _global_interceptor_chain

    if _global_interceptor_chain is None:
        _global_interceptor_chain = InterceptorChain()

        # Add BugCatcher interceptor (highest priority - outermost)
        _global_interceptor_chain.add_interceptor(BugCatcherInterceptor())

        # Add PerfCatcher interceptor
        _global_interceptor_chain.add_interceptor(PerfCatcherInterceptor())

        logger.info("Global interceptor chain initialized with BugCatcher and PerfCatcher")

    return _global_interceptor_chain


def intercept_tool_call(
    tool_name: str,
    tool_func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    context: Dict[str, Any] = None
) -> Any:
    """
    Execute tool with global interceptor chain.

    Convenience function for applying all global interceptors.

    Args:
        tool_name: Name of the tool
        tool_func: Tool function to execute
        args: Positional arguments
        kwargs: Keyword arguments
        context: Execution context

    Returns:
        Tool execution result
    """
    chain = get_global_interceptor_chain()
    return chain.intercept_tool_call(tool_name, tool_func, args, kwargs, context)
