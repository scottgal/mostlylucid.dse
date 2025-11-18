"""
Universal Comparison Tool

Supports multiple comparison strategies:
1. Performance Comparison - Compare tool/endpoint performance
2. Content Comparison - Compare text, quality, outputs
3. Statistical Comparison - Compare distributions, metrics
4. Semantic Comparison - Compare meaning, intent

Integrates with:
- telemetry_tracker.py for performance data
- drift_detector.py for baseline comparisons
- pattern_clusterer.py for semantic similarity
"""

import time
import asyncio
import statistics
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import difflib
import numpy as np
from pathlib import Path
import json
import logging


class ComparisonType(Enum):
    """Types of comparisons supported"""
    PERFORMANCE = "performance"
    CONTENT = "content"
    QUALITY = "quality"
    SEMANTIC = "semantic"
    STATISTICAL = "statistical"


class ComparisonStrategy(Enum):
    """Performance testing strategies"""
    SEQUENTIAL = "sequential"  # Run A then B
    INTERLEAVED = "interleaved"  # Alternate A and B
    PARALLEL = "parallel"  # Run A and B simultaneously
    WARMUP = "warmup"  # Warm up before measuring
    SUSTAINED = "sustained"  # Sustained load testing


@dataclass
class PerformanceResult:
    """Performance measurement result"""
    name: str
    duration_ms: float
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Result of a comparison operation"""
    type: ComparisonType
    item_a_name: str
    item_b_name: str
    score: float  # 0-100+ scale (0=dead stop, 100=identical, >100=faster)
    winner: Optional[str]  # Which item "won"
    details: Dict[str, Any]
    summary: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "item_a": self.item_a_name,
            "item_b": self.item_b_name,
            "score": self.score,
            "winner": self.winner,
            "details": self.details,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat()
        }


class PerformanceComparer:
    """
    Performance comparison with telemetry integration.

    Strategies:
    - Sequential: Run A, then B (prevents interference)
    - Interleaved: Run A, B, A, B... (accounts for warmup)
    - Parallel: Run A and B together (tests under load)
    - Warmup: Run several iterations before measuring
    - Sustained: Long-duration load testing
    """

    def __init__(self, telemetry_tracker=None):
        self.telemetry = telemetry_tracker
        if self.telemetry is None:
            try:
                from telemetry_tracker import get_tracker
                self.telemetry = get_tracker()
            except:
                logging.warning("Telemetry tracker not available")

    async def compare_endpoints(
        self,
        endpoint_a: Callable,
        endpoint_b: Callable,
        params_a: Dict[str, Any],
        params_b: Dict[str, Any],
        iterations: int = 10,
        strategy: ComparisonStrategy = ComparisonStrategy.INTERLEAVED,
        warmup_iterations: int = 2
    ) -> ComparisonResult:
        """
        Compare two endpoints/tools for performance.

        Args:
            endpoint_a: First function/endpoint to test
            endpoint_b: Second function/endpoint to test
            params_a: Parameters for endpoint A
            params_b: Parameters for endpoint B
            iterations: Number of test iterations
            strategy: Testing strategy to use
            warmup_iterations: Warm-up runs before measurement

        Returns:
            ComparisonResult with performance analysis
        """
        results_a = []
        results_b = []

        # Warmup phase
        if warmup_iterations > 0:
            logging.info(f"Warming up ({warmup_iterations} iterations)...")
            for _ in range(warmup_iterations):
                try:
                    await self._execute_with_telemetry(endpoint_a, params_a, "warmup_a")
                    await self._execute_with_telemetry(endpoint_b, params_b, "warmup_b")
                except:
                    pass  # Ignore warmup errors

        # Main testing phase
        logging.info(f"Running {iterations} iterations with {strategy.value} strategy...")

        if strategy == ComparisonStrategy.SEQUENTIAL:
            # Run all A, then all B
            for i in range(iterations):
                result_a = await self._measure_performance(
                    endpoint_a, params_a, f"endpoint_a_iter_{i}"
                )
                results_a.append(result_a)

            for i in range(iterations):
                result_b = await self._measure_performance(
                    endpoint_b, params_b, f"endpoint_b_iter_{i}"
                )
                results_b.append(result_b)

        elif strategy == ComparisonStrategy.INTERLEAVED:
            # Alternate A and B
            for i in range(iterations):
                result_a = await self._measure_performance(
                    endpoint_a, params_a, f"endpoint_a_iter_{i}"
                )
                results_a.append(result_a)

                result_b = await self._measure_performance(
                    endpoint_b, params_b, f"endpoint_b_iter_{i}"
                )
                results_b.append(result_b)

        elif strategy == ComparisonStrategy.PARALLEL:
            # Run A and B simultaneously
            for i in range(iterations):
                result_a, result_b = await asyncio.gather(
                    self._measure_performance(endpoint_a, params_a, f"endpoint_a_iter_{i}"),
                    self._measure_performance(endpoint_b, params_b, f"endpoint_b_iter_{i}")
                )
                results_a.append(result_a)
                results_b.append(result_b)

        # Analyze results
        return self._analyze_performance_results(results_a, results_b)

    async def _measure_performance(
        self,
        func: Callable,
        params: Dict[str, Any],
        name: str
    ) -> PerformanceResult:
        """Measure performance of a single execution"""
        import psutil
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()
        process = psutil.Process()
        cpu_before = process.cpu_percent()

        start_time = time.perf_counter()
        error = None

        try:
            # Execute with telemetry if available
            if self.telemetry:
                with self.telemetry.track_tool_call(name, params):
                    if asyncio.iscoroutinefunction(func):
                        await func(**params)
                    else:
                        func(**params)
            else:
                if asyncio.iscoroutinefunction(func):
                    await func(**params)
                else:
                    func(**params)

        except Exception as e:
            error = str(e)
            logging.error(f"Error in {name}: {e}")

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_mb = peak / 1024 / 1024

        # Get CPU usage
        cpu_after = process.cpu_percent()
        cpu_percent = cpu_after - cpu_before

        return PerformanceResult(
            name=name,
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            error=error
        )

    async def _execute_with_telemetry(self, func: Callable, params: Dict, name: str):
        """Execute function with telemetry tracking"""
        if self.telemetry:
            with self.telemetry.track_tool_call(name, params):
                if asyncio.iscoroutinefunction(func):
                    return await func(**params)
                else:
                    return func(**params)
        else:
            if asyncio.iscoroutinefunction(func):
                return await func(**params)
            else:
                return func(**params)

    def _analyze_performance_results(
        self,
        results_a: List[PerformanceResult],
        results_b: List[PerformanceResult]
    ) -> ComparisonResult:
        """
        Analyze performance results and compute comparison score.

        Score scale:
        - 0: Endpoint A completely failed (dead stop)
        - 50: A is 2x slower than B
        - 100: A and B are identical
        - 200: A is 2x faster than B
        - 300: A is 3x faster than B
        """
        # Filter out errors
        valid_a = [r for r in results_a if r.error is None]
        valid_b = [r for r in results_b if r.error is None]

        if not valid_a and not valid_b:
            return ComparisonResult(
                type=ComparisonType.PERFORMANCE,
                item_a_name="endpoint_a",
                item_b_name="endpoint_b",
                score=0,
                winner=None,
                details={"error": "Both endpoints failed"},
                summary="Both endpoints failed completely"
            )

        if not valid_a:
            return ComparisonResult(
                type=ComparisonType.PERFORMANCE,
                item_a_name="endpoint_a",
                item_b_name="endpoint_b",
                score=0,
                winner="endpoint_b",
                details={"error": "Endpoint A failed completely"},
                summary="Endpoint A failed completely. Endpoint B wins by default."
            )

        if not valid_b:
            return ComparisonResult(
                type=ComparisonType.PERFORMANCE,
                item_a_name="endpoint_a",
                item_b_name="endpoint_b",
                score=float('inf'),
                winner="endpoint_a",
                details={"error": "Endpoint B failed completely"},
                summary="Endpoint B failed completely. Endpoint A wins by default."
            )

        # Calculate statistics
        durations_a = [r.duration_ms for r in valid_a]
        durations_b = [r.duration_ms for r in valid_b]

        mean_a = statistics.mean(durations_a)
        mean_b = statistics.mean(durations_b)
        median_a = statistics.median(durations_a)
        median_b = statistics.median(durations_b)
        stdev_a = statistics.stdev(durations_a) if len(durations_a) > 1 else 0
        stdev_b = statistics.stdev(durations_b) if len(durations_b) > 1 else 0

        # Calculate relative performance score
        # Score = 100 * (B / A)
        # If A is faster: score > 100
        # If B is faster: score < 100
        # If identical: score = 100
        if mean_a > 0:
            score = 100 * (mean_b / mean_a)
        else:
            score = float('inf')

        # Determine winner
        if abs(score - 100) < 5:  # Within 5% is considered tie
            winner = None
            winner_text = "Tie (performance within 5%)"
        elif score > 100:
            winner = "endpoint_a"
            speedup = score / 100
            winner_text = f"Endpoint A is {speedup:.2f}x faster"
        else:
            winner = "endpoint_b"
            speedup = 100 / score
            winner_text = f"Endpoint B is {speedup:.2f}x faster"

        # Build detailed analysis
        details = {
            "endpoint_a": {
                "mean_ms": mean_a,
                "median_ms": median_a,
                "stdev_ms": stdev_a,
                "min_ms": min(durations_a),
                "max_ms": max(durations_a),
                "samples": len(valid_a),
                "errors": len(results_a) - len(valid_a)
            },
            "endpoint_b": {
                "mean_ms": mean_b,
                "median_ms": median_b,
                "stdev_ms": stdev_b,
                "min_ms": min(durations_b),
                "max_ms": max(durations_b),
                "samples": len(valid_b),
                "errors": len(results_b) - len(valid_b)
            },
            "relative_performance": {
                "score": score,
                "speedup_ratio": score / 100 if score >= 100 else 100 / score,
                "faster_endpoint": winner
            }
        }

        summary = f"""Performance Comparison Results:

