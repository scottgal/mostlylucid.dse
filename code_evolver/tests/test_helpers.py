"""
Test helper utilities for monitoring tests.

Provides utility functions for:
- Creating test exceptions
- Generating mock data
- Asserting complex conditions
- Test data builders
"""
import time
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta


class ExceptionGenerator:
    """Helper class to generate test exceptions."""

    @staticmethod
    def create_value_error(message: str = "Test error") -> ValueError:
        """Create a ValueError for testing."""
        return ValueError(message)

    @staticmethod
    def create_key_error(key: str = "missing_key") -> KeyError:
        """Create a KeyError for testing."""
        return KeyError(key)

    @staticmethod
    def create_attribute_error(attr: str = "missing_attr") -> AttributeError:
        """Create an AttributeError for testing."""
        return AttributeError(f"'object' has no attribute '{attr}'")

    @staticmethod
    def create_type_error(message: str = "Type mismatch") -> TypeError:
        """Create a TypeError for testing."""
        return TypeError(message)

    @staticmethod
    def trigger_and_capture(exception_type: str = "ValueError"):
        """
        Trigger an exception and return it with traceback.

        Args:
            exception_type: Type of exception to create

        Returns:
            Tuple of (exception, traceback_string)
        """
        import traceback as tb

        try:
            if exception_type == "ValueError":
                raise ValueError("Test ValueError")
            elif exception_type == "KeyError":
                data = {}
                _ = data["missing_key"]
            elif exception_type == "AttributeError":
                obj = object()
                _ = obj.missing_attr
            elif exception_type == "TypeError":
                _ = "string" + 42
            else:
                raise Exception(f"Unknown exception type: {exception_type}")
        except Exception as e:
            traceback_str = tb.format_exc()
            return e, traceback_str


