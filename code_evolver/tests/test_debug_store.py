"""
Tests for the hybrid debug store (LMDB + DuckDB)
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from debug_store import DebugStore, DebugContext, DebugRecord


class TestDebugStore:
    """Test suite for DebugStore"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def store(self, temp_dir):
        """Create a debug store instance"""
        store = DebugStore(
            session_id="test_session",
            base_path=temp_dir,
            enable_auto_sync=False  # Manual sync for testing
        )
        yield store
        store.close()

    def test_write_and_read_record(self, store):
        """Test writing and reading a single record"""
        record_id = store.write_record(
            context_type="tool",
            context_id="test_tool",
            context_name="Test Tool",
            request_data={"input": "test"},
            response_data={"output": "result"},
            duration_ms=123.45,
            memory_mb=10.5,
            cpu_percent=25.0,
            status="success"
        )

        assert record_id is not None

        # Read back
        record = store.get_record(record_id)
        assert record is not None
        assert record.context_type == "tool"
        assert record.context_id == "test_tool"
        assert record.request_data == {"input": "test"}
        assert record.response_data == {"output": "result"}
        assert record.duration_ms == 123.45
        assert record.status == "success"

    def test_get_records_by_context(self, store):
        """Test retrieving records by context"""
        # Write multiple records
        for i in range(5):
            store.write_record(
                context_type="tool",
                context_id="test_tool",
                context_name="Test Tool",
                request_data={"input": f"test_{i}"},
                response_data={"output": f"result_{i}"},
                duration_ms=100.0 + i,
                status="success"
            )

        # Write record for different context
        store.write_record(
            context_type="tool",
            context_id="other_tool",
            context_name="Other Tool",
            request_data={"input": "other"},
            response_data={"output": "other_result"},
            duration_ms=50.0,
            status="success"
        )

        # Retrieve records
        records = store.get_records_by_context("tool", "test_tool", limit=10)
        assert len(records) == 5

        # Check that they're all for test_tool
        for record in records:
            assert record.context_id == "test_tool"

    def test_sync_to_duckdb(self, store):
        """Test syncing from LMDB to DuckDB"""
        # Write some records
        for i in range(10):
            store.write_record(
                context_type="tool",
                context_id=f"tool_{i % 3}",
                context_name=f"Tool {i % 3}",
                request_data={"i": i},
                response_data={"result": i * 2},
                duration_ms=100.0 + i,
                status="success" if i % 2 == 0 else "error",
                error=f"Error {i}" if i % 2 != 0 else None
            )

        # Sync to DuckDB
        synced_count = store.sync_to_duckdb()
        assert synced_count == 10

        # Query from DuckDB
        result = store.query_analytics("SELECT COUNT(*) as count FROM records").fetchone()
        assert result[0] == 10

        # Verify no pending records
        stats = store.get_stats()
        assert stats['pending_sync'] == 0

    def test_performance_summary(self, store):
        """Test performance summary view"""
        # Write records with different performance characteristics
        contexts = [
            ("tool_a", "Tool A", 100.0, "success"),
            ("tool_a", "Tool A", 150.0, "success"),
            ("tool_a", "Tool A", 200.0, "error"),
            ("tool_b", "Tool B", 50.0, "success"),
            ("tool_b", "Tool B", 60.0, "success"),
        ]

        for context_id, context_name, duration, status in contexts:
            store.write_record(
                context_type="tool",
                context_id=context_id,
                context_name=context_name,
                request_data={},
                response_data={},
                duration_ms=duration,
                status=status
            )

        # Sync and get summary
        store.sync_to_duckdb()
        summary = store.get_performance_summary()

        assert len(summary) == 2  # Two different tools
        assert "Tool A" in summary['context_name'].values
        assert "Tool B" in summary['context_name'].values

        # Check Tool A stats
        tool_a = summary[summary['context_name'] == "Tool A"].iloc[0]
        assert tool_a['total_calls'] == 3
        assert tool_a['error_count'] == 1
        assert tool_a['success_count'] == 2

    def test_error_tracking(self, store):
        """Test error record retrieval"""
        # Write mix of success and errors
        for i in range(10):
            store.write_record(
                context_type="tool",
                context_id="error_test",
                context_name="Error Test",
                request_data={"attempt": i},
                response_data={},
                duration_ms=100.0,
                status="error" if i < 3 else "success",
                error=f"Error message {i}" if i < 3 else None
            )

        store.sync_to_duckdb()
        errors = store.get_error_records(limit=10)

        assert len(errors) == 3
        for _, error_row in errors.iterrows():
            assert error_row['status'] == 'error'
            assert error_row['error'] is not None

    def test_slow_operations(self, store):
        """Test slow operation detection"""
        # Write records with varying durations
        durations = [50, 100, 500, 1000, 1500, 2000, 100, 200]
        for i, duration in enumerate(durations):
            store.write_record(
                context_type="tool",
                context_id=f"tool_{i}",
                context_name=f"Tool {i}",
                request_data={},
                response_data={},
                duration_ms=duration,
                status="success"
            )

        store.sync_to_duckdb()
        slow_ops = store.get_slow_operations(threshold_ms=1000, limit=10)

        # Should find operations >= 1000ms
        assert len(slow_ops) == 3  # 1000, 1500, 2000
        assert all(row['duration_ms'] >= 1000 for _, row in slow_ops.iterrows())

    def test_code_tracking(self, store):
        """Test code snapshot and variant tracking"""
        code_v1 = "def func(): return 1"
        code_v2 = "def func(): return 2"

        # Write records with different code versions
        store.write_record(
            context_type="function",
            context_id="func",
            context_name="func",
            request_data={},
            response_data={"result": 1},
            duration_ms=100.0,
            status="success",
            code_snapshot=code_v1,
            code_hash="hash_v1",
            variant_id="variant_1"
        )

        store.write_record(
            context_type="function",
            context_id="func",
            context_name="func",
            request_data={},
            response_data={"result": 2},
            duration_ms=80.0,
            status="success",
            code_snapshot=code_v2,
            code_hash="hash_v2",
            variant_id="variant_2"
        )

        store.sync_to_duckdb()

        # Query by variant
        result = store.query_analytics("""
            SELECT variant_id, code_snapshot, AVG(duration_ms) as avg_duration
            FROM records
            WHERE variant_id IS NOT NULL
            GROUP BY variant_id, code_snapshot
        """).fetchdf()

        assert len(result) == 2
        assert "variant_1" in result['variant_id'].values
        assert "variant_2" in result['variant_id'].values

    def test_debug_context_success(self, store):
        """Test DebugContext for successful execution"""
        with DebugContext(
            store,
            context_type="tool",
            context_id="test_context",
            context_name="Test Context"
        ) as ctx:
            ctx.set_request({"input": "data"})
            time.sleep(0.1)  # Simulate work
            ctx.set_response({"output": "result"})

        # Record should be created
        records = store.get_records_by_context("tool", "test_context")
        assert len(records) == 1

        record = records[0]
        assert record.status == "success"
        assert record.request_data == {"input": "data"}
        assert record.response_data == {"output": "result"}
        assert record.duration_ms >= 100  # At least 100ms

    def test_debug_context_error(self, store):
        """Test DebugContext for failed execution"""
        try:
            with DebugContext(
                store,
                context_type="tool",
                context_id="error_context",
                context_name="Error Context"
            ) as ctx:
                ctx.set_request({"input": "data"})
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

        # Record should be created with error
        records = store.get_records_by_context("tool", "error_context")
        assert len(records) == 1

        record = records[0]
        assert record.status == "error"
        assert record.error == "Test error"

    def test_hierarchical_context(self, store):
        """Test parent-child context relationships"""
        # Parent workflow
        parent_id = store.write_record(
            context_type="workflow",
            context_id="parent_workflow",
            context_name="Parent Workflow",
            request_data={},
            response_data={},
            duration_ms=500.0,
            status="success"
        )

        # Child steps
        for i in range(3):
            store.write_record(
                context_type="step",
                context_id=f"step_{i}",
                context_name=f"Step {i}",
                request_data={},
                response_data={},
                duration_ms=100.0,
                status="success",
                parent_context="parent_workflow"
            )

        store.sync_to_duckdb()

        # Query child steps
        children = store.query_analytics("""
            SELECT * FROM records
            WHERE parent_context = 'parent_workflow'
        """).fetchdf()

        assert len(children) == 3

    def test_store_stats(self, store):
        """Test getting store statistics"""
        # Write some records
        for i in range(5):
            store.write_record(
                context_type="tool",
                context_id="test",
                context_name="Test",
                request_data={},
                response_data={},
                duration_ms=100.0,
                status="success"
            )

        stats = store.get_stats()

        assert stats['session_id'] == "test_session"
        assert stats['lmdb_entries'] > 0
        assert stats['pending_sync'] == 5

        # After sync
        store.sync_to_duckdb()
        stats = store.get_stats()

        assert stats['pending_sync'] == 0
        assert stats['duckdb_entries'] == 5

    def test_concurrent_writes(self, store):
        """Test concurrent write operations"""
        import threading

        def write_records(thread_id, count):
            for i in range(count):
                store.write_record(
                    context_type="tool",
                    context_id=f"thread_{thread_id}",
                    context_name=f"Thread {thread_id}",
                    request_data={"i": i},
                    response_data={},
                    duration_ms=100.0,
                    status="success"
                )

        # Create multiple threads
        threads = []
        for thread_id in range(5):
            t = threading.Thread(target=write_records, args=(thread_id, 10))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Sync and verify
        store.sync_to_duckdb()
        result = store.query_analytics("SELECT COUNT(*) as count FROM records").fetchone()
        assert result[0] == 50  # 5 threads * 10 records each


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
