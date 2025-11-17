"""
Test all recent feature updates.

Tests:
1. Task Evaluator - URL detection fix
2. Workflow Tool Support - ToolType.WORKFLOW
3. Pynguin Windows detection
4. Background Tools Loader
"""
import sys
import platform
sys.path.insert(0, '.')

def test_task_evaluator():
    """Test that task evaluator doesn't reject valid URL requests."""
    print("\n" + "="*70)
    print("TEST 1: Task Evaluator - URL Detection Fix")
    print("="*70)

    from src.task_evaluator import TaskEvaluator
    from src.ollama_client import OllamaClient
    from src.config_manager import ConfigManager

    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    evaluator = TaskEvaluator(client)

    # Test case that was failing before
    description = 'go fetch a gif image from www.bbc.co.uk and save it to disk'
    result = evaluator.evaluate_task_type(description)

    print(f"Description: {description}")
    print(f"Task Type: {result['task_type'].value}")
    print(f"Is Accidental: {result.get('is_accidental', False)}")

    if result.get('is_accidental'):
        print("[FAIL] Request incorrectly classified as accidental!")
        return False
    else:
        print("[PASS] Request correctly accepted as valid task")
        return True


def test_workflow_tool_support():
    """Test that workflow tools can be invoked."""
    print("\n" + "="*70)
    print("TEST 2: Workflow Tool Support")
    print("="*70)

    from node_runtime import call_tool

    try:
        # Check if translate_the_data workflow exists
        import os
        workflow_path = "nodes/translate_the_data/main.py"
        if not os.path.exists(workflow_path):
            print(f"[SKIP] Workflow {workflow_path} not found")
            return True

        # Try calling the workflow
        result = call_tool('translate_the_data', 'Hello, test!', disable_tracking=True)

        print(f"[PASS] Workflow tool invoked successfully")
        print(f"Result preview: {result[:100]}...")
        return True

    except ValueError as e:
        if "Unknown tool type" in str(e):
            print(f"[FAIL] Workflow tools still not supported: {e}")
            return False
        raise
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False


def test_pynguin_windows_detection():
    """Test that Pynguin is skipped on Windows."""
    print("\n" + "="*70)
    print("TEST 3: Pynguin Windows Detection")
    print("="*70)

    print(f"Platform: {platform.system()}")

    if platform.system() != 'Windows':
        print("[SKIP] Not running on Windows, skipping Pynguin test")
        return True

    # Import the ChatCLI class
    from chat_cli import ChatCLI

    # Create instance (will load config)
    cli = ChatCLI()

    # Call _generate_tests_with_pynguin
    result = cli._generate_tests_with_pynguin(
        node_id='dummy_node',
        timeout=5  # Short timeout
    )

    # On Windows, it should return immediately with success=False
    if result['success'] == False and result['method'] == 'none':
        print("[PASS] Pynguin correctly skipped on Windows")
        return True
    else:
        print(f"[FAIL] Pynguin was attempted on Windows: {result}")
        return False


def test_background_tools_loader():
    """Test that background tools loader initializes correctly."""
    print("\n" + "="*70)
    print("TEST 4: Background Tools Loader")
    print("="*70)

    from src.background_tools_loader import BackgroundToolsLoader
    from src.config_manager import ConfigManager
    from src.ollama_client import OllamaClient
    from src.rag_memory import RAGMemory

    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    rag = RAGMemory(ollama_client=client)

    loader = BackgroundToolsLoader(config, client, rag)

    # Start loading
    loader.start()

    print("Loader started in background...")
    print(f"Status: {loader.get_status()}")

    # Wait for completion (with timeout)
    import time
    max_wait = 30  # 30 seconds max
    start = time.time()

    while not loader.is_ready_sync() and (time.time() - start) < max_wait:
        time.sleep(1)
        status = loader.get_status()
        if "Loading" in status:
            print(f"  {status}")

    if loader.is_ready_sync():
        tools = loader.get_tools(wait=False)
        tool_count = len(tools.tools) if tools else 0
        print(f"[PASS] Tools loaded in background ({tool_count} tools)")
        return True
    else:
        print(f"[FAIL] Tools loading timed out after {max_wait}s")
        return False


if __name__ == "__main__":
    print("\n")
    print("=" * 70)
    print("FEATURE VALIDATION TEST SUITE")
    print("=" * 70)

    results = []

    # Run all tests
    try:
        results.append(("Task Evaluator", test_task_evaluator()))
    except Exception as e:
        print(f"[ERROR] Task Evaluator test failed: {e}")
        results.append(("Task Evaluator", False))

    try:
        results.append(("Workflow Tools", test_workflow_tool_support()))
    except Exception as e:
        print(f"[ERROR] Workflow Tools test failed: {e}")
        results.append(("Workflow Tools", False))

    try:
        results.append(("Pynguin Detection", test_pynguin_windows_detection()))
    except Exception as e:
        print(f"[ERROR] Pynguin Detection test failed: {e}")
        results.append(("Pynguin Detection", False))

    try:
        results.append(("Background Loader", test_background_tools_loader()))
    except Exception as e:
        print(f"[ERROR] Background Loader test failed: {e}")
        results.append(("Background Loader", False))

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\nSUCCESS: All features working correctly!")
        sys.exit(0)
    else:
        print(f"\nFAILED: {total - passed} test(s) failed")
        sys.exit(1)
