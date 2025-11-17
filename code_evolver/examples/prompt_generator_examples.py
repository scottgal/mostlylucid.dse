"""
Example workflows demonstrating the Prompt Generator System.

This file contains practical examples showing how to:
1. Generate layered prompts
2. Query models conversationally
3. Create dynamic tools
4. Build complex workflows

Run with:
    python examples/prompt_generator_examples.py
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_manager import ConfigManager
from tools_manager import ToolsManager
from prompt_generator_tool import create_prompt_generator_tool, PromptGeneratorTool
from model_selector_tool import create_model_selector_tool
from dynamic_tool_registry import create_dynamic_tool_registry


def setup():
    """Initialize the system components."""
    print("=" * 80)
    print("Initializing Prompt Generator System...")
    print("=" * 80)

    config = ConfigManager()
    tools_manager = ToolsManager(config)

    # Create and register tools
    prompt_gen = create_prompt_generator_tool(config, tools_manager)
    model_selector = create_model_selector_tool(config, tools_manager)
    tool_registry = create_dynamic_tool_registry(config, tools_manager)

    print(f"✓ Loaded {len(prompt_gen.model_registry)} models")
    print(f"✓ Dynamic tool registry ready\n")

    return config, tools_manager, prompt_gen, model_selector, tool_registry


def example_1_basic_prompt_generation(prompt_gen):
    """Example 1: Generate a basic layered prompt."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Prompt Generation")
    print("=" * 80)

    result = prompt_gen.generate_prompt(
        description="Review Python code for security vulnerabilities",
        task_type="code"
    )

    print("\nGenerated Prompt:")
    print("-" * 80)
    print(result["prompt"])
    print("-" * 80)

    print("\nMetadata:")
    print(f"  Task Type: {result['metadata']['task_type']}")
    print(f"  Tier: {result['metadata']['tier']}")
    print(f"  Temperature: {result['metadata']['temperature']}")

    print("\nSuggested Models:")
    for model in result["suggested_models"][:3]:
        print(f"  {model['name']}")
        print(f"    Speed: {model['speed']}, Quality: {model['quality']}, Cost: {model['cost']}")


def example_2_weight_adjustment(prompt_gen):
    """Example 2: Adjust layer weights for emphasis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Weight Adjustment")
    print("=" * 80)

    # Default weights
    result_default = prompt_gen.generate_prompt(
        description="Optimize database queries for performance",
        task_type="code"
    )

    # Adjusted weights - emphasize constraints
    result_adjusted = prompt_gen.generate_prompt(
        description="Optimize database queries for performance",
        task_type="code",
        weights={
            "constraints": 1.0,  # Critical emphasis
            "system": 0.9,
            "context": 0.5,      # De-emphasize
            "examples": 0.0      # Exclude
        }
    )

    print("\nDefault Weights:")
    print("  System: 1.0, Role: 0.8, Context: 0.7, Task: 1.0, Constraints: 0.9")

    print("\nAdjusted Weights:")
    print("  System: 0.9, Role: 0.8, Context: 0.5, Task: 1.0, Constraints: 1.0, Examples: 0.0")

    print("\nNotice how 'CRITICAL' appears on Constraints layer in adjusted version:")
    print("-" * 80)
    # Show just the constraints section
    for line in result_adjusted["prompt"].split("\n"):
        if "CONSTRAINT" in line or line.startswith("- "):
            print(line)
    print("-" * 80)


def example_3_query_models(model_selector):
    """Example 3: Query models conversationally."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Conversational Model Queries")
    print("=" * 80)

    queries = [
        "what fast summary models do we have",
        "show me the best code models",
        "which free models can handle large context"
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)

        models = model_selector.query_models(query)

        if models:
            for model in models[:3]:
                print(f"  {model['name']}")
                print(f"    Backend: {model['backend']}")
                print(f"    Speed: {model['speed']}, Quality: {model['quality']}, Cost: {model['cost']}")
                print(f"    Context: {model['context_window']} tokens")
        else:
            print("  No matching models found")


