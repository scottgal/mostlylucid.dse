"""Tests for Consensus Engine."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forge.core.consensus import ConsensusEngine, MetricDimension
from forge.core.registry import ForgeRegistry
from src.rag_memory import RAGMemory
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager


@pytest.fixture
def config_manager():
    """Create config manager."""
    return ConfigManager("config.example.yaml")


@pytest.fixture
def registry(config_manager):
    """Create registry."""
    rag = RAGMemory(config_manager)
    tools = ToolsManager(config_manager)
    return ForgeRegistry(rag, tools)


@pytest.fixture
def consensus(registry, config_manager):
    """Create consensus engine."""
    return ConsensusEngine(
        registry=registry,
        config=config_manager.config
    )


def test_calculate_consensus_score(consensus):
    """Test consensus score calculation."""
    execution_history = [
        {
            'timestamp': '2025-11-18T12:00:00Z',
            'metrics': {'latency_ms': 150},
            'success': True
        },
        {
            'timestamp': '2025-11-18T12:01:00Z',
            'metrics': {'latency_ms': 180},
            'success': True
        }
    ]

    validation_result = {
        'validation_score': 0.95,
        'stages': [
            {'name': 'security_static', 'score': 0.98}
        ]
    }

    score = consensus.calculate_consensus_score(
        tool_id="test_tool",
        version="1.0.0",
        execution_history=execution_history,
        validation_result=validation_result
    )

    assert score is not None
    assert 0.0 <= score.weight <= 1.0
    assert 'correctness' in score.scores


def test_record_execution(consensus, registry):
    """Test recording execution metrics."""
    # Record execution
    consensus.record_execution(
        tool_id="test_tool",
        version="1.0.0",
        metrics={'latency_ms': 150, 'correctness': 0.95},
        success=True
    )

    # Should update consensus score
    # (Note: Would need registered manifest for full test)


def test_adjust_weights_by_constraints(consensus):
    """Test weight adjustment based on constraints."""
    # Latency-critical
    weights = consensus._adjust_weights({'latency_ms_p95': 200})
    assert weights['latency'] > consensus.default_weights['latency']

    # Safety-critical
    weights = consensus._adjust_weights({'risk_score': 0.05})
    assert weights['safety'] > consensus.default_weights['safety']

    # Cost-critical
    weights = consensus._adjust_weights({'max_cost_per_call': 0.001})
    assert weights['cost'] > consensus.default_weights['cost']


def test_collect_dimensions(consensus):
    """Test collecting metric dimensions."""
    execution_history = [
        {'metrics': {'latency_ms': 150}, 'success': True},
        {'metrics': {'latency_ms': 180}, 'success': True},
        {'metrics': {'latency_ms': 200}, 'success': False}
    ]

    validation_result = {
        'validation_score': 0.95,
        'stages': []
    }

    dimensions = consensus._collect_dimensions(
        tool_id="test",
        version="1.0.0",
        execution_history=execution_history,
        validation_result=validation_result
    )

    assert len(dimensions) > 0
    assert any(d.name == 'resilience' for d in dimensions)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
