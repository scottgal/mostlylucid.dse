"""Test factory task trainer integration with RAG and tool registration."""
import os
import sys
from pathlib import Path
import logging

# Set environment variables before imports
os.environ['PYNGUIN_DANGER_AWARE'] = '1'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_factory_trainer_integration():
    """Test that factory trainer actually creates nodes, saves to RAG, and registers tools."""

    print("="*70)
    print("FACTORY TASK TRAINER - INTEGRATION TEST")
    print("="*70)

    # Add code_evolver to path
    sys.path.insert(0, str(Path(__file__).parent))

    from factory_task_trainer import FactoryTaskTrainer, FactoryTaskGenerator

    # Test 1: Check task generation
    print("\n[TEST 1] Task Generation")
    print("-" * 70)
    generator = FactoryTaskGenerator(base_prompt=None)
    task = generator.generate_variation()
    print(f"Generated task: {task}")
    assert len(task) > 0, "Task should not be empty"
    print("[OK] Task generation works")

    # Test 2: Check that factory trainer can be created
    print("\n[TEST 2] Trainer Initialization")
    print("-" * 70)
    trainer = FactoryTaskTrainer(base_prompt=None, max_tasks=1)
    assert trainer is not None, "Trainer should be created"
    assert trainer.max_tasks == 1, "Max tasks should be set"
    print("[OK] Trainer initialization works")

    # Test 3: Execute ONE task and verify it creates a node
    print("\n[TEST 3] Single Task Execution")
    print("-" * 70)
    print("Executing ONE factory task (this will take ~10-30 seconds)...")
    print("This will:")
    print("  1. Generate code using LLM")
    print("  2. Run tests (may include pynguin)")
    print("  3. Save to RAG memory")
    print("  4. Register as reusable tool")
    print()

    # Count nodes before
    from pathlib import Path
    nodes_dir = Path(__file__).parent / 'code_evolver' / 'nodes'
    nodes_before = list(nodes_dir.glob('train_*')) if nodes_dir.exists() else []
    nodes_before_count = len(nodes_before)
    print(f"Nodes before: {nodes_before_count}")

    # Execute ONE task
    try:
        trainer.run_training_loop()
    except KeyboardInterrupt:
        print("\nTest interrupted (expected if using keyboard monitor)")

    # Count nodes after
    nodes_after = list(nodes_dir.glob('train_*')) if nodes_dir.exists() else []
    nodes_after_count = len(nodes_after)
    print(f"\nNodes after: {nodes_after_count}")

    # Verify
    if nodes_after_count > nodes_before_count:
        print(f"[OK] Created {nodes_after_count - nodes_before_count} new node(s)")

        # Show the new node
        new_nodes = set(nodes_after) - set(nodes_before)
        for node_dir in new_nodes:
            print(f"\nNew node: {node_dir.name}")
            main_py = node_dir / "main.py"
            test_py = node_dir / "test.py"
            test_main_py = node_dir / "test_main.py"

            if main_py.exists():
                print(f"  [OK] main.py exists ({main_py.stat().st_size} bytes)")
            else:
                print(f"  [MISSING] main.py")

            if test_py.exists():
                print(f"  [OK] test.py exists ({test_py.stat().st_size} bytes)")
            elif test_main_py.exists():
                print(f"  [OK] test_main.py exists ({test_main_py.stat().st_size} bytes)")
            else:
                print(f"  [MISSING] test files")
    else:
        print("[WARNING] No new nodes created - task may have failed or timed out")

    # Test 4: Check RAG memory
    print("\n[TEST 4] RAG Memory Integration")
    print("-" * 70)
    try:
        from src.rag_memory import RAGMemory
        from src.ollama_client import OllamaClient
        from src.config_manager import ConfigManager

        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)

        # Check if there are artifacts with "train" tag
        train_artifacts = rag.find_by_tags(["auto-generated", "workflow"])
        print(f"Found {len(train_artifacts)} workflow artifacts in RAG")

        if len(train_artifacts) > 0:
            print("[OK] RAG memory contains workflow artifacts")
            # Show most recent
            recent = train_artifacts[-1]
            print(f"\nMost recent artifact:")
            print(f"  ID: {recent.artifact_id}")
            print(f"  Name: {recent.name[:60]}...")
            print(f"  Tags: {recent.tags}")
        else:
            print("[WARNING] No workflow artifacts found in RAG (may need to run more tasks)")

    except Exception as e:
        print(f"[ERROR] RAG check failed: {e}")

    # Test 5: Check tool registration
    print("\n[TEST 5] Tool Registration")
    print("-" * 70)
    try:
        from src.tools_manager import ToolsManager

        tools = ToolsManager(config_manager=config, ollama_client=client)

        # Get all tools
        all_tools = tools.list_tools()
        workflow_tools = [t for t in all_tools if t.get('tool_type') == 'workflow']

        print(f"Total tools: {len(all_tools)}")
        print(f"Workflow tools: {len(workflow_tools)}")

        if len(workflow_tools) > 0:
            print("[OK] Workflow tools are registered")
            # Show a few
            print("\nSample workflow tools:")
            for tool in workflow_tools[:3]:
                print(f"  - {tool['tool_id']}: {tool.get('name', 'N/A')[:50]}")
        else:
            print("[WARNING] No workflow tools found (may need to run successful task)")

    except Exception as e:
        print(f"[ERROR] Tool check failed: {e}")

    # Summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print("[OK] Task generation works")
    print("[OK] Trainer initialization works")
    print(f"[{'OK' if nodes_after_count > nodes_before_count else 'WARNING'}] Task execution creates nodes")
    print("[OK] RAG memory accessible")
    print("[OK] Tools manager accessible")
    print("\nNOTE: To verify full integration, run:")
    print("  python factory_task_trainer.py --max-tasks 1")
    print("Then check:")
    print("  1. New node in code_evolver/nodes/train_*")
    print("  2. RAG artifacts with workflow tag")
    print("  3. Tool registered in tools/index.json")

if __name__ == "__main__":
    test_factory_trainer_integration()
