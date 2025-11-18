"""Tests for Forge Registry."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forge.core.registry import ForgeRegistry, ToolManifest, ConsensusScore
from src.rag_memory import RAGMemory
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager


@pytest.fixture
def config_manager():
    """Create config manager for tests."""
    return ConfigManager("config.example.yaml")


@pytest.fixture
def rag_memory(config_manager):
    """Create RAG memory for tests."""
    return RAGMemory(config_manager)


@pytest.fixture
def tools_manager(config_manager):
    """Create tools manager for tests."""
    return ToolsManager(config_manager)


@pytest.fixture
def registry(rag_memory, tools_manager):
    """Create forge registry for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ForgeRegistry(
            rag_memory=rag_memory,
            tools_manager=tools_manager,
            manifest_dir=Path(tmpdir)
        )
        yield registry


def test_register_tool_manifest(registry):
    """Test registering a tool manifest."""
    manifest = ToolManifest(
        tool_id="test_tool",
        version="1.0.0",
        name="Test Tool",
        type="mcp",
        description="A test tool",
        origin={
            'author': 'test',
            'source_model': 'test',
            'created_at': datetime.utcnow().isoformat() + "Z"
        },
        lineage={
            'ancestor_tool_id': None,
            'mutation_reason': 'test',
            'commits': []
        },
        trust={
            'level': 'experimental',
            'validation_score': 0.0,
            'risk_score': 1.0
        },
        tags=['test', 'forge']
    )

    # Register manifest
    success = registry.register_tool_manifest(manifest)
    assert success

    # Retrieve manifest
    retrieved = registry.get_tool_manifest("test_tool", "1.0.0")
    assert retrieved is not None
    assert retrieved.tool_id == "test_tool"
    assert retrieved.version == "1.0.0"


def test_query_tools(registry):
    """Test querying tools with constraints."""
    # Register test tool
    manifest = ToolManifest(
        tool_id="translator",
        version="1.0.0",
        name="Translator",
        type="mcp",
        description="Translation tool",
        origin={'author': 'test', 'source_model': 'test', 'created_at': datetime.utcnow().isoformat() + "Z"},
        lineage={'ancestor_tool_id': None, 'mutation_reason': 'test', 'commits': []},
        trust={'level': 'core', 'validation_score': 0.95, 'risk_score': 0.1},
        tags=['translation', 'forge'],
        metrics={
            'latest': {
                'correctness': 0.95,
                'latency_ms_p95': 200,
                'failure_rate': 0.01
            }
        }
    )

    registry.register_tool_manifest(manifest)

    # Query with constraints
    results = registry.query_tools(
        capability="translate",
        constraints={'latency_ms_p95': 500, 'risk_score': 0.2}
    )

    # Should find the tool
    assert results['best_tool'] is not None


def test_consensus_score(registry):
    """Test storing and retrieving consensus scores."""
    score = ConsensusScore(
        tool_id="test_tool",
        version="1.0.0",
        scores={
            'correctness': 0.95,
            'latency': 0.88,
            'cost': 0.92,
            'safety': 0.99
        },
        weight=0.935,
        evaluators=[
            {'id': 'validator_1', 'contribution': 0.25},
            {'id': 'validator_2', 'contribution': 0.25}
        ]
    )

    # Store score
    success = registry.store_consensus_score(score)
    assert success

    # Retrieve score
    retrieved = registry._get_consensus_score("test_tool", "1.0.0")
    assert retrieved is not None
    assert retrieved.weight == 0.935


def test_list_tools(registry):
    """Test listing tools with filters."""
    # Register multiple tools
    for i in range(3):
        manifest = ToolManifest(
            tool_id=f"tool_{i}",
            version="1.0.0",
            name=f"Tool {i}",
            type="mcp",
            description=f"Test tool {i}",
            origin={'author': 'test', 'source_model': 'test', 'created_at': datetime.utcnow().isoformat() + "Z"},
            lineage={'ancestor_tool_id': None, 'mutation_reason': 'test', 'commits': []},
            trust={'level': 'experimental' if i == 0 else 'core', 'validation_score': 0.5 if i == 0 else 0.95, 'risk_score': 1.0 if i == 0 else 0.1},
            tags=['test', 'forge']
        )
        registry.register_tool_manifest(manifest)

    # List all tools
    all_tools = registry.list_tools()
    assert len(all_tools) >= 3

    # Filter by trust level
    core_tools = registry.list_tools(trust_level='core')
    assert len(core_tools) >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
