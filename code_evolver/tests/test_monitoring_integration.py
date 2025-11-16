"""
Integration tests for the complete monitoring → analysis → repair workflow.

Tests the interaction between:
- BugCatcher/PerfCatcher (capture data)
- BugAnalyzer/PerfAnalyzer (analyze patterns)
- FixTemplateStore (save and reuse fixes)
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.bugcatcher import BugCatcher, get_bugcatcher, ExceptionSeverity
from src.buganalyzer import BugAnalyzer
from src.perfanalyzer import PerfAnalyzer
from src.fix_template_store import FixTemplateStore, save_bug_fix, save_perf_optimization
from src.tool_interceptors import (
    BugCatcherInterceptor,
    PerfCatcherInterceptor,
    InterceptorChain
)


class TestBugCaptureAnalyzeFix:
    """Test complete bug capture → analyze → fix workflow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "fix_templates"

        # Reset singleton
        import src.bugcatcher
        src.bugcatcher._global_bugcatcher = None

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_capture_and_store_exception(self):
        """Test capturing exception and storing fix template."""
        # Step 1: Setup BugCatcher
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)

        # Step 2: Track request
        bugcatcher.track_request('request_1', {
            'workflow_id': 'wf_test',
            'step_id': 'step_1',
            'tool_name': 'test_tool'
        })

        # Step 3: Capture exception
        try:
            raise ValueError("Invalid input: expected int, got str")
        except ValueError as e:
            bugcatcher.capture_exception(
                e,
                request_id='request_1',
                severity=ExceptionSeverity.ERROR
            )

        # Verify exception was captured
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1

        # Step 4: Create fix template from captured exception
        exception_data = {
            'exception_type': 'ValueError',
            'exception_message': 'Invalid input: expected int, got str',
            'tool_name': 'test_tool'
        }

        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        template = save_bug_fix(
            tool_name='test_tool',
            exception_data=exception_data,
            fix_implementation='if not isinstance(value, int): value = int(value)',
            fix_description='Add type conversion for input validation'
        )

        # Verify template was saved
        assert template.template_id in store.templates

        # Step 5: Find similar issues
        similar_problem = {
            'type': 'bug',
            'exception_type': 'ValueError',
            'tool_name': 'test_tool'
        }

        matches = store.find_similar_fixes(similar_problem)
        assert len(matches) >= 1
        assert matches[0].fix_description == 'Add type conversion for input validation'

    @patch('src.buganalyzer.requests.get')
    def test_analyze_bug_patterns_and_generate_fix(self, mock_get):
        """Test analyzing bug patterns and generating fix suggestions."""
        # Mock Loki response with repeated exceptions
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {},
                        'values': [
                            ['1234567890000000000', '{"exception_type": "KeyError", "exception_message": "missing_key", "tool_name": "dict_tool", "workflow_id": "wf1"}'],
                            ['1234567890000000001', '{"exception_type": "KeyError", "exception_message": "missing_key", "tool_name": "dict_tool", "workflow_id": "wf1"}'],
                            ['1234567890000000002', '{"exception_type": "KeyError", "exception_message": "missing_key", "tool_name": "dict_tool", "workflow_id": "wf2"}'],
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Step 1: Analyze exceptions
        analyzer = BugAnalyzer(lookback_hours=1)
        exceptions = analyzer.query_exceptions(tool_name='dict_tool')

        assert len(exceptions) == 3

        # Step 2: Analyze patterns
        analysis = analyzer.analyze_exception_patterns(exceptions)

        assert analysis['total_exceptions'] == 3
        assert analysis['by_exception_type']['KeyError'] == 3

        # Step 3: Generate suggested fixes
        exception_data = exceptions[0]
        fixes = analyzer._generate_suggested_fixes(exception_data)

        # Should suggest safe dict access for KeyError
        assert any(f['type'] == 'safe_dict_access' for f in fixes)

        # Step 4: Save successful fix to template store
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        safe_dict_fix = next(f for f in fixes if f['type'] == 'safe_dict_access')

        template = store.save_fix_template(
            problem_type='bug',
            tool_name='dict_tool',
            problem_description='KeyError: missing_key',
            problem_data=exception_data,
            fix_description=safe_dict_fix['description'],
            fix_implementation=safe_dict_fix['example'],
            conditions={'exception_type': 'KeyError'}
        )

        # Step 5: Apply template to similar issue
        result = store.apply_template(template.template_id, 'dict_tool')

        assert result['success'] is True
        assert 'get' in result['fix_implementation']  # Safe dict access uses .get()


class TestPerfCaptureAnalyzeOptimize:
    """Test complete performance capture → analyze → optimize workflow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "fix_templates"

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch('src.perfanalyzer.requests.get')
    def test_analyze_performance_and_generate_optimization(self, mock_get):
        """Test analyzing performance variances and generating optimizations."""
        # Mock Loki response with performance variances
        perf_data = [
            {
                "tool_name": "slow_tool",
                "variance": 0.6,
                "current_time_ms": 300,
                "mean_time_ms": 150,
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
                            [f'123456789000000000{i}', f'{{"tool_name": "slow_tool", "variance": 0.6, "current_time_ms": 300, "mean_time_ms": 150, "workflow_id": "wf1"}}']
                            for i in range(15)
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Step 1: Analyze performance
        analyzer = PerfAnalyzer(lookback_hours=1)
        perf_issues = analyzer.query_performance_issues(tool_name='slow_tool')

        assert len(perf_issues) == 15

        # Step 2: Analyze patterns
        analysis = analyzer.analyze_performance_patterns(perf_issues)

        assert analysis['total_variance_events'] == 15
        assert 'bottlenecks' in analysis

        # Step 3: Generate recommendations
        recommendations = analyzer.generate_optimization_recommendations(
            'slow_tool',
            perf_issues
        )

        # High variance should trigger caching recommendation
        assert any(r['type'] == 'caching' for r in recommendations)

        # Step 4: Save optimization to template store
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        caching_rec = next(r for r in recommendations if r['type'] == 'caching')

        template = save_perf_optimization(
            tool_name='slow_tool',
            perf_data={'variance': 0.6, 'current_time_ms': 300},
            optimization_implementation='from functools import lru_cache\n@lru_cache(maxsize=128)',
            optimization_description=caching_rec['description'],
            optimization_type='caching'
        )

        # Verify template was saved
        assert template.problem_type == 'perf'
        assert template.metadata['optimization_type'] == 'caching'

        # Step 5: Find similar performance issues
        similar_issue = {
            'type': 'perf',
            'variance': 0.55,  # Similar variance
            'tool_name': 'slow_tool'
        }

        matches = store.find_similar_fixes(similar_issue)
        assert len(matches) >= 1
        assert 'lru_cache' in matches[0].fix_implementation


class TestInterceptorIntegration:
    """Test interceptors in complete workflow."""

    def setup_method(self):
        """Setup test fixtures."""
        # Reset singleton
        import src.bugcatcher
        src.bugcatcher._global_bugcatcher = None

    def test_bugcatcher_interceptor_full_flow(self):
        """Test BugCatcher interceptor capturing exception through tool call."""
        # Create interceptor
        interceptor = BugCatcherInterceptor()
        interceptor.enabled = True

        # Simulate tool execution with exception
        context = {}

        # Before execution
        context = interceptor.before_execution(
            tool_name='test_tool',
            args=(),
            kwargs={'value': 'invalid'},
            context=context
        )

        assert 'bugcatcher_request_id' in context

        # Simulate exception during execution
        exception = ValueError("Invalid value")

        # On exception
        suppress = interceptor.on_exception(
            tool_name='test_tool',
            exception=exception,
            context=context
        )

        # Should not suppress exception
        assert suppress is False

        # Verify exception was captured
        bugcatcher = get_bugcatcher()
        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] >= 1

    def test_perfcatcher_interceptor_variance_detection(self):
        """Test PerfCatcher interceptor detecting variance."""
        # Create interceptor with low variance threshold
        interceptor = PerfCatcherInterceptor()
        interceptor.enabled = True
        interceptor.variance_threshold = 0.2

        context = {}

        # Establish baseline with fast executions
        for i in range(10):
            context_copy = context.copy()
            context_copy = interceptor.before_execution(
                tool_name='varying_tool',
                args=(),
                kwargs={},
                context=context_copy
            )

            # Simulate fast execution
            import time
            time.sleep(0.01)

            result = interceptor.after_execution(
                tool_name='varying_tool',
                result={'success': True},
                context=context_copy
            )

        # Now trigger slow execution (should detect variance)
        context_slow = context.copy()
        context_slow = interceptor.before_execution(
            tool_name='varying_tool',
            args=(),
            kwargs={},
            context=context_slow
        )

        import time
        time.sleep(0.05)  # 5x slower

        result = interceptor.after_execution(
            tool_name='varying_tool',
            result={'success': True},
            context=context_slow
        )

        # Verify performance data is being tracked
        assert 'varying_tool' in interceptor.performance_data


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow scenarios."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "fix_templates"

        # Reset singletons
        import src.bugcatcher
        src.bugcatcher._global_bugcatcher = None
        import src.fix_template_store
        src.fix_template_store._global_fix_store = None

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_bug_learning_and_reuse(self):
        """Test that bugs are learned from and fixes are reused."""
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Scenario 1: First occurrence of ValueError
        bugcatcher.track_request('req_1', {'tool_name': 'validation_tool'})

        try:
            raise ValueError("Email validation failed")
        except ValueError as e:
            bugcatcher.capture_exception(e, request_id='req_1')

        # Developer fixes it and saves template
        template1 = save_bug_fix(
            tool_name='validation_tool',
            exception_data={
                'exception_type': 'ValueError',
                'exception_message': 'Email validation failed',
                'tool_name': 'validation_tool'
            },
            fix_implementation='import re\nif not re.match(r"[^@]+@[^@]+\.[^@]+", email): raise ValueError()',
            fix_description='Add regex validation for email format'
        )

        # Scenario 2: Similar ValueError occurs
        similar_problem = {
            'type': 'bug',
            'exception_type': 'ValueError',
            'tool_name': 'validation_tool'
        }

        # Find matching templates
        matches = store.find_similar_fixes(similar_problem)

        # Should find the previously saved fix
        assert len(matches) >= 1
        assert 'regex' in matches[0].fix_implementation.lower()

        # Apply the template
        result = store.apply_template(matches[0].template_id, 'validation_tool')

        assert result['success'] is True
        assert result['applied_count'] == 1

        # Apply again - count should increment
        result2 = store.apply_template(matches[0].template_id, 'validation_tool')
        assert result2['applied_count'] == 2

    def test_performance_optimization_learning(self):
        """Test that performance optimizations are learned and reused."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Scenario 1: Database tool has high variance
        perf_issue_1 = {
            'tool_name': 'db_query_tool',
            'variance': 0.7,
            'current_time_ms': 500,
            'mean_time_ms': 200
        }

        # Save optimization: add caching
        template1 = save_perf_optimization(
            tool_name='db_query_tool',
            perf_data=perf_issue_1,
            optimization_implementation='@lru_cache(maxsize=256)\ndef query(sql): ...',
            optimization_description='Add LRU cache to reduce database calls',
            optimization_type='caching'
        )

        # Scenario 2: Similar database tool has variance
        similar_issue = {
            'type': 'perf',
            'variance': 0.65,  # Similar high variance
            'tool_name': 'db_query_tool'
        }

        # Find matching optimizations
        matches = store.find_similar_fixes(similar_issue)

        # Should find the caching optimization
        assert len(matches) >= 1
        assert matches[0].metadata['optimization_type'] == 'caching'
        assert 'lru_cache' in matches[0].fix_implementation

    @patch('src.buganalyzer.requests.get')
    def test_complete_monitoring_cycle(self, mock_get):
        """Test complete monitoring cycle: capture → analyze → fix → reuse."""
        # Setup components
        bugcatcher = BugCatcher(loki_enabled=False, log_to_file=False)
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Mock Loki to return captured exceptions
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'result': [
                    {
                        'stream': {},
                        'values': [
                            ['1234567890000000000', '{"exception_type": "AttributeError", "exception_message": "object has no attribute x", "tool_name": "attr_tool", "workflow_id": "wf1", "traceback": "..."}']
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Step 1: Capture exceptions
        for i in range(3):
            bugcatcher.track_request(f'req_{i}', {'tool_name': 'attr_tool'})
            try:
                obj = object()
                _ = obj.missing_attr
            except AttributeError as e:
                bugcatcher.capture_exception(e, request_id=f'req_{i}')

        # Step 2: Analyze captured data
        analyzer = BugAnalyzer(lookback_hours=1)
        exceptions = analyzer.query_exceptions(tool_name='attr_tool')

        assert len(exceptions) >= 1

        # Step 3: Generate fix
        analysis = analyzer.analyze_exception_patterns(exceptions)
        reproduction = analyzer.reproduce_exception(exceptions[0])

        assert len(reproduction['suggested_fixes']) > 0

        # Step 4: Save successful fix
        best_fix = reproduction['suggested_fixes'][0]
        template = store.save_fix_template(
            problem_type='bug',
            tool_name='attr_tool',
            problem_description='AttributeError: object has no attribute x',
            problem_data=exceptions[0],
            fix_description=best_fix['description'],
            fix_implementation=best_fix['example'],
            conditions={'exception_type': 'AttributeError'}
        )

        # Step 5: Reuse fix for similar issue
        similar_problem = {
            'type': 'bug',
            'exception_type': 'AttributeError',
            'tool_name': 'attr_tool'
        }

        matches = store.find_similar_fixes(similar_problem)
        assert len(matches) >= 1

        # Apply fix
        result = store.apply_template(matches[0].template_id, 'attr_tool')
        assert result['success'] is True

        # Step 6: Verify template statistics
        stats = store.get_template_stats()
        assert stats['total_templates'] >= 1
        assert stats['bug_templates'] >= 1


class TestMonitoringSystemResilience:
    """Test monitoring system resilience and error handling."""

    def test_monitoring_continues_despite_loki_failure(self):
        """Test that monitoring continues even if Loki is unavailable."""
        # BugCatcher with Loki enabled but unavailable
        bugcatcher = BugCatcher(
            loki_enabled=True,
            loki_url="http://localhost:9999",  # Invalid URL
            log_to_file=False
        )

        # Should still track exceptions locally
        try:
            raise RuntimeError("Test error")
        except RuntimeError as e:
            bugcatcher.capture_exception(e)

        stats = bugcatcher.get_stats()
        assert stats['total_exceptions'] == 1

    def test_template_store_works_without_qdrant(self):
        """Test that template store works without Qdrant."""
        temp_dir = tempfile.mkdtemp()
        try:
            storage_path = Path(temp_dir) / "templates"

            # Create store without Qdrant
            store = FixTemplateStore(
                storage_path=str(storage_path),
                use_qdrant=False
            )

            # Should still save and find templates
            template = store.save_fix_template(
                problem_type='bug',
                tool_name='test',
                problem_description='Test',
                problem_data={},
                fix_description='Fix',
                fix_implementation='code',
                conditions={'exception_type': 'ValueError'}
            )

            # Rule-based matching should work
            problem = {'type': 'bug', 'exception_type': 'ValueError'}
            matches = store.find_similar_fixes(problem)

            assert len(matches) >= 1
        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
