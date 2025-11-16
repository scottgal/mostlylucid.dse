"""
Monitoring Test Tools - Lightweight tools to test BugCatcher and PerfCatcher.

Provides simulator tools that can be composed into test workflows:
- bug_trigger: Triggers specific exception scenarios
- perf_trigger: Triggers performance variance scenarios
- validator: Validates monitoring output

These are SUPER lightweight for testing the monitoring system.
"""
import time
import logging
import random
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BugTrigger:
    """
    Lightweight tool to trigger specific exception scenarios.

    Used in test workflows to validate BugCatcher functionality.
    """

    @staticmethod
    def trigger_value_error(message: str = "Test ValueError"):
        """
        Trigger a ValueError.

        Args:
            message: Error message

        Raises:
            ValueError: Always raises
        """
        raise ValueError(message)

    @staticmethod
    def trigger_key_error(key: str = "missing_key"):
        """
        Trigger a KeyError.

        Args:
            key: Missing key name

        Raises:
            KeyError: Always raises
        """
        data = {"existing_key": "value"}
        return data[key]  # Raises KeyError

    @staticmethod
    def trigger_attribute_error(attr: str = "missing_attr"):
        """
        Trigger an AttributeError.

        Args:
            attr: Missing attribute name

        Raises:
            AttributeError: Always raises
        """
        obj = object()
        return getattr(obj, attr)  # Raises AttributeError

    @staticmethod
    def trigger_zero_division():
        """
        Trigger a ZeroDivisionError.

        Raises:
            ZeroDivisionError: Always raises
        """
        return 1 / 0

    @staticmethod
    def trigger_type_error(value: int = 42):
        """
        Trigger a TypeError.

        Args:
            value: Value to concatenate

        Raises:
            TypeError: Always raises
        """
        return "string" + value  # Raises TypeError

    @staticmethod
    def trigger_custom_exception(
        exc_type: str = "ValueError",
        message: str = "Test exception"
    ):
        """
        Trigger a specific exception type.

        Args:
            exc_type: Exception type name
            message: Error message

        Raises:
            Exception: Specified exception type
        """
        exc_class = {
            "ValueError": ValueError,
            "KeyError": KeyError,
            "AttributeError": AttributeError,
            "TypeError": TypeError,
            "RuntimeError": RuntimeError,
            "ZeroDivisionError": ZeroDivisionError
        }.get(exc_type, Exception)

        raise exc_class(message)


class PerfTrigger:
    """
    Lightweight tool to trigger performance variance scenarios.

    Used in test workflows to validate PerfCatcher functionality.
    """

    def __init__(self):
        """Initialize perf trigger."""
        self.call_count = 0
        self.base_delay_ms = 100

    def trigger_slow_execution(self, delay_ms: int = 1000):
        """
        Trigger slow execution (above threshold).

        Args:
            delay_ms: Delay in milliseconds

        Returns:
            Execution time
        """
        start = time.time()
        time.sleep(delay_ms / 1000)
        duration = (time.time() - start) * 1000
        return {"duration_ms": duration, "triggered": "slow_execution"}

    def trigger_variance(
        self,
        base_ms: int = 100,
        variance_factor: float = 2.0
    ):
        """
        Trigger performance variance.

        Alternates between fast and slow execution to create variance.

        Args:
            base_ms: Base execution time
            variance_factor: Multiplier for slow execution

        Returns:
            Execution time and call count
        """
        self.call_count += 1

        # Alternate between fast and slow
        if self.call_count % 2 == 0:
            delay_ms = base_ms * variance_factor
        else:
            delay_ms = base_ms

        start = time.time()
        time.sleep(delay_ms / 1000)
        duration = (time.time() - start) * 1000

        return {
            "duration_ms": duration,
            "call_count": self.call_count,
            "triggered": "variance"
        }

    def trigger_gradual_degradation(
        self,
        initial_ms: int = 100,
        degradation_rate: float = 1.1
    ):
        """
        Trigger gradual performance degradation.

        Each call gets slower to simulate resource exhaustion.

        Args:
            initial_ms: Initial execution time
            degradation_rate: Rate of degradation per call

        Returns:
            Execution time and degradation info
        """
        self.call_count += 1

        # Increase delay with each call
        delay_ms = initial_ms * (degradation_rate ** self.call_count)

        start = time.time()
        time.sleep(delay_ms / 1000)
        duration = (time.time() - start) * 1000

        return {
            "duration_ms": duration,
            "call_count": self.call_count,
            "degradation_factor": degradation_rate ** self.call_count,
            "triggered": "gradual_degradation"
        }

    def trigger_spike(
        self,
        base_ms: int = 100,
        spike_ms: int = 1000,
        spike_frequency: int = 10
    ):
        """
        Trigger occasional performance spikes.

        Most calls are fast, occasional spike to simulate resource contention.

        Args:
            base_ms: Normal execution time
            spike_ms: Spike execution time
            spike_frequency: Spike every N calls

        Returns:
            Execution time and spike info
        """
        self.call_count += 1

        # Spike every N calls
        if self.call_count % spike_frequency == 0:
            delay_ms = spike_ms
            is_spike = True
        else:
            delay_ms = base_ms
            is_spike = False

        start = time.time()
        time.sleep(delay_ms / 1000)
        duration = (time.time() - start) * 1000

        return {
            "duration_ms": duration,
            "call_count": self.call_count,
            "is_spike": is_spike,
            "triggered": "spike"
        }

    def trigger_random_variance(
        self,
        base_ms: int = 100,
        max_variance: float = 0.5
    ):
        """
        Trigger random performance variance.

        Execution time varies randomly within threshold.

        Args:
            base_ms: Base execution time
            max_variance: Maximum variance (0.5 = 50%)

        Returns:
            Execution time and variance
        """
        self.call_count += 1

        # Random variance
        variance = random.uniform(-max_variance, max_variance)
        delay_ms = base_ms * (1 + variance)

        start = time.time()
        time.sleep(delay_ms / 1000)
        duration = (time.time() - start) * 1000

        return {
            "duration_ms": duration,
            "call_count": self.call_count,
            "variance": variance,
            "triggered": "random_variance"
        }

    def reset(self):
        """Reset call count for new test."""
        self.call_count = 0


