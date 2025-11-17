"""
Pytest fixtures and configuration for monitoring tests.

Provides shared fixtures for:
- BugCatcher instances
- PerfCatcher instances
- Mock Loki responses
- Temporary storage directories
- Sample exception/performance data
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from src.bugcatcher import BugCatcher, ExceptionSeverity
from src.fix_template_store import FixTemplateStore


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def bugcatcher_instance():
    """Create a BugCatcher instance for testing."""
    # Reset singleton
    import src.bugcatcher
    src.bugcatcher._global_bugcatcher = None

    bugcatcher = BugCatcher(
        loki_enabled=False,
        log_to_file=False,
        cache_size=100
    )
    yield bugcatcher

    # Reset after test
    bugcatcher.reset_stats()


@pytest.fixture
def fix_template_store(temp_dir):
    """Create a FixTemplateStore instance for testing."""
    storage_path = Path(temp_dir) / "fix_templates"

    # Reset singleton
    import src.fix_template_store
    src.fix_template_store._global_fix_store = None

    store = FixTemplateStore(
        storage_path=str(storage_path),
        use_qdrant=False
    )
    yield store


@pytest.fixture
def sample_exception_data():
    """Sample exception data for testing."""
    return {
        'exception_type': 'ValueError',
        'exception_message': 'Invalid input: expected int, got str',
        'tool_name': 'test_tool',
        'workflow_id': 'wf_test',
        'step_id': 'step_1',
        'timestamp': '2024-01-01T00:00:00',
        'traceback': 'Traceback (most recent call last):\n  File "test.py", line 10\n    raise ValueError()',
        'inputs': {'value': 'invalid'},
        'severity': 'error'
    }


@pytest.fixture
def sample_performance_data():
    """Sample performance data for testing."""
    return {
        'tool_name': 'slow_tool',
        'workflow_id': 'wf_perf',
        'variance': 0.5,
        'current_time_ms': 200,
        'mean_time_ms': 100,
        'std_dev_ms': 25,
        'timestamp': '2024-01-01T00:00:00',
        'variance_level': 'medium'
    }


@pytest.fixture
def mock_loki_exception_response():
    """Mock Loki API response for exception queries."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': {
            'result': [
                {
                    'stream': {'job': 'bugcatcher'},
                    'values': [
                        [
                            '1234567890000000000',
                            '{"exception_type": "ValueError", "exception_message": "Test error", "tool_name": "test_tool", "workflow_id": "wf1"}'
                        ],
                        [
                            '1234567890000000001',
                            '{"exception_type": "KeyError", "exception_message": "missing_key", "tool_name": "dict_tool", "workflow_id": "wf1"}'
                        ]
                    ]
                }
            ]
        }
    }
    return mock_response


@pytest.fixture
def mock_loki_performance_response():
    """Mock Loki API response for performance queries."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': {
            'result': [
                {
                    'stream': {'job': 'code_evolver_perfcatcher'},
                    'values': [
                        [
                            f'123456789000000000{i}',
                            '{"tool_name": "slow_tool", "variance": 0.6, "current_time_ms": 300, "mean_time_ms": 150, "workflow_id": "wf1"}'
                        ]
                        for i in range(10)
                    ]
                }
            ]
        }
    }
    return mock_response


@pytest.fixture
def mock_loki_empty_response():
    """Mock Loki API response with no results."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': {
            'result': []
        }
    }
    return mock_response


@pytest.fixture
def sample_exceptions():
    """Sample list of exceptions for pattern analysis."""
    return [
        {
            'exception_type': 'ValueError',
            'exception_message': 'Invalid input',
            'tool_name': 'tool1',
            'workflow_id': 'wf1',
            'timestamp': '2024-01-01T00:00:00'
        },
        {
            'exception_type': 'ValueError',
            'exception_message': 'Invalid input',
            'tool_name': 'tool1',
            'workflow_id': 'wf1',
            'timestamp': '2024-01-01T00:01:00'
        },
        {
            'exception_type': 'KeyError',
            'exception_message': 'missing_key',
            'tool_name': 'tool2',
            'workflow_id': 'wf2',
            'timestamp': '2024-01-01T00:02:00'
        },
        {
            'exception_type': 'AttributeError',
            'exception_message': 'no attribute x',
            'tool_name': 'tool3',
            'workflow_id': 'wf3',
            'timestamp': '2024-01-01T00:03:00'
        }
    ]


