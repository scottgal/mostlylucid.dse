#!/usr/bin/env python3
"""
Unit tests for conversation_manager.py tool.
Tests conversation management functionality.
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConversationManager(unittest.TestCase):
    """Test cases for conversation manager tool."""

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    @patch('tools.executable.conversation_manager.ConversationTool')
    def test_start_conversation(self, mock_tool_class, mock_stdout, mock_stdin):
        """Test starting a conversation."""
        input_data = json.dumps({
            "action": "start",
            "topic": "test_topic",
            "config_path": "config.yaml"
        })

        mock_tool_instance = MagicMock()
        mock_tool_instance.start_conversation.return_value = {
            "conversation_id": "test_123",
            "topic": "test_topic",
            "started": True
        }
        mock_tool_class.create_from_config_file.return_value = mock_tool_instance

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            try:
                main()
            except SystemExit:
                pass

        # Verify the tool was called correctly
        mock_tool_instance.start_conversation.assert_called_once_with(topic="test_topic")

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    @patch('tools.executable.conversation_manager.ConversationTool')
    def test_end_conversation(self, mock_tool_class, mock_stdout, mock_stdin):
        """Test ending a conversation."""
        input_data = json.dumps({
            "action": "end",
            "topic": "test_topic",
            "save_metadata": True,
            "config_path": "config.yaml"
        })

        mock_tool_instance = MagicMock()
        mock_tool_instance.end_conversation.return_value = {
            "conversation_id": "test_123",
            "ended": True,
            "messages_saved": 10
        }
        mock_tool_class.create_from_config_file.return_value = mock_tool_instance

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            try:
                main()
            except SystemExit:
                pass

        # Verify the tool was called correctly
        mock_tool_instance.end_conversation.assert_called_once_with(
            topic="test_topic",
            save_metadata=True
        )

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    @patch('tools.executable.conversation_manager.ConversationTool')
    def test_add_user_message(self, mock_tool_class, mock_stdout, mock_stdin):
        """Test adding a user message."""
        input_data = json.dumps({
            "action": "add_user_message",
            "content": "Hello, this is a test message",
            "config_path": "config.yaml"
        })

        mock_tool_instance = MagicMock()
        mock_tool_instance.add_user_message.return_value = {
            "message_added": True,
            "message_count": 1
        }
        mock_tool_class.create_from_config_file.return_value = mock_tool_instance

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            try:
                main()
            except SystemExit:
                pass

        # Verify the tool was called correctly
        mock_tool_instance.add_user_message.assert_called_once_with(
            content="Hello, this is a test message"
        )

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    @patch('tools.executable.conversation_manager.ConversationTool')
    def test_add_assistant_message(self, mock_tool_class, mock_stdout, mock_stdin):
        """Test adding an assistant message."""
        input_data = json.dumps({
            "action": "add_assistant_message",
            "content": "This is a response",
            "performance_data": {"tokens": 100, "time": 1.5},
            "config_path": "config.yaml"
        })

        mock_tool_instance = MagicMock()
        mock_tool_instance.add_assistant_message.return_value = {
            "message_added": True,
            "message_count": 2
        }
        mock_tool_class.create_from_config_file.return_value = mock_tool_instance

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            try:
                main()
            except SystemExit:
                pass

        # Verify the tool was called correctly
        mock_tool_instance.add_assistant_message.assert_called_once()

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    @patch('tools.executable.conversation_manager.ConversationTool')
    def test_get_status(self, mock_tool_class, mock_stdout, mock_stdin):
        """Test getting conversation status."""
        input_data = json.dumps({
            "action": "status",
            "config_path": "config.yaml"
        })

        mock_tool_instance = MagicMock()
        mock_tool_instance.get_conversation_status.return_value = {
            "active": True,
            "message_count": 5,
            "topic": "test"
        }
        mock_tool_class.create_from_config_file.return_value = mock_tool_instance

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            try:
                main()
            except SystemExit:
                pass

        # Verify the tool was called correctly
        mock_tool_instance.get_conversation_status.assert_called_once()

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    @patch('tools.executable.conversation_manager.ConversationTool')
    def test_list_conversations(self, mock_tool_class, mock_stdout, mock_stdin):
        """Test listing active conversations."""
        input_data = json.dumps({
            "action": "list",
            "config_path": "config.yaml"
        })

        mock_tool_instance = MagicMock()
        mock_tool_instance.list_active_conversations.return_value = [
            {"id": "conv1", "topic": "topic1"},
            {"id": "conv2", "topic": "topic2"}
        ]
        mock_tool_class.create_from_config_file.return_value = mock_tool_instance

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            try:
                main()
            except SystemExit:
                pass

        # Verify the tool was called correctly
        mock_tool_instance.list_active_conversations.assert_called_once()

    @patch('sys.stdin', new_callable=StringIO)
    def test_invalid_action(self, mock_stdin):
        """Test handling of invalid action."""
        input_data = json.dumps({
            "action": "invalid_action",
            "config_path": "config.yaml"
        })

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            with self.assertRaises(SystemExit) as cm:
                main()

            self.assertEqual(cm.exception.code, 1)

    @patch('sys.stdin', new_callable=StringIO)
    def test_missing_required_field(self, mock_stdin):
        """Test handling of missing required fields."""
        input_data = json.dumps({
            "action": "add_user_message",
            # Missing 'content' field
            "config_path": "config.yaml"
        })

        with patch('sys.stdin.read', return_value=input_data):
            from tools.executable.conversation_manager import main
            with self.assertRaises(SystemExit) as cm:
                main()

            self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
