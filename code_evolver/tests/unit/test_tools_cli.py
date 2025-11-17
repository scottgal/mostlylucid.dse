#!/usr/bin/env python3
"""
Unit Tests for Tools CLI
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.tools_cli import ToolsCLI, CommandType, CommandResult


@pytest.fixture
def mock_tools_manager():
    """Create mock tools manager."""
    manager = Mock()
    manager.tools = {}
    manager.get_tool = Mock(return_value=None)
    manager.get_all_tools = Mock(return_value=[])
    return manager


@pytest.fixture
def mock_rag():
    """Create mock RAG memory."""
    rag = Mock()
    rag.find_by_tags = Mock(return_value=[])
    return rag


@pytest.fixture
def mock_client():
    """Create mock Ollama client."""
    client = Mock()
    return client


@pytest.fixture
def tools_cli(mock_tools_manager, mock_rag, mock_client):
    """Create ToolsCLI instance."""
    return ToolsCLI(
        tools_manager=mock_tools_manager,
        rag=mock_rag,
        client=mock_client,
        verbose=False  # Disable verbose for testing
    )


def test_parse_command_optimize_all(tools_cli):
    """Test parsing /tools optimize all command."""
    cmd_type, tool_name = tools_cli._parse_command("/tools optimize all")

    assert cmd_type == CommandType.OPTIMIZE_ALL
    assert tool_name is None


def test_parse_command_optimize_single(tools_cli):
    """Test parsing /tools optimize --n <name> command."""
    cmd_type, tool_name = tools_cli._parse_command("/tools optimize --n content_splitter")

    assert cmd_type == CommandType.OPTIMIZE_SINGLE
    assert tool_name == "content_splitter"


def test_parse_command_test_all(tools_cli):
    """Test parsing /tools test all command."""
    cmd_type, tool_name = tools_cli._parse_command("/tools test all")

    assert cmd_type == CommandType.TEST_ALL
    assert tool_name is None


def test_parse_command_test_single(tools_cli):
    """Test parsing /tools test --n <name> command."""
    cmd_type, tool_name = tools_cli._parse_command("/tools test --n summarizer_fast")

    assert cmd_type == CommandType.TEST_SINGLE
    assert tool_name == "summarizer_fast"


def test_parse_command_unknown(tools_cli):
    """Test parsing unknown command."""
    cmd_type, tool_name = tools_cli._parse_command("/tools invalid command")

    assert cmd_type == CommandType.UNKNOWN
    assert tool_name is None


def test_parse_command_missing_flag(tools_cli):
    """Test parsing command with missing --n value."""
    cmd_type, tool_name = tools_cli._parse_command("/tools optimize --n")

    # Should default to OPTIMIZE_ALL if no tool name provided
    assert cmd_type == CommandType.UNKNOWN


def test_handle_unknown_command(tools_cli):
    """Test handling unknown command."""
    result = tools_cli.handle_command("/tools unknown")

    assert not result.success
    assert result.command_type == CommandType.UNKNOWN
    assert "Unknown command" in result.message


def test_command_result_structure(tools_cli):
    """Test CommandResult structure."""
    # Patch the _optimizer directly instead of the property
    with patch.object(tools_cli, '_optimizer') as mock_optimizer:
        mock_optimizer.optimize_all_tools.return_value = []
        tools_cli._optimizer = mock_optimizer  # Set it directly

        result = tools_cli.handle_command("/tools optimize all")

        assert isinstance(result, CommandResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'command_type')
        assert hasattr(result, 'message')
        assert hasattr(result, 'details')
        assert hasattr(result, 'duration')
        assert result.duration >= 0


def test_optimize_all_success(tools_cli):
    """Test successful optimize all command."""
    mock_optimizer = Mock()
    mock_optimizer.optimize_all_tools.return_value = [
        {"tool_name": "tool1", "improved": True},
        {"tool_name": "tool2", "improved": False}
    ]
    tools_cli._optimizer = mock_optimizer

    result = tools_cli.handle_command("/tools optimize all")

    assert result.success
    assert result.command_type == CommandType.OPTIMIZE_ALL
    assert "2 tools" in result.message
    assert "1 improved" in result.message


def test_test_all_success(tools_cli):
    """Test successful test all command."""
    mock_tester = Mock()
    mock_tester.test_all_tools.return_value = [
        {"tool_name": "tool1", "passed": True},
        {"tool_name": "tool2", "passed": True},
        {"tool_name": "tool3", "passed": False}
    ]
    tools_cli._tester = mock_tester

    result = tools_cli.handle_command("/tools test all")

    assert result.command_type == CommandType.TEST_ALL
    assert "2/3 passed" in result.message


def test_lazy_loading_optimizer(tools_cli):
    """Test lazy loading of optimizer."""
    assert tools_cli._optimizer is None

    # Access optimizer property - it should create one
    with patch('src.tool_optimizer.ToolOptimizer') as MockOptimizer:
        mock_instance = Mock()
        MockOptimizer.return_value = mock_instance

        optimizer = tools_cli.optimizer

        MockOptimizer.assert_called_once()
        assert tools_cli._optimizer is mock_instance


def test_lazy_loading_tester(tools_cli):
    """Test lazy loading of tester."""
    assert tools_cli._tester is None

    # Access tester property - it should create one
    with patch('src.tool_tester.ToolTester') as MockTester:
        mock_instance = Mock()
        MockTester.return_value = mock_instance

        tester = tools_cli.tester

        MockTester.assert_called_once()
        assert tools_cli._tester is mock_instance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
