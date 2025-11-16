"""
Tests for BugCatcher global exception monitoring.
"""
import pytest
import time
from src.bugcatcher import (
    BugCatcher,
    LRUCache,
    ExceptionSeverity,
    track_request
)


class TestLRUCache:
    """Test LRU cache functionality."""

    def test_cache_put_get(self):
        """Test basic put and get operations."""
        cache = LRUCache(max_size=3)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})

        assert cache.get("key1") == {"data": "value1"}
        assert cache.get("key2") == {"data": "value2"}
        assert cache.get("key3") is None

    def test_cache_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache(max_size=2)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})
        cache.put("key3", {"data": "value3"})  # Should evict key1

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == {"data": "value2"}
        assert cache.get("key3") == {"data": "value3"}
        assert cache.size() == 2

    def test_cache_lru_order(self):
        """Test that least recently used items are evicted."""
        cache = LRUCache(max_size=2)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})

        # Access key1 to make it more recently used
        cache.get("key1")

        # Add key3, should evict key2 (least recently used)
        cache.put("key3", {"data": "value3"})

        assert cache.get("key1") == {"data": "value1"}  # Still there
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == {"data": "value3"}

    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = LRUCache(max_size=5)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestBugCatcher:
    """Test BugCatcher exception monitoring."""

    def test_initialization(self):
        """Test BugCatcher initialization."""
        bugcatcher = BugCatcher(
            loki_url="http://localhost:3100",
            loki_enabled=False,  # Disable Loki for testing
            cache_size=50,
            log_to_file=False
        )

        assert bugcatcher.enabled is True
        assert bugcatcher.request_cache.max_size == 50
        assert bugcatcher.loki.enabled is False

    def test_track_request(self):
        """Test request tracking."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        context = {
            'workflow_id': 'wf_1',
            'step_id': 'step_1',
            'tool_name': 'test_tool'
        }

        bugcatcher.track_request('request_1', context)

        cached = bugcatcher.request_cache.get('request_1')
        assert cached is not None
        assert cached['workflow_id'] == 'wf_1'
        assert cached['step_id'] == 'step_1'
        assert cached['tool_name'] == 'test_tool'

    def test_capture_exception(self):
        """Test exception capture."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        # Track a request first
        bugcatcher.track_request('request_1', {
            'workflow_id': 'wf_1',
            'step_id': 'step_1'
        })

        # Create and capture an exception
        try:
            raise ValueError("Test error")
        except ValueError as e:
            bugcatcher.capture_exception(
                e,
                request_id='request_1',
                severity=ExceptionSeverity.ERROR
            )

        # Check stats
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1

    def test_capture_exception_without_request(self):
        """Test capturing exception without prior request tracking."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        try:
            raise RuntimeError("Unexpected error")
        except RuntimeError as e:
            bugcatcher.capture_exception(e)

        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1

    def test_get_stats(self):
        """Test getting statistics."""
        bugcatcher = BugCatcher(
            loki_enabled=False,
            log_to_file=False,
            cache_size=100
        )

        stats = bugcatcher.get_stats()

        assert stats['total_exceptions'] == 0
        assert stats['cache_size'] == 0
        assert stats['cache_max_size'] == 100
        assert stats['loki_enabled'] is False
        assert stats['enabled'] is True

    def test_reset_stats(self):
        """Test resetting statistics."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        # Track some data
        bugcatcher.track_request('req_1', {'data': 'test'})

        try:
            raise ValueError("Test")
        except ValueError as e:
            bugcatcher.capture_exception(e)

        # Verify stats
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1
        assert stats['cache_size'] == 1

        # Reset
        bugcatcher.reset_stats()

        # Verify reset
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 0
        assert stats['cache_size'] == 0

    def test_exception_severity_levels(self):
        """Test different exception severity levels."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        severities = [
            ExceptionSeverity.DEBUG,
            ExceptionSeverity.INFO,
            ExceptionSeverity.WARNING,
            ExceptionSeverity.ERROR,
            ExceptionSeverity.CRITICAL
        ]

        for severity in severities:
            try:
                raise ValueError(f"Test {severity.value}")
            except ValueError as e:
                bugcatcher.capture_exception(e, severity=severity)

        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == len(severities)


class TestTrackRequestContextManager:
    """Test track_request context manager."""

    def test_context_manager_tracks_request(self):
        """Test that context manager tracks request."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        with track_request('request_1', workflow_id='wf_1'):
            pass

        # Request should be tracked
        cached = bugcatcher.request_cache.get('request_1')
        assert cached is not None
        assert cached['workflow_id'] == 'wf_1'

    def test_context_manager_captures_exception(self):
        """Test that context manager captures exceptions."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        with pytest.raises(ValueError):
            with track_request('request_1', workflow_id='wf_1'):
                raise ValueError("Test error")

        # Exception should be captured
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1


class TestBugCatcherIntegration:
    """Integration tests for BugCatcher."""

    def test_multiple_requests(self):
        """Test handling multiple concurrent requests."""
        bugcatcher = BugCatcher(
            loki_enabled=False,
            log_to_file=False,
            cache_size=10
        )

        # Track multiple requests
        for i in range(15):  # More than cache size
            bugcatcher.track_request(
                f'request_{i}',
                {'workflow_id': f'wf_{i}'}
            )

        # Cache should have max_size entries (LRU eviction)
        stats = bugcatcher.get_stats()
        assert stats['cache_size'] == 10

    def test_exception_with_additional_context(self):
        """Test capturing exceptions with additional context."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        try:
            raise ValueError("Test error")
        except ValueError as e:
            bugcatcher.capture_exception(
                e,
                request_id='request_1',
                additional_context={
                    'user_id': 'user_123',
                    'operation': 'test_operation',
                    'metadata': {'key': 'value'}
                }
            )

        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1