{winner_text}

Endpoint A: {mean_a:.2f}ms avg ({median_a:.2f}ms median, ±{stdev_a:.2f}ms)
Endpoint B: {mean_b:.2f}ms avg ({median_b:.2f}ms median, ±{stdev_b:.2f}ms)

Relative Performance Score: {score:.1f}/100
(0=dead stop, 100=identical, >100=A faster, <100=B faster)
"""

        return ComparisonResult(
            type=ComparisonType.PERFORMANCE,
            item_a_name="endpoint_a",
            item_b_name="endpoint_b",
            score=score,
            winner=winner,
            details=details,
            summary=summary.strip()
        )


class ContentComparer:
    """
    Compare content (text, outputs, quality).

    Supports:
    - Text diff (character, word, line level)
    - Quality scoring
    - Semantic similarity
    """

    def __init__(self, rag_memory=None):
        self.rag = rag_memory

    def compare_text(
        self,
        text_a: str,
        text_b: str,
        method: str = "similarity"
    ) -> ComparisonResult:
        """
        Compare two text strings.

        Methods:
        - similarity: Overall similarity score
        - diff: Detailed diff analysis
        - semantic: Semantic similarity (requires RAG)
        """
        if method == "similarity":
            return self._compare_similarity(text_a, text_b)
        elif method == "diff":
            return self._compare_diff(text_a, text_b)
        elif method == "semantic":
            return self._compare_semantic(text_a, text_b)
        else:
            raise ValueError(f"Unknown comparison method: {method}")

    def _compare_similarity(self, text_a: str, text_b: str) -> ComparisonResult:
        """Compare using sequence matcher"""
        matcher = difflib.SequenceMatcher(None, text_a, text_b)
        ratio = matcher.ratio()
        score = ratio * 100  # Convert to 0-100 scale

        # Find matching blocks
        matching_blocks = matcher.get_matching_blocks()
        total_match_len = sum(block.size for block in matching_blocks)

        # Calculate differences
        opcodes = matcher.get_opcodes()
        differences = []
        for tag, i1, i2, j1, j2 in opcodes:
            if tag != 'equal':
                differences.append({
                    "type": tag,
                    "text_a": text_a[i1:i2],
                    "text_b": text_b[j1:j2]
                })

        winner = None
        if score >= 95:
            winner_text = "Nearly identical"
        elif score >= 80:
            winner_text = "Very similar"
        elif score >= 60:
            winner_text = "Moderately similar"
        elif score >= 40:
            winner_text = "Somewhat different"
        else:
            winner_text = "Very different"

        details = {
            "similarity_ratio": ratio,
            "matching_chars": total_match_len,
            "total_chars_a": len(text_a),
            "total_chars_b": len(text_b),
            "num_differences": len(differences),
            "differences": differences[:10]  # Limit to first 10
        }

        summary = f"""Text Similarity: {score:.1f}%