class PerformanceDataGenerator:
    """Helper class to generate performance test data."""

    @staticmethod
    def create_variance_sequence(
        tool_name: str,
        base_time_ms: float,
        variance_factor: float,
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Create a sequence of performance data with variance.

        Args:
            tool_name: Name of the tool
            base_time_ms: Base execution time
            variance_factor: Variance multiplier
            count: Number of data points

        Returns:
            List of performance data dictionaries
        """
        data = []
        mean_time = base_time_ms

        for i in range(count):
            # Alternate between fast and slow
            if i % 2 == 0:
                current_time = base_time_ms
            else:
                current_time = base_time_ms * (1 + variance_factor)

            variance = abs(current_time - mean_time) / mean_time if mean_time > 0 else 0

            data.append({
                'tool_name': tool_name,
                'workflow_id': f'wf_{i}',
                'variance': variance,
                'current_time_ms': current_time,
                'mean_time_ms': mean_time,
                'std_dev_ms': mean_time * variance_factor / 2,
                'timestamp': str((int(time.time()) + i) * 1_000_000_000)
            })

        return data

    @staticmethod
    def create_degradation_sequence(
        tool_name: str,
        initial_time_ms: float,
        degradation_rate: float,
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Create performance data showing gradual degradation.

        Args:
            tool_name: Name of the tool
            initial_time_ms: Initial execution time
            degradation_rate: Rate of degradation per iteration
            count: Number of data points

        Returns:
            List of performance data with increasing execution time
        """
        data = []

        for i in range(count):
            current_time = initial_time_ms * (degradation_rate ** i)
            mean_time = initial_time_ms * (degradation_rate ** (i / 2))  # Slower mean increase
            variance = (current_time - mean_time) / mean_time if mean_time > 0 else 0

            data.append({
                'tool_name': tool_name,
                'workflow_id': f'wf_{i}',
                'variance': variance,
                'current_time_ms': current_time,
                'mean_time_ms': mean_time,
                'timestamp': str((int(time.time()) + i) * 1_000_000_000)
            })

        return data

    @staticmethod
    def create_spike_sequence(
        tool_name: str,
        normal_time_ms: float,
        spike_time_ms: float,
        spike_frequency: int,
        count: int
    ) -> List[Dict[str, Any]]:
        """
        Create performance data with occasional spikes.

        Args:
            tool_name: Name of the tool
            normal_time_ms: Normal execution time
            spike_time_ms: Spike execution time
            spike_frequency: Spike every N calls
            count: Number of data points

        Returns:
            List of performance data with spikes
        """
        data = []

        for i in range(count):
            # Spike every N calls
            if i % spike_frequency == 0 and i > 0:
                current_time = spike_time_ms
            else:
                current_time = normal_time_ms

            mean_time = normal_time_ms  # Mean stays at normal
            variance = (current_time - mean_time) / mean_time if mean_time > 0 else 0

            data.append({
                'tool_name': tool_name,
                'workflow_id': f'wf_{i}',
                'variance': variance,
                'current_time_ms': current_time,
                'mean_time_ms': mean_time,
                'is_spike': i % spike_frequency == 0 and i > 0,
                'timestamp': str((int(time.time()) + i) * 1_000_000_000)
            })

        return data


class LokiResponseBuilder:
    """Helper class to build mock Loki API responses."""

    @staticmethod
    def build_exception_response(exceptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a mock Loki response for exception queries.

        Args:
            exceptions: List of exception dictionaries

        Returns:
            Mock Loki API response
        """
        import json

        values = []
        for i, exc in enumerate(exceptions):
            timestamp_ns = str((int(time.time()) + i) * 1_000_000_000)
            log_line = json.dumps(exc)
            values.append([timestamp_ns, log_line])

        return {
            'data': {
                'result': [
                    {
                        'stream': {'job': 'bugcatcher'},
                        'values': values
                    }
                ]
            }
        }

    @staticmethod
    def build_performance_response(perf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a mock Loki response for performance queries.

        Args:
            perf_data: List of performance data dictionaries

        Returns:
            Mock Loki API response
        """
        import json

        values = []
        for i, perf in enumerate(perf_data):
            timestamp_ns = perf.get('timestamp', str((int(time.time()) + i) * 1_000_000_000))
            log_line = json.dumps(perf)
            values.append([timestamp_ns, log_line])

        return {
            'data': {
                'result': [
                    {
                        'stream': {'job': 'code_evolver_perfcatcher'},
                        'values': values
                    }
                ]
            }
        }


class FixTemplateBuilder:
    """Helper class to build fix template test data."""

    @staticmethod
    def build_bug_fix_template(
        tool_name: str = "test_tool",
        exception_type: str = "ValueError",
        exception_message: str = "Test error"
    ) -> Dict[str, Any]:
        """
        Build a bug fix template.

        Args:
            tool_name: Name of the tool
            exception_type: Type of exception
            exception_message: Exception message

        Returns:
            Fix template dictionary
        """
        return {
            'problem_type': 'bug',
            'tool_name': tool_name,
            'problem_description': f'{exception_type}: {exception_message}',
            'problem_data': {
                'exception_type': exception_type,
                'exception_message': exception_message
            },
            'fix_description': f'Fix for {exception_type}',
            'fix_implementation': 'if not valid: raise ValueError()',
            'conditions': {
                'exception_type': exception_type
            }
        }

    @staticmethod
    def build_perf_optimization_template(
        tool_name: str = "slow_tool",
        variance: float = 0.5,
        optimization_type: str = "caching"
    ) -> Dict[str, Any]:
        """
        Build a performance optimization template.

        Args:
            tool_name: Name of the tool
            variance: Performance variance
            optimization_type: Type of optimization

        Returns:
            Fix template dictionary
        """
        return {
            'problem_type': 'perf',
            'tool_name': tool_name,
            'problem_description': f'Performance variance {variance:.1%}',
            'problem_data': {
                'variance': variance
            },
            'fix_description': f'Apply {optimization_type} optimization',
            'fix_implementation': '@lru_cache(maxsize=128)\ndef func(): ...',
            'conditions': {
                'min_variance': variance * 0.8
            },
            'metadata': {
                'optimization_type': optimization_type
            }
        }


class AssertionHelpers:
    """Helper functions for complex assertions."""

    @staticmethod
    def assert_exception_captured(
        bugcatcher,
        exception_type: str,
        min_count: int = 1
    ):
        """
        Assert that exceptions of a type were captured.

        Args:
            bugcatcher: BugCatcher instance
            exception_type: Expected exception type
            min_count: Minimum expected count
        """
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] >= min_count, \
            f"Expected at least {min_count} exceptions, got {stats['total_exceptions']}"

    @staticmethod
    def assert_variance_detected(
        perfcatcher,
        tool_name: str,
        min_variance: float = 0.2
    ):
        """
        Assert that performance variance was detected.

        Args:
            perfcatcher: PerfCatcher interceptor
            tool_name: Tool name to check
            min_variance: Minimum expected variance
        """
        assert tool_name in perfcatcher.performance_data, \
            f"Tool {tool_name} not found in performance data"

        data = perfcatcher.performance_data[tool_name]
        assert len(data) > 0, f"No performance data for {tool_name}"

    @staticmethod
    def assert_template_matches_problem(
        template,
        problem: Dict[str, Any]
    ):
        """
        Assert that a template matches a problem.

        Args:
            template: FixTemplate instance
            problem: Problem dictionary
        """
        assert template.matches_problem(problem), \
            f"Template {template.template_id} does not match problem {problem}"

    @staticmethod
    def assert_fix_applied_successfully(
        store,
        template_id: str,
        expected_count: int = 1
    ):
        """
        Assert that a fix was applied successfully.

        Args:
            store: FixTemplateStore instance
            template_id: Template ID
            expected_count: Expected applied count
        """
        template = store.templates.get(template_id)
        assert template is not None, f"Template {template_id} not found"
        assert template.applied_count >= expected_count, \
            f"Expected applied_count >= {expected_count}, got {template.applied_count}"


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """
    Wait for a condition to become true.

    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds

    Returns:
        True if condition met, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)

    return False


def create_test_context(
    workflow_id: str = "test_workflow",
    step_id: str = "test_step",
    tool_name: str = "test_tool",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test context dictionary.

    Args:
        workflow_id: Workflow ID
        step_id: Step ID
        tool_name: Tool name
        **kwargs: Additional context fields

    Returns:
        Context dictionary
    """
    context = {
        'workflow_id': workflow_id,
        'step_id': step_id,
        'tool_name': tool_name,
        'timestamp': datetime.now().isoformat()
    }
    context.update(kwargs)
    return context


def generate_request_id(prefix: str = "req") -> str:
    """
    Generate a unique request ID for testing.

    Args:
        prefix: Prefix for the request ID

    Returns:
        Unique request ID
    """
    timestamp = int(time.time() * 1_000_000)
    random_suffix = random.randint(1000, 9999)
    return f"{prefix}_{timestamp}_{random_suffix}"
