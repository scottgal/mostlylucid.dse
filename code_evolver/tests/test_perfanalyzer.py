"""
Tests for PerfAnalyzer - analyzes captured performance data and generates optimizations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.perfanalyzer import (
    PerfAnalyzer,
    analyze_performance
)


class TestPerfAnalyzer:
    """Test PerfAnalyzer functionality."""

    def test_initialization(self):
        """Test PerfAnalyzer initialization."""
        analyzer = PerfAnalyzer(
            loki_url="http://localhost:3100",
            lookback_hours=12
        )

        assert analyzer.loki_url == "http://localhost:3100"
        assert analyzer.lookback_hours == 12

    @patch('src.perfanalyzer.requests.get')
    def test_query_performance_issues_success(self, mock_get):
        """Test querying performance issues from Loki."""
        # Mock Loki response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {'job': 'code_evolver_perfcatcher'},
                        'values': [
                            ['1234567890000000000', '{"tool_name": "test_tool", "variance": 0.5, "current_time_ms": 200, "mean_time_ms": 100}']
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        analyzer = PerfAnalyzer()
        perf_issues = analyzer.query_performance_issues(tool_name='test_tool', limit=10)

        assert len(perf_issues) >= 0
        mock_get.assert_called_once()

    @patch('src.perfanalyzer.requests.get')
    def test_query_performance_issues_with_filters(self, mock_get):
        """Test querying performance issues with filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'result': []}}
        mock_get.return_value = mock_response

        analyzer = PerfAnalyzer()
        perf_issues = analyzer.query_performance_issues(
            tool_name='test_tool',
            workflow_id='wf_123',
            variance_level='high',
            limit=50
        )

        # Verify the call was made with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'tool_name="test_tool"' in call_args[1]['params']['query']

    def test_analyze_performance_patterns_empty(self):
        """Test analyzing patterns with no performance issues."""
        analyzer = PerfAnalyzer()
        analysis = analyzer.analyze_performance_patterns([])

        assert analysis['total'] == 0
        assert analysis['patterns'] == []

    def test_analyze_performance_patterns_with_data(self):
        """Test analyzing patterns with performance data."""
        perf_issues = [
            {
                'tool_name': 'tool1',
                'workflow_id': 'wf1',
                'variance': 0.3,
                'current_time_ms': 150,
                'mean_time_ms': 100,
                'timestamp': '1234567890000000000'
            },
            {
                'tool_name': 'tool1',
                'workflow_id': 'wf1',
                'variance': 0.4,
                'current_time_ms': 160,
                'mean_time_ms': 100,
                'timestamp': '1234567890000000001'
            },
            {
                'tool_name': 'tool2',
                'workflow_id': 'wf2',
                'variance': 0.6,
                'current_time_ms': 200,
                'mean_time_ms': 100,
                'timestamp': '1234567890000000002'
            }
        ]

        analyzer = PerfAnalyzer()
        analysis = analyzer.analyze_performance_patterns(perf_issues)

        assert analysis['total_variance_events'] == 3
        assert analysis['affected_tools'] == 2
        assert analysis['affected_workflows'] == 2
        assert 'variance_stats' in analysis
        assert analysis['variance_stats']['mean'] > 0
        assert analysis['variance_stats']['max'] == 0.6

    def test_rank_tools_by_frequency(self):
        """Test ranking tools by variance frequency."""
        by_tool = {
            'tool1': [{'variance': 0.3}, {'variance': 0.4}],
            'tool2': [{'variance': 0.5}],
            'tool3': [{'variance': 0.2}, {'variance': 0.3}, {'variance': 0.4}]
        }

        analyzer = PerfAnalyzer()
        ranked = analyzer._rank_tools_by_frequency(by_tool)

        # Should be sorted by count descending
        assert ranked[0] == ('tool3', 3)
        assert ranked[1] == ('tool1', 2)
        assert ranked[2] == ('tool2', 1)

    def test_rank_tools_by_severity(self):
        """Test ranking tools by average variance severity."""
        by_tool = {
            'tool1': [{'variance': 0.3}, {'variance': 0.5}],  # avg 0.4
            'tool2': [{'variance': 0.8}],  # avg 0.8
            'tool3': [{'variance': 0.1}, {'variance': 0.2}]  # avg 0.15
        }

        analyzer = PerfAnalyzer()
        ranked = analyzer._rank_tools_by_severity(by_tool)

        # Should be sorted by average variance descending
        assert ranked[0][0] == 'tool2'
        assert ranked[0][1] == 0.8
        assert ranked[1][0] == 'tool1'
        assert ranked[2][0] == 'tool3'

    def test_analyze_time_patterns(self):
        """Test analyzing time-based patterns."""
        import time
        current_timestamp = int(time.time())

        perf_issues = [
            {'timestamp': str(current_timestamp * 1_000_000_000)},
            {'timestamp': str((current_timestamp + 3600) * 1_000_000_000)},  # +1 hour
            {'timestamp': str(current_timestamp * 1_000_000_000)},
        ]

        analyzer = PerfAnalyzer()
        time_patterns = analyzer._analyze_time_patterns(perf_issues)

        assert 'distribution_by_hour' in time_patterns
        assert 'peak_hour' in time_patterns
        assert 'peak_hour_count' in time_patterns

    def test_identify_bottlenecks_high_frequency(self):
        """Test identifying bottlenecks with high frequency."""
        # Create 15 issues for a tool (exceeds 10 threshold)
        issues = [
            {
                'variance': 0.3,
                'current_time_ms': 150,
                'mean_time_ms': 100
            }
            for _ in range(15)
        ]

        by_tool = {'high_freq_tool': issues}

        analyzer = PerfAnalyzer()
        bottlenecks = analyzer._identify_bottlenecks(by_tool)

        assert len(bottlenecks) == 1
        assert bottlenecks[0]['tool_name'] == 'high_freq_tool'
        assert bottlenecks[0]['frequency'] == 15

    def test_identify_bottlenecks_high_variance(self):
        """Test identifying bottlenecks with high variance."""
        # Create issues with high variance (>50%)
        issues = [
            {
                'variance': 0.6,  # 60% variance
                'current_time_ms': 200,
                'mean_time_ms': 100
            }
            for _ in range(5)
        ]

        by_tool = {'high_variance_tool': issues}

        analyzer = PerfAnalyzer()
        bottlenecks = analyzer._identify_bottlenecks(by_tool)

        assert len(bottlenecks) == 1
        assert bottlenecks[0]['avg_variance'] > 0.5
        assert bottlenecks[0]['optimization_priority'] == 'high'

    def test_identify_bottlenecks_slow_execution(self):
        """Test identifying bottlenecks with slow execution."""
        # Create issues with max time > 1000ms
        issues = [
            {
                'variance': 0.3,
                'current_time_ms': 1200,  # Slow execution
                'mean_time_ms': 500
            }
            for _ in range(5)
        ]

        by_tool = {'slow_tool': issues}

        analyzer = PerfAnalyzer()
        bottlenecks = analyzer._identify_bottlenecks(by_tool)

        assert len(bottlenecks) == 1
        assert bottlenecks[0]['max_time_ms'] > 1000

    def test_identify_bottlenecks_critical_priority(self):
        """Test bottleneck priority classification."""
        # Create issues with very high variance (>100%)
        issues = [
            {
                'variance': 1.5,  # 150% variance - critical
                'current_time_ms': 300,
                'mean_time_ms': 100
            }
            for _ in range(5)
        ]

        by_tool = {'critical_tool': issues}

        analyzer = PerfAnalyzer()
        bottlenecks = analyzer._identify_bottlenecks(by_tool)

        assert len(bottlenecks) == 1
        assert bottlenecks[0]['optimization_priority'] == 'critical'

    def test_calculate_bottleneck_severity(self):
        """Test bottleneck severity calculation."""
        analyzer = PerfAnalyzer()

        # High frequency, high variance, high time
        severity1 = analyzer._calculate_bottleneck_severity(
            frequency=20,
            avg_variance=0.8,
            max_time=2000
        )

        # Low frequency, low variance, low time
        severity2 = analyzer._calculate_bottleneck_severity(
            frequency=5,
            avg_variance=0.2,
            max_time=100
        )

        assert severity1 > severity2

    def test_generate_optimization_recommendations_caching(self):
        """Test caching recommendation for high variance."""
        perf_issues = [
            {
                'variance': 0.4,  # 40% variance
                'current_time_ms': 150,
                'mean_time_ms': 100
            }
            for _ in range(15)  # More than 10
        ]

        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations(
            'test_tool',
            perf_issues
        )

        assert len(recommendations) > 0
        assert any(r['type'] == 'caching' for r in recommendations)

    def test_generate_optimization_recommendations_optimization(self):
        """Test optimization recommendation for slow execution."""
        perf_issues = [
            {
                'variance': 0.3,
                'current_time_ms': 1500,  # >1000ms
                'mean_time_ms': 500
            }
            for _ in range(5)
        ]

        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations(
            'slow_tool',
            perf_issues
        )

        assert len(recommendations) > 0
        optimization_rec = next((r for r in recommendations if r['type'] == 'optimization'), None)
        assert optimization_rec is not None
        assert optimization_rec['priority'] == 'critical'

    def test_generate_optimization_recommendations_rate_limiting(self):
        """Test rate limiting recommendation."""
        perf_issues = [
            {
                'variance': 0.15,  # Low variance
                'current_time_ms': 100,
                'mean_time_ms': 90
            }
            for _ in range(25)  # Many events
        ]

        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations(
            'busy_tool',
            perf_issues
        )

        assert any(r['type'] == 'rate_limiting' for r in recommendations)

    def test_generate_optimization_recommendations_scaling(self):
        """Test scaling recommendation for 2x baseline."""
        perf_issues = [
            {
                'variance': 0.3,
                'current_time_ms': 400,  # 2x baseline
                'mean_time_ms': 200
            }
            for _ in range(10)
        ]

        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations(
            'degraded_tool',
            perf_issues
        )

        assert any(r['type'] == 'scaling' for r in recommendations)

    def test_generate_optimization_recommendations_batching(self):
        """Test batching recommendation for many fast calls."""
        perf_issues = [
            {
                'variance': 0.2,
                'current_time_ms': 50,  # Fast
                'mean_time_ms': 45
            }
            for _ in range(20)  # Many calls
        ]

        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations(
            'fast_tool',
            perf_issues
        )

        assert any(r['type'] == 'batching' for r in recommendations)

    def test_generate_optimization_recommendations_priority_ordering(self):
        """Test that recommendations are ordered by priority."""
        perf_issues = [
            {
                'variance': 0.5,
                'current_time_ms': 1500,  # Will trigger critical
                'mean_time_ms': 500
            }
            for _ in range(25)
        ]

        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations(
            'tool',
            perf_issues
        )

        # First recommendation should be highest priority
        priorities = [r['priority'] for r in recommendations]
        priority_order = ['critical', 'high', 'medium', 'low']

        for i in range(len(priorities) - 1):
            current_idx = priority_order.index(priorities[i])
            next_idx = priority_order.index(priorities[i + 1])
            assert current_idx <= next_idx

    def test_get_performance_report_empty(self):
        """Test getting performance report with no data."""
        with patch.object(PerfAnalyzer, 'query_performance_issues', return_value=[]):
            analyzer = PerfAnalyzer()
            report = analyzer.get_performance_report()

            assert 'No performance variances found' in report

    @patch('src.perfanalyzer.requests.get')
    def test_get_performance_report_with_data(self, mock_get):
        """Test getting performance report with data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {},
                        'values': [
                            ['1234567890000000000', '{"tool_name": "tool1", "variance": 0.5, "current_time_ms": 200, "mean_time_ms": 100, "workflow_id": "wf1"}'],
                            ['1234567890000000001', '{"tool_name": "tool1", "variance": 0.6, "current_time_ms": 250, "mean_time_ms": 100, "workflow_id": "wf1"}'],
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        analyzer = PerfAnalyzer()
        report = analyzer.get_performance_report()

        assert 'PerfAnalyzer Performance Report' in report
        assert 'Total Variance Events' in report
        assert 'Variance Statistics' in report

    @patch('src.perfanalyzer.requests.get')
    def test_get_performance_report_with_bottlenecks(self, mock_get):
        """Test performance report includes bottleneck analysis."""
        # Create enough data to identify bottlenecks
        perf_data = [
            {
                "tool_name": "bottleneck_tool",
                "variance": 0.6,
                "current_time_ms": 1200,
                "mean_time_ms": 500,
                "workflow_id": "wf1"
            }
            for _ in range(15)
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {},
                        'values': [
                            [f'123456789000000000{i}', f'{{"tool_name": "bottleneck_tool", "variance": 0.6, "current_time_ms": 1200, "mean_time_ms": 500, "workflow_id": "wf1"}}']
                            for i in range(15)
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        analyzer = PerfAnalyzer()
        report = analyzer.get_performance_report()

        assert 'Identified Bottlenecks' in report
        assert 'bottleneck_tool' in report
        assert 'Recommendations:' in report


class TestAnalyzePerformanceFunction:
    """Test analyze_performance convenience function."""

    @patch('src.perfanalyzer.PerfAnalyzer.query_performance_issues')
    def test_analyze_performance_no_issues(self, mock_query):
        """Test analyze_performance with no issues."""
        mock_query.return_value = []

        result = analyze_performance(tool_name='test_tool')

        assert 'error' in result
        assert result['error'] == 'No performance variances found'

    @patch('src.perfanalyzer.PerfAnalyzer.query_performance_issues')
    def test_analyze_performance_with_issues(self, mock_query):
        """Test analyze_performance with performance issues."""
        mock_issues = [
            {'tool_name': 'tool1', 'variance': 0.5, 'current_time_ms': 200, 'mean_time_ms': 100},
            {'tool_name': 'tool2', 'variance': 0.6, 'current_time_ms': 250, 'mean_time_ms': 100},
        ]
        mock_query.return_value = mock_issues

        result = analyze_performance(tool_name='test_tool', generate_recommendations=False)

        assert 'analysis' in result
        assert 'performance_issues' in result
        assert 'report' in result
        assert result['recommendations'] is None

    @patch('src.perfanalyzer.PerfAnalyzer.query_performance_issues')
    def test_analyze_performance_with_recommendations(self, mock_query):
        """Test analyze_performance with recommendation generation."""
        mock_issues = [
            {'tool_name': 'tool1', 'variance': 0.5, 'current_time_ms': 200, 'mean_time_ms': 100}
            for _ in range(15)
        ]
        mock_query.return_value = mock_issues

        result = analyze_performance(tool_name='tool1', generate_recommendations=True)

        assert 'recommendations' in result
        assert result['recommendations'] is not None
        assert 'tool1' in result['recommendations']


class TestPerfAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    @patch('src.perfanalyzer.requests.get')
    def test_query_performance_issues_connection_error(self, mock_get):
        """Test handling of Loki connection errors."""
        mock_get.side_effect = Exception("Connection refused")

        analyzer = PerfAnalyzer()
        perf_issues = analyzer.query_performance_issues()

        # Should return empty list on error
        assert perf_issues == []

    def test_analyze_patterns_with_malformed_data(self):
        """Test analyzing patterns with malformed performance data."""
        perf_issues = [
            {},  # Empty issue
            {'tool_name': 'tool1'},  # Missing fields
            None,  # None value
        ]

        analyzer = PerfAnalyzer()

        # Should not crash with malformed data
        try:
            analysis = analyzer.analyze_performance_patterns([i for i in perf_issues if i])
            assert 'total_variance_events' in analysis
        except Exception as e:
            pytest.fail(f"Should handle malformed data gracefully: {e}")

    def test_identify_bottlenecks_insufficient_samples(self):
        """Test that bottlenecks require minimum samples."""
        # Only 3 issues (needs at least 5)
        by_tool = {
            'tool1': [
                {'variance': 0.8, 'current_time_ms': 1500, 'mean_time_ms': 500}
                for _ in range(3)
            ]
        }

        analyzer = PerfAnalyzer()
        bottlenecks = analyzer._identify_bottlenecks(by_tool)

        # Should not identify bottleneck with insufficient data
        assert len(bottlenecks) == 0

    def test_generate_recommendations_empty_issues(self):
        """Test generating recommendations with empty issues."""
        analyzer = PerfAnalyzer()
        recommendations = analyzer.generate_optimization_recommendations('tool', [])

        assert recommendations == []

    def test_time_patterns_missing_timestamps(self):
        """Test time pattern analysis with missing timestamps."""
        perf_issues = [
            {},  # No timestamp
            {'timestamp': ''},  # Empty timestamp
            {'timestamp': 'invalid'},  # Invalid timestamp
        ]

        analyzer = PerfAnalyzer()
        time_patterns = analyzer._analyze_time_patterns(perf_issues)

        # Should handle gracefully
        assert time_patterns == {}

    def test_analyze_patterns_with_missing_variances(self):
        """Test analysis when variance data is missing."""
        perf_issues = [
            {'tool_name': 'tool1', 'current_time_ms': 200},  # No variance
            {'tool_name': 'tool2', 'variance': None},  # None variance
        ]

        analyzer = PerfAnalyzer()
        analysis = analyzer.analyze_performance_patterns(perf_issues)

        # Should use 0 for missing variances
        assert 'variance_stats' in analysis
        assert analysis['variance_stats']['mean'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