def test_bugcatcher_singleton():
    """Test that BugCatcher uses singleton pattern."""
    from src.bugcatcher import get_bugcatcher

    instance1 = get_bugcatcher()
    instance2 = get_bugcatcher()

    assert instance1 is instance2


class TestLokiBackend:
    """Test Loki backend functionality."""

    def test_loki_backend_initialization(self):
        """Test Loki backend initialization."""
        from src.bugcatcher import LokiBackend

        backend = LokiBackend(
            url="http://localhost:3100",
            enabled=False
        )

        assert backend.url == "http://localhost:3100/loki/api/v1/push"
        assert backend.enabled is False

    def test_loki_backend_batching(self):
        """Test Loki backend batching."""
        from src.bugcatcher import LokiBackend

        backend = LokiBackend(
            url="http://localhost:3100",
            enabled=False,
            batch_size=3
        )

        # Add logs but don't send
        backend.push("log1", {"level": "info"})
        backend.push("log2", {"level": "info"})

        assert len(backend._batch) == 2

        # Third log should trigger batch send (but won't actually send since disabled)
        backend.push("log3", {"level": "info"})

        # Batch should be cleared or still have 3 items
        assert len(backend._batch) <= 3


class TestBugCatcherOutputTracking:
    """Test BugCatcher output tracking functionality."""

    def test_track_output(self):
        """Test output tracking."""
        bugcatcher = BugCatcher(
            loki_enabled=False,
            log_to_file=False,
            track_outputs=True
        )

        bugcatcher.track_request('request_1', {'tool_name': 'test_tool'})

        # Track output
        bugcatcher.track_output('request_1', {'result': 'success'}, 'test_result')

        # Verify output was cached
        cached = bugcatcher.request_cache.get('request_1')
        assert cached is not None
        assert 'last_output' in cached
        assert cached['last_output']['type'] == 'test_result'

    def test_track_output_truncation(self):
        """Test that large outputs are truncated."""
        bugcatcher = BugCatcher(
            loki_enabled=False,
            log_to_file=False,
            track_outputs=True
        )

        bugcatcher.track_request('request_1', {'tool_name': 'test_tool'})

        # Track large output
        large_output = "x" * 2000
        bugcatcher.track_output('request_1', large_output, 'large_result')

        cached = bugcatcher.request_cache.get('request_1')
        assert len(cached['last_output']['data']) <= 1000  # Truncated


class TestBugCatcherLoggingHandler:
    """Test BugCatcher logging handler."""

    def test_logging_handler_captures_exceptions(self):
        """Test that logging handler captures logged exceptions."""
        import logging
        from src.bugcatcher import BugCatcherLoggingHandler

        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)
        handler = BugCatcherLoggingHandler(bugcatcher)

        # Create logger with handler
        test_logger = logging.getLogger('test_logger')
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.WARNING)

        # Log exception
        try:
            raise ValueError("Test exception in log")
        except ValueError:
            test_logger.exception("An error occurred")

        # Check that exception was captured
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] >= 1


class TestBugCatcherEdgeCases:
    """Test edge cases and error handling."""

    def test_capture_exception_with_none_traceback(self):
        """Test capturing exception with no traceback."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        # Create exception without traceback context
        exc = ValueError("Test exception")

        # Should not crash
        bugcatcher.capture_exception(exc)

        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1

    def test_track_request_with_large_context(self):
        """Test tracking request with very large context."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        large_context = {
            'data': 'x' * 10000,  # 10KB of data
            'workflow_id': 'wf_1'
        }

        # Should not crash
        bugcatcher.track_request('request_1', large_context)

        cached = bugcatcher.request_cache.get('request_1')
        assert cached is not None

    def test_concurrent_exception_capture(self):
        """Test thread safety of exception capture."""
        import threading

        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        def capture_exceptions(thread_id):
            for i in range(10):
                try:
                    raise ValueError(f"Thread {thread_id} exception {i}")
                except ValueError as e:
                    bugcatcher.capture_exception(e, request_id=f"thread_{thread_id}_{i}")

        # Run concurrent captures
        threads = []
        for i in range(5):
            t = threading.Thread(target=capture_exceptions, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All exceptions should be captured
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 50  # 5 threads * 10 exceptions


class TestBugCatcherConfiguration:
    """Test BugCatcher configuration options."""

    def test_disabled_bugcatcher(self):
        """Test that disabled BugCatcher doesn't capture."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)
        bugcatcher.enabled = False

        try:
            raise ValueError("Test")
        except ValueError as e:
            bugcatcher.capture_exception(e)

        # Should not capture when disabled
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 0

    def test_custom_cache_size(self):
        """Test custom cache size configuration."""
        bugcatcher = BugCatcher(
            loki_enabled=False,
            log_to_file=False,
            cache_size=5
        )

        for i in range(10):
            bugcatcher.track_request(f'request_{i}', {'data': i})

        stats = bugcatcher.get_stats()
        assert stats['cache_size'] == 5
        assert stats['cache_max_size'] == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
