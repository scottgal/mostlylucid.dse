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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
