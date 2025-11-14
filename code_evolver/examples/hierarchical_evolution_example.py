#!/usr/bin/env python3
"""
Example: Hierarchical Evolution with RAG Integration

Demonstrates:
1. Execution → Evaluation → Evolution feedback loop
2. RAG search at every level (workflow → function)
3. Tools retrieved from RAG for overseer
4. Token optimization and self-learning
5. Parent nodes learning from children
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from overseer_llm import OverseerLlm, ExecutionPlan
from evaluator_llm import EvaluatorLlm, FitnessEvaluation
from hierarchical_evolver import HierarchicalEvolver, SharedPlanContext
from rag_integrated_tools import RAGIntegratedTools, FunctionMetadata
from rag_memory import RAGMemory, ArtifactType
from ollama_client import OllamaClient
from node_runner import NodeRunner
from registry import Registry

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def example_1_basic_execution_flow():
    """Example 1: Basic Plan → Execute → Evaluate → Evolve flow."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 1: Basic Execution Flow")
    logger.info("="*80)

    # Initialize components
    rag_memory = RAGMemory(memory_path="./rag_memory_example")
    overseer = OverseerLlm(rag_memory=rag_memory)
    evaluator = EvaluatorLlm()
    runner = NodeRunner(nodes_path="./nodes_example")
    registry = Registry(registry_path="./registry_example")

    evolver = HierarchicalEvolver(
        overseer=overseer,
        evaluator=evaluator,
        rag_memory=rag_memory,
        runner=runner,
        registry=registry
    )

    # Task: Sort a list of numbers
    task = "Sort a list of numbers using an efficient algorithm"
    node_id = "sort_numbers_v1"

    # Execute with plan
    plan, execution_result, evaluation = evolver.execute_with_plan(
        task_description=task,
        node_id=node_id,
        input_data={"numbers": [5, 2, 8, 1, 9]},
        constraints={"quality_target": 0.8, "speed_target_ms": 100}
    )

    # Print results
    logger.info("\n--- Execution Results ---")
    logger.info(f"Plan ID: {plan.plan_id}")
    logger.info(f"Strategy: {plan.strategy}")
    logger.info(f"Quality Score: {evaluation.overall_score:.2f}")
    logger.info(f"Verdict: {evaluation.verdict}")

    # Evolve with feedback if score is low
    if evaluation.overall_score < 0.8:
        logger.info("\n--- Starting Evolution ---")
        improved_plan, improved_eval = evolver.evolve_with_feedback(
            plan=plan,
            execution_result=execution_result,
            evaluation=evaluation,
            iterations=2
        )

        logger.info(f"✓ Evolution complete")
        logger.info(f"  Original score: {evaluation.overall_score:.2f}")
        logger.info(f"  Improved score: {improved_eval.overall_score:.2f}")


