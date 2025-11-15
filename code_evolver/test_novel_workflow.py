#!/usr/bin/env python3
"""
Test script for novel workflow composition system.
Tests intelligent tool composition for tasks like "write a romance novel".
"""
import sys
from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager
from src.ollama_client import OllamaClient
from src import create_rag_memory
import json

def test_composition():
    """Test the workflow composition system."""
    print("="*70)
    print("TESTING NOVEL WORKFLOW COMPOSITION")
    print("="*70)

    # Initialize components
    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    rag = create_rag_memory(config_manager=config, ollama_client=client)
    tools_manager = ToolsManager(config_manager=config, ollama_client=client, rag_memory=rag)

    print(f"\nLoaded {len(tools_manager.list_all())} tools")

    # Test cases
    test_cases = [
        "write a romance novel",
        "translate a technical document from English to Spanish",
        "quickly summarize a long article"
    ]

    for i, task in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {task}")
        print(f"{'='*70}")

        composition = tools_manager.compose_novel_workflow(task)

        if composition:
            print(f"\n[OK] Composed workflow successfully!")
            print(f"\nCharacteristics detected:")
            for key, value in composition.get("characteristics", {}).items():
                print(f"  • {key}: {value}")

            print(f"\nRecommended tools ({len(composition['recommended_tools'])}):")
            for tool_info in composition["recommended_tools"][:3]:
                print(f"  • {tool_info['name']}")
                print(f"    Model: {tool_info.get('model', 'N/A')}")
                print(f"    Score: {tool_info['score']:.1f}")
                print(f"    Cost/Speed/Quality: {tool_info.get('cost_tier')}/{tool_info.get('speed_tier')}/{tool_info.get('quality_tier')}")

            print(f"\nWorkflow steps ({len(composition['workflow_steps'])}):")
            for step in composition["workflow_steps"]:
                print(f"  {step['step']}. {step['action']}")
                print(f"     Tool: {step.get('tool', 'N/A')}")
                print(f"     {step['description']}")

            print(f"\nRationale:")
            for rationale in composition.get("rationale", []):
                print(f"  • {rationale}")
        else:
            print(f"\n[SKIP] No composition generated (task may be too simple or no matching tools)")

    print(f"\n{'='*70}")
    print("TESTING COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    test_composition()
