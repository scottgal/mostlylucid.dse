"""
Tests for Tool Interceptors (BugCatcher and PerfCatcher).
"""
import pytest
import time
from src.tool_interceptors import (
    ToolInterceptor,
    InterceptorPriority,
    BugCatcherInterceptor,
    PerfCatcherInterceptor,
    InterceptorChain,
    intercept_tool_call,
    get_global_interceptor_chain
)


class TestInterceptorPriority:
    """Test interceptor priority enumeration."""

    def test_priority_values(self):
        """Test that priority values are correctly ordered."""
        assert InterceptorPriority.FIRST.value < InterceptorPriority.HIGH.value
        assert InterceptorPriority.HIGH.value < InterceptorPriority.NORMAL.value
        assert InterceptorPriority.NORMAL.value < InterceptorPriority.LOW.value
        assert InterceptorPriority.LOW.value < InterceptorPriority.LAST.value


class TestToolInterceptor:
    """Test base ToolInterceptor class."""

    def test_interceptor_initialization(self):
        """Test interceptor initialization."""
        interceptor = ToolInterceptor(priority=InterceptorPriority.NORMAL)

        assert interceptor.priority == InterceptorPriority.NORMAL
        assert interceptor.enabled is True

    def test_before_execution_returns_context(self):
        """Test that before_execution returns context."""
        interceptor = ToolInterceptor()

        context = {'key': 'value'}
        result = interceptor.before_execution('tool', (), {}, context)

        assert result == context

    def test_after_execution_returns_result(self):
        """Test that after_execution returns result."""
        interceptor = ToolInterceptor()

        result = interceptor.after_execution('tool', 'result', {})

        assert result == 'result'

    def test_on_exception_does_not_suppress(self):
        """Test that on_exception doesn't suppress by default."""
        interceptor = ToolInterceptor()

        suppress = interceptor.on_exception('tool', ValueError("test"), {})

        assert suppress is False


class TestBugCatcherInterceptor:
    """Test BugCatcher interceptor."""

    def test_bugcatcher_interceptor_initialization(self):
        """Test BugCatcher interceptor initialization."""
        import os
        os.environ['BUGCATCHER_ENABLED'] = 'true'

        interceptor = BugCatcherInterceptor()

        assert interceptor.priority == InterceptorPriority.FIRST
        # Enabled state depends on whether BugCatcher can be imported

    def test_bugcatcher_disabled_via_env(self):
        """Test disabling BugCatcher via environment variable."""
        import os
        os.environ['BUGCATCHER_ENABLED'] = 'false'

        interceptor = BugCatcherInterceptor()

        assert interceptor.enabled is False

    def test_before_execution_tracks_request(self):
        """Test that before_execution tracks request."""
        import os
        os.environ['BUGCATCHER_ENABLED'] = 'true'

        interceptor = BugCatcherInterceptor()

        if not interceptor.enabled:
            pytest.skip("BugCatcher not available")

        context = {}
        result_context = interceptor.before_execution(
            'test_tool',
            ('arg1',),
            {'kwarg': 'value'},
            context
        )

        # Should add request_id to context
        assert 'bugcatcher_request_id' in result_context

    def test_on_exception_captures_exception(self):
        """Test that on_exception captures exceptions."""
        import os
        os.environ['BUGCATCHER_ENABLED'] = 'true'

        interceptor = BugCatcherInterceptor()

        if not interceptor.enabled or not interceptor.bugcatcher:
            pytest.skip("BugCatcher not available")

        context = {'bugcatcher_request_id': 'test_request'}
        exception = ValueError("Test exception")

        # Should capture but not suppress
        suppress = interceptor.on_exception('test_tool', exception, context)

        assert suppress is False

        # Check that exception was captured
        stats = interceptor.bugcatcher.get_stats()
        assert stats['total_exceptions'] >= 1