{winner_text}

Text A: {len(text_a)} characters
Text B: {len(text_b)} characters
Matching: {total_match_len} characters
Differences: {len(differences)} changes
"""

        return ComparisonResult(
            type=ComparisonType.CONTENT,
            item_a_name="text_a",
            item_b_name="text_b",
            score=score,
            winner=winner,
            details=details,
            summary=summary.strip()
        )

    def _compare_diff(self, text_a: str, text_b: str) -> ComparisonResult:
        """Generate detailed diff"""
        differ = difflib.Differ()
        diff = list(differ.compare(text_a.splitlines(), text_b.splitlines()))

        added = sum(1 for line in diff if line.startswith('+ '))
        removed = sum(1 for line in diff if line.startswith('- '))
        unchanged = sum(1 for line in diff if line.startswith('  '))

        total_lines = max(len(text_a.splitlines()), len(text_b.splitlines()))
        if total_lines > 0:
            score = (unchanged / total_lines) * 100
        else:
            score = 100

        details = {
            "added_lines": added,
            "removed_lines": removed,
            "unchanged_lines": unchanged,
            "total_changes": added + removed,
            "diff_preview": diff[:20]  # First 20 lines
        }

        summary = f"""Line-by-Line Diff Analysis:

Unchanged: {unchanged} lines
Added: {added} lines
Removed: {removed} lines
Total Changes: {added + removed} lines