def example_2_rag_tool_retrieval():
    """Example 2: RAG-based tool retrieval at multiple levels."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 2: RAG Tool Retrieval")
    logger.info("="*80)

    # Initialize RAG tools
    rag_memory = RAGMemory(memory_path="./rag_memory_example")
    rag_tools = RAGIntegratedTools(rag_memory=rag_memory)

    # Register some example functions to RAG
    logger.info("\n--- Registering Functions to RAG ---")

    # Example function 1: Quicksort
    quicksort_code = '''
def quicksort(arr: list) -> list:
    """
    Sort array using quicksort algorithm.

    #tags: sort, divide-conquer, efficient
    #use-case: Sorting large arrays efficiently
    #complexity: O(n log n) average
    """
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
'''

    artifact_id_1 = rag_tools.register_function_to_rag(
        function_code=quicksort_code,
        tags=["sort", "algorithm"],
        use_cases=["sorting numbers", "array processing"],
        quality_score=0.9
    )

    logger.info(f"✓ Registered quicksort: {artifact_id_1}")

    # Example function 2: Binary search
    binary_search_code = '''
def binary_search(arr: list, target: int) -> int:
    """
    Search for target in sorted array using binary search.

    #tags: search, divide-conquer, efficient
    #use-case: Finding elements in sorted arrays
    #complexity: O(log n)
    """
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
'''

    artifact_id_2 = rag_tools.register_function_to_rag(
        function_code=binary_search_code,
        tags=["search", "algorithm"],
        use_cases=["searching numbers", "finding elements"],
        quality_score=0.85
    )

    logger.info(f"✓ Registered binary_search: {artifact_id_2}")

    # Search for tools
    logger.info("\n--- Searching for Tools ---")

    # Search for sorting functions
    sort_results = rag_tools.find_solution_at_level(
        level="function",
        task_description="Sort a list of numbers efficiently",
        top_k=3
    )

    logger.info(f"\nFound {len(sort_results)} sorting solution(s):")
    for artifact, similarity in sort_results:
        logger.info(f"  - {artifact.name} (similarity: {similarity:.2f}, quality: {artifact.quality_score:.2f})")

    # Get tools for overseer
    logger.info("\n--- Getting Tools for Overseer ---")
    tools = rag_tools.get_tools_for_overseer(
        task_description="Sort and search an array",
        level="workflow",
        max_tools=5
    )

    logger.info(f"\nRetrieved {len(tools)} tools:")
    for tool in tools:
        logger.info(f"  - {tool['name']} ({tool['type']}) - similarity: {tool['similarity']:.2f}")


def example_3_hierarchical_learning():
    """Example 3: Parent node learning from children."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 3: Hierarchical Learning")
    logger.info("="*80)

    # Initialize evolver
    rag_memory = RAGMemory(memory_path="./rag_memory_example")
    evolver = HierarchicalEvolver(rag_memory=rag_memory)

    # Parent task: Process data pipeline
    parent_node = "data_pipeline"
    parent_task = "Process data through validation, transformation, and aggregation"

    logger.info(f"\nParent Task: {parent_task}")
    logger.info(f"Parent Node: {parent_node}")

    # Execute parent (simplified)
    logger.info("\n--- Executing Child Nodes ---")

    # Child 1: Validation approach A (fast but less thorough)
    logger.info("\nChild 1: Validation A (fast)")
    plan1, result1, eval1 = evolver.execute_with_plan(
        task_description="Validate data with basic checks",
        node_id="validate_a",
        parent_node_id=parent_node,
        depth=1,
        constraints={"quality_target": 0.7, "speed_target_ms": 50}
    )
    # Simulate: quality 0.7, speed 45ms
    eval1.overall_score = 0.7
    eval1.quality_score = 0.7
    result1["metrics"]["latency_ms"] = 45

    # Child 2: Validation approach B (thorough but slower)
    logger.info("\nChild 2: Validation B (thorough)")
    plan2, result2, eval2 = evolver.execute_with_plan(
        task_description="Validate data with comprehensive checks",
        node_id="validate_b",
        parent_node_id=parent_node,
        depth=1,
        constraints={"quality_target": 0.9, "speed_target_ms": 150}
    )
    # Simulate: quality 0.95, speed 120ms
    eval2.overall_score = 0.95
    eval2.quality_score = 0.95
    result2["metrics"]["latency_ms"] = 120

    # Parent learns from children
    logger.info("\n--- Parent Learning ---")
    learning = evolver.learn_from_children(
        parent_node_id=parent_node,
        optimization_goal="quality"  # Prefer quality over speed
    )

    if learning:
        logger.info(f"\n✓ Parent learned:")
        logger.info(f"  Lesson: {learning.lesson}")
        logger.info(f"  Recommendation: {learning.recommendation}")
        logger.info(f"  Quality achieved: {learning.quality_achieved:.2f}")

    # Get statistics
    logger.info("\n--- Node Statistics ---")
    for node_id in ["validate_a", "validate_b"]:
        stats = evolver.get_node_statistics(node_id)
        if "error" not in stats:
            logger.info(f"\n{node_id}:")
            logger.info(f"  Executions: {stats['executions']}")
            logger.info(f"  Avg Quality: {stats['avg_quality']:.2f}")
            logger.info(f"  Avg Speed: {stats['avg_speed_ms']:.0f}ms")


def example_4_token_optimization():
    """Example 4: Token optimization and self-learning."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 4: Token Optimization")
    logger.info("="*80)

    # Initialize RAG tools
    rag_memory = RAGMemory(memory_path="./rag_memory_example")
    rag_tools = RAGIntegratedTools(rag_memory=rag_memory)

    # Example: Verbose function that needs optimization
    verbose_code = '''
def calculate_average_of_numbers_in_list(input_list_of_numbers: list) -> float:
    """
    This function calculates the average (mean) value of all numbers in a given list.
    It takes a list of numbers as input and returns the average as a float.

    #tags: math, statistics, average
    #use-case: Calculate mean of numeric values
    """
    # First, we need to check if the list is empty
    if len(input_list_of_numbers) == 0:
        # If the list is empty, we return 0
        return 0.0

    # Initialize a variable to store the sum
    total_sum_of_all_numbers = 0.0

    # Iterate through each number in the list
    for individual_number in input_list_of_numbers:
        # Add the number to our running total
        total_sum_of_all_numbers = total_sum_of_all_numbers + individual_number

    # Calculate the average by dividing sum by count
    average_value = total_sum_of_all_numbers / len(input_list_of_numbers)

    # Return the calculated average
    return average_value
'''

    logger.info("\n--- Original Code ---")
    logger.info(f"Token count: ~{rag_tools._estimate_tokens(verbose_code)} tokens")

    # Optimize and save
    logger.info("\n--- Optimizing Code ---")
    artifact_id = rag_tools.optimize_and_save(
        code=verbose_code,
        task_description="Calculate average of numbers in a list",
        level="function",
        quality_score=0.8
    )

    logger.info(f"✓ Optimized and saved: {artifact_id}")

    # Retrieve optimized version
    artifact = rag_memory.get_artifact(artifact_id)
    if artifact:
        logger.info("\n--- Optimized Code ---")
        logger.info(f"Token count: ~{artifact.metadata.get('token_count', 0)} tokens")
        logger.info(f"\nCode:\n{artifact.content}")


def main():
    """Run all examples."""
    logger.info("\n" + "="*80)
    logger.info("HIERARCHICAL EVOLUTION SYSTEM - EXAMPLES")
    logger.info("="*80)

    try:
        # Run examples
        example_1_basic_execution_flow()
        example_2_rag_tool_retrieval()
        example_3_hierarchical_learning()
        example_4_token_optimization()

        logger.info("\n" + "="*80)
        logger.info("✓ All examples completed successfully!")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\n❌ Error running examples: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
