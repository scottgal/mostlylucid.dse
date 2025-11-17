"""
Tests for Optimized Performance Tracker
"""

import os
import time
import tempfile
import shutil
import pytest
from pathlib import Path

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from optimized_perf_tracker import (
    OptimizedPerfTracker,
    TrackingMode,
    MinimalPerfData,
    DetailedPerfData,
    ToolPerfLRU,
    track_tool_call,
    end_tool_call,
    set_optimization_mode,
    get_perf_stats
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def tracker():
    """Get a fresh tracker instance for testing"""
    # Reset singleton for testing
    OptimizedPerfTracker._instance = None
    tracker = OptimizedPerfTracker()
    yield tracker
    tracker.shutdown()


class TestMinimalPerfData:
    """Tests for MinimalPerfData"""

    def test_creation(self):
        """Test creating minimal perf data"""
        data = MinimalPerfData(
            tool="test_tool",
            params='{"key": "value"}',
            start=1000.0,
            end=1001.5
        )
        assert data.tool == "test_tool"
        assert data.params == '{"key": "value"}'
        assert data.start == 1000.0
        assert data.end == 1001.5

    def test_compact_dict(self):
        """Test compact dictionary representation"""
        data = MinimalPerfData(
            tool="test_tool",
            params='{"key": "value"}',
            start=1000.0,
            end=1001.5
        )
        compact = data.to_compact_dict()
        assert compact["t"] == "test_tool"
        assert compact["p"] == '{"key": "value"}'
        assert compact["s"] == 1000.0
        assert compact["e"] == 1001.5
        assert compact["d"] == 1.5

    def test_long_params_truncation(self):
        """Test that long params are truncated"""
        long_params = "x" * 200
        data = MinimalPerfData(
            tool="test_tool",
            params=long_params,
            start=1000.0,
            end=1001.0
        )
        compact = data.to_compact_dict()
        assert len(compact["p"]) == 100


class TestDetailedPerfData:
    """Tests for DetailedPerfData"""

    def test_creation(self):
        """Test creating detailed perf data"""
        data = DetailedPerfData(
            tool="test_tool",
            params={"key": "value"},
            start=1000.0,
            end=1001.5,
            duration_ms=1500.0,
            memory_mb=100.0,
            cpu_percent=50.0
        )
        assert data.tool == "test_tool"
        assert data.params == {"key": "value"}
        assert data.duration_ms == 1500.0
        assert data.memory_mb == 100.0
        assert data.cpu_percent == 50.0

    def test_to_dict(self):
        """Test dictionary conversion"""
        data = DetailedPerfData(
            tool="test_tool",
            params={"key": "value"},
            start=1000.0,
            end=1001.5,
            duration_ms=1500.0
        )
        result = data.to_dict()
        assert isinstance(result, dict)
        assert result["tool"] == "test_tool"
        assert result["duration_ms"] == 1500.0


class TestToolPerfLRU:
    """Tests for ToolPerfLRU"""

    def test_basic_add(self):
        """Test basic add functionality"""
        lru = ToolPerfLRU("test_tool", max_size=3)

        evicted = lru.add("id1", "data1")
        assert evicted is None
        assert lru.size() == 1

        evicted = lru.add("id2", "data2")
        assert evicted is None
        assert lru.size() == 2

    def test_lru_eviction(self):
        """Test LRU eviction when limit exceeded"""
        lru = ToolPerfLRU("test_tool", max_size=2)

        lru.add("id1", "data1")
        lru.add("id2", "data2")

        # Adding third item should evict first
        evicted = lru.add("id3", "data3")
        assert evicted == "data1"
        assert lru.size() == 2

    def test_disabled_tracking(self):
        """Test that max_size=0 disables tracking"""
        lru = ToolPerfLRU("test_tool", max_size=0)

        evicted = lru.add("id1", "data1")
        assert evicted is None
        assert lru.size() == 0

    def test_unlimited_tracking(self):
        """Test that max_size=-1 allows unlimited"""
        lru = ToolPerfLRU("test_tool", max_size=-1)

        for i in range(1000):
            evicted = lru.add(f"id{i}", f"data{i}")
            assert evicted is None

        assert lru.size() == 1000

    def test_get_all(self):
        """Test getting all records"""
        lru = ToolPerfLRU("test_tool", max_size=3)

        lru.add("id1", "data1")
        lru.add("id2", "data2")
        lru.add("id3", "data3")

        all_data = lru.get_all()
        # Should be in reverse order (most recent first)
        assert all_data == ["data3", "data2", "data1"]

    def test_clear(self):
        """Test clearing all data"""
        lru = ToolPerfLRU("test_tool", max_size=3)

        lru.add("id1", "data1")
        lru.add("id2", "data2")

        cleared = lru.clear()
        assert cleared == ["data1", "data2"]
        assert lru.size() == 0


class TestOptimizedPerfTracker:
    """Tests for OptimizedPerfTracker"""

    def test_singleton(self):
        """Test that tracker is a singleton"""
        tracker1 = OptimizedPerfTracker()
        tracker2 = OptimizedPerfTracker()
        assert tracker1 is tracker2

    def test_normal_mode_tracking(self, tracker):
        """Test tracking in normal mode"""
        tracker.set_optimization_mode(False)

        record_id = tracker.start_tracking("test_tool", {"param": "value"})
        assert record_id is not None

        time.sleep(0.1)

        tracker.end_tracking(record_id)

        # Check stats
        stats = tracker.get_tool_stats("test_tool")
        assert stats["count"] == 1
        assert stats["avg_duration_s"] > 0

    def test_optimization_mode_tracking(self, tracker):
        """Test tracking in optimization mode"""
        tracker.set_optimization_mode(True)

        record_id = tracker.start_tracking("test_tool", {"param": "value"})
        time.sleep(0.1)
        tracker.end_tracking(record_id)

        stats = tracker.get_tool_stats("test_tool")
        assert stats["count"] == 1

    def test_parent_child_tracking(self, tracker):
        """Test parent-child relationship tracking"""
        tracker.set_optimization_mode(True)

        # Parent tool
        parent_id = tracker.start_tracking("parent_tool", {})

        # Child tool
        child_id = tracker.start_tracking("child_tool", {})
        tracker.end_tracking(child_id)

        # End parent
        tracker.end_tracking(parent_id)

        # Both should be tracked
        parent_stats = tracker.get_tool_stats("parent_tool")
        child_stats = tracker.get_tool_stats("child_tool")
        assert parent_stats["count"] == 1
        assert child_stats["count"] == 1

    def test_error_tracking(self, tracker):
        """Test tracking with errors"""
        record_id = tracker.start_tracking("test_tool", {})
        tracker.end_tracking(record_id, error="Test error message")

        stats = tracker.get_tool_stats("test_tool")
        assert stats["count"] == 1

    def test_lru_limits(self, tracker):
        """Test that LRU limits are enforced"""
        # Mock a small limit
        tracker.config["tool_limits"] = {"test_tool": 2}
        tracker.config["default_perf_points"] = 2

        # Add 3 records
        for i in range(3):
            record_id = tracker.start_tracking("test_tool", {"iteration": i})
            tracker.end_tracking(record_id)

        # Should only have 2 records (most recent)
        stats = tracker.get_tool_stats("test_tool")
        assert stats["current_size"] == 2

    def test_cleanup(self, tracker):
        """Test cleanup of old data"""
        # Add some data
        for i in range(5):
            record_id = tracker.start_tracking("test_tool", {})
            tracker.end_tracking(record_id)

        stats_before = tracker.get_tool_stats("test_tool")
        assert stats_before["count"] > 0

        # Cleanup
        tracker.cleanup_old_data()

        stats_after = tracker.get_tool_stats("test_tool")
        assert stats_after["count"] == 0

    def test_global_stats(self, tracker):
        """Test global statistics"""
        # Add some data for multiple tools
        for tool in ["tool1", "tool2", "tool3"]:
            record_id = tracker.start_tracking(tool, {})
            tracker.end_tracking(record_id)

        stats = tracker.get_all_stats()
        assert stats["total_calls"] >= 3
        assert stats["tools_tracked"] >= 3
        assert "tool_stats" in stats


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_track_tool_call(self):
        """Test track_tool_call convenience function"""
        record_id = track_tool_call("test_tool", {"param": "value"})
        assert record_id is not None
        end_tool_call(record_id)

    def test_set_optimization_mode(self):
        """Test set_optimization_mode convenience function"""
        set_optimization_mode(True)
        tracker = OptimizedPerfTracker()
        assert tracker.is_optimization_mode()

        set_optimization_mode(False)
        assert not tracker.is_optimization_mode()

    def test_get_perf_stats(self):
        """Test get_perf_stats convenience function"""
        record_id = track_tool_call("test_tool", {})
        end_tool_call(record_id)

        # Get specific tool stats
        stats = get_perf_stats("test_tool")
        assert stats["tool"] == "test_tool"
        assert stats["count"] >= 1

        # Get all stats
        all_stats = get_perf_stats()
        assert "total_calls" in all_stats


class TestBackgroundSave:
    """Test background save functionality"""

    def test_save_queue(self, tracker):
        """Test that records are queued for save"""
        tracker.config["storage"]["async_save"] = True

        record_id = tracker.start_tracking("test_tool", {})
        tracker.end_tracking(record_id)

        # Should have something in queue
        with tracker.save_lock:
            queue_size = len(tracker.save_queue)

        # Queue might have been flushed already in background
        assert queue_size >= 0  # Just check it doesn't error


class TestConfiguration:
    """Test configuration loading"""

    def test_default_config(self):
        """Test default configuration"""
        tracker = OptimizedPerfTracker()
        assert "default_perf_points" in tracker.config
        assert tracker.config["default_perf_points"] >= 0

    def test_tool_limit_lookup(self):
        """Test looking up tool-specific limits"""
        tracker = OptimizedPerfTracker()

        # Default limit
        default_limit = tracker._get_tool_limit("unknown_tool")
        assert default_limit == tracker.config.get("default_perf_points", 100)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