def example_4_create_dynamic_tool(prompt_gen, tool_registry):
    """Example 4: Create a dynamic LLM tool."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Dynamic Tool Creation")
    print("=" * 80)

    # Create a specialized translator
    tool_def = prompt_gen.create_dynamic_tool(
        tool_name="medical_doc_translator",
        description="Translate medical documentation from English to Spanish, preserving technical terminology",
        task_type="translation",
        tier="tier_2"
    )

    print("\nCreated Tool Definition:")
    print("-" * 80)
    print(f"Name: {tool_def['name']}")
    print(f"Type: {tool_def['type']}")
    print(f"Description: {tool_def['description']}")
    print(f"\nLLM Configuration:")
    print(f"  Model: {tool_def['llm']['model']}")
    print(f"  Backend: {tool_def['llm']['backend']}")
    print(f"  Temperature: {tool_def['llm']['temperature']}")
    print(f"\nMetadata:")
    print(f"  Quality: {tool_def['metadata']['quality_tier']}")
    print(f"  Speed: {tool_def['metadata']['speed_tier']}")
    print(f"  Cost: {tool_def['metadata']['cost_tier']}")
    print(f"  Context Window: {tool_def['metadata']['context_window']}")
    print(f"  Timeout: {tool_def['metadata']['timeout']}s")

    # Register the tool
    tool_id = tool_registry.register_tool(
        tool_name=tool_def['name'],
        tool_definition=tool_def,
        validate=True,
        persist=True
    )

    if tool_id:
        print(f"\n✓ Tool registered successfully: {tool_id}")
        print(f"✓ Saved to: ./tools/dynamic/{tool_id}.yaml")
    else:
        print("\n✗ Tool registration failed")


def example_5_multi_step_workflow(prompt_gen, model_selector):
    """Example 5: Multi-step workflow combining multiple features."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Multi-Step Workflow")
    print("=" * 80)

    # Step 1: Query available models
    print("\nStep 1: Finding suitable models for code optimization...")
    models = model_selector.query_models("best local code models")

    if models:
        selected_model = models[0]
        print(f"  Selected: {selected_model['name']}")
        print(f"  Reason: Quality={selected_model['quality']}, Speed={selected_model['speed']}")

        # Step 2: Generate optimized prompt
        print("\nStep 2: Generating prompt for code optimization...")
        prompt_result = prompt_gen.generate_prompt(
            description="Optimize Python code for performance and memory efficiency",
            task_type="code",
            tier="tier_2",
            weights={
                "constraints": 1.0,
                "task": 1.0,
                "system": 0.9
            }
        )

        print(f"  Prompt ready: {len(prompt_result['prompt'])} characters")
        print(f"  Layers: {len(prompt_result['layers'])} layers")

        # Step 3: Create specialized tool
        print("\nStep 3: Creating specialized optimization tool...")
        tool_def = prompt_gen.create_dynamic_tool(
            tool_name="python_performance_optimizer",
            description="Optimize Python code focusing on loops, memory usage, and algorithmic efficiency",
            task_type="code",
            model_preference=selected_model['name'],
            tier="tier_2"
        )

        print(f"  Tool created: {tool_def['name']}")
        print(f"  Using model: {tool_def['llm']['model']}")

        print("\n✓ Workflow complete: Ready to optimize Python code!")


def example_6_tier_comparison(prompt_gen):
    """Example 6: Compare prompts across different tiers."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Tier Comparison")
    print("=" * 80)

    description = "Translate technical documentation to Spanish"

    for tier in ["tier_1", "tier_2", "tier_3"]:
        result = prompt_gen.generate_prompt(
            description=description,
            task_type="translation",
            tier=tier
        )

        print(f"\n{tier.upper()}:")
        print(f"  Suggested Model: {result['suggested_models'][0]['name'] if result['suggested_models'] else 'N/A'}")
        print(f"  Temperature: {result['metadata']['temperature']}")
        print(f"  Complexity: {tier.replace('tier_', 'Level ')}")
        print(f"  Prompt Length: {len(result['prompt'])} chars")


def example_7_format_styles(prompt_gen):
    """Example 7: Different output format styles."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Format Styles")
    print("=" * 80)

    description = "Summarize research papers"

    formats = ["markdown", "xml", "plain"]

    for fmt in formats:
        result = prompt_gen.generate_prompt(
            description=description,
            task_type="summary",
            format_style=fmt
        )

        print(f"\n{fmt.upper()} Format:")
        print("-" * 40)
        # Show first 300 chars
        print(result["prompt"][:300] + "...")


def main():
    """Run all examples."""
    try:
        # Setup
        config, tools_manager, prompt_gen, model_selector, tool_registry = setup()

        # Run examples
        example_1_basic_prompt_generation(prompt_gen)
        example_2_weight_adjustment(prompt_gen)
        example_3_query_models(model_selector)
        example_4_create_dynamic_tool(prompt_gen, tool_registry)
        example_5_multi_step_workflow(prompt_gen, model_selector)
        example_6_tier_comparison(prompt_gen)
        example_7_format_styles(prompt_gen)

        # Summary
        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETE")
        print("=" * 80)
        print("\nSummary:")
        print(f"  ✓ Generated multiple layered prompts")
        print(f"  ✓ Demonstrated weight adjustment")
        print(f"  ✓ Queried models conversationally")
        print(f"  ✓ Created dynamic tools")
        print(f"  ✓ Built multi-step workflows")
        print(f"  ✓ Compared tiers and formats")
        print("\nCheck ./tools/dynamic/ for created tools")
        print("See PROMPT_GENERATOR_SYSTEM.md for complete documentation")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