Similarity Score: {score:.1f}%
"""

        return ComparisonResult(
            type=ComparisonType.CONTENT,
            item_a_name="text_a",
            item_b_name="text_b",
            score=score,
            winner=None,
            details=details,
            summary=summary.strip()
        )

    def _compare_semantic(self, text_a: str, text_b: str) -> ComparisonResult:
        """Compare semantic similarity using embeddings"""
        if not self.rag:
            return self._compare_similarity(text_a, text_b)

        try:
            # Get embeddings
            embedding_a = self.rag.embed_text(text_a)
            embedding_b = self.rag.embed_text(text_b)

            # Calculate cosine similarity
            dot_product = np.dot(embedding_a, embedding_b)
            norm_a = np.linalg.norm(embedding_a)
            norm_b = np.linalg.norm(embedding_b)

            if norm_a > 0 and norm_b > 0:
                cosine_sim = dot_product / (norm_a * norm_b)
                score = (cosine_sim + 1) * 50  # Convert -1,1 to 0,100
            else:
                score = 0

            winner = None
            if score >= 90:
                winner_text = "Semantically identical"
            elif score >= 70:
                winner_text = "Semantically similar"
            elif score >= 50:
                winner_text = "Somewhat related"
            else:
                winner_text = "Semantically different"

            details = {
                "cosine_similarity": float(cosine_sim),
                "embedding_dim": len(embedding_a)
            }

            summary = f"""Semantic Similarity: {score:.1f}%

