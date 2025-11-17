#!/usr/bin/env python3
"""
Comprehensive test suite for mostlylucid DiSE tools.
Tests all new features and tools automatically.
"""
import subprocess
import time
import json

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Command: {cmd}")
    print()
    
    start = time.time()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=120
    )
    elapsed = time.time() - start
    
    success = result.returncode == 0
    status = "PASS" if success else "FAIL"
    
    print(f"Status: {status} (took {elapsed:.1f}s)")
    
    if not success:
        print(f"Error output: {result.stderr[:500]}")
    else:
        # Show last few lines of output
        lines = result.stdout.strip().split('\n')
        relevant_lines = [l for l in lines[-15:] if 'OK' in l or 'WORKFLOW' in l or 'quality' in l]
        if relevant_lines:
            print("Output highlights:")
            for line in relevant_lines[:10]:
                print(f"  {line}")
    
    return success

def main():
    """Run all tests."""
    print("""
================================================================================
CODE EVOLVER - COMPREHENSIVE TOOL TESTING
================================================================================
Testing all new features and tools with live Ollama instances.
""")
    
    tests = [
        # Test 1: Basic code generation
        (
            'cd code_evolver && echo "multiply 50 and 3" | timeout 120 python chat_cli.py',
            "Basic code generation (multiply numbers)"
        ),
        
        # Test 2: Check RAG stats
        (
            'cd code_evolver && python cleanup_rag.py --stats',
            "RAG memory statistics"
        ),
        
        # Test 3: List all tools (verify new tools loaded)
        (
            'cd code_evolver && python -c "from src.config_manager import ConfigManager; from src.tools_manager import ToolsManager; c = ConfigManager(); t = ToolsManager(config_manager=c, ollama_client=None, rag_memory=None); print(f\\\"Total tools: {len(t.list_tools())}\\\"); print(\\\"quick_feedback:\\\", t.get_tool(\\\"quick_feedback\\\") is not None); print(\\\"summarizer:\\\", t.get_tool(\\\"summarizer\\\") is not None); print(\\\"nmt_translator:\\\", t.get_tool(\\\"nmt_translator\\\") is not None)"',
            "Verify new tools loaded"
        ),
        
        # Test 4: Context window configuration
        (
            'cd code_evolver && python -c "from src.config_manager import ConfigManager; c = ConfigManager(); print(\\\"tinyllama:\\\", c.get_context_window(\\\"tinyllama\\\")); print(\\\"gemma2:2b:\\\", c.get_context_window(\\\"gemma2:2b\\\")); print(\\\"qwen2.5-coder:14b:\\\", c.get_context_window(\\\"qwen2.5-coder:14b\\\"))"',
            "Context window configuration"
        ),
        
        # Test 5: Generate and test a simple function
        (
            'cd code_evolver && echo "create a function that returns the square of a number" | timeout 120 python chat_cli.py',
            "Code generation with testing pipeline"
        ),
    ]
    
    results = []
    for cmd, desc in tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
        time.sleep(2)  # Brief pause between tests
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for desc, success in results:
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {desc}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
