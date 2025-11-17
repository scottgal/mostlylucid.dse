#!/usr/bin/env python3
"""Test Smart Conversation Mode"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.conversation import ConversationTool
import yaml

def test_conversation_mode():
    """Test the conversation mode functionality"""
    print("=" * 60)
    print("Testing Smart Conversation Mode")
    print("=" * 60)

    # Load config
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        print("[OK] Config loaded")
    except Exception as e:
        print(f"[FAIL] Failed to load config: {e}")
        return False

    # Initialize conversation tool
    try:
        conv_config = config.get("conversation", {})
        conv = ConversationTool(
            config=conv_config,
            conversation_model=conv_config.get("conversation_model", "gemma3:1b")
        )
        print("[OK] ConversationTool initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize ConversationTool: {e}")
        return False

    # Start conversation
    try:
        result = conv.start_conversation(topic="Python Testing")
        conversation_id = result["conversation_id"]
        print(f"[OK] Conversation started: {conversation_id}")
    except Exception as e:
        print(f"[FAIL] Failed to start conversation: {e}")
        return False

    # Add user message
    try:
        conv.add_user_message("What are the benefits of type hints?")
        print("[OK] User message added")
    except Exception as e:
        print(f"[FAIL] Failed to add user message: {e}")
        return False

    # Prepare context
    try:
        context_result = conv.prepare_context_for_response(
            user_message="What are the benefits of type hints?",
            response_model="llama3"
        )
        print(f"[OK] Context prepared ({len(str(context_result))} chars)")
        print(f"  Messages: {len(context_result.get('messages', []))}")
    except Exception as e:
        print(f"[FAIL] Failed to prepare context: {e}")
        import traceback
        traceback.print_exc()
        return False

    # End conversation
    try:
        summary = conv.end_conversation(save_metadata=True)
        print(f"[OK] Conversation ended")
        print(f"  Messages: {summary.get('message_count', 'N/A')}")
        print(f"  Duration: {summary.get('duration_seconds', 'N/A')}s")
    except Exception as e:
        print(f"[FAIL] Failed to end conversation: {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] All conversation mode tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_conversation_mode()
    sys.exit(0 if success else 1)
