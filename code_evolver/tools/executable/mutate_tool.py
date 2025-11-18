#!/usr/bin/env python3
"""
Mutate Tool - CLI for prompt mutation management.

Enables on-demand mutation of LLM tools with overseer consultation.
Treats LLM tools like code - enables mutation/specialization.

Usage:
    # Interactive mode
    python mutate_tool.py

    # Auto-mutate with overseer decision
    python mutate_tool.py --tool code_reviewer --use-case "security audit" --auto

    # Force mutation without overseer
    python mutate_tool.py --tool code_reviewer --use-case "security audit" --strategy specialize

    # List mutations for a tool
    python mutate_tool.py --tool code_reviewer --list

    # Export mutation as new tool YAML
    python mutate_tool.py --mutation-id xxx --export output.yaml

    # Get best mutation for use case
    python mutate_tool.py --tool code_reviewer --best-for "security review"
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src import OllamaClient, ToolsManager, ConfigManager, create_rag_memory
from src.overseer_llm import OverseerLlm
from src.prompt_mutator import PromptMutator, MutationStrategy


def setup():
    """Setup clients and managers."""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
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


def interactive_mode(tools: ToolsManager, mutator: PromptMutator):
    """Interactive mutation mode."""
    print("\n=== Prompt Mutation Tool ===\n")

    # Select tool
    print("Available tools:")
    llm_tools = [t for t in tools.tools.values() if t.tool_type.value == "llm"]
    for i, tool in enumerate(llm_tools, 1):
        print(f"  {i}. {tool.name} ({tool.tool_id})")

    tool_idx = int(input("\nSelect tool number: ")) - 1
    tool = llm_tools[tool_idx]

    print(f"\nSelected: {tool.name}")
    print(f"Current system prompt: {tool.metadata.get('system_prompt', 'N/A')[:100]}...")
    print(f"Current template: {tool.metadata.get('prompt_template', 'N/A')[:100]}...")

    # Get use case
    use_case = input("\nDescribe the specific use case for mutation: ")

    # Get context
    frequency = input("How often will this be used? (daily/weekly/monthly/rarely): ")
    current_quality = float(input("Current quality (0.0-1.0): ") or "0.5")
    target_quality = float(input("Target quality (0.0-1.0): ") or "0.9")

    context = {
        "frequency": frequency,
        "current_quality": current_quality,
        "target_quality": target_quality
    }

    # Ask overseer
    print("\n🤔 Consulting overseer...")
    decision = mutator.should_mutate(
        tool_id=tool.tool_id,
        use_case=use_case,
        context=context
    )

    print(f"\n{'✓' if decision.should_mutate else '✗'} Overseer decision: {'MUTATE' if decision.should_mutate else 'SKIP'}")
    print(f"Reasoning: {decision.reasoning}")

    if decision.should_mutate:
        print(f"Recommended strategy: {decision.recommended_strategy.value if decision.recommended_strategy else 'N/A'}")
        print(f"Efficiency gain: {decision.efficiency_gain:.1%}")
        print(f"Cost/benefit ratio: {decision.cost_benefit_ratio:.2f}")

    # Proceed with mutation?
    if decision.should_mutate:
        proceed = input("\nProceed with mutation? (y/n): ").lower()
        if proceed != 'y':
            print("Mutation cancelled.")
            return
    else:
        override = input("\nMutate anyway? (y/n): ").lower()
        if override != 'y':
            print("Mutation skipped.")
            return

        # Select strategy
        print("\nAvailable strategies:")
        for i, strategy in enumerate(MutationStrategy, 1):
            print(f"  {i}. {strategy.value}")
        strategy_idx = int(input("Select strategy: ")) - 1
        decision.recommended_strategy = list(MutationStrategy)[strategy_idx]

    # Perform mutation
    print(f"\n🔄 Mutating with {decision.recommended_strategy.value} strategy...")

    system_prompt = tool.metadata.get('system_prompt', '')
    prompt_template = tool.metadata.get('prompt_template', '')

    mutated = mutator.mutate_prompt(
        tool_id=tool.tool_id,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        use_case=use_case,
        strategy=decision.recommended_strategy
    )

    # Display results
    print("\n✓ Mutation complete!")
    print(f"Mutation ID: {mutated.mutation_id}")
    print(f"\nNew system prompt:\n{mutated.mutated_system_prompt}\n")
    print(f"New template:\n{mutated.mutated_prompt_template}\n")

    # Export option
    export = input("Export as new tool YAML? (y/n): ").lower()
    if export == 'y':
        output_file = input("Output file path: ")
        export_mutation_as_yaml(mutated, output_file)
        print(f"✓ Exported to {output_file}")


def auto_mutate(
    tools: ToolsManager,
    mutator: PromptMutator,
    tool_id: str,
    use_case: str,
    context: Optional[dict] = None
):
    """Automatic mutation with overseer decision."""
    tool = tools.get_tool(tool_id)
    if not tool:
        print(f"Error: Tool '{tool_id}' not found", file=sys.stderr)
        return 1

    system_prompt = tool.metadata.get('system_prompt', '')
    prompt_template = tool.metadata.get('prompt_template', '')

    mutated = mutator.auto_mutate(
        tool_id=tool_id,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        use_case=use_case,
        context=context or {}
    )

    if not mutated:
        print("Overseer recommends NOT mutating this tool.")
        return 0

    # Output as JSON
    result = {
        "mutation_id": mutated.mutation_id,
        "parent_tool_id": mutated.parent_tool_id,
        "use_case": mutated.use_case,
        "strategy": mutated.strategy.value,
        "mutated_system_prompt": mutated.mutated_system_prompt,
        "mutated_prompt_template": mutated.mutated_prompt_template,
        "metadata": mutated.metadata
    }

    print(json.dumps(result, indent=2))
    return 0


def force_mutate(
    tools: ToolsManager,
    mutator: PromptMutator,
    tool_id: str,
    use_case: str,
    strategy: str,
    constraints: Optional[str] = None
):
    """Force mutation without overseer consultation."""
    tool = tools.get_tool(tool_id)
    if not tool:
        print(f"Error: Tool '{tool_id}' not found", file=sys.stderr)
        return 1

    try:
        strategy_enum = MutationStrategy(strategy.lower())
    except ValueError:
        print(f"Error: Invalid strategy '{strategy}'", file=sys.stderr)
        print(f"Valid strategies: {', '.join(s.value for s in MutationStrategy)}")
        return 1

    system_prompt = tool.metadata.get('system_prompt', '')
    prompt_template = tool.metadata.get('prompt_template', '')

    additional_constraints = constraints.split(',') if constraints else None

    mutated = mutator.mutate_prompt(
        tool_id=tool_id,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        use_case=use_case,
        strategy=strategy_enum,
        additional_constraints=additional_constraints
    )

    # Output as JSON
    result = {
        "mutation_id": mutated.mutation_id,
        "parent_tool_id": mutated.parent_tool_id,
        "use_case": mutated.use_case,
        "strategy": mutated.strategy.value,
        "mutated_system_prompt": mutated.mutated_system_prompt,
        "mutated_prompt_template": mutated.mutated_prompt_template,
        "metadata": mutated.metadata
    }

    print(json.dumps(result, indent=2))
    return 0


def list_mutations(mutator: PromptMutator, tool_id: str):
    """List all mutations for a tool."""
    mutations = mutator.get_mutations_for_tool(tool_id)

    if not mutations:
        print(f"No mutations found for tool '{tool_id}'")
        return 0

    result = []
    for mutation in mutations:
        result.append({
            "mutation_id": mutation.mutation_id,
            "use_case": mutation.use_case,
            "strategy": mutation.strategy.value,
            "created_at": mutation.created_at,
            "avg_quality": mutation.get_average_quality(),
            "avg_speed_ms": mutation.get_average_speed(),
            "usage_count": len(mutation.performance_metrics)
        })

    print(json.dumps(result, indent=2))
    return 0


def get_best_mutation(mutator: PromptMutator, tool_id: str, use_case: str):
    """Get best mutation for a use case."""
    best = mutator.get_best_mutation_for_use_case(tool_id, use_case)

    if not best:
        print(f"No suitable mutation found for '{use_case}'")
        return 0

    result = {
        "mutation_id": best.mutation_id,
        "parent_tool_id": best.parent_tool_id,
        "use_case": best.use_case,
        "strategy": best.strategy.value,
        "mutated_system_prompt": best.mutated_system_prompt,
        "mutated_prompt_template": best.mutated_prompt_template,
        "avg_quality": best.get_average_quality(),
        "avg_speed_ms": best.get_average_speed()
    }

    print(json.dumps(result, indent=2))
    return 0


def export_mutation_as_yaml(mutation, output_path: str):
    """Export mutation as a new tool YAML file."""
    import yaml

    # Create new tool ID
    new_tool_id = mutation.mutation_id

    # Build YAML structure
    tool_yaml = {
        "name": f"{mutation.parent_tool_id} ({mutation.use_case})",
        "type": "llm",
        "description": f"Specialized version of {mutation.parent_tool_id} for: {mutation.use_case}",
        "llm": {
            "tier": "quality.tier_2",
            "role": "base",
            "system_prompt": mutation.mutated_system_prompt,
            "prompt_template": mutation.mutated_prompt_template
        },
        "tags": [
            "mutation",
            mutation.strategy.value,
            mutation.parent_tool_id
        ],
        "cost_tier": "medium",
        "speed_tier": "medium",
        "quality_tier": "excellent",
        "metadata": {
            "parent_tool_id": mutation.parent_tool_id,
            "mutation_id": mutation.mutation_id,
            "use_case": mutation.use_case,
            "strategy": mutation.strategy.value,
            "created_at": mutation.created_at
        }
    }

    # Write to file
    with open(output_path, 'w') as f:
        yaml.dump(tool_yaml, f, default_flow_style=False, sort_keys=False)


def export_mutation(mutator: PromptMutator, mutation_id: str, output_path: str):
    """Export existing mutation to YAML."""
    mutation = mutator.get_mutation(mutation_id)
    if not mutation:
        print(f"Error: Mutation '{mutation_id}' not found", file=sys.stderr)
        return 1

    export_mutation_as_yaml(mutation, output_path)
    print(f"✓ Exported mutation to {output_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Mutate LLM tool prompts for specific use cases"
    )

    parser.add_argument(
        "--tool",
        help="Tool ID to mutate"
    )

    parser.add_argument(
        "--use-case",
        help="Specific use case for mutation"
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatic mutation with overseer decision"
    )

    parser.add_argument(
        "--strategy",
        choices=[s.value for s in MutationStrategy],
        help="Force specific mutation strategy (skips overseer)"
    )

    parser.add_argument(
        "--constraints",
        help="Additional constraints (comma-separated)"
    )

    parser.add_argument(
        "--context",
        type=json.loads,
        help="Context as JSON string"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List mutations for a tool"
    )

    parser.add_argument(
        "--best-for",
        help="Get best mutation for use case"
    )

    parser.add_argument(
        "--mutation-id",
        help="Mutation ID for export"
    )

    parser.add_argument(
        "--export",
        help="Export mutation to YAML file"
    )

    args = parser.parse_args()

    # Setup
    config, client, tools, overseer, mutator = setup()

    # Interactive mode
    if not any([args.tool, args.mutation_id]):
        interactive_mode(tools, mutator)
        return 0

    # Export mode
    if args.mutation_id and args.export:
        return export_mutation(mutator, args.mutation_id, args.export)

    # List mode
    if args.list:
        return list_mutations(mutator, args.tool)

    # Best mutation mode
    if args.best_for:
        return get_best_mutation(mutator, args.tool, args.best_for)

    # Auto mutate mode
    if args.auto:
        return auto_mutate(tools, mutator, args.tool, args.use_case, args.context)

    # Force mutate mode
    if args.strategy:
        return force_mutate(
            tools, mutator, args.tool, args.use_case,
            args.strategy, args.constraints
        )

    # No valid mode
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