class MonitoringValidator:
    """
    Validates that monitoring tools captured expected data.

    Lightweight validator for test workflows.
    """

    @staticmethod
    def validate_exception_captured(
        tool_name: str,
        exception_type: str,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Validate that BugCatcher captured an exception.

        Args:
            tool_name: Name of the tool
            exception_type: Expected exception type
            timeout: Max wait time in seconds

        Returns:
            Validation result
        """
        # Query BugAnalyzer for recent exceptions
        try:
            from .buganalyzer import BugAnalyzer

            analyzer = BugAnalyzer(lookback_hours=1)
            exceptions = analyzer.query_exceptions(
                tool_name=tool_name,
                limit=10
            )

            # Check if expected exception was captured
            for exc in exceptions:
                if exc.get('exception_type') == exception_type:
                    return {
                        'success': True,
                        'message': f"Exception {exception_type} captured for {tool_name}",
                        'exception': exc
                    }

            return {
                'success': False,
                'message': f"Exception {exception_type} not found for {tool_name}",
                'found_exceptions': [e.get('exception_type') for e in exceptions]
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to validate: {e}",
                'error': str(e)
            }

    @staticmethod
    def validate_performance_captured(
        tool_name: str,
        min_variance: float = 0.2,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Validate that PerfCatcher captured performance variance.

        Args:
            tool_name: Name of the tool
            min_variance: Minimum expected variance
            timeout: Max wait time in seconds

        Returns:
            Validation result
        """
        # Query PerfAnalyzer for recent variances
        try:
            from .perfanalyzer import PerfAnalyzer

            analyzer = PerfAnalyzer(lookback_hours=1)
            perf_issues = analyzer.query_performance_issues(
                tool_name=tool_name,
                limit=10
            )

            # Check if variance was captured
            for issue in perf_issues:
                variance = issue.get('variance', 0)
                if variance >= min_variance:
                    return {
                        'success': True,
                        'message': f"Performance variance {variance:.1%} captured for {tool_name}",
                        'perf_issue': issue
                    }

            return {
                'success': False,
                'message': f"No variance >= {min_variance:.1%} found for {tool_name}",
                'found_variances': [i.get('variance') for i in perf_issues]
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to validate: {e}",
                'error': str(e)
            }

    @staticmethod
    def validate_loki_connection() -> Dict[str, Any]:
        """
        Validate that Loki is accessible.

        Returns:
            Validation result
        """
        try:
            from .bugcatcher_setup import check_loki_connection

            connected = check_loki_connection()

            return {
                'success': connected,
                'message': "Loki is accessible" if connected else "Loki is not accessible",
                'connected': connected
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"Failed to check Loki: {e}",
                'error': str(e)
            }


# Lightweight test functions for direct use

def test_bug_trigger(exc_type: str = "ValueError") -> Dict[str, Any]:
    """
    Test BugCatcher by triggering an exception.

    Args:
        exc_type: Exception type to trigger

    Returns:
        Test result
    """
    trigger = BugTrigger()

    try:
        trigger.trigger_custom_exception(exc_type)
        return {
            'success': False,
            'message': f"{exc_type} was not raised"
        }

    except Exception as e:
        # Exception was raised (expected)
        return {
            'success': True,
            'message': f"{exc_type} was raised and should be captured",
            'exception_type': type(e).__name__,
            'exception_message': str(e)
        }


def test_perf_trigger(scenario: str = "variance") -> Dict[str, Any]:
    """
    Test PerfCatcher by triggering performance variance.

    Args:
        scenario: Scenario to trigger (variance, spike, degradation)

    Returns:
        Test result
    """
    trigger = PerfTrigger()

    # Run scenario multiple times to generate data
    results = []

    if scenario == "variance":
        for i in range(10):
            result = trigger.trigger_variance()
            results.append(result)

    elif scenario == "spike":
        for i in range(15):
            result = trigger.trigger_spike()
            results.append(result)

    elif scenario == "degradation":
        for i in range(10):
            result = trigger.trigger_gradual_degradation()
            results.append(result)

    else:
        return {
            'success': False,
            'message': f"Unknown scenario: {scenario}"
        }

    durations = [r['duration_ms'] for r in results]
    avg_duration = sum(durations) / len(durations)

    return {
        'success': True,
        'message': f"Performance scenario '{scenario}' triggered {len(results)} times",
        'results': results,
        'avg_duration_ms': avg_duration,
        'min_duration_ms': min(durations),
        'max_duration_ms': max(durations)
    }
