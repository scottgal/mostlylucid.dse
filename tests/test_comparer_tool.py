"""
Tests for the Universal Comparison Tool
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code_evolver"))

from src.comparer_tool import (
    PerformanceComparer,
    ContentComparer,
    ComparisonType,
    ComparisonStrategy,
    ComparisonResult,
    PerformanceResult,
    compare_performance,
    compare_text,
    compare_quality
)


# Test Fixtures
# =============

@pytest.fixture
def perf_comparer():
    """Performance comparer without telemetry"""
    return PerformanceComparer(telemetry_tracker=None)


@pytest.fixture
def content_comparer():
    """Content comparer without RAG"""
    return ContentComparer(rag_memory=None)


# Dummy functions for testing
# ============================

async def fast_function(value):
    """Fast test function"""
    await asyncio.sleep(0.01)
    return value * 2


async def slow_function(value):
    """Slow test function"""
    await asyncio.sleep(0.05)
    return value * 2


async def failing_function(value):
    """Function that always fails"""
    await asyncio.sleep(0.01)
    raise ValueError("Intentional failure")


def sync_function(value):
    """Synchronous test function"""
    time.sleep(0.01)
    return value + 1


# Performance Comparison Tests
# =============================

def test_performance_comparison_sequential(perf_comparer):
    """Test sequential performance comparison"""
    result = asyncio.run(perf_comparer.compare_endpoints(
        endpoint_a=fast_function,
        endpoint_b=slow_function,
        params_a={"value": 10},
        params_b={"value": 10},
        iterations=3,
        strategy=ComparisonStrategy.SEQUENTIAL,
        warmup_iterations=0
    ))

    assert result.type == ComparisonType.PERFORMANCE
    assert result.winner == "endpoint_a"
    assert result.score > 100  # A is faster
    assert "endpoint_a" in result.details
    assert "endpoint_b" in result.details


def test_performance_comparison_interleaved(perf_comparer):
    """Test interleaved performance comparison"""
    result = asyncio.run(perf_comparer.compare_endpoints(
        endpoint_a=fast_function,
        endpoint_b=slow_function,
        params_a={"value": 10},
        params_b={"value": 10},
        iterations=3,
        strategy=ComparisonStrategy.INTERLEAVED,
        warmup_iterations=1
    ))

    assert result.type == ComparisonType.PERFORMANCE
    assert result.winner == "endpoint_a"
    assert result.score > 100


def test_performance_comparison_parallel(perf_comparer):
    """Test parallel performance comparison"""
    result = asyncio.run(perf_comparer.compare_endpoints(
        endpoint_a=fast_function,
        endpoint_b=slow_function,
        params_a={"value": 10},
        params_b={"value": 10},
        iterations=3,
        strategy=ComparisonStrategy.PARALLEL,
        warmup_iterations=0
    ))

    assert result.type == ComparisonType.PERFORMANCE
    assert result.winner == "endpoint_a"


def test_performance_comparison_with_failure(perf_comparer):
    """Test performance comparison when one endpoint fails"""
    result = asyncio.run(perf_comparer.compare_endpoints(
        endpoint_a=failing_function,
        endpoint_b=fast_function,
        params_a={"value": 10},
        params_b={"value": 10},
        iterations=3,
        strategy=ComparisonStrategy.SEQUENTIAL,
        warmup_iterations=0
    ))

    assert result.type == ComparisonType.PERFORMANCE
    assert result.winner == "endpoint_b"
    assert result.score == 0  # A failed completely


def test_performance_comparison_both_fail(perf_comparer):
    """Test performance comparison when both endpoints fail"""
    result = asyncio.run(perf_comparer.compare_endpoints(
        endpoint_a=failing_function,
        endpoint_b=failing_function,
        params_a={"value": 10},
        params_b={"value": 10},
        iterations=3,
        strategy=ComparisonStrategy.SEQUENTIAL,
        warmup_iterations=0
    ))

    assert result.type == ComparisonType.PERFORMANCE
    assert result.winner is None
    assert result.score == 0


def test_performance_comparison_identical(perf_comparer):
    """Test performance comparison with identical functions"""
    result = asyncio.run(perf_comparer.compare_endpoints(
        endpoint_a=fast_function,
        endpoint_b=fast_function,
        params_a={"value": 10},
        params_b={"value": 10},
        iterations=5,
        strategy=ComparisonStrategy.INTERLEAVED,
        warmup_iterations=1
    ))

    assert result.type == ComparisonType.PERFORMANCE
    # Score should be around 100 (within 5% tolerance = tie)
    assert 90 <= result.score <= 110
    # Could be tie or could have slight winner due to variance


# Content Comparison Tests
# =========================

def test_text_similarity_identical(content_comparer):
    """Test text comparison with identical strings"""
    text = "The quick brown fox jumps over the lazy dog"

    result = content_comparer.compare_text(text, text, method="similarity")

    assert result.type == ComparisonType.CONTENT
    assert result.score == 100.0
    assert result.details["similarity_ratio"] == 1.0


def test_text_similarity_different(content_comparer):
    """Test text comparison with different strings"""
    text_a = "Hello world"
    text_b = "Goodbye universe"

    result = content_comparer.compare_text(text_a, text_b, method="similarity")

    assert result.type == ComparisonType.CONTENT
    assert result.score < 50  # Very different


def test_text_similarity_partial(content_comparer):
    """Test text comparison with partially similar strings"""
    text_a = "The quick brown fox jumps over the lazy dog"
    text_b = "The quick brown fox leaps over the sleepy dog"

    result = content_comparer.compare_text(text_a, text_b, method="similarity")

    assert result.type == ComparisonType.CONTENT
    assert 70 <= result.score <= 95  # Mostly similar


def test_text_diff(content_comparer):
    """Test line-by-line diff comparison"""
    text_a = "line 1\nline 2\nline 3"
    text_b = "line 1\nline 2 modified\nline 3\nline 4"

    result = content_comparer.compare_text(text_a, text_b, method="diff")

    assert result.type == ComparisonType.CONTENT
    assert result.details["added_lines"] > 0
    assert result.details["removed_lines"] > 0
    assert result.details["unchanged_lines"] == 2


def test_text_semantic_without_rag(content_comparer):
    """Test semantic comparison falls back without RAG"""
    text_a = "The cat sat on the mat"
    text_b = "The feline rested on the rug"

    # Should fall back to similarity comparison
    result = content_comparer.compare_text(text_a, text_b, method="semantic")

    assert result.type in [ComparisonType.CONTENT, ComparisonType.SEMANTIC]


# Quality Comparison Tests
# =========================

def simple_metric(item: str) -> float:
    """Simple quality metric - count words"""
    return len(item.split()) * 10


def length_metric(item: str) -> float:
    """Quality metric based on length"""
    return min(len(item), 100)


def test_quality_comparison(content_comparer):
    """Test quality comparison with custom metrics"""
    item_a = "short"
    item_b = "this is a much longer string with many words"

    result = content_comparer.compare_quality(
        item_a,
        item_b,
        quality_metrics=[simple_metric, length_metric]
    )

    assert result.type == ComparisonType.QUALITY
    assert result.winner == "item_b"  # B has higher quality
    assert "item_a_scores" in result.details
    assert "item_b_scores" in result.details


def test_quality_comparison_tie(content_comparer):
    """Test quality comparison with similar items"""
    item_a = "hello world"
    item_b = "hello earth"

    result = content_comparer.compare_quality(
        item_a,
        item_b,
        quality_metrics=[simple_metric, length_metric]
    )

    assert result.type == ComparisonType.QUALITY
    # Scores should be very close
    assert 90 <= result.score <= 110


def test_quality_comparison_no_metrics(content_comparer):
    """Test quality comparison with no valid metrics"""
    def failing_metric(item):
        raise ValueError("Metric failed")

    result = content_comparer.compare_quality(
        "test",
        "test",
        quality_metrics=[failing_metric]
    )

    assert result.type == ComparisonType.QUALITY
    assert result.score == 0
    assert "error" in result.details


# Convenience Function Tests
# ===========================

def test_compare_performance_convenience():
    """Test compare_performance convenience function"""
    result = compare_performance(
        func_a=sync_function,
        func_b=sync_function,
        params_a={"value": 5},
        params_b={"value": 5},
        iterations=3,
        strategy="sequential"
    )

    assert isinstance(result, ComparisonResult)
    assert result.type == ComparisonType.PERFORMANCE


def test_compare_text_convenience():
    """Test compare_text convenience function"""
    result = compare_text("hello", "hello world", method="similarity")

    assert isinstance(result, ComparisonResult)
    assert result.type == ComparisonType.CONTENT


def test_compare_quality_convenience():
    """Test compare_quality convenience function"""
    result = compare_quality(
        "short",
        "longer text here",
        metrics=[simple_metric]
    )

    assert isinstance(result, ComparisonResult)
    assert result.type == ComparisonType.QUALITY


# Result Serialization Tests
# ===========================

def test_comparison_result_to_dict(content_comparer):
    """Test ComparisonResult serialization to dict"""
    result = content_comparer.compare_text("test", "test", method="similarity")

    result_dict = result.to_dict()

    assert "type" in result_dict
    assert "item_a" in result_dict
    assert "item_b" in result_dict
    assert "score" in result_dict
    assert "winner" in result_dict
    assert "details" in result_dict
    assert "summary" in result_dict
    assert "timestamp" in result_dict


# Edge Cases
# ===========

def test_text_comparison_empty_strings(content_comparer):
    """Test text comparison with empty strings"""
    result = content_comparer.compare_text("", "", method="similarity")

    assert result.type == ComparisonType.CONTENT
    assert result.score == 100.0  # Empty strings are identical


def test_text_comparison_invalid_method(content_comparer):
    """Test text comparison with invalid method"""
    with pytest.raises(ValueError):
        content_comparer.compare_text("test", "test", method="invalid_method")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