@pytest.fixture
def sample_performance_issues():
    """Sample list of performance issues for analysis."""
    return [
        {
            'tool_name': 'tool1',
            'workflow_id': 'wf1',
            'variance': 0.4,
            'current_time_ms': 150,
            'mean_time_ms': 100,
            'timestamp': '1234567890000000000'
        },
        {
            'tool_name': 'tool1',
            'workflow_id': 'wf1',
            'variance': 0.5,
            'current_time_ms': 160,
            'mean_time_ms': 100,
            'timestamp': '1234567890000000001'
        },
        {
            'tool_name': 'tool2',
            'workflow_id': 'wf2',
            'variance': 0.8,
            'current_time_ms': 300,
            'mean_time_ms': 150,
            'timestamp': '1234567890000000002'
        },
        {
            'tool_name': 'tool1',
            'workflow_id': 'wf1',
            'variance': 0.3,
            'current_time_ms': 140,
            'mean_time_ms': 100,
            'timestamp': '1234567890000000003'
        }
    ]


@pytest.fixture
def sample_fix_template_data():
    """Sample fix template data."""
    return {
        'template_id': 'test_template_12345678',
        'problem_type': 'bug',
        'tool_name': 'validation_tool',
        'problem_description': 'ValueError: Email validation failed',
        'problem_data': {
            'exception_type': 'ValueError',
            'exception_message': 'Email validation failed'
        },
        'fix_description': 'Add regex validation for email format',
        'fix_implementation': 'import re\nif not re.match(r"[^@]+@[^@]+\\.[^@]+", email): raise ValueError()',
        'conditions': {
            'exception_type': 'ValueError',
            'tool_name': 'validation_tool'
        },
        'metadata': {
            'severity': 'medium'
        },
        'created_at': '2024-01-01T00:00:00',
        'applied_count': 0
    }


@pytest.fixture
def sample_perf_template_data():
    """Sample performance optimization template data."""
    return {
        'template_id': 'perf_template_87654321',
        'problem_type': 'perf',
        'tool_name': 'db_query_tool',
        'problem_description': 'Performance variance 50.0%',
        'problem_data': {
            'variance': 0.5,
            'current_time_ms': 300,
            'mean_time_ms': 200
        },
        'fix_description': 'Add LRU cache to reduce database calls',
        'fix_implementation': '@lru_cache(maxsize=256)\ndef query(sql): ...',
        'conditions': {
            'tool_name': 'db_query_tool',
            'min_variance': 0.4
        },
        'metadata': {
            'optimization_type': 'caching'
        },
        'created_at': '2024-01-01T00:00:00',
        'applied_count': 0
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    import src.bugcatcher
    import src.fix_template_store

    # Store original values
    original_bugcatcher = getattr(src.bugcatcher, '_global_bugcatcher', None) if hasattr(src, 'bugcatcher') else None
    original_store = getattr(src.fix_template_store, '_global_fix_store', None) if hasattr(src, 'fix_template_store') else None

    # Reset
    if hasattr(src, 'bugcatcher') and hasattr(src.bugcatcher, '_global_bugcatcher'):
        src.bugcatcher._global_bugcatcher = None
    if hasattr(src, 'fix_template_store') and hasattr(src.fix_template_store, '_global_fix_store'):
        src.fix_template_store._global_fix_store = None

    yield

    # Restore (optional - helps with test isolation)
    if hasattr(src, 'bugcatcher') and hasattr(src.bugcatcher, '_global_bugcatcher'):
        src.bugcatcher._global_bugcatcher = original_bugcatcher
    if hasattr(src, 'fix_template_store') and hasattr(src.fix_template_store, '_global_fix_store'):
        src.fix_template_store._global_fix_store = original_store


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client for testing."""
    mock_client = MagicMock()
    mock_client.store.return_value = {'status': 'success'}
    mock_client.search.return_value = [
        {
            'metadata': {
                'template_id': 'test_template',
                'problem_type': 'bug'
            },
            'score': 0.95
        }
    ]
    return mock_client


# Pytest configuration
def pytest_configure(config):
    """Pytest configuration hook."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "loki: mark test as requiring Loki"
    )
    config.addinivalue_line(
        "markers", "qdrant: mark test as requiring Qdrant"
    )
