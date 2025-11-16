"""
Tests for Fix Template Store - saves and reuses successful bug/performance fixes.
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.fix_template_store import (
    FixTemplate,
    FixTemplateStore,
    get_fix_template_store,
    save_bug_fix,
    save_perf_optimization
)


class TestFixTemplate:
    """Test FixTemplate functionality."""

    def test_initialization(self):
        """Test FixTemplate initialization."""
        template = FixTemplate(
            template_id="test_template",
            problem_type="bug",
            tool_name="test_tool",
            problem_description="Test error",
            problem_data={'exception_type': 'ValueError'},
            fix_description="Add validation",
            fix_implementation="if not value: raise ValueError()",
            conditions={'exception_type': 'ValueError'},
            metadata={'severity': 'high'}
        )

        assert template.template_id == "test_template"
        assert template.problem_type == "bug"
        assert template.tool_name == "test_tool"
        assert template.applied_count == 0

    def test_to_dict(self):
        """Test FixTemplate serialization to dict."""
        template = FixTemplate(
            template_id="test_template",
            problem_type="bug",
            tool_name="test_tool",
            problem_description="Test error",
            problem_data={'exception_type': 'ValueError'},
            fix_description="Add validation",
            fix_implementation="if not value: raise ValueError()",
            conditions={'exception_type': 'ValueError'}
        )

        data = template.to_dict()

        assert data['template_id'] == "test_template"
        assert data['problem_type'] == "bug"
        assert data['tool_name'] == "test_tool"
        assert 'created_at' in data
        assert data['applied_count'] == 0

    def test_from_dict(self):
        """Test FixTemplate deserialization from dict."""
        data = {
            'template_id': 'test_template',
            'problem_type': 'bug',
            'tool_name': 'test_tool',
            'problem_description': 'Test error',
            'problem_data': {'exception_type': 'ValueError'},
            'fix_description': 'Add validation',
            'fix_implementation': 'if not value: raise ValueError()',
            'conditions': {'exception_type': 'ValueError'},
            'metadata': {},
            'created_at': '2024-01-01T00:00:00',
            'applied_count': 5
        }

        template = FixTemplate.from_dict(data)

        assert template.template_id == 'test_template'
        assert template.problem_type == 'bug'
        assert template.applied_count == 5

    def test_matches_problem_bug_type_match(self):
        """Test matching bug problems."""
        template = FixTemplate(
            template_id="bug_template",
            problem_type="bug",
            tool_name="test_tool",
            problem_description="ValueError fix",
            problem_data={'exception_type': 'ValueError'},
            fix_description="Add validation",
            fix_implementation="code",
            conditions={'exception_type': 'ValueError'}
        )

        problem = {
            'type': 'bug',
            'exception_type': 'ValueError',
            'tool_name': 'test_tool'
        }

        assert template.matches_problem(problem) is True

    def test_matches_problem_bug_type_mismatch(self):
        """Test bug problem with wrong exception type."""
        template = FixTemplate(
            template_id="bug_template",
            problem_type="bug",
            tool_name="test_tool",
            problem_description="ValueError fix",
            problem_data={'exception_type': 'ValueError'},
            fix_description="Add validation",
            fix_implementation="code",
            conditions={'exception_type': 'ValueError'}
        )

        problem = {
            'type': 'bug',
            'exception_type': 'KeyError',  # Different exception
            'tool_name': 'test_tool'
        }

        assert template.matches_problem(problem) is False

    def test_matches_problem_perf_variance_match(self):
        """Test matching performance problems with variance threshold."""
        template = FixTemplate(
            template_id="perf_template",
            problem_type="perf",
            tool_name="slow_tool",
            problem_description="High variance",
            problem_data={'variance': 0.5},
            fix_description="Add caching",
            fix_implementation="@lru_cache",
            conditions={'min_variance': 0.4}
        )

        problem = {
            'type': 'perf',
            'variance': 0.6,  # Above threshold
            'tool_name': 'slow_tool'
        }

        assert template.matches_problem(problem) is True

    def test_matches_problem_perf_variance_below_threshold(self):
        """Test performance problem below variance threshold."""
        template = FixTemplate(
            template_id="perf_template",
            problem_type="perf",
            tool_name="slow_tool",
            problem_description="High variance",
            problem_data={'variance': 0.5},
            fix_description="Add caching",
            fix_implementation="@lru_cache",
            conditions={'min_variance': 0.4}
        )

        problem = {
            'type': 'perf',
            'variance': 0.3,  # Below threshold
            'tool_name': 'slow_tool'
        }

        assert template.matches_problem(problem) is False

    def test_matches_problem_wrong_type(self):
        """Test problem with wrong type."""
        template = FixTemplate(
            template_id="bug_template",
            problem_type="bug",
            tool_name="test_tool",
            problem_description="Bug fix",
            problem_data={},
            fix_description="Fix",
            fix_implementation="code",
            conditions={}
        )

        problem = {
            'type': 'perf',  # Wrong type
            'tool_name': 'test_tool'
        }

        assert template.matches_problem(problem) is False

    def test_get_embedding_text_bug(self):
        """Test embedding text generation for bug template."""
        template = FixTemplate(
            template_id="bug_template",
            problem_type="bug",
            tool_name="test_tool",
            problem_description="ValueError when parsing",
            problem_data={
                'exception_type': 'ValueError',
                'exception_message': 'invalid literal for int()'
            },
            fix_description="Add input validation",
            fix_implementation="code",
            conditions={}
        )

        embedding_text = template.get_embedding_text()

        assert 'bug' in embedding_text
        assert 'test_tool' in embedding_text
        assert 'ValueError when parsing' in embedding_text
        assert 'ValueError' in embedding_text
        assert 'invalid literal for int()' in embedding_text

    def test_get_embedding_text_perf(self):
        """Test embedding text generation for performance template."""
        template = FixTemplate(
            template_id="perf_template",
            problem_type="perf",
            tool_name="slow_tool",
            problem_description="High variance",
            problem_data={'variance': 0.5},
            fix_description="Add caching",
            fix_implementation="code",
            conditions={},
            metadata={'optimization_type': 'caching'}
        )

        embedding_text = template.get_embedding_text()

        assert 'perf' in embedding_text
        assert 'slow_tool' in embedding_text
        assert 'caching' in embedding_text


class TestFixTemplateStore:
    """Test FixTemplateStore functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "fix_templates"

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization_without_qdrant(self):
        """Test FixTemplateStore initialization without Qdrant."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        assert store.storage_path == self.storage_path
        assert store.use_qdrant is False
        assert len(store.templates) == 0

    def test_save_fix_template(self):
        """Test saving a fix template."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        template = store.save_fix_template(
            problem_type='bug',
            tool_name='test_tool',
            problem_description='ValueError: invalid input',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Add input validation',
            fix_implementation='if not value: raise ValueError()',
            conditions={'exception_type': 'ValueError'}
        )

        # Check template was created
        assert template.template_id in store.templates
        assert template.problem_type == 'bug'

        # Check file was created
        template_file = self.storage_path / f"{template.template_id}.json"
        assert template_file.exists()

        # Verify file contents
        with open(template_file) as f:
            data = json.load(f)
            assert data['problem_type'] == 'bug'
            assert data['tool_name'] == 'test_tool'

    def test_load_templates_from_disk(self):
        """Test loading templates from disk on initialization."""
        # Create a template file manually
        self.storage_path.mkdir(parents=True, exist_ok=True)

        template_data = {
            'template_id': 'existing_template',
            'problem_type': 'bug',
            'tool_name': 'old_tool',
            'problem_description': 'Old bug',
            'problem_data': {},
            'fix_description': 'Old fix',
            'fix_implementation': 'code',
            'conditions': {},
            'metadata': {},
            'created_at': '2024-01-01T00:00:00',
            'applied_count': 0
        }

        template_file = self.storage_path / "existing_template.json"
        with open(template_file, 'w') as f:
            json.dump(template_data, f)

        # Initialize store - should load existing template
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        assert 'existing_template' in store.templates
        assert store.templates['existing_template'].tool_name == 'old_tool'

    def test_find_matching_templates_rule_based(self):
        """Test rule-based template matching (fallback)."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Save templates
        store.save_fix_template(
            problem_type='bug',
            tool_name='tool1',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Fix',
            fix_implementation='code',
            conditions={'exception_type': 'ValueError'}
        )

        store.save_fix_template(
            problem_type='bug',
            tool_name='tool2',
            problem_description='KeyError',
            problem_data={'exception_type': 'KeyError'},
            fix_description='Fix',
            fix_implementation='code',
            conditions={'exception_type': 'KeyError'}
        )

        # Find matching templates
        problem = {
            'type': 'bug',
            'exception_type': 'ValueError'
        }

        matches = store._find_matching_templates(problem)

        assert len(matches) == 1
        assert matches[0].problem_data['exception_type'] == 'ValueError'

    def test_find_matching_templates_sorted_by_applied_count(self):
        """Test that matches are sorted by applied_count."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Save templates
        template1 = store.save_fix_template(
            problem_type='bug',
            tool_name='tool1',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Fix 1',
            fix_implementation='code1',
            conditions={'exception_type': 'ValueError'}
        )

        template2 = store.save_fix_template(
            problem_type='bug',
            tool_name='tool2',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Fix 2',
            fix_implementation='code2',
            conditions={'exception_type': 'ValueError'}
        )

        # Increase applied_count for template2
        template2.applied_count = 10
        template1.applied_count = 2

        # Find matches
        problem = {'type': 'bug', 'exception_type': 'ValueError'}
        matches = store._find_matching_templates(problem)

        # Should be sorted by applied_count descending
        assert matches[0].template_id == template2.template_id
        assert matches[1].template_id == template1.template_id

    def test_apply_template(self):
        """Test applying a fix template."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Save template
        template = store.save_fix_template(
            problem_type='bug',
            tool_name='test_tool',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Add validation',
            fix_implementation='if not value: raise ValueError()',
            conditions={}
        )

        initial_count = template.applied_count

        # Apply template
        result = store.apply_template(template.template_id, 'test_tool')

        assert result['success'] is True
        assert result['template_id'] == template.template_id
        assert result['fix_implementation'] == 'if not value: raise ValueError()'
        assert result['applied_count'] == initial_count + 1

    def test_apply_template_not_found(self):
        """Test applying non-existent template."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        result = store.apply_template('nonexistent_template', 'test_tool')

        assert 'error' in result
        assert 'not found' in result['error']

    def test_get_template_stats(self):
        """Test getting template statistics."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Save templates
        store.save_fix_template(
            problem_type='bug',
            tool_name='tool1',
            problem_description='Bug 1',
            problem_data={},
            fix_description='Fix',
            fix_implementation='code',
            conditions={}
        )

        store.save_fix_template(
            problem_type='perf',
            tool_name='tool2',
            problem_description='Perf issue',
            problem_data={},
            fix_description='Optimize',
            fix_implementation='code',
            conditions={}
        )

        stats = store.get_template_stats()

        assert stats['total_templates'] == 2
        assert stats['bug_templates'] == 1
        assert stats['perf_templates'] == 1
        assert 'by_tool' in stats
        assert 'most_applied' in stats

    def test_generate_template_id_deterministic(self):
        """Test that template ID generation is deterministic."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        id1 = store._generate_template_id('bug', 'tool1', 'Description')
        id2 = store._generate_template_id('bug', 'tool1', 'Description')

        assert id1 == id2

    def test_generate_template_id_unique(self):
        """Test that different inputs generate different IDs."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        id1 = store._generate_template_id('bug', 'tool1', 'Description 1')
        id2 = store._generate_template_id('bug', 'tool1', 'Description 2')

        assert id1 != id2


class TestFixTemplateStoreWithQdrant:
    """Test FixTemplateStore with Qdrant integration."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "fix_templates"

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch('src.fix_template_store.QdrantRAGMemory')
    def test_initialization_with_qdrant(self, mock_qdrant_class):
        """Test initialization with Qdrant enabled."""
        mock_qdrant = MagicMock()
        mock_qdrant_class.return_value = mock_qdrant

        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=True,
            qdrant_url="http://localhost:6333"
        )

        assert store.use_qdrant is True
        mock_qdrant_class.assert_called_once()

    @patch('src.fix_template_store.QdrantRAGMemory')
    def test_save_template_with_qdrant(self, mock_qdrant_class):
        """Test saving template stores in Qdrant."""
        mock_qdrant = MagicMock()
        mock_qdrant_class.return_value = mock_qdrant

        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=True
        )

        template = store.save_fix_template(
            problem_type='bug',
            tool_name='test_tool',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Fix',
            fix_implementation='code',
            conditions={}
        )

        # Verify Qdrant store was called
        mock_qdrant.store.assert_called_once()
        call_args = mock_qdrant.store.call_args
        assert template.template_id == call_args[1]['doc_id']

    @patch('src.fix_template_store.QdrantRAGMemory')
    def test_find_similar_fixes_with_qdrant(self, mock_qdrant_class):
        """Test finding similar fixes using Qdrant."""
        mock_qdrant = MagicMock()
        mock_qdrant_class.return_value = mock_qdrant

        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=True
        )

        # Save a template
        template = store.save_fix_template(
            problem_type='bug',
            tool_name='test_tool',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Fix',
            fix_implementation='code',
            conditions={}
        )

        # Mock Qdrant search results
        mock_qdrant.search.return_value = [
            {'metadata': {'template_id': template.template_id}}
        ]

        # Find similar fixes
        problem = {
            'type': 'bug',
            'exception_type': 'ValueError'
        }

        matches = store.find_similar_fixes(problem, top_k=5)

        # Verify Qdrant search was called
        mock_qdrant.search.assert_called_once()
        assert len(matches) == 1
        assert matches[0].template_id == template.template_id

    @patch('src.fix_template_store.QdrantRAGMemory')
    def test_find_similar_fixes_qdrant_fallback(self, mock_qdrant_class):
        """Test fallback to rule-based matching when Qdrant fails."""
        mock_qdrant = MagicMock()
        mock_qdrant.search.side_effect = Exception("Qdrant error")
        mock_qdrant_class.return_value = mock_qdrant

        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=True
        )

        # Save a template
        store.save_fix_template(
            problem_type='bug',
            tool_name='test_tool',
            problem_description='ValueError',
            problem_data={'exception_type': 'ValueError'},
            fix_description='Fix',
            fix_implementation='code',
            conditions={'exception_type': 'ValueError'}
        )

        # Find similar - should fallback to rule-based
        problem = {
            'type': 'bug',
            'exception_type': 'ValueError'
        }

        matches = store.find_similar_fixes(problem)

        # Should still find matches via fallback
        assert len(matches) == 1