{winner_text}

Cosine Similarity: {cosine_sim:.3f}
"""

            return ComparisonResult(
                type=ComparisonType.SEMANTIC,
                item_a_name="text_a",
                item_b_name="text_b",
                score=score,
                winner=winner,
                details=details,
                summary=summary.strip()
            )

        except Exception as e:
            logging.error(f"Semantic comparison failed: {e}")
            return self._compare_similarity(text_a, text_b)

    def compare_quality(
        self,
        item_a: Any,
        item_b: Any,
        quality_metrics: List[Callable[[Any], float]]
    ) -> ComparisonResult:
        """
        Compare quality using custom metrics.

        Args:
            item_a: First item to compare
            item_b: Second item to compare
            quality_metrics: List of functions that score quality (0-100)

        Returns:
            ComparisonResult with quality analysis
        """
        scores_a = []
        scores_b = []
        metric_names = []

        for metric in quality_metrics:
            try:
                score_a = metric(item_a)
                score_b = metric(item_b)
                scores_a.append(score_a)
                scores_b.append(score_b)
                metric_names.append(metric.__name__)
            except Exception as e:
                logging.error(f"Quality metric {metric.__name__} failed: {e}")

        if not scores_a:
            return ComparisonResult(
                type=ComparisonType.QUALITY,
                item_a_name="item_a",
                item_b_name="item_b",
                score=0,
                winner=None,
                details={"error": "No valid quality metrics"},
                summary="Quality comparison failed - no valid metrics"
            )

        mean_a = statistics.mean(scores_a)
        mean_b = statistics.mean(scores_b)

        # Calculate relative quality score (similar to performance)
        if mean_a > 0:
            score = 100 * (mean_a / mean_b) if mean_b > 0 else float('inf')
        else:
            score = 0

        if score > 105:
            winner = "item_a"
            winner_text = f"Item A has higher quality ({mean_a:.1f} vs {mean_b:.1f})"
        elif score < 95:
            winner = "item_b"
            winner_text = f"Item B has higher quality ({mean_b:.1f} vs {mean_a:.1f})"
        else:
            winner = None
            winner_text = "Similar quality"

        details = {
            "item_a_scores": {name: score for name, score in zip(metric_names, scores_a)},
            "item_b_scores": {name: score for name, score in zip(metric_names, scores_b)},
            "mean_quality_a": mean_a,
            "mean_quality_b": mean_b
        }

        summary = f"""Quality Comparison:

{winner_text}

Item A: {mean_a:.1f} avg quality
Item B: {mean_b:.1f} avg quality

Relative Score: {score:.1f}/100
"""

        return ComparisonResult(
            type=ComparisonType.QUALITY,
            item_a_name="item_a",
            item_b_name="item_b",
            score=score,
            winner=winner,
            details=details,
            summary=summary.strip()
        )


# Convenience functions
def compare_performance(
    func_a: Callable,
    func_b: Callable,
    params_a: Dict,
    params_b: Dict,
    iterations: int = 10,
    strategy: str = "interleaved"
) -> ComparisonResult:
    """
    Compare performance of two functions.

    Returns:
        ComparisonResult with score on 0-inf scale:
        - 0: A failed completely
        - 100: A and B identical
        - 200: A is 2x faster
        - 50: B is 2x faster
    """
    comparer = PerformanceComparer()
    strategy_enum = ComparisonStrategy[strategy.upper()]

    return asyncio.run(
        comparer.compare_endpoints(func_a, func_b, params_a, params_b, iterations, strategy_enum)
    )


def compare_text(text_a: str, text_b: str, method: str = "similarity") -> ComparisonResult:
    """Compare two text strings"""
    comparer = ContentComparer()
    return comparer.compare_text(text_a, text_b, method)


def compare_quality(item_a: Any, item_b: Any, metrics: List[Callable]) -> ComparisonResult:
    """Compare quality using custom metrics"""
    comparer = ContentComparer()
    return comparer.compare_quality(item_a, item_b, metrics)
