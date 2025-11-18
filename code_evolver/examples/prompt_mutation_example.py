#!/usr/bin/env python3
"""
Example: Prompt Mutation System

Demonstrates how to use the prompt mutation system to treat LLM tools like code,
enabling specialization for specific use cases instead of using overly general prompts.

This example shows:
1. Consulting the overseer to decide if mutation is beneficial
2. Mutating prompts for specific use cases
3. Tracking performance of mutations
4. Exporting successful mutations as new tools
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import OllamaClient, ToolsManager, ConfigManager, create_rag_memory
from src.overseer_llm import OverseerLlm
from src.prompt_mutator import PromptMutator, MutationStrategy


def setup():
    """Setup all components."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = ConfigManager(str(config_path))

    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)

    tools = ToolsManager(
        config_manager=config,
        ollama_client=client,
        rag_memory=rag
    )

    overseer = OverseerLlm(client=client, rag_memory=rag)

    mutator = PromptMutator(
        ollama_client=client,
        overseer_llm=overseer,
        rag_memory=rag
    )

    return config, client, tools, overseer, mutator


def example_1_overseer_decision():
    """Example 1: Ask overseer if mutation is beneficial."""
    print("\n" + "="*60)
    print("Example 1: Overseer Decision for Mutation")
    print("="*60 + "\n")

    _, _, tools, _, mutator = setup()

    # Get a tool
    tool = tools.get_tool("code_reviewer")
    if not tool:
        print("Tool 'code_reviewer' not found. Skipping example.")
        return

    # Define specific use case
    use_case = "Security audit of authentication and authorization code"

    # Provide context for decision
    context = {
        "frequency": "daily",  # Used daily
        "current_quality": 0.6,  # Current general prompt gets 60% quality
        "target_quality": 0.95,  # We want 95% quality
        "importance": "critical"  # Security is critical
    }

    print(f"Tool: {tool.name}")
    print(f"Use Case: {use_case}")
    print(f"Context: {context}\n")

    # Ask overseer
    print("🤔 Consulting overseer...\n")
    decision = mutator.should_mutate(
        tool_id=tool.tool_id,
        use_case=use_case,
        context=context
    )

    # Display decision
    print(f"{'✓' if decision.should_mutate else '✗'} Decision: {'MUTATE' if decision.should_mutate else 'SKIP'}")
    print(f"Reasoning: {decision.reasoning}")

    if decision.should_mutate:
        print(f"\nRecommended Strategy: {decision.recommended_strategy.value if decision.recommended_strategy else 'N/A'}")
        print(f"Expected Efficiency Gain: {decision.efficiency_gain:.1%}")
        print(f"Cost/Benefit Ratio: {decision.cost_benefit_ratio:.2f}")


def example_2_auto_mutation():
    """Example 2: Automatic mutation with overseer consultation."""
    print("\n" + "="*60)
    print("Example 2: Auto-Mutation with Overseer")
    print("="*60 + "\n")

    _, _, tools, _, mutator = setup()

    # Get tool
    tool = tools.get_tool("technical_writer")
    if not tool:
        print("Tool 'technical_writer' not found. Skipping example.")
        return

    system_prompt = tool.metadata.get('system_prompt', '')
    prompt_template = tool.metadata.get('prompt_template', '')

    print(f"Original Tool: {tool.name}")
    print(f"Original System Prompt: {system_prompt[:100]}...")
    print(f"Original Template: {prompt_template[:100]}...\n")

    # Auto-mutate for specific use case
    use_case = "API documentation for Python libraries with type hints"
    context = {
        "frequency": "weekly",
        "current_quality": 0.7,
        "target_quality": 0.9
    }

    print(f"Target Use Case: {use_case}\n")
    print("🔄 Auto-mutating (overseer will decide)...\n")

    mutated = mutator.auto_mutate(
        tool_id=tool.tool_id,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        use_case=use_case,
        context=context
    )

    if mutated:
        print("✓ Mutation created!")
        print(f"Mutation ID: {mutated.mutation_id}")
        print(f"\nMutated System Prompt:\n{mutated.mutated_system_prompt}\n")
        print(f"Mutated Template:\n{mutated.mutated_prompt_template}\n")
    else:
        print("Overseer recommends NOT mutating this tool.")


