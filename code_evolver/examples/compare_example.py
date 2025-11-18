"""
Example usage of the Universal Comparison Tool

Demonstrates:
1. Performance comparison between two implementations
2. Text comparison for content similarity
3. Quality comparison with custom metrics
"""

import asyncio
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.comparer_tool import (
    PerformanceComparer,
    ContentComparer,
    ComparisonStrategy,
    compare_performance,
    compare_text,
    compare_quality
)


# Example 1: Performance Comparison
# ==================================

async def slow_sort(items, reverse=False):
    """Bubble sort - intentionally slow"""
    result = items.copy()
    n = len(result)
    for i in range(n):
        for j in range(0, n - i - 1):
            if (result[j] > result[j + 1]) != reverse:
                result[j], result[j + 1] = result[j + 1], result[j]
    return result


async def fast_sort(items, reverse=False):
    """Python's built-in sort - fast"""
    result = items.copy()
    result.sort(reverse=reverse)
    return result


async def example_performance_comparison():
    """Compare performance of two sorting implementations"""
    print("="*70)
    print("EXAMPLE 1: Performance Comparison")
    print("="*70)
    print("\nComparing bubble sort vs. built-in sort...\n")

    comparer = PerformanceComparer()

    # Test data
    test_data = list(range(100, 0, -1))  # Reverse sorted list

    result = await comparer.compare_endpoints(
        endpoint_a=slow_sort,
        endpoint_b=fast_sort,
        params_a={"items": test_data, "reverse": False},
        params_b={"items": test_data, "reverse": False},
        iterations=5,
        strategy=ComparisonStrategy.INTERLEAVED,
        warmup_iterations=1
    )

    print(result.summary)
    print(f"\nWinner: {result.winner or 'Tie'}")
    print(f"Score: {result.score:.1f}")

    return result


# Example 2: Text Comparison
# ===========================

def example_text_comparison():
    """Compare similarity between two text strings"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Text Comparison")
    print("="*70)

    text_a = """
    The quick brown fox jumps over the lazy dog.
    This is a classic pangram used for testing.
    It contains all letters of the alphabet.
    """

    text_b = """
    The quick brown fox leaps over the sleepy dog.
    This is a classic pangram used for testing.
    It contains all letters of the alphabet.
    """

    print("\nText A:")
    print(text_a.strip())
    print("\nText B:")
    print(text_b.strip())
    print("\n" + "-"*70)

    # Method 1: Similarity
    result1 = compare_text(text_a, text_b, method="similarity")
    print("\nMethod: Similarity")
    print(result1.summary)

    # Method 2: Line diff
    result2 = compare_text(text_a, text_b, method="diff")
    print("\n" + "-"*70)
    print("\nMethod: Line Diff")
    print(result2.summary)

    return result1, result2


# Example 3: Quality Comparison
# ==============================

def readability_score(text: str) -> float:
    """Score text readability (0-100)"""
    if not text:
        return 0

    sentences = text.count('.') + text.count('!') + text.count('?')
    words = len(text.split())

    if sentences == 0:
        return 0

    avg_words_per_sentence = words / sentences

    # Ideal: 15-20 words per sentence
    if 15 <= avg_words_per_sentence <= 20:
        return 100
    elif avg_words_per_sentence < 15:
        return 100 - (15 - avg_words_per_sentence) * 5
    else:
        return max(0, 100 - (avg_words_per_sentence - 20) * 3)


def completeness_score(text: str) -> float:
    """Score text completeness (0-100)"""
    required_keywords = ['function', 'example', 'code', 'return']
    found = sum(1 for kw in required_keywords if kw.lower() in text.lower())
    return (found / len(required_keywords)) * 100


def length_score(text: str) -> float:
    """Score text length appropriateness (0-100)"""
    words = len(text.split())
    # Ideal: 100-200 words
    if 100 <= words <= 200:
        return 100
    elif words < 100:
        return (words / 100) * 100
    else:
        return max(0, 100 - (words - 200) * 0.5)


def example_quality_comparison():
    """Compare quality of two code descriptions"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Quality Comparison")
    print("="*70)

    description_a = """
    This function sorts a list. It takes an input and sorts it.
    Returns the sorted list.
    """

    description_b = """
    This function implements a sorting algorithm for lists of comparable items.
    It accepts a list as input and an optional reverse parameter.
    The function returns a new sorted list without modifying the original.
    Example usage: sorted_items = sort_items([3, 1, 2])
    This returns [1, 2, 3].
    The function handles empty lists and single-element lists efficiently.
    """

    print("\nDescription A:")
    print(description_a.strip())
    print("\nDescription B:")
    print(description_b.strip())
    print("\n" + "-"*70)

    metrics = [readability_score, completeness_score, length_score]

    result = compare_quality(description_a, description_b, metrics)

    print("\n" + result.summary)
    print(f"\nDetailed scores:")
    for name, score in result.details['item_a_scores'].items():
        score_b = result.details['item_b_scores'][name]
        print(f"  {name:20s}: A={score:6.1f}  B={score_b:6.1f}")

    return result


# Example 4: Real-World Scenario
# ===============================

async def database_query_v1(table, filters):
    """Simulated database query - older version"""
    await asyncio.sleep(0.05)  # Simulate query time
    return f"Results from {table} with {len(filters)} filters"


async def database_query_v2(table, filters):
    """Simulated database query - optimized version"""
    await asyncio.sleep(0.02)  # Faster query time
    return f"Results from {table} with {len(filters)} filters"


async def example_real_world_comparison():
    """Real-world scenario: comparing two API endpoint versions"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Real-World API Comparison")
    print("="*70)
    print("\nComparing database query endpoints v1 vs v2...\n")

    comparer = PerformanceComparer()

    result = await comparer.compare_endpoints(
        endpoint_a=database_query_v1,
        endpoint_b=database_query_v2,
        params_a={"table": "users", "filters": {"age": ">18", "active": True}},
        params_b={"table": "users", "filters": {"age": ">18", "active": True}},
        iterations=10,
        strategy=ComparisonStrategy.PARALLEL,
        warmup_iterations=2
    )

    print(result.summary)

    # Save results to JSON
    import json
    output_file = Path(__file__).parent / "comparison_results.json"
    with open(output_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return result


# Main
# ====

async def main():
    """Run all examples"""
    print("\n" + "Universal Comparison Tool - Examples" + "\n")

    # Example 1: Performance
    await example_performance_comparison()

    # Example 2: Text
    example_text_comparison()

    # Example 3: Quality
    example_quality_comparison()

    # Example 4: Real-world
    await example_real_world_comparison()

    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
