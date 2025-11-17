#!/usr/bin/env python3
"""
Conversation Manager Tool

Executable wrapper for the conversation tool system.
Handles conversation lifecycle, context management, and semantic search.
"""
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.conversation import ConversationTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for conversation manager tool."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        action = input_data.get("action")
        config_path = input_data.get("config_path", "code_evolver/config.yaml")
        conversation_model = input_data.get("conversation_model", "gemma3:1b")

        # Initialize tool
        tool = ConversationTool.create_from_config_file(
            config_path=config_path,
            conversation_model=conversation_model
        )

        result = {}

        if action == "start":
            # Start conversation
            topic = input_data.get("topic", "general")
            result = tool.start_conversation(topic=topic)

        elif action == "end":
            # End conversation
            topic = input_data.get("topic")
            save_metadata = input_data.get("save_metadata", True)
            result = tool.end_conversation(topic=topic, save_metadata=save_metadata)

        elif action == "add_user_message":
            # Add user message
            content = input_data.get("content")
            if not content:
                raise ValueError("content is required for add_user_message action")
            result = tool.add_user_message(content=content)

        elif action == "add_assistant_message":
            # Add assistant message
            content = input_data.get("content")
            if not content:
                raise ValueError("content is required for add_assistant_message action")
            performance_data = input_data.get("performance_data")
            result = tool.add_assistant_message(
                content=content,
                performance_data=performance_data
            )

        elif action == "prepare_context":
            # Prepare context for response
            user_message = input_data.get("user_message")
            response_model = input_data.get("response_model")
            if not user_message:
                raise ValueError("user_message is required for prepare_context action")
            result = tool.prepare_context_for_response(
                user_message=user_message,
                response_model=response_model
            )

        elif action == "detect_intent":
            # Detect conversation intent
            user_input = input_data.get("user_input")
            if not user_input:
                raise ValueError("user_input is required for detect_intent action")
            result = tool.detect_conversation_intent(user_input=user_input)

        elif action == "status":
            # Get conversation status
            result = tool.get_conversation_status()

        elif action == "list":
            # List active conversations
            result = {"conversations": tool.list_active_conversations()}

        else:
            raise ValueError(f"Unknown action: {action}")

        # Output result
        output = {
            "success": True,
            "action": action,
            "result": result
        }
        print(json.dumps(output, indent=2))

    except Exception as e:
        logger.error(f"Error in conversation manager: {e}", exc_info=True)
        output = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
