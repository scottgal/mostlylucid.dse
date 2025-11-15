"""
Tests for the debug analyzer and LLM output generation
"""

import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from debug_store import DebugStore
from debug_analyzer import DebugAnalyzer, AnalysisPackage, CodeVariant


class TestDebugAnalyzer:
    """Test suite for DebugAnalyzer"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def populated_store(self, temp_dir):
        """Create a store with test data"""
        store = DebugStore(
            session_id="analysis_test",
            base_path=temp_dir,
            enable_auto_sync=False
        )

        # Add test data for a tool with multiple variants
        code_v1 = "def process(x):\n    return x * 2"
        code_v2 = "def process(x):\n    return x << 1  # Faster bit shift"

        # Variant 1: Slower but stable
        for i in range(20):
            store.write_record(
                context_type="tool",
                context_id="process",
                context_name="Process Data",
                request_data={"x": i},
                response_data={"result": i * 2},
                duration_ms=150.0 + (i % 10) * 5,
                memory_mb=10.0,
                cpu_percent=50.0,
                status="success",
                code_snapshot=code_v1,
                code_hash="hash_v1",
                variant_id="variant_1"
            )

        # Variant 2: Faster but occasional errors
        for i in range(15):
            is_error = i % 7 == 0
            store.write_record(
                context_type="tool",
                context_id="process",
                context_name="Process Data",
                request_data={"x": i},
                response_data={"result": i << 1} if not is_error else {},
                duration_ms=80.0 + (i % 5) * 3,
                memory_mb=8.0,
                cpu_percent=40.0,
                status="error" if is_error else "success",
                error=f"Bit shift overflow {i}" if is_error else None,
                code_snapshot=code_v2,
                code_hash="hash_v2",
                variant_id="variant_2"
            )

        # Add some other tool data
        for i in range(10):
            store.write_record(
                context_type="tool",
                context_id="fetch_data",
                context_name="Fetch Data",
                request_data={"url": f"http://example.com/{i}"},
                response_data={"status": 200},
                duration_ms=500.0 + i * 50,
                status="success"
            )

        store.sync_to_duckdb()
        yield store
        store.close()

    def test_analyze_context(self, populated_store):
        """Test analyzing a specific context"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process",
            include_variants=True,
            max_samples=5
        )

        assert package is not None
        assert package.context_type == "tool"
        assert package.context_name == "process"
        assert len(package.code_variants) == 2
        assert len(package.raw_samples) <= 5

        # Check summary contains key info
        assert "Total Executions: 35" in package.summary
        assert "Success Rate" in package.summary
        assert "Average Duration" in package.summary

    def test_code_variant_analysis(self, populated_store):
        """Test code variant comparison"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process",
            include_variants=True
        )

        variants = package.code_variants
        assert len(variants) == 2

        # Find each variant
        v1 = next((v for v in variants if v.variant_id == "variant_1"), None)
        v2 = next((v for v in variants if v.variant_id == "variant_2"), None)

        assert v1 is not None
        assert v2 is not None

        # Variant 1 should be slower but more reliable
        assert v1.success_rate == 1.0  # 100% success
        assert v1.avg_duration_ms > v2.avg_duration_ms

        # Variant 2 should be faster but have errors
        assert v2.success_rate < 1.0
        assert len(v2.error_samples) > 0

    def test_performance_comparison(self, populated_store):
        """Test performance comparison analysis"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        perf = package.performance_comparison

        assert 'overall' in perf
        assert 'by_status' in perf
        assert 'by_variant' in perf

        # Overall stats
        assert perf['overall']['total_executions'] == 35
        assert 'avg_duration_ms' in perf['overall']
        assert 'p95_duration_ms' in perf['overall']

        # By variant stats
        assert len(perf['by_variant']) == 2

    def test_error_analysis(self, populated_store):
        """Test error pattern analysis"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        error_analysis = package.error_analysis

        assert 'total_errors' in error_analysis
        assert 'error_rate' in error_analysis
        assert 'common_errors' in error_analysis

        # Should have detected errors from variant_2
        assert error_analysis['total_errors'] > 0
        assert error_analysis['error_rate'] > 0

        # Should have grouped common errors
        if error_analysis['common_errors']:
            # Each entry is (error_type, count)
            assert isinstance(error_analysis['common_errors'][0], tuple)

    def test_recommendations(self, populated_store):
        """Test recommendation generation"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        recommendations = package.recommendations

        assert len(recommendations) > 0

        # Should recommend the faster variant
        variant_recommendation = next(
            (r for r in recommendations if "faster" in r.lower()),
            None
        )
        assert variant_recommendation is not None

    def test_markdown_export(self, populated_store):
        """Test markdown output generation"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        markdown = package.to_markdown()

        # Check structure
        assert "# Debug Analysis" in markdown
        assert "## Summary" in markdown
        assert "## Code Variants" in markdown
        assert "## Performance Comparison" in markdown
        assert "## Recommendations" in markdown

        # Check code blocks
        assert "```python" in markdown
        assert "```json" in markdown

        # Check variant info
        assert "variant_1" in markdown
        assert "variant_2" in markdown

    def test_markdown_token_limit(self, populated_store):
        """Test markdown output with token limit"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        # Generate with very small token limit
        markdown = package.to_markdown(max_tokens=500)

        # Should be truncated
        assert len(markdown) < 3000  # Rough estimate
        # Should still have key sections
        assert "# Debug Analysis" in markdown

    def test_json_export(self, populated_store):
        """Test JSON output generation"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        json_output = package.to_json()

        # Should be valid JSON
        import json
        data = json.loads(json_output)

        assert data['context_type'] == "tool"
        assert data['context_name'] == "process"
        assert 'code_variants' in data
        assert 'performance_comparison' in data
        assert 'recommendations' in data

    def test_export_to_file(self, populated_store, temp_dir):
        """Test exporting analysis to file"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process"
        )

        output_path = Path(temp_dir) / "analysis.md"
        analyzer.export_to_file(package, str(output_path), format="markdown")

        # File should exist
        assert output_path.exists()

        # Should contain valid content
        content = output_path.read_text()
        assert "# Debug Analysis" in content
        assert "variant_1" in content

    def test_optimization_candidates(self, populated_store):
        """Test finding optimization candidates"""
        analyzer = DebugAnalyzer(populated_store)

        candidates = analyzer.get_optimization_candidates(
            min_executions=5,
            min_duration_ms=100.0
        )

        assert len(candidates) > 0

        # Should include both tools
        context_names = {c['context_name'] for c in candidates}
        assert "Fetch Data" in context_names

        # Check structure
        for candidate in candidates:
            assert 'context_type' in candidate
            assert 'context_id' in candidate
            assert 'execution_count' in candidate
            assert 'avg_duration_ms' in candidate
            assert 'total_duration_ms' in candidate
            assert 'optimization_score' in candidate

        # Should be sorted by optimization score
        scores = [c['optimization_score'] for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_representative_samples(self, populated_store):
        """Test extraction of representative samples"""
        analyzer = DebugAnalyzer(populated_store)

        package = analyzer.analyze_context(
            context_type="tool",
            context_id="process",
            max_samples=10
        )

        samples = package.raw_samples
        assert len(samples) <= 10

        # Should include diverse samples
        statuses = {s['status'] for s in samples}
        assert 'success' in statuses

        # Should have timing info
        for sample in samples:
            assert 'duration_ms' in sample
            assert 'timestamp' in sample

    def test_compare_sessions(self, temp_dir):
        """Test cross-session comparison"""
        # Create multiple stores with different data
        stores = []

        for session_id in ["session_1", "session_2"]:
            store = DebugStore(
                session_id=session_id,
                base_path=temp_dir,
                enable_auto_sync=False
            )

            # Add data
            for i in range(10):
                store.write_record(
                    context_type="tool",
                    context_id="shared_tool",
                    context_name="Shared Tool",
                    request_data={},
                    response_data={},
                    duration_ms=100.0 if session_id == "session_1" else 200.0,
                    status="success"
                )

            store.sync_to_duckdb()
            stores.append(store)

        # Compare
        analyzer = DebugAnalyzer(stores[0])
        comparison = analyzer.compare_sessions(
            stores,
            context_type="tool",
            context_id="shared_tool"
        )

        # Should contain comparison data
        assert "Cross-Session Comparison" in comparison
        assert "session_1" in comparison
        assert "session_2" in comparison

        # Clean up
        for store in stores:
            store.close()

    def test_empty_context(self, temp_dir):
        """Test analyzing non-existent context"""
        store = DebugStore(
            session_id="empty_test",
            base_path=temp_dir,
            enable_auto_sync=False
        )

        analyzer = DebugAnalyzer(store)

        # Should raise ValueError for non-existent context
        with pytest.raises(ValueError):
            analyzer.analyze_context(
                context_type="tool",
                context_id="nonexistent"
            )

        store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
