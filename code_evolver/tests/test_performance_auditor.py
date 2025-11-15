"""
Tests for the performance auditor system
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from performance_auditor import (
    PerformanceAuditor,
    PerformanceThreshold,
    AuditResult,
    OptimizationCandidate
)


class TestPerformanceAuditor:
    """Test suite for PerformanceAuditor"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def auditor(self, temp_dir):
        """Create auditor instance"""
        auditor = PerformanceAuditor(
            session_id="test_audit",
            base_path=temp_dir,
            optimization_queue_path=str(Path(temp_dir) / "queue.json")
        )
        yield auditor
        auditor.close()

    def test_default_thresholds(self, auditor):
        """Test default threshold values"""
        assert "function" in auditor.thresholds
        assert "tool" in auditor.thresholds
        assert "node" in auditor.thresholds

        tool_threshold = auditor.thresholds["tool"]
        assert tool_threshold.max_duration_ms == 1000.0
        assert tool_threshold.min_success_rate == 0.95

    def test_create_tracking_version(self, auditor):
        """Test creating tracking version of a function"""

        def sample_function(x: int) -> int:
            time.sleep(0.01)
            return x * 2

        # Create tracking version
        tracked = auditor.create_tracking_version(
            sample_function,
            layer="tool",
            tool_name="sample_tool"
        )

        # Execute it
        result = tracked(5)

        # Should return same result
        assert result == 10

        # Should have recorded metrics
        auditor.collector.store.sync_to_duckdb()
        records = auditor.collector.store.query_analytics(
            "SELECT COUNT(*) FROM records WHERE context_id = 'sample_tool'"
        ).fetchone()

        assert records[0] >= 1

    def test_audit_component_passing(self, auditor):
        """Test auditing a component that passes thresholds"""

        def fast_function(x: int) -> int:
            """Fast function that should pass"""
            return x + 1

        # Create tracking version and execute multiple times
        tracked = auditor.create_tracking_version(fast_function, "function", "fast_func")

        for i in range(10):
            tracked(i)

        # Audit it
        result = auditor.audit_component(
            fast_function,
            layer="function",
            component_name="fast_func",
            run_tests=False
        )

        # Should pass (very fast function)
        assert result.passed
        assert len(result.violations) == 0

    def test_audit_component_failing_duration(self, auditor):
        """Test auditing a component that fails duration threshold"""

        def slow_function(x: int) -> int:
            """Slow function that should fail"""
            time.sleep(0.15)  # 150ms
            return x + 1

        # Create tracking version and execute
        tracked = auditor.create_tracking_version(slow_function, "function", "slow_func")

        for i in range(5):
            tracked(i)

        # Audit with strict threshold
        result = auditor.audit_component(
            slow_function,
            layer="function",
            component_name="slow_func",
            run_tests=False
        )

        # Should fail (exceeds 100ms threshold for functions)
        assert not result.passed
        assert any("Duration" in v for v in result.violations)

    def test_audit_component_failing_errors(self, auditor):
        """Test auditing a component with errors"""

        call_count = [0]

        def error_prone_function(x: int) -> int:
            """Function that sometimes errors"""
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                raise ValueError("Simulated error")
            return x + 1

        # Create tracking version and execute
        tracked = auditor.create_tracking_version(
            error_prone_function,
            "function",
            "error_func"
        )

        for i in range(10):
            try:
                tracked(i)
            except ValueError:
                pass

        # Audit
        result = auditor.audit_component(
            error_prone_function,
            layer="function",
            component_name="error_func",
            run_tests=False
        )

        # Should fail due to errors
        assert not result.passed
        assert result.metrics["error_count"] > 0

    def test_optimization_queue(self, auditor):
        """Test optimization queue management"""

        def slow_function():
            time.sleep(0.15)
            return True

        # Create and execute tracking version
        tracked = auditor.create_tracking_version(slow_function, "function", "queue_test")

        for _ in range(5):
            tracked()

        # Audit (should fail and add to queue)
        result = auditor.audit_component(
            slow_function,
            layer="function",
            component_name="queue_test",
            run_tests=False
        )

        # Should be in optimization queue
        queue = auditor.get_optimization_queue()
        assert len(queue) > 0

        # Should find our component
        our_candidate = next((c for c in queue if c.component_name == "queue_test"), None)
        assert our_candidate is not None
        assert our_candidate.priority >= 1
        assert len(our_candidate.violations) > 0

    def test_priority_calculation(self, auditor):
        """Test optimization priority calculation"""

        # Severely slow function
        def very_slow_function():
            time.sleep(0.3)  # 300ms
            return True

        # Moderately slow function
        def slow_function():
            time.sleep(0.12)  # 120ms
            return True

        # Track and execute both
        very_slow_tracked = auditor.create_tracking_version(very_slow_function, "function", "very_slow")
        slow_tracked = auditor.create_tracking_version(slow_function, "function", "slow")

        for _ in range(5):
            very_slow_tracked()
            slow_tracked()

        # Audit both
        auditor.audit_component(very_slow_function, "function", "very_slow", run_tests=False)
        auditor.audit_component(slow_function, "function", "slow", run_tests=False)

        # Get queue
        queue = auditor.get_optimization_queue()

        # Very slow should have higher priority
        very_slow_candidate = next(c for c in queue if c.component_name == "very_slow")
        slow_candidate = next(c for c in queue if c.component_name == "slow")

        assert very_slow_candidate.priority > slow_candidate.priority

    def test_generate_audit_report(self, auditor):
        """Test audit report generation"""

        def test_func1():
            time.sleep(0.01)
            return True

        def test_func2():
            time.sleep(0.15)
            return True

        # Track and execute
        tracked1 = auditor.create_tracking_version(test_func1, "function", "func1")
        tracked2 = auditor.create_tracking_version(test_func2, "function", "func2")

        for _ in range(5):
            tracked1()
            tracked2()

        # Audit both
        auditor.audit_component(test_func1, "function", "func1", run_tests=False)
        auditor.audit_component(test_func2, "function", "func2", run_tests=False)

        # Generate report
        report = auditor.generate_audit_report()

        # Check report content
        assert "# Performance Audit Report" in report
        assert "## Executive Summary" in report
        assert "## Audit Results by Layer" in report
        assert "func1" in report or "func2" in report

    def test_save_and_load_queue(self, temp_dir):
        """Test saving and loading optimization queue"""

        queue_path = Path(temp_dir) / "test_queue.json"

        # Create auditor and add to queue
        auditor1 = PerformanceAuditor(
            session_id="save_test",
            base_path=temp_dir,
            optimization_queue_path=str(queue_path)
        )

        def slow_func():
            time.sleep(0.15)
            return True

        tracked = auditor1.create_tracking_version(slow_func, "function", "save_test_func")

        for _ in range(5):
            tracked()

        auditor1.audit_component(slow_func, "function", "save_test_func", run_tests=False)

        queue1 = auditor1.get_optimization_queue()
        assert len(queue1) > 0

        auditor1.close()

        # Create new auditor - should load existing queue
        auditor2 = PerformanceAuditor(
            session_id="save_test2",
            base_path=temp_dir,
            optimization_queue_path=str(queue_path)
        )

        queue2 = auditor2.get_optimization_queue()
        assert len(queue2) == len(queue1)

        auditor2.close()

    def test_custom_thresholds(self, temp_dir):
        """Test using custom thresholds"""

        custom_thresholds = {
            "tool": PerformanceThreshold(
                max_duration_ms=50.0,  # Very strict
                min_success_rate=0.99
            )
        }

        auditor = PerformanceAuditor(
            session_id="custom_threshold_test",
            thresholds=custom_thresholds,
            base_path=temp_dir
        )

        def moderate_func():
            time.sleep(0.06)  # 60ms
            return True

        tracked = auditor.create_tracking_version(moderate_func, "tool", "moderate_tool")

        for _ in range(5):
            tracked()

        result = auditor.audit_component(moderate_func, "tool", "moderate_tool", run_tests=False)

        # Should fail with strict threshold
        assert not result.passed

        auditor.close()

    def test_metrics_extraction(self, auditor):
        """Test metrics extraction from debug store"""

        def metric_test_func(x: int):
            time.sleep(0.01 * x)  # Variable duration
            return x * 2

        tracked = auditor.create_tracking_version(metric_test_func, "function", "metric_func")

        for i in range(1, 6):
            tracked(i)

        result = auditor.audit_component(metric_test_func, "function", "metric_func", run_tests=False)

        # Check metrics are populated
        assert "avg_duration_ms" in result.metrics
        assert "total_executions" in result.metrics
        assert "success_rate" in result.metrics

        assert result.metrics["total_executions"] >= 5
        assert result.metrics["avg_duration_ms"] > 0

    def test_violation_messages(self, auditor):
        """Test violation message generation"""

        def slow_memory_func():
            time.sleep(0.15)
            # Simulate memory usage
            _ = [0] * (1024 * 1024 * 10)  # Allocate some memory
            return True

        tracked = auditor.create_tracking_version(slow_memory_func, "function", "violation_func")

        for _ in range(5):
            tracked()

        result = auditor.audit_component(slow_memory_func, "function", "violation_func", run_tests=False)

        # Should have violations
        assert len(result.violations) > 0

        # Violations should be descriptive
        for violation in result.violations:
            assert len(violation) > 0
            assert any(word in violation.lower() for word in ["duration", "memory", "cpu", "error", "success"])

    def test_recommendation_generation(self, auditor):
        """Test recommendation generation"""

        def needs_optimization():
            time.sleep(0.2)
            return True

        tracked = auditor.create_tracking_version(needs_optimization, "function", "rec_func")

        for _ in range(5):
            tracked()

        result = auditor.audit_component(needs_optimization, "function", "rec_func", run_tests=False)

        # Should have recommendation
        assert result.recommendation is not None
        assert len(result.recommendation) > 0

        if not result.passed:
            # Failing components should have actionable recommendations
            assert any(word in result.recommendation.lower() for word in ["optimize", "reduce", "fix", "improve"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