def example_3_force_mutation():
    """Example 3: Force mutation with specific strategy."""
    print("\n" + "="*60)
    print("Example 3: Force Mutation with Specific Strategy")
    print("="*60 + "\n")

    _, _, tools, _, mutator = setup()

    # Get tool
    tool = tools.get_tool("code_explainer")
    if not tool:
        print("Tool 'code_explainer' not found. Skipping example.")
        return

    system_prompt = tool.metadata.get('system_prompt', '')
    prompt_template = tool.metadata.get('prompt_template', '')

    print(f"Tool: {tool.name}")
    print(f"Strategy: SPECIALIZE\n")

    # Force mutation without overseer
    use_case = "Explaining async/await patterns in Python"

    constraints = [
        "Must include examples with asyncio",
        "Explain event loop concepts",
        "Cover common pitfalls"
    ]

    print(f"Use Case: {use_case}")
    print(f"Constraints: {constraints}\n")
    print("🔄 Mutating with SPECIALIZE strategy...\n")

    mutated = mutator.mutate_prompt(
        tool_id=tool.tool_id,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        use_case=use_case,
        strategy=MutationStrategy.SPECIALIZE,
        additional_constraints=constraints
    )

    print("✓ Mutation complete!")
    print(f"Mutation ID: {mutated.mutation_id}")
    print(f"\nMutated System Prompt:\n{mutated.mutated_system_prompt}\n")
    print(f"Mutated Template:\n{mutated.mutated_prompt_template}\n")


def example_4_mutation_tracking():
    """Example 4: Track mutation performance and get best."""
    print("\n" + "="*60)
    print("Example 4: Mutation Performance Tracking")
    print("="*60 + "\n")

    _, client, tools, _, mutator = setup()

    # Simulate creating and using mutations
    tool = tools.get_tool("code_reviewer")
    if not tool:
        print("Tool 'code_reviewer' not found. Skipping example.")
        return

    system_prompt = tool.metadata.get('system_prompt', '')
    prompt_template = tool.metadata.get('prompt_template', '')

    # Create a mutation
    print("Creating mutation for 'security review' use case...\n")
    mutated = mutator.mutate_prompt(
        tool_id=tool.tool_id,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        use_case="Security review of authentication code",
        strategy=MutationStrategy.SPECIALIZE
    )

    print(f"✓ Created: {mutated.mutation_id}\n")

    # Simulate using it and recording performance
    print("Simulating usage and recording performance...\n")

    # Record successful uses
    mutated.record_performance(quality=0.95, speed_ms=1200, success=True, context="Auth review #1")
    mutated.record_performance(quality=0.93, speed_ms=1150, success=True, context="Auth review #2")
    mutated.record_performance(quality=0.96, speed_ms=1100, success=True, context="Auth review #3")

    print(f"Average Quality: {mutated.get_average_quality():.2f}")
    print(f"Average Speed: {mutated.get_average_speed():.0f}ms")
    print(f"Usage Count: {len(mutated.performance_metrics)}\n")

    # Find best mutation for similar use case
    print("Finding best mutation for 'security audit' use case...\n")
    best = mutator.get_best_mutation_for_use_case(
        tool_id=tool.tool_id,
        use_case="security audit",
        min_quality=0.9
    )

    if best:
        print(f"✓ Found best mutation: {best.mutation_id}")
        print(f"Average Quality: {best.get_average_quality():.2f}")
        print(f"Average Speed: {best.get_average_speed():.0f}ms")
    else:
        print("No suitable mutation found.")


def example_5_export_mutation():
    """Example 5: Export mutation as new tool YAML."""
    print("\n" + "="*60)
    print("Example 5: Export Mutation as New Tool")
    print("="*60 + "\n")

    _, _, tools, _, mutator = setup()

    # Get mutations
    mutations = mutator.get_mutations_for_tool("code_reviewer")
    if not mutations:
        print("No mutations found. Create one first using example 4.")
        return

    mutation = mutations[0]

    print(f"Exporting mutation: {mutation.mutation_id}")
    print(f"Use Case: {mutation.use_case}\n")

    # Export to YAML
    output_file = f"/tmp/{mutation.mutation_id}.yaml"

    from tools.executable.mutate_tool import export_mutation_as_yaml
    export_mutation_as_yaml(mutation, output_file)

    print(f"✓ Exported to: {output_file}\n")
    print("This YAML can now be copied to code_evolver/tools/llm/")
    print("and will be loaded like any other tool.")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("PROMPT MUTATION SYSTEM - EXAMPLES")
    print("="*60)

    try:
        example_1_overseer_decision()
        example_2_auto_mutation()
        example_3_force_mutation()
        example_4_mutation_tracking()
        example_5_export_mutation()

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "="*60)
    print("Examples complete!")
    print("="*60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
