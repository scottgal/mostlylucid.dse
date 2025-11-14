#!/usr/bin/env python3
"""
Qdrant Integration Example

Demonstrates how to use Qdrant vector database with the hierarchical evolution system.
Shows the performance benefits of using Qdrant for large-scale RAG operations.
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qdrant_rag_memory import QdrantRAGMemory
from rag_memory import ArtifactType
from ollama_client import OllamaClient
from hierarchical_evolver import HierarchicalEvolver
from overseer_llm import OverseerLlm
from evaluator_llm import EvaluatorLlm
from rag_integrated_tools import RAGIntegratedTools

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def example_1_basic_qdrant_usage():
    """Example 1: Basic Qdrant RAG operations."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 1: Basic Qdrant RAG Usage")
    logger.info("="*80)

    # Initialize Qdrant RAG
    logger.info("\nInitializing Qdrant RAG Memory...")

    client = OllamaClient()
    rag = QdrantRAGMemory(
        memory_path="./qdrant_rag_example",
        ollama_client=client,
        qdrant_url="http://localhost:6333",
        collection_name="code_evolver_example"
    )

    logger.info("✓ Connected to Qdrant")

    # Store some artifacts
    logger.info("\n--- Storing Artifacts ---")

    # Store a function
    quicksort_code = '''
def quicksort(arr: list) -> list:
    """Sort array using quicksort algorithm."""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
'''

    artifact1 = rag.store_artifact(
        artifact_id="quicksort_v1",
        artifact_type=ArtifactType.FUNCTION,
        name="Quicksort Algorithm",
        description="Efficient divide-and-conquer sorting algorithm with O(n log n) average complexity",
        content=quicksort_code,
        tags=["sort", "algorithm", "divide-conquer"],
        auto_embed=True
    )

    logger.info(f"✓ Stored: {artifact1.artifact_id}")

    # Store another function
    binary_search_code = '''
def binary_search(arr: list, target: int) -> int:
    """Search for target in sorted array using binary search."""
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

    artifact2 = rag.store_artifact(
        artifact_id="binary_search_v1",
        artifact_type=ArtifactType.FUNCTION,
        name="Binary Search",
        description="Efficient search algorithm for sorted arrays with O(log n) complexity",
        content=binary_search_code,
        tags=["search", "algorithm", "divide-conquer"],
        auto_embed=True
    )

    logger.info(f"✓ Stored: {artifact2.artifact_id}")

    # Store a plan
    plan_content = '''
{
  "strategy": "Use quicksort for sorting, then binary search for finding elements",
  "steps": [
    {"step": 1, "action": "sort_array", "tool": "quicksort"},
    {"step": 2, "action": "search_element", "tool": "binary_search"}
  ],
  "expected_quality": 0.9,
  "expected_speed_ms": 100
}
'''

    artifact3 = rag.store_artifact(
        artifact_id="sort_and_search_plan",
        artifact_type=ArtifactType.PLAN,
        name="Sort and Search Plan",
        description="Efficient plan for sorting an array and then searching for elements",
        content=plan_content,
        tags=["plan", "sort", "search"],
        auto_embed=True
    )

    logger.info(f"✓ Stored: {artifact3.artifact_id}")

    # Search for similar artifacts
    logger.info("\n--- Searching for Similar Artifacts ---")

    results = rag.find_similar(
        query="Sort numbers efficiently",
        artifact_type=ArtifactType.FUNCTION,
        top_k=5,
        min_similarity=0.5
    )

    logger.info(f"\nFound {len(results)} similar function(s):")
    for artifact, similarity in results:
        logger.info(f"  - {artifact.name} (similarity: {similarity:.3f})")
        logger.info(f"    Tags: {', '.join(artifact.tags)}")

    # Search with tag filter
    logger.info("\n--- Searching with Tag Filter ---")

    results = rag.find_similar(
        query="Find element in collection",
        tags=["algorithm"],
        top_k=5
    )

    logger.info(f"\nFound {len(results)} artifact(s) with 'algorithm' tag:")
    for artifact, similarity in results:
        logger.info(f"  - {artifact.name} (type: {artifact.artifact_type.value}, similarity: {similarity:.3f})")

    # Get statistics
    logger.info("\n--- RAG Statistics ---")
    stats = rag.get_statistics()

    logger.info(f"Total Artifacts: {stats['total_artifacts']}")
    logger.info(f"Vectors in Qdrant: {stats['vectors_in_qdrant']}")
    logger.info(f"Vector Dimension: {stats['vector_size']}")
    logger.info(f"Artifact Types: {stats['by_type']}")


def example_2_hierarchical_evolution_with_qdrant():
    """Example 2: Using Qdrant with hierarchical evolution."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 2: Hierarchical Evolution with Qdrant")
    logger.info("="*80)

    # Initialize components with Qdrant
    client = OllamaClient()

    qdrant_rag = QdrantRAGMemory(
        memory_path="./qdrant_rag_example",
        ollama_client=client,
        qdrant_url="http://localhost:6333",
        collection_name="code_evolver_hierarchical"
    )

    logger.info("✓ Initialized Qdrant RAG")

    # Initialize hierarchical evolver
    overseer = OverseerLlm(rag_memory=qdrant_rag, model="llama3")
    evaluator = EvaluatorLlm(model="llama3")

    evolver = HierarchicalEvolver(
        overseer=overseer,
        evaluator=evaluator,
        rag_memory=qdrant_rag
    )

    logger.info("✓ Initialized Hierarchical Evolver with Qdrant")

    # Execute a task
    logger.info("\n--- Executing Task ---")

    task = "Create a data validation pipeline"
    node_id = "data_validator_v1"

    plan, execution_result, evaluation = evolver.execute_with_plan(
        task_description=task,
        node_id=node_id,
        depth=0,
        constraints={"quality_target": 0.8, "speed_target_ms": 200}
    )

    logger.info(f"\n✓ Task Executed:")
    logger.info(f"  Plan ID: {plan.plan_id}")
    logger.info(f"  Quality: {evaluation.overall_score:.2f}")
    logger.info(f"  Verdict: {evaluation.verdict}")

    # The plan is now stored in Qdrant and can be retrieved later
    logger.info("\n--- Retrieving Similar Plans from Qdrant ---")

    similar_plans = qdrant_rag.find_similar(
        query="data validation and processing",
        artifact_type=ArtifactType.PLAN,
        top_k=3
    )

    logger.info(f"\nFound {len(similar_plans)} similar plan(s):")
    for artifact, similarity in similar_plans:
        logger.info(f"  - {artifact.name} (similarity: {similarity:.3f})")


def example_3_rag_tools_with_qdrant():
    """Example 3: RAG-integrated tools with Qdrant."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 3: RAG Tools with Qdrant")
    logger.info("="*80)

    # Initialize
    client = OllamaClient()

    qdrant_rag = QdrantRAGMemory(
        memory_path="./qdrant_rag_example",
        ollama_client=client,
        qdrant_url="http://localhost:6333",
        collection_name="code_evolver_tools"
    )

    rag_tools = RAGIntegratedTools(
        rag_memory=qdrant_rag,
        ollama_client=client
    )

    logger.info("✓ Initialized RAG Tools with Qdrant")

    # Register some functions
    logger.info("\n--- Registering Functions ---")

    validate_email_code = '''
