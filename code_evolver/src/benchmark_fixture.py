"""
Benchmark Fixture Tool

Provides a standardized way to fire test data at code chunks and measure
their performance consistently across all tools.

Features:
- Predefined test datasets for different data types
- Configurable benchmark scenarios
- Automatic performance measurement
- Comparison across implementations
- Integration with PerformanceCollector and Auditor
"""

import time
import random
import string
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from performance_collector import PerformanceCollector


@dataclass
class BenchmarkScenario:
    """Defines a benchmark test scenario"""
    name: str
    description: str
    input_data: List[Any]
    expected_behavior: str  # Description of expected behavior
    iterations: int = 10


@dataclass
class BenchmarkResult:
    """Results from benchmarking a single implementation"""
    scenario_name: str
    implementation_name: str
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p95_duration_ms: float
    avg_memory_mb: float
    peak_memory_mb: float
    success_count: int
    error_count: int
    success_rate: float
    errors: List[str]


class BenchmarkFixture:
    """
    Benchmark fixture for consistent performance testing across tools.

    Usage:
        fixture = BenchmarkFixture(session_id="bench_run_1")

        # Define scenarios
        scenarios = fixture.create_standard_scenarios("text_processing")

        # Benchmark implementations
        results = fixture.benchmark(
            implementations={
                "v1": original_function,
                "v2": optimized_function
            },
            scenarios=scenarios,
            layer="tool"
        )

        # Generate comparison report
        report = fixture.generate_comparison_report(results)
    """

    def __init__(
        self,
        session_id: str,
        base_path: str = "debug_data",
        enable_profiling: bool = True
    ):
        """
        Initialize benchmark fixture.

        Args:
            session_id: Unique benchmark session ID
            base_path: Base path for storing results
            enable_profiling: Enable detailed performance profiling
        """
        self.session_id = session_id
        self.base_path = Path(base_path)

        if enable_profiling:
            self.collector = PerformanceCollector(
                session_id=session_id,
                base_path=str(self.base_path),
                enable_io_tracking=True,
                enable_memory_profiling=True
            )
        else:
            self.collector = None

        # Standard datasets
        self._datasets = self._init_standard_datasets()

    @staticmethod
    def _init_standard_datasets() -> Dict[str, List[Any]]:
        """Initialize standard test datasets"""
        return {
            # Text data
            "short_texts": [
                "hello",
                "world",
                "test",
                "data",
                "benchmark"
            ],
            "medium_texts": [
                "This is a medium length text for testing.",
                "Another sample text with more words.",
                "Benchmark fixture text processing test.",
            ],
            "long_texts": [
                " ".join(["Lorem ipsum"] * 100),
                " ".join(["Test data"] * 150),
                " ".join(["Performance benchmark"] * 200),
            ],

            # Numeric data
            "small_numbers": list(range(10)),
            "medium_numbers": list(range(1000)),
            "large_numbers": list(range(100000)),

            # Lists
            "small_lists": [list(range(i)) for i in range(1, 11)],
            "medium_lists": [list(range(i)) for i in range(10, 110, 10)],
            "large_lists": [list(range(i)) for i in range(100, 1100, 100)],

            # Dicts
            "small_dicts": [{"key": i, "value": i * 2} for i in range(10)],
            "medium_dicts": [
                {f"key_{j}": j * i for j in range(10)}
                for i in range(10)
            ],

            # Mixed data
            "mixed_data": [
                42,
                "string",
                [1, 2, 3],
                {"a": 1, "b": 2},
                None,
                True,
                3.14
            ],

            # Edge cases
            "edge_cases": [
                "",  # Empty string
                [],  # Empty list
                {},  # Empty dict
                None,  # None
                0,  # Zero
                -1,  # Negative
            ]
        }

    def create_standard_scenarios(
        self,
        category: str,
        iterations: int = 10
    ) -> List[BenchmarkScenario]:
        """
        Create standard benchmark scenarios for a category.

        Args:
            category: Category of scenarios (e.g., 'text_processing', 'data_transformation')
            iterations: Number of iterations per scenario

        Returns:
            List of benchmark scenarios
        """
        scenarios = []

        if category == "text_processing":
            scenarios = [
                BenchmarkScenario(
                    name="short_text_processing",
                    description="Process short text strings",
                    input_data=self._datasets["short_texts"],
                    expected_behavior="Transform short strings efficiently",
                    iterations=iterations
                ),
                BenchmarkScenario(
                    name="medium_text_processing",
                    description="Process medium length text",
                    input_data=self._datasets["medium_texts"],
                    expected_behavior="Handle moderate text size",
                    iterations=iterations
                ),
                BenchmarkScenario(
                    name="long_text_processing",
                    description="Process long text documents",
                    input_data=self._datasets["long_texts"],
                    expected_behavior="Efficiently process large texts",
                    iterations=iterations
                )
            ]

        elif category == "numeric_computation":
            scenarios = [
                BenchmarkScenario(
                    name="small_number_computation",
                    description="Compute on small numbers",
                    input_data=self._datasets["small_numbers"],
                    expected_behavior="Fast numeric operations",
                    iterations=iterations
                ),
                BenchmarkScenario(
                    name="medium_number_computation",
                    description="Compute on medium range numbers",
                    input_data=self._datasets["medium_numbers"],
                    expected_behavior="Efficient bulk numeric operations",
                    iterations=iterations
                ),
                BenchmarkScenario(
                    name="large_number_computation",
                    description="Compute on large numbers",
                    input_data=self._datasets["large_numbers"],
                    expected_behavior="Scalable numeric processing",
                    iterations=iterations
                )
            ]

        elif category == "list_operations":
            scenarios = [
                BenchmarkScenario(
                    name="small_list_operations",
                    description="Operations on small lists",
                    input_data=self._datasets["small_lists"],
                    expected_behavior="Fast list processing",
                    iterations=iterations
                ),
                BenchmarkScenario(
                    name="medium_list_operations",
                    description="Operations on medium lists",
                    input_data=self._datasets["medium_lists"],
                    expected_behavior="Efficient medium list handling",
                    iterations=iterations
                ),
                BenchmarkScenario(
                    name="large_list_operations",
                    description="Operations on large lists",
                    input_data=self._datasets["large_lists"],
                    expected_behavior="Scalable list processing",
                    iterations=iterations
                )
            ]

        elif category == "edge_cases":
            scenarios = [
                BenchmarkScenario(
                    name="edge_case_handling",
                    description="Handle edge cases gracefully",
                    input_data=self._datasets["edge_cases"],
                    expected_behavior="Robust edge case handling",
                    iterations=iterations
                )
            ]

        elif category == "mixed":
            scenarios = [
                BenchmarkScenario(
                    name="mixed_data_handling",
                    description="Handle mixed data types",
                    input_data=self._datasets["mixed_data"],
                    expected_behavior="Type-agnostic processing",
                    iterations=iterations
                )
            ]

        return scenarios

    def benchmark(
        self,
        implementations: Dict[str, Callable],
        scenarios: List[BenchmarkScenario],
        layer: str = "tool"
    ) -> Dict[str, List[BenchmarkResult]]:
        """
        Benchmark multiple implementations across scenarios.

        Args:
            implementations: Dict of implementation_name -> function
            scenarios: List of benchmark scenarios to run
            layer: Layer type for tracking ("tool", "function", etc.)

        Returns:
            Dict mapping scenario_name -> list of BenchmarkResults
        """
        results = {}

        print(f"\n🏁 Starting benchmark: {len(implementations)} implementations, {len(scenarios)} scenarios")

        for scenario in scenarios:
            print(f"\n📊 Scenario: {scenario.name}")
            scenario_results = []

            for impl_name, impl_func in implementations.items():
                print(f"   Testing {impl_name}...")

                # Benchmark this implementation
                result = self._benchmark_implementation(
                    impl_func,
                    impl_name,
                    scenario,
                    layer
                )

                scenario_results.append(result)

                # Print quick summary
                status = "✅" if result.success_rate >= 0.95 else "❌"
                print(f"      {status} {result.avg_duration_ms:.2f}ms avg, {result.success_rate:.1%} success")

            results[scenario.name] = scenario_results

        return results

    def _benchmark_implementation(
        self,
        func: Callable,
        impl_name: str,
        scenario: BenchmarkScenario,
        layer: str
    ) -> BenchmarkResult:
        """Benchmark a single implementation on a scenario"""

        durations = []
        memories = []
        errors = []
        success_count = 0
        error_count = 0

        # Wrap with tracking if collector available
        if self.collector:
            tracked_func = self.collector.instrument(
                layer=layer,
                tool_name=f"{impl_name}_{scenario.name}",
                capture_args=True,
                capture_result=True
            )(func)
        else:
            tracked_func = func

        # Run benchmark iterations
        for iteration in range(scenario.iterations):
            for input_data in scenario.input_data:
                start_time = time.time()

                try:
                    # Execute function
                    _ = tracked_func(input_data)
                    success_count += 1

                    # Record duration
                    duration_ms = (time.time() - start_time) * 1000
                    durations.append(duration_ms)

                except Exception as e:
                    error_count += 1
                    errors.append(str(e))
                    durations.append(0)  # Failed execution

        # Calculate statistics
        valid_durations = [d for d in durations if d > 0]

        if valid_durations:
            avg_duration = sum(valid_durations) / len(valid_durations)
            min_duration = min(valid_durations)
            max_duration = max(valid_durations)

            # P95
            sorted_durations = sorted(valid_durations)
            p95_idx = int(len(sorted_durations) * 0.95)
            p95_duration = sorted_durations[p95_idx] if sorted_durations else 0
        else:
            avg_duration = min_duration = max_duration = p95_duration = 0

        # Get memory stats from collector if available
        avg_memory = 0
        peak_memory = 0

        if self.collector:
            self.collector.store.sync_to_duckdb()

            memory_stats = self.collector.store.query_analytics("""
                SELECT AVG(memory_mb), MAX(memory_mb)
                FROM records
                WHERE context_id = ?
            """, [f"{impl_name}_{scenario.name}"]).fetchone()

            if memory_stats:
                avg_memory = float(memory_stats[0] or 0)
                peak_memory = float(memory_stats[1] or 0)

        # Calculate success rate
        total_executions = success_count + error_count
        success_rate = success_count / total_executions if total_executions > 0 else 0.0

        return BenchmarkResult(
            scenario_name=scenario.name,
            implementation_name=impl_name,
            avg_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            p95_duration_ms=p95_duration,
            avg_memory_mb=avg_memory,
            peak_memory_mb=peak_memory,
            success_count=success_count,
            error_count=error_count,
            success_rate=success_rate,
            errors=list(set(errors))[:5]  # Unique errors, max 5
        )

    def generate_comparison_report(
        self,
        results: Dict[str, List[BenchmarkResult]],
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate comparison report for benchmark results.

        Args:
            results: Results from benchmark()
            output_path: Optional file path to save report

        Returns:
            Markdown-formatted comparison report
        """
        sections = []

        # Header
        sections.append("# Benchmark Comparison Report")
        sections.append(f"\n**Session:** {self.session_id}\n")

        # Executive summary
        total_scenarios = len(results)
        total_implementations = len(next(iter(results.values()))) if results else 0

        sections.append("## Executive Summary\n")
        sections.append(f"- **Scenarios:** {total_scenarios}")
        sections.append(f"- **Implementations:** {total_implementations}\n")

        # Per-scenario comparison
        sections.append("## Scenario Comparisons\n")

        for scenario_name, scenario_results in results.items():
            sections.append(f"### {scenario_name}\n")

            # Sort by performance
            sorted_results = sorted(scenario_results, key=lambda r: r.avg_duration_ms)

            # Table
            sections.append("| Implementation | Avg Duration | Min | Max | P95 | Memory | Success Rate |")
            sections.append("|---------------|--------------|-----|-----|-----|--------|--------------|")

            for result in sorted_results:
                sections.append(
                    f"| {result.implementation_name} | "
                    f"{result.avg_duration_ms:.2f}ms | "
                    f"{result.min_duration_ms:.2f}ms | "
                    f"{result.max_duration_ms:.2f}ms | "
                    f"{result.p95_duration_ms:.2f}ms | "
                    f"{result.avg_memory_mb:.2f}MB | "
                    f"{result.success_rate:.1%} |"
                )

            # Winner
            if sorted_results:
                winner = sorted_results[0]
                sections.append(f"\n**Winner:** {winner.implementation_name} ")
                sections.append(f"({winner.avg_duration_ms:.2f}ms avg)\n")

                # Speedup comparison
                if len(sorted_results) > 1:
                    sections.append("**Speedup vs others:**")
                    for other in sorted_results[1:]:
                        speedup = (other.avg_duration_ms / winner.avg_duration_ms - 1) * 100
                        sections.append(f"- {speedup:.1f}% faster than {other.implementation_name}")
                    sections.append("\n")

        # Overall winner
        sections.append("## Overall Performance\n")

        # Calculate average performance across scenarios
        impl_avg_perf = {}
        for scenario_results in results.values():
            for result in scenario_results:
                if result.implementation_name not in impl_avg_perf:
                    impl_avg_perf[result.implementation_name] = []
                impl_avg_perf[result.implementation_name].append(result.avg_duration_ms)

        overall_winners = sorted(
            impl_avg_perf.items(),
            key=lambda x: sum(x[1]) / len(x[1])
        )

        sections.append("| Implementation | Avg Duration (all scenarios) |")
        sections.append("|---------------|---------------------------|")

        for impl_name, durations in overall_winners:
            avg = sum(durations) / len(durations)
            sections.append(f"| {impl_name} | {avg:.2f}ms |")

        if overall_winners:
            best_overall = overall_winners[0]
            sections.append(f"\n**🏆 Overall Winner:** {best_overall[0]}\n")

        # Error analysis
        sections.append("## Error Analysis\n")

        has_errors = False
        for scenario_name, scenario_results in results.items():
            for result in scenario_results:
                if result.error_count > 0:
                    has_errors = True
                    sections.append(f"- **{result.implementation_name}** ({scenario_name}): "
                                  f"{result.error_count} errors")
                    for error in result.errors:
                        sections.append(f"  - {error}")

        if not has_errors:
            sections.append("✅ No errors detected across all benchmarks.\n")

        markdown = "\n".join(sections)

        if output_path:
            Path(output_path).write_text(markdown)

        return markdown

    def close(self):
        """Close the fixture and collector"""
        if self.collector:
            self.collector.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
