#!/usr/bin/env python3
"""Test Tool Naming in Conversations"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Import only what we need to test
import importlib.util

# Load the module directly without importing the full package
spec = importlib.util.spec_from_file_location(
    "smart_orchestrator",
    os.path.join(os.path.dirname(__file__), "src/conversation/smart_orchestrator.py")
)
smart_orchestrator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smart_orchestrator_module)
SmartConversationOrchestrator = smart_orchestrator_module.SmartConversationOrchestrator

def test_tool_naming():
    """Test that preferred tools are prioritized in the planner"""
    print("=" * 60)
    print("Testing Tool Naming & Prioritization")
    print("=" * 60)

    # Initialize orchestrator
    try:
        orchestrator = SmartConversationOrchestrator(
            model_name="gemma3:1b",
            ollama_endpoint="http://localhost:11434"
        )
        print("[OK] SmartConversationOrchestrator initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize orchestrator: {e}")
        return False

    # Test 1: Tool selection WITHOUT preferred tools
    print("\n--- Test 1: Tool Selection WITHOUT Preferred Tools ---")
    try:
        available_tools = ["coder", "writer", "analyzer", "tester", "debugger"]

        result = orchestrator.select_tools_for_task(
            task_description="Fix a bug in the code",
            task_type="code_generation",
            available_tools=available_tools,
            preferred_tools=None  # No preferred tools
        )

        print(f"[OK] Tool selection completed")
        print(f"  Recommended tools: {result['recommended_tools']}")
        print(f"  Reasoning: {result['reasoning']}")
        print(f"  Used preferred: {result.get('used_preferred', False)}")

        # Should NOT have used preferred tools
        assert result.get('used_preferred', False) == False, "Should not use preferred when none specified"
        print("[OK] Correctly did not use preferred tools")

    except Exception as e:
        print(f"[FAIL] Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Tool selection WITH preferred tools
    print("\n--- Test 2: Tool Selection WITH Preferred Tools ---")
    try:
        available_tools = ["coder", "writer", "analyzer", "tester", "debugger"]
        preferred_tools = ["debugger", "tester"]

        result = orchestrator.select_tools_for_task(
            task_description="Fix a bug in the code",
            task_type="code_generation",
            available_tools=available_tools,
            preferred_tools=preferred_tools
        )

        print(f"[OK] Tool selection completed")
        print(f"  Recommended tools: {result['recommended_tools']}")
        print(f"  Reasoning: {result['reasoning']}")
        print(f"  Used preferred: {result.get('used_preferred', False)}")

        # Should have used preferred tools
        assert result.get('used_preferred', False) == True, "Should use preferred tools when specified"
        assert result['recommended_tools'] == preferred_tools, f"Should recommend preferred tools: expected {preferred_tools}, got {result['recommended_tools']}"
        print("[OK] Correctly prioritized preferred tools")

    except Exception as e:
        print(f"[FAIL] Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Preferred tools not in available list (should fallback)
    print("\n--- Test 3: Preferred Tools NOT Available (Fallback) ---")
    try:
        available_tools = ["coder", "writer", "analyzer"]
        preferred_tools = ["debugger", "tester"]  # Not in available tools

        result = orchestrator.select_tools_for_task(
            task_description="Fix a bug in the code",
            task_type="code_generation",
            available_tools=available_tools,
            preferred_tools=preferred_tools
        )

        print(f"[OK] Tool selection completed")
        print(f"  Recommended tools: {result['recommended_tools']}")
        print(f"  Reasoning: {result['reasoning']}")
        print(f"  Used preferred: {result.get('used_preferred', False)}")

        # Should NOT have used preferred tools (fell back to semantic search)
        assert result.get('used_preferred', False) == False, "Should fallback when preferred tools not available"
        print("[OK] Correctly fell back to semantic search")

    except Exception as e:
        print(f"[FAIL] Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Partial match of preferred tools
    print("\n--- Test 4: Partial Match of Preferred Tools ---")
    try:
        available_tools = ["coder", "writer", "analyzer", "tester", "debugger"]
        preferred_tools = ["debugger", "nonexistent_tool", "tester"]

        result = orchestrator.select_tools_for_task(
            task_description="Fix a bug in the code",
            task_type="code_generation",
            available_tools=available_tools,
            preferred_tools=preferred_tools
        )

        print(f"[OK] Tool selection completed")
        print(f"  Recommended tools: {result['recommended_tools']}")
        print(f"  Reasoning: {result['reasoning']}")
        print(f"  Used preferred: {result.get('used_preferred', False)}")

        # Should have used the available preferred tools
        assert result.get('used_preferred', False) == True, "Should use available preferred tools"
        assert "debugger" in result['recommended_tools'], "Should include debugger"
        assert "tester" in result['recommended_tools'], "Should include tester"
        assert "nonexistent_tool" not in result['recommended_tools'], "Should not include nonexistent tool"
        print("[OK] Correctly used available preferred tools only")

    except Exception as e:
        print(f"[FAIL] Test 4 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] All tool naming tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_tool_naming()
    sys.exit(0 if success else 1)
