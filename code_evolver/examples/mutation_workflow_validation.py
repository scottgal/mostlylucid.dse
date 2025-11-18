#!/usr/bin/env python3
"""
Example: Mutation Validation in Workflows

Demonstrates how to validate mutations during workflow execution to ensure
the prompt still fits even though it's using a mutation.

CRITICAL: Always validate mutations before using them in workflows!
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import OllamaClient, ToolsManager, ConfigManager, create_rag_memory
from src.overseer_llm import OverseerLlm
from src.prompt_mutator import PromptMutator
from src.mutation_validator import (
    MutationValidator,
    validate_mutation_for_optimization,
    get_validated_mutation_for_workflow
)


def example_1_basic_validation():
    """Example 1: Basic mutation validation."""
    print("\n" + "="*60)
    print("Example 1: Basic Mutation Validation")
    print("="*60 + "\n")

    # Setup
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = ConfigManager(str(config_path))
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    overseer = OverseerLlm(client=client, rag_memory=rag)
    mutator = PromptMutator(ollama_client=client, overseer_llm=overseer, rag_memory=rag)

    # Create a mutation for Claude
    print("Creating mutation optimized for Claude Sonnet...\n")
    mutation = mutator.mutate_prompt(
        tool_id="code_reviewer",
        system_prompt="You are a code reviewer.",
        prompt_template="Review this code:\n{code}",
        use_case="Security audit of authentication code",
        strategy=mutator.MutationStrategy.SPECIALIZE,
        llm_config={
            "backend": "anthropic",
            "model": "claude-sonnet-4",
            "tier": "quality.tier_3"
        }
    )

    print(f"✓ Created mutation: {mutation.mutation_id}")
    print(f"  Optimized for: {mutation.llm_backend}/{mutation.llm_model}\n")

    # Scenario 1: Using with Claude (compatible)
    print("Scenario 1: Using mutation with Claude Sonnet (compatible)\n")

    is_compatible, reason = mutator.check_mutation_compatibility(
        mutation,
        {"backend": "anthropic", "model": "claude-sonnet-4"}
    )

    print(f"  Compatible: {is_compatible}")
    print(f"  Reason: {reason}\n")

    # Scenario 2: Using with Llama (incompatible)
    print("Scenario 2: Trying to use mutation with Llama (incompatible)\n")

    is_compatible, reason = mutator.check_mutation_compatibility(
        mutation,
        {"backend": "ollama", "model": "llama3"}
    )

    print(f"  Compatible: {is_compatible}")
    print(f"  Reason: {reason}\n")

    # Scenario 3: Using with Claude Opus (compatible model family)
    print("Scenario 3: Using mutation with Claude Opus (same family)\n")

    is_compatible, reason = mutator.check_mutation_compatibility(
        mutation,
        {"backend": "anthropic", "model": "claude-opus-4"}
    )

    print(f"  Compatible: {is_compatible}")
    print(f"  Reason: {reason}\n")


def example_2_workflow_validation():
    """Example 2: Comprehensive workflow validation."""
    print("\n" + "="*60)
    print("Example 2: Comprehensive Workflow Validation")
    print("="*60 + "\n")

    # Setup
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = ConfigManager(str(config_path))
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    overseer = OverseerLlm(client=client, rag_memory=rag)
    mutator = PromptMutator(ollama_client=client, overseer_llm=overseer, rag_memory=rag)

    # Create mutation with usage history
    mutation = mutator.mutate_prompt(
        tool_id="technical_writer",
        system_prompt="You are a technical writer.",
        prompt_template="Write documentation for: {topic}",
        use_case="API documentation for Python libraries",
        strategy=mutator.MutationStrategy.SPECIALIZE,
        llm_config={
            "backend": "anthropic",
            "model": "claude-sonnet-4"
        }
    )

    # Simulate usage history
    print("Simulating usage history...\n")
    mutation.record_performance(quality=0.92, speed_ms=1500, success=True)
    mutation.record_performance(quality=0.89, speed_ms=1400, success=True)
    mutation.record_performance(quality=0.93, speed_ms=1600, success=True)
    mutation.record_performance(quality=0.91, speed_ms=1450, success=True)

    # Validate for workflow
    validator = MutationValidator(mutator)

    current_llm_config = {
        "backend": "anthropic",
        "model": "claude-sonnet-4",
        "tier": "quality.tier_2"
    }

    is_valid, warnings = validator.validate_for_workflow(
        mutation,
        current_llm_config,
        strict=False,
        check_age=True,
        check_performance=True
    )

    print(f"Validation Result: {'✓ VALID' if is_valid else '✗ INVALID'}\n")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("No warnings - mutation is fully compatible!\n")

    print(f"Average Quality: {mutation.get_average_quality():.2f}")
    print(f"Average Speed: {mutation.get_average_speed():.0f}ms")
    print(f"Usage Count: {len(mutation.performance_metrics)}\n")


def example_3_optimization_validation():
    """Example 3: Validation during optimization."""
    print("\n" + "="*60)
    print("Example 3: Validation During Optimization")
    print("="*60 + "\n")

    # Setup
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = ConfigManager(str(config_path))
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    overseer = OverseerLlm(client=client, rag_memory=rag)
    mutator = PromptMutator(ollama_client=client, overseer_llm=overseer, rag_memory=rag)

    # Create mutations for different LLMs
    print("Creating mutations for different LLMs...\n")

    claude_mutation = mutator.mutate_prompt(
        tool_id="code_reviewer",
        system_prompt="You are a code reviewer.",
        prompt_template="Review: {code}",
        use_case="Security review",
        strategy=mutator.MutationStrategy.SPECIALIZE,
        llm_config={"backend": "anthropic", "model": "claude-sonnet-4"}
    )
    claude_mutation.record_performance(0.95, 1200, True)
    claude_mutation.record_performance(0.93, 1150, True)
    claude_mutation.record_performance(0.94, 1180, True)

    llama_mutation = mutator.mutate_prompt(
        tool_id="code_reviewer",
        system_prompt="You are a code reviewer.",
        prompt_template="Review: {code}",
        use_case="Security review",
        strategy=mutator.MutationStrategy.SPECIALIZE,
        llm_config={"backend": "ollama", "model": "llama3"}
    )
    llama_mutation.record_performance(0.82, 800, True)
    llama_mutation.record_performance(0.85, 750, True)

    print(f"✓ Created Claude mutation: {claude_mutation.mutation_id}")
    print(f"  Quality: {claude_mutation.get_average_quality():.2f}\n")

    print(f"✓ Created Llama mutation: {llama_mutation.mutation_id}")
    print(f"  Quality: {llama_mutation.get_average_quality():.2f}\n")

    # Simulate optimization: selecting best mutation for current LLM
    print("="*60)
    print("OPTIMIZATION: Selecting best mutation for current LLM")
    print("="*60 + "\n")

    # Scenario: Workflow is running on Claude
    workflow_llm = {"backend": "anthropic", "model": "claude-sonnet-4"}

    print(f"Workflow LLM: {workflow_llm['backend']}/{workflow_llm['model']}\n")

    print("Validating mutations...\n")

    # Validate Claude mutation
    should_use_claude, reason = validate_mutation_for_optimization(
        claude_mutation,
        workflow_llm,
        mutator
    )
    print(f"Claude mutation:")
    print(f"  Should use: {should_use_claude}")
    print(f"  Reason: {reason}\n")

    # Validate Llama mutation
    should_use_llama, reason = validate_mutation_for_optimization(
        llama_mutation,
        workflow_llm,
        mutator
    )
    print(f"Llama mutation:")
    print(f"  Should use: {should_use_llama}")
    print(f"  Reason: {reason}\n")

    print("="*60)
    if should_use_claude:
        print("✓ Using Claude mutation (optimized for current LLM)")
    elif should_use_llama:
        print("⚠ Using Llama mutation (not optimized, but compatible)")
    else:
        print("✗ No compatible mutation - using original prompt")
    print("="*60 + "\n")


def example_4_workflow_integration():
    """Example 4: Complete workflow integration."""
    print("\n" + "="*60)
    print("Example 4: Complete Workflow Integration")
    print("="*60 + "\n")

    # Setup
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = ConfigManager(str(config_path))
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    overseer = OverseerLlm(client=client, rag_memory=rag)
    mutator = PromptMutator(ollama_client=client, overseer_llm=overseer, rag_memory=rag)

    # Create and use mutation with workflow helper
    print("Creating mutation...\n")

    mutation = mutator.mutate_prompt(
        tool_id="technical_writer",
        system_prompt="You are a technical writer.",
        prompt_template="Write about: {topic}",
        use_case="API documentation",
        strategy=mutator.MutationStrategy.SPECIALIZE,
        llm_config={"backend": "anthropic", "model": "claude-sonnet-4"}
    )

    # Simulate usage
    mutation.record_performance(0.90, 1500, True)
    mutation.record_performance(0.92, 1450, True)
    mutation.record_performance(0.91, 1480, True)

    print(f"✓ Created mutation: {mutation.mutation_id}\n")

    # In a real workflow: Get validated mutation
    print("="*60)
    print("WORKFLOW EXECUTION")
    print("="*60 + "\n")

    workflow_llm = {
        "backend": "anthropic",
        "model": "claude-sonnet-4",
        "tier": "quality.tier_2"
    }

    mutation_to_use, is_mutated = get_validated_mutation_for_workflow(
        tool_id="technical_writer",
        use_case="API documentation",
        current_llm_config=workflow_llm,
        prompt_mutator=mutator,
        fallback_to_original=True
    )

    if is_mutated:
        print("✓ Using validated mutation")
        print(f"  Mutation ID: {mutation_to_use.mutation_id}")
        print(f"  Quality: {mutation_to_use.get_average_quality():.2f}")
        print(f"  Optimized for: {mutation_to_use.llm_backend}/{mutation_to_use.llm_model}")
        print(f"\n  Mutated Prompt:")
        print(f"  {mutation_to_use.mutated_prompt_template[:100]}...")
    else:
        print("⚠ No valid mutation found - using original prompt")
        print("  This ensures the workflow still works even without mutations")


def example_5_strict_vs_loose_validation():
    """Example 5: Strict vs loose validation modes."""
    print("\n" + "="*60)
    print("Example 5: Strict vs Loose Validation")
    print("="*60 + "\n")

    # Setup
    config_path = Path(__file__).parent.parent / "config.yaml"
    config = ConfigManager(str(config_path))
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    overseer = OverseerLlm(client=client, rag_memory=rag)
    mutator = PromptMutator(ollama_client=client, overseer_llm=overseer, rag_memory=rag)

    # Create mutation for Claude Sonnet
    mutation = mutator.mutate_prompt(
        tool_id="code_reviewer",
        system_prompt="You are a code reviewer.",
        prompt_template="Review: {code}",
        use_case="Code review",
        strategy=mutator.MutationStrategy.OPTIMIZE,
        llm_config={"backend": "anthropic", "model": "claude-sonnet-4"}
    )

    print(f"Mutation optimized for: {mutation.llm_backend}/{mutation.llm_model}\n")

    # Test with Claude Opus (different model, same backend)
    test_config = {"backend": "anthropic", "model": "claude-opus-4"}

    print(f"Testing with: {test_config['backend']}/{test_config['model']}\n")

    # Strict mode
    print("STRICT MODE:")
    is_compat, reason = mutator.check_mutation_compatibility(
        mutation, test_config, strict=True
    )
    print(f"  Compatible: {is_compat}")
    print(f"  Reason: {reason}\n")

    # Loose mode
    print("LOOSE MODE:")
    is_compat, reason = mutator.check_mutation_compatibility(
        mutation, test_config, strict=False
    )
    print(f"  Compatible: {is_compat}")
    print(f"  Reason: {reason}\n")

    print("="*60)
    print("RECOMMENDATION:")
    print("  - Use STRICT mode for production workflows (exact match)")
    print("  - Use LOOSE mode for optimization (allow compatible models)")
    print("="*60 + "\n")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("MUTATION VALIDATION IN WORKFLOWS - EXAMPLES")
    print("="*60)

    try:
        example_1_basic_validation()
        example_2_workflow_validation()
        example_3_optimization_validation()
        example_4_workflow_integration()
        example_5_strict_vs_loose_validation()

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "="*60)
    print("✓ All examples complete!")
    print("="*60 + "\n")

    print("KEY TAKEAWAYS:")
    print("1. Always validate mutations before using in workflows")
    print("2. Check LLM compatibility (backend, model, tier)")
    print("3. Monitor performance metrics and age")
    print("4. Use helper functions for easy integration")
    print("5. Fallback to original prompt if no valid mutation\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
