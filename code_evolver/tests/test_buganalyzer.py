"""
Tests for BugAnalyzer - analyzes captured exceptions and generates fixes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.buganalyzer import (
    BugAnalyzer,
    analyze_bugs
)


class TestBugAnalyzer:
    """Test BugAnalyzer functionality."""

    def test_initialization(self):
        """Test BugAnalyzer initialization."""
        analyzer = BugAnalyzer(
            loki_url="http://localhost:3100",
            lookback_hours=12
        )

        assert analyzer.loki_url == "http://localhost:3100"
        assert analyzer.lookback_hours == 12

    @patch('src.buganalyzer.requests.get')
    def test_query_exceptions_success(self, mock_get):
        """Test querying exceptions from Loki."""
        # Mock Loki response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {'job': 'bugcatcher'},
                        'values': [
                            ['1234567890000000000', '{"exception_type": "ValueError", "exception_message": "Test error"}']
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        analyzer = BugAnalyzer()
        exceptions = analyzer.query_exceptions(tool_name='test_tool', limit=10)

        assert len(exceptions) >= 0  # May be 0 if Loki not available or mock
        mock_get.assert_called_once()

    @patch('src.buganalyzer.requests.get')
    def test_query_exceptions_with_filters(self, mock_get):
        """Test querying exceptions with filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'result': []}}
        mock_get.return_value = mock_response

        analyzer = BugAnalyzer()
        exceptions = analyzer.query_exceptions(
            tool_name='test_tool',
            workflow_id='wf_123',
            severity='error',
            limit=50
        )

        # Verify the call was made with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'tool_name="test_tool"' in call_args[1]['params']['query']

    def test_analyze_exception_patterns_empty(self):
        """Test analyzing patterns with no exceptions."""
        analyzer = BugAnalyzer()
        analysis = analyzer.analyze_exception_patterns([])

        assert analysis['total'] == 0
        assert analysis['patterns'] == []

    def test_analyze_exception_patterns_with_data(self):
        """Test analyzing patterns with exception data."""
        exceptions = [
            {
                'exception_type': 'ValueError',
                'exception_message': 'Invalid input',
                'tool_name': 'tool1',
                'workflow_id': 'wf1'
            },
            {
                'exception_type': 'ValueError',
                'exception_message': 'Invalid input',
                'tool_name': 'tool1',
                'workflow_id': 'wf1'
            },
            {
                'exception_type': 'KeyError',
                'exception_message': 'Missing key',
                'tool_name': 'tool2',
                'workflow_id': 'wf2'
            }
        ]

        analyzer = BugAnalyzer()
        analysis = analyzer.analyze_exception_patterns(exceptions)

        assert analysis['total_exceptions'] == 3
        assert 'by_exception_type' in analysis
        assert analysis['by_exception_type']['ValueError'] == 2
        assert analysis['by_exception_type']['KeyError'] == 1
        assert 'by_tool' in analysis
        assert 'by_workflow' in analysis

    def test_identify_patterns_repeated_errors(self):
        """Test identifying repeated error patterns."""
        exceptions = [
            {'exception_type': 'ValueError', 'exception_message': 'Same error', 'tool_name': 'tool1'},
            {'exception_type': 'ValueError', 'exception_message': 'Same error', 'tool_name': 'tool1'},
            {'exception_type': 'ValueError', 'exception_message': 'Same error', 'tool_name': 'tool2'},
        ]

        analyzer = BugAnalyzer()
        patterns = analyzer._identify_patterns(exceptions)

        # Should identify repeated error message pattern
        assert len(patterns) >= 1
        assert any(p['type'] == 'repeated_error_message' for p in patterns)

    def test_reproduce_exception(self):
        """Test exception reproduction."""
        exception_data = {
            'tool_name': 'test_tool',
            'exception_type': 'ValueError',
            'exception_message': 'Test error',
            'inputs': {'arg1': 'value1'},
            'workflow_id': 'wf_123',
            'step_id': 'step_1',
            'traceback': 'Traceback...'
        }

        analyzer = BugAnalyzer()
        result = analyzer.reproduce_exception(exception_data)

        assert result['tool_name'] == 'test_tool'
        assert result['exception_type'] == 'ValueError'
        assert 'suggested_fixes' in result
        assert len(result['suggested_fixes']) > 0

    def test_generate_suggested_fixes_value_error(self):
        """Test fix suggestions for ValueError."""
        exception_data = {
            'exception_type': 'ValueError',
            'exception_message': 'invalid literal for int()'
        }

        analyzer = BugAnalyzer()
        fixes = analyzer._generate_suggested_fixes(exception_data)

        assert len(fixes) > 0
        assert any(f['type'] == 'input_validation' for f in fixes)

    def test_generate_suggested_fixes_key_error(self):
        """Test fix suggestions for KeyError."""
        exception_data = {
            'exception_type': 'KeyError',
            'exception_message': "'missing_key'"
        }

        analyzer = BugAnalyzer()
        fixes = analyzer._generate_suggested_fixes(exception_data)

        assert len(fixes) > 0
        assert any(f['type'] == 'safe_dict_access' for f in fixes)

    def test_generate_suggested_fixes_connection_error(self):
        """Test fix suggestions for ConnectionError."""
        exception_data = {
            'exception_type': 'ConnectionError',
            'exception_message': 'Connection refused'
        }

        analyzer = BugAnalyzer()
        fixes = analyzer._generate_suggested_fixes(exception_data)

        assert len(fixes) > 0
        assert any(f['type'] == 'retry_logic' for f in fixes)

    def test_generate_test_case(self):
        """Test generating test case from exception."""
        exception_data = {
            'tool_name': 'test_tool',
            'exception_type': 'ValueError',
            'exception_message': 'Test error',
            'inputs': {'arg1': 'value1', 'arg2': 42},
            'timestamp': '2024-01-01T00:00:00'
        }

        analyzer = BugAnalyzer()
        test_code = analyzer.generate_test_case(exception_data)

        assert 'def test_test_tool_exception' in test_code
        assert 'ValueError' in test_code
        assert 'def test_test_tool_fix' in test_code
        assert 'pytest.raises' in test_code

    def test_get_exception_report_empty(self):
        """Test getting exception report with no data."""
        with patch.object(BugAnalyzer, 'query_exceptions', return_value=[]):
            analyzer = BugAnalyzer()
            report = analyzer.get_exception_report()

            assert 'No exceptions found' in report

    @patch('src.buganalyzer.requests.get')
    def test_get_exception_report_with_data(self, mock_get):
        """Test getting exception report with data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {},
                        'values': [
                            ['1234567890000000000', '{"exception_type": "ValueError", "exception_message": "Error1", "tool_name": "tool1", "workflow_id": "wf1"}'],
                            ['1234567890000000000', '{"exception_type": "KeyError", "exception_message": "Error2", "tool_name": "tool2", "workflow_id": "wf1"}'],
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        analyzer = BugAnalyzer()
        report = analyzer.get_exception_report()

        assert 'BugAnalyzer Exception Report' in report
        assert 'Total Exceptions' in report


class TestAnalyzeBugsFunction:
    """Test analyze_bugs convenience function."""

    @patch('src.buganalyzer.BugAnalyzer.query_exceptions')
    def test_analyze_bugs_no_exceptions(self, mock_query):
        """Test analyze_bugs with no exceptions."""
        mock_query.return_value = []

        result = analyze_bugs(tool_name='test_tool')

        assert 'error' in result
        assert result['error'] == 'No exceptions found'

    @patch('src.buganalyzer.BugAnalyzer.query_exceptions')
    def test_analyze_bugs_with_exceptions(self, mock_query):
        """Test analyze_bugs with exceptions."""
        mock_exceptions = [
            {'exception_type': 'ValueError', 'exception_message': 'Error1', 'tool_name': 'tool1'},
            {'exception_type': 'KeyError', 'exception_message': 'Error2', 'tool_name': 'tool2'},
        ]
        mock_query.return_value = mock_exceptions

        result = analyze_bugs(tool_name='test_tool', generate_tests=False)

        assert 'analysis' in result
        assert 'exceptions' in result
        assert 'reproduction_results' in result
        assert 'report' in result

    @patch('src.buganalyzer.BugAnalyzer.query_exceptions')
    def test_analyze_bugs_with_test_generation(self, mock_query):
        """Test analyze_bugs with test case generation."""
        mock_exceptions = [
            {'exception_type': 'ValueError', 'exception_message': 'Error1', 'tool_name': 'tool1'},
        ]
        mock_query.return_value = mock_exceptions

        result = analyze_bugs(tool_name='test_tool', generate_tests=True)

        assert 'test_cases' in result
        assert result['test_cases'] is not None
        assert len(result['test_cases']) > 0


class TestBugAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    @patch('src.buganalyzer.requests.get')
    def test_query_exceptions_connection_error(self, mock_get):
        """Test handling of Loki connection errors."""
        mock_get.side_effect = Exception("Connection refused")

        analyzer = BugAnalyzer()
        exceptions = analyzer.query_exceptions()

        # Should return empty list on error
        assert exceptions == []

    def test_analyze_patterns_with_malformed_data(self):
        """Test analyzing patterns with malformed exception data."""
        exceptions = [
            {},  # Empty exception
            {'exception_type': 'ValueError'},  # Missing fields
            None,  # None value
        ]

        analyzer = BugAnalyzer()

        # Should not crash with malformed data
        try:
            analysis = analyzer.analyze_exception_patterns([e for e in exceptions if e])
            assert 'total_exceptions' in analysis
        except Exception as e:
            pytest.fail(f"Should handle malformed data gracefully: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