class TestConvenienceFunctions:
    """Test convenience functions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Reset global store
        import src.fix_template_store
        src.fix_template_store._global_fix_store = None

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_get_fix_template_store_singleton(self):
        """Test that get_fix_template_store returns singleton."""
        store1 = get_fix_template_store()
        store2 = get_fix_template_store()

        assert store1 is store2

    @patch('src.fix_template_store.FixTemplateStore')
    def test_save_bug_fix(self, mock_store_class):
        """Test save_bug_fix convenience function."""
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store

        # Reset singleton
        import src.fix_template_store
        src.fix_template_store._global_fix_store = None

        exception_data = {
            'exception_type': 'ValueError',
            'exception_message': 'Invalid input',
            'tool_name': 'test_tool'
        }

        save_bug_fix(
            tool_name='test_tool',
            exception_data=exception_data,
            fix_implementation='code',
            fix_description='Add validation'
        )

        # Verify store was called with correct parameters
        assert mock_store.save_fix_template.called
        call_kwargs = mock_store.save_fix_template.call_args[1]
        assert call_kwargs['problem_type'] == 'bug'
        assert call_kwargs['tool_name'] == 'test_tool'

    @patch('src.fix_template_store.FixTemplateStore')
    def test_save_perf_optimization(self, mock_store_class):
        """Test save_perf_optimization convenience function."""
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store

        # Reset singleton
        import src.fix_template_store
        src.fix_template_store._global_fix_store = None

        perf_data = {
            'variance': 0.5,
            'tool_name': 'slow_tool'
        }

        save_perf_optimization(
            tool_name='slow_tool',
            perf_data=perf_data,
            optimization_implementation='@lru_cache',
            optimization_description='Add caching',
            optimization_type='caching'
        )

        # Verify store was called with correct parameters
        assert mock_store.save_fix_template.called
        call_kwargs = mock_store.save_fix_template.call_args[1]
        assert call_kwargs['problem_type'] == 'perf'
        assert call_kwargs['tool_name'] == 'slow_tool'
        assert call_kwargs['metadata']['optimization_type'] == 'caching'


class TestFixTemplateStoreEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "fix_templates"

    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_load_templates_with_corrupted_file(self):
        """Test loading templates with corrupted JSON file."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Create corrupted file
        corrupted_file = self.storage_path / "corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json }")

        # Should not crash, just log error
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        assert len(store.templates) == 0

    @patch('src.fix_template_store.QdrantRAGMemory')
    def test_qdrant_initialization_failure(self, mock_qdrant_class):
        """Test handling Qdrant initialization failure."""
        mock_qdrant_class.side_effect = Exception("Qdrant connection failed")

        # Should fall back to non-Qdrant mode
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=True
        )

        assert store.use_qdrant is False

    def test_find_similar_fixes_empty_store(self):
        """Test finding fixes when store is empty."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        problem = {'type': 'bug', 'exception_type': 'ValueError'}
        matches = store.find_similar_fixes(problem)

        assert len(matches) == 0

    def test_apply_template_increments_count_persistently(self):
        """Test that applied_count is persisted to disk."""
        store = FixTemplateStore(
            storage_path=str(self.storage_path),
            use_qdrant=False
        )

        # Save template
        template = store.save_fix_template(
            problem_type='bug',
            tool_name='test_tool',
            problem_description='Bug',
            problem_data={},
            fix_description='Fix',
            fix_implementation='code',
            conditions={}
        )

        # Apply template
        store.apply_template(template.template_id, 'test_tool')

        # Reload from disk
        template_file = self.storage_path / f"{template.template_id}.json"
        with open(template_file) as f:
            data = json.load(f)
            assert data['applied_count'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