def validate_email(email: str) -> bool:
    """
    Validate email address format.

    #tags: validation, email, string
    #use-case: User input validation
    #complexity: O(n)
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
'''

    artifact_id = rag_tools.register_function_to_rag(
        function_code=validate_email_code,
        tags=["validation", "utility"],
        use_cases=["form validation", "user input"],
        quality_score=0.85
    )

    logger.info(f"✓ Registered function: {artifact_id}")

    # Search for tools
    logger.info("\n--- Searching for Validation Tools ---")

    tools = rag_tools.get_tools_for_overseer(
        task_description="Validate user input data",
        level="function",
        max_tools=5
    )

    logger.info(f"\nFound {len(tools)} relevant tool(s):")
    for tool in tools:
        logger.info(f"  - {tool['name']} ({tool['type']})")
        logger.info(f"    Similarity: {tool['similarity']:.3f}")
        logger.info(f"    Quality: {tool.get('quality', 0):.2f}")


def example_4_performance_comparison():
    """Example 4: Performance comparison between numpy and Qdrant."""
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 4: Performance Comparison")
    logger.info("="*80)

    import time

    client = OllamaClient()

    # Initialize Qdrant
    qdrant_rag = QdrantRAGMemory(
        memory_path="./qdrant_perf_test",
        ollama_client=client,
        qdrant_url="http://localhost:6333",
        collection_name="perf_test"
    )

    # Store some test artifacts
    logger.info("\n--- Storing Test Artifacts ---")

    for i in range(10):
        qdrant_rag.store_artifact(
            artifact_id=f"test_func_{i}",
            artifact_type=ArtifactType.FUNCTION,
            name=f"Test Function {i}",
            description=f"Test function for performance testing iteration {i}",
            content=f"def test_{i}(): return {i}",
            tags=["test", f"iteration_{i}"],
            auto_embed=True
        )

    logger.info(f"✓ Stored 10 test artifacts")

    # Benchmark search
    logger.info("\n--- Benchmarking Search Performance ---")

    iterations = 5
    total_time = 0

    for _ in range(iterations):
        start = time.time()

        results = qdrant_rag.find_similar(
            query="test function for performance",
            top_k=5
        )

        elapsed = time.time() - start
        total_time += elapsed

    avg_time = (total_time / iterations) * 1000  # Convert to ms

    logger.info(f"Average search time (Qdrant): {avg_time:.2f}ms")
    logger.info(f"Results returned: {len(results)}")

    # Show statistics
    stats = qdrant_rag.get_statistics()
    logger.info(f"\nQdrant Collection Stats:")
    logger.info(f"  Vectors: {stats['vectors_in_qdrant']}")
    logger.info(f"  Dimension: {stats['vector_size']}")


def main():
    """Run all examples."""
    logger.info("\n" + "="*80)
    logger.info("QDRANT INTEGRATION EXAMPLES")
    logger.info("="*80)
    logger.info("\nMake sure Qdrant is running on http://localhost:6333")
    logger.info("Start with: docker run -p 6333:6333 qdrant/qdrant")
    logger.info("="*80)

    try:
        # Run examples
        example_1_basic_qdrant_usage()
        example_2_hierarchical_evolution_with_qdrant()
        example_3_rag_tools_with_qdrant()
        example_4_performance_comparison()

        logger.info("\n" + "="*80)
        logger.info("✓ All examples completed successfully!")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\n❌ Error running examples: {e}", exc_info=True)
        logger.info("\nMake sure Qdrant is running:")
        logger.info("  docker run -p 6333:6333 qdrant/qdrant")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