class TestPerfCatcherInterceptor:
    """Test PerfCatcher interceptor."""

    def test_perfcatcher_interceptor_initialization(self):
        """Test PerfCatcher interceptor initialization."""
        import os
        os.environ['PERFCATCHER_ENABLED'] = 'true'
        os.environ['PERFCATCHER_VARIANCE_THRESHOLD'] = '0.3'
        os.environ['PERFCATCHER_WINDOW_SIZE'] = '50'

        interceptor = PerfCatcherInterceptor()

        assert interceptor.priority == InterceptorPriority.HIGH
        assert interceptor.variance_threshold == 0.3
        assert interceptor.window_size == 50

    def test_perfcatcher_disabled_via_env(self):
        """Test disabling PerfCatcher via environment variable."""
        import os
        os.environ['PERFCATCHER_ENABLED'] = 'false'

        interceptor = PerfCatcherInterceptor()

        assert interceptor.enabled is False

    def test_before_execution_records_time(self):
        """Test that before_execution records start time."""
        import os
        os.environ['PERFCATCHER_ENABLED'] = 'true'

        interceptor = PerfCatcherInterceptor()

        context = {}
        result_context = interceptor.before_execution('tool', (), {}, context)

        assert 'perfcatcher_start_time' in result_context

    def test_after_execution_tracks_performance(self):
        """Test that after_execution tracks performance."""
        import os
        os.environ['PERFCATCHER_ENABLED'] = 'true'

        interceptor = PerfCatcherInterceptor()

        context = {'perfcatcher_start_time': time.time()}

        time.sleep(0.01)  # Small delay

        result = interceptor.after_execution('test_tool', 'result', context)

        assert result == 'result'
        assert 'execution_time_ms' in context
        assert context['execution_time_ms'] > 0

    def test_variance_detection(self):
        """Test performance variance detection."""
        import os
        os.environ['PERFCATCHER_ENABLED'] = 'true'
        os.environ['PERFCATCHER_VARIANCE_THRESHOLD'] = '0.2'
        os.environ['PERFCATCHER_MIN_SAMPLES'] = '5'

        interceptor = PerfCatcherInterceptor()

        # Establish baseline with consistent times
        for i in range(10):
            context = {'perfcatcher_start_time': time.time()}
            time.sleep(0.01)
            interceptor.after_execution('test_tool', 'result', context)

        # Now trigger variance with slow execution
        context = {'perfcatcher_start_time': time.time()}
        time.sleep(0.05)  # Much longer
        interceptor.after_execution('test_tool', 'result', context)

        # Variance should have been detected and logged
        # (Check would require mocking Loki backend)

    def test_get_tool_stats(self):
        """Test getting tool statistics."""
        import os
        os.environ['PERFCATCHER_ENABLED'] = 'true'

        interceptor = PerfCatcherInterceptor()

        # Run tool multiple times
        for i in range(20):
            context = {'perfcatcher_start_time': time.time()}
            time.sleep(0.01)
            interceptor.after_execution('test_tool', 'result', context)

        stats = interceptor.get_tool_stats('test_tool')

        assert stats is not None
        assert stats['sample_count'] == 20
        assert stats['mean_ms'] > 0
        assert stats['min_ms'] > 0
        assert stats['max_ms'] > 0


class TestInterceptorChain:
    """Test interceptor chain functionality."""

    def test_chain_initialization(self):
        """Test chain initialization."""
        chain = InterceptorChain()

        assert len(chain.interceptors) == 0

    def test_add_interceptor(self):
        """Test adding interceptors."""
        chain = InterceptorChain()

        interceptor1 = ToolInterceptor(priority=InterceptorPriority.HIGH)
        interceptor2 = ToolInterceptor(priority=InterceptorPriority.NORMAL)

        chain.add_interceptor(interceptor1)
        chain.add_interceptor(interceptor2)

        assert len(chain.interceptors) == 2

    def test_interceptor_priority_ordering(self):
        """Test that interceptors are ordered by priority."""
        chain = InterceptorChain()

        # Add in reverse priority order
        normal = ToolInterceptor(priority=InterceptorPriority.NORMAL)
        first = ToolInterceptor(priority=InterceptorPriority.FIRST)
        last = ToolInterceptor(priority=InterceptorPriority.LAST)

        chain.add_interceptor(normal)
        chain.add_interceptor(last)
        chain.add_interceptor(first)

        # Should be sorted: FIRST, NORMAL, LAST
        assert chain.interceptors[0].priority == InterceptorPriority.FIRST
        assert chain.interceptors[1].priority == InterceptorPriority.NORMAL
        assert chain.interceptors[2].priority == InterceptorPriority.LAST

    def test_remove_interceptor(self):
        """Test removing interceptors by type."""
        chain = InterceptorChain()

        interceptor1 = ToolInterceptor(priority=InterceptorPriority.HIGH)
        interceptor2 = ToolInterceptor(priority=InterceptorPriority.NORMAL)

        chain.add_interceptor(interceptor1)
        chain.add_interceptor(interceptor2)

        chain.remove_interceptor(ToolInterceptor)

        assert len(chain.interceptors) == 0

    def test_intercept_tool_call_success(self):
        """Test successful tool call interception."""
        chain = InterceptorChain()

        def test_tool(arg1, kwarg1=None):
            return f"result: {arg1}, {kwarg1}"

        result = chain.intercept_tool_call(
            'test_tool',
            test_tool,
            args=('value1',),
            kwargs={'kwarg1': 'value2'}
        )

        assert result == "result: value1, value2"

    def test_intercept_tool_call_with_exception(self):
        """Test tool call interception with exception."""
        chain = InterceptorChain()

        def failing_tool():
            raise ValueError("Tool failed")

        with pytest.raises(ValueError, match="Tool failed"):
            chain.intercept_tool_call('failing_tool', failing_tool)

    def test_interceptor_context_modification(self):
        """Test that interceptors can modify context."""
        class ContextModifier(ToolInterceptor):
            def before_execution(self, tool_name, args, kwargs, context):
                context['modified'] = True
                return context

        chain = InterceptorChain()
        chain.add_interceptor(ContextModifier())

        context = {}

        def test_tool():
            return "result"

        chain.intercept_tool_call('test_tool', test_tool, context=context)

        assert context['modified'] is True


class TestGlobalInterceptorChain:
    """Test global interceptor chain."""

    def test_global_chain_initialization(self):
        """Test that global chain is initialized with default interceptors."""
        chain = get_global_interceptor_chain()

        # Should have BugCatcher and PerfCatcher
        assert len(chain.interceptors) >= 2

        # BugCatcher should be first
        assert isinstance(chain.interceptors[0], BugCatcherInterceptor)

    def test_intercept_tool_call_function(self):
        """Test convenience intercept_tool_call function."""
        def test_tool(x, y):
            return x + y

        result = intercept_tool_call(
            'test_tool',
            test_tool,
            args=(5, 3)
        )

        assert result == 8


class TestInterceptorIntegration:
    """Integration tests for interceptors."""

    def test_full_chain_with_exception(self):
        """Test full interceptor chain with exception."""
        import os
        os.environ['BUGCATCHER_ENABLED'] = 'true'
        os.environ['PERFCATCHER_ENABLED'] = 'true'

        def failing_tool():
            raise ValueError("Integration test exception")

        with pytest.raises(ValueError, match="Integration test exception"):
            intercept_tool_call('failing_tool', failing_tool)

        # Exception should have been captured by BugCatcher

    def test_full_chain_performance_tracking(self):
        """Test full chain with performance tracking."""
        import os
        os.environ['BUGCATCHER_ENABLED'] = 'true'
        os.environ['PERFCATCHER_ENABLED'] = 'true'

        def slow_tool():
            time.sleep(0.05)
            return "result"

        result = intercept_tool_call('slow_tool', slow_tool)

        assert result == "result"
        # Performance should have been tracked by PerfCatcher


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
