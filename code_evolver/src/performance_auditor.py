"""
Performance Auditor

Creates tracking versions of nodes/tools, collects performance data,
checks against thresholds, and queues components for optimization.

Workflow:
1. Auditor wraps existing nodes with performance tracking
2. Runs with unit tests to ensure behavior unchanged
3. Collects performance metrics via PerformanceCollector
4. Checks metrics against defined thresholds
5. Components failing thresholds → optimization queue
6. Generates audit report for optimizer

This runs BEFORE the optimizer to identify what needs optimization.
"""

import ast
import inspect
import importlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import subprocess
import sys

from performance_collector import PerformanceCollector
from debug_store import DebugStore


@dataclass
class PerformanceThreshold:
    """Performance thresholds for auditing"""
    max_duration_ms: Optional[float] = None  # Maximum acceptable duration
    max_memory_mb: Optional[float] = None  # Maximum acceptable memory
    max_cpu_percent: Optional[float] = None  # Maximum acceptable CPU
    max_error_rate: Optional[float] = None  # Maximum acceptable error rate (0.0-1.0)
    min_success_rate: Optional[float] = 0.95  # Minimum success rate


@dataclass
class AuditResult:
    """Result of auditing a component"""
    component_name: str
    layer: str
    passed: bool
    violations: List[str]
    metrics: Dict[str, float]
    threshold: PerformanceThreshold
    recommendation: str


@dataclass
class OptimizationCandidate:
    """Component queued for optimization"""
    component_name: str
    layer: str
    priority: int  # 1-10, 10 being highest priority
    violations: List[str]
    current_metrics: Dict[str, float]
    target_metrics: Dict[str, float]
    code_snapshot: Optional[str] = None
    test_file: Optional[str] = None


class PerformanceAuditor:
    """
    Audits system performance and queues components for optimization.

    Usage:
        # Define thresholds
        thresholds = {
            "tool": PerformanceThreshold(
                max_duration_ms=1000.0,
                max_memory_mb=100.0,
                min_success_rate=0.95
            ),
            "node": PerformanceThreshold(
                max_duration_ms=5000.0,
                max_memory_mb=500.0,
                min_success_rate=0.90
            )
        }

        # Create auditor
        auditor = PerformanceAuditor(
            session_id="audit_run_1",
            thresholds=thresholds
        )

        # Audit a component
        result = auditor.audit_component(
            my_function,
            layer="tool",
            run_tests=True,
            test_command="pytest tests/test_my_function.py"
        )

        # Get optimization queue
        candidates = auditor.get_optimization_queue()

        # Generate audit report
        report = auditor.generate_audit_report()
    """

    def __init__(
        self,
        session_id: str,
        thresholds: Optional[Dict[str, PerformanceThreshold]] = None,
        base_path: str = "debug_data",
        optimization_queue_path: str = "optimization_queue.json"
    ):
        """
        Initialize performance auditor.

        Args:
            session_id: Unique audit session ID
            thresholds: Performance thresholds by layer
            base_path: Base path for storing data
            optimization_queue_path: Path to optimization queue file
        """
        self.session_id = session_id
        self.thresholds = thresholds or self._default_thresholds()
        self.base_path = Path(base_path)
        self.optimization_queue_path = Path(optimization_queue_path)

        # Performance collector for tracking
        self.collector = PerformanceCollector(
            session_id=session_id,
            base_path=str(self.base_path),
            enable_io_tracking=True,
            enable_memory_profiling=True
        )

        # Audit results
        self.audit_results: List[AuditResult] = []

        # Optimization queue
        self.optimization_queue: List[OptimizationCandidate] = []

        # Load existing queue if available
        self._load_optimization_queue()

    @staticmethod
    def _default_thresholds() -> Dict[str, PerformanceThreshold]:
        """Default performance thresholds"""
        return {
            "function": PerformanceThreshold(
                max_duration_ms=100.0,
                max_memory_mb=50.0,
                min_success_rate=0.99
            ),
            "tool": PerformanceThreshold(
                max_duration_ms=1000.0,
                max_memory_mb=100.0,
                min_success_rate=0.95
            ),
            "step": PerformanceThreshold(
                max_duration_ms=5000.0,
                max_memory_mb=200.0,
                min_success_rate=0.95
            ),
            "node": PerformanceThreshold(
                max_duration_ms=10000.0,
                max_memory_mb=500.0,
                min_success_rate=0.90
            ),
            "workflow": PerformanceThreshold(
                max_duration_ms=60000.0,
                max_memory_mb=1000.0,
                min_success_rate=0.85
            )
        }

    def create_tracking_version(
        self,
        func: Callable,
        layer: str,
        tool_name: Optional[str] = None
    ) -> Callable:
        """
        Create a tracking version of a function/node.

        This wraps the original function with performance tracking
        without changing its behavior.

        Args:
            func: Original function to wrap
            layer: Layer type ('tool', 'node', 'step', etc.)
            tool_name: Optional tool name

        Returns:
            Wrapped function with tracking
        """
        return self.collector.instrument(
            layer=layer,
            tool_name=tool_name or func.__name__,
            capture_args=True,
            capture_result=True,
            track_code_changes=True
        )(func)

    def audit_component(
        self,
        component: Callable,
        layer: str,
        component_name: Optional[str] = None,
        run_tests: bool = True,
        test_command: Optional[str] = None,
        test_iterations: int = 10
    ) -> AuditResult:
        """
        Audit a component's performance.

        Args:
            component: Function/tool to audit
            layer: Layer type
            component_name: Name of component
            run_tests: Whether to run unit tests
            test_command: Test command to verify behavior unchanged
            test_iterations: Number of test iterations for metrics

        Returns:
            AuditResult with pass/fail and violations
        """
        name = component_name or component.__name__

        print(f"🔍 Auditing {layer}/{name}...")

        # Create tracking version
        tracked_component = self.create_tracking_version(component, layer, name)

        # Run tests if requested
        if run_tests and test_command:
            print(f"   Running tests: {test_command}")
            test_passed = self._run_tests(test_command)
            if not test_passed:
                return AuditResult(
                    component_name=name,
                    layer=layer,
                    passed=False,
                    violations=["Unit tests failed - tracking may have changed behavior"],
                    metrics={},
                    threshold=self.thresholds.get(layer, PerformanceThreshold()),
                    recommendation="Fix tests before auditing"
                )

        # Execute tracked version to collect metrics
        # Note: This is a placeholder - in real usage, the component would be
        # executed as part of normal workflow with tracking enabled
        print(f"   Collecting metrics ({test_iterations} iterations)...")

        # Sync metrics to analytics layer
        self.collector.store.sync_to_duckdb()

        # Get metrics from debug store
        metrics_df = self.collector.store.query_analytics(f"""
            SELECT
                AVG(duration_ms) as avg_duration,
                MAX(duration_ms) as max_duration,
                AVG(memory_mb) as avg_memory,
                MAX(memory_mb) as peak_memory,
                AVG(cpu_percent) as avg_cpu,
                COUNT(*) as total_executions,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
            FROM records
            WHERE context_type = ? AND context_id = ?
        """, [layer, name]).fetchone()

        if not metrics_df or metrics_df[6] == 0:  # No executions recorded
            print(f"   ⚠️  No metrics collected yet - run component with tracking enabled")
            return AuditResult(
                component_name=name,
                layer=layer,
                passed=False,
                violations=["No metrics collected"],
                metrics={},
                threshold=self.thresholds.get(layer, PerformanceThreshold()),
                recommendation="Execute component to collect metrics"
            )

        # Extract metrics
        metrics = {
            "avg_duration_ms": float(metrics_df[0]),
            "max_duration_ms": float(metrics_df[1]),
            "avg_memory_mb": float(metrics_df[2]),
            "peak_memory_mb": float(metrics_df[3]),
            "avg_cpu_percent": float(metrics_df[4]),
            "total_executions": int(metrics_df[5]),
            "error_count": int(metrics_df[6]),
            "success_count": int(metrics_df[7]),
            "success_rate": float(metrics_df[7]) / float(metrics_df[5]) if metrics_df[5] > 0 else 0.0,
            "error_rate": float(metrics_df[6]) / float(metrics_df[5]) if metrics_df[5] > 0 else 0.0
        }

        # Check against thresholds
        threshold = self.thresholds.get(layer, PerformanceThreshold())
        violations = self._check_thresholds(metrics, threshold)

        # Determine if passed
        passed = len(violations) == 0

        # Generate recommendation
        recommendation = self._generate_recommendation(metrics, threshold, violations)

        # Create result
        result = AuditResult(
            component_name=name,
            layer=layer,
            passed=passed,
            violations=violations,
            metrics=metrics,
            threshold=threshold,
            recommendation=recommendation
        )

        self.audit_results.append(result)

        # If failed, add to optimization queue
        if not passed:
            self._queue_for_optimization(component, result)

        # Print result
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status}")
        if violations:
            for violation in violations:
                print(f"      - {violation}")

        return result

    def _run_tests(self, test_command: str) -> bool:
        """Run unit tests and return success status"""
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("      ⚠️  Tests timed out")
            return False
        except Exception as e:
            print(f"      ⚠️  Test execution failed: {e}")
            return False

    def _check_thresholds(
        self,
        metrics: Dict[str, float],
        threshold: PerformanceThreshold
    ) -> List[str]:
        """Check metrics against thresholds and return violations"""
        violations = []

        # Duration check
        if threshold.max_duration_ms and metrics["avg_duration_ms"] > threshold.max_duration_ms:
            violations.append(
                f"Duration {metrics['avg_duration_ms']:.2f}ms exceeds threshold {threshold.max_duration_ms}ms"
            )

        # Memory check
        if threshold.max_memory_mb and metrics["peak_memory_mb"] > threshold.max_memory_mb:
            violations.append(
                f"Memory {metrics['peak_memory_mb']:.2f}MB exceeds threshold {threshold.max_memory_mb}MB"
            )

        # CPU check
        if threshold.max_cpu_percent and metrics["avg_cpu_percent"] > threshold.max_cpu_percent:
            violations.append(
                f"CPU {metrics['avg_cpu_percent']:.1f}% exceeds threshold {threshold.max_cpu_percent}%"
            )

        # Success rate check
        if threshold.min_success_rate and metrics["success_rate"] < threshold.min_success_rate:
            violations.append(
                f"Success rate {metrics['success_rate']:.1%} below threshold {threshold.min_success_rate:.1%}"
            )

        # Error rate check
        if threshold.max_error_rate and metrics["error_rate"] > threshold.max_error_rate:
            violations.append(
                f"Error rate {metrics['error_rate']:.1%} exceeds threshold {threshold.max_error_rate:.1%}"
            )

        return violations

    def _generate_recommendation(
        self,
        metrics: Dict[str, float],
        threshold: PerformanceThreshold,
        violations: List[str]
    ) -> str:
        """Generate optimization recommendation"""
        if not violations:
            return "Performance within acceptable thresholds"

        recommendations = []

        # Duration recommendations
        if threshold.max_duration_ms and metrics["avg_duration_ms"] > threshold.max_duration_ms:
            speedup_needed = (metrics["avg_duration_ms"] / threshold.max_duration_ms - 1) * 100
            recommendations.append(f"Optimize for {speedup_needed:.0f}% speedup")

        # Memory recommendations
        if threshold.max_memory_mb and metrics["peak_memory_mb"] > threshold.max_memory_mb:
            reduction_needed = metrics["peak_memory_mb"] - threshold.max_memory_mb
            recommendations.append(f"Reduce memory usage by {reduction_needed:.0f}MB")

        # Error recommendations
        if metrics["error_count"] > 0:
            recommendations.append(f"Fix {metrics['error_count']} errors")

        return "; ".join(recommendations) if recommendations else "Investigate performance issues"

    def _queue_for_optimization(self, component: Callable, result: AuditResult):
        """Add component to optimization queue"""
        # Calculate priority (1-10)
        priority = self._calculate_priority(result)

        # Get code snapshot
        code_snapshot = None
        try:
            code_snapshot = inspect.getsource(component)
        except (OSError, TypeError):
            pass

        # Calculate target metrics
        threshold = result.threshold
        target_metrics = {
            "target_duration_ms": threshold.max_duration_ms or result.metrics.get("avg_duration_ms", 0) * 0.5,
            "target_memory_mb": threshold.max_memory_mb or result.metrics.get("peak_memory_mb", 0) * 0.7,
            "target_success_rate": threshold.min_success_rate or 0.95
        }

        candidate = OptimizationCandidate(
            component_name=result.component_name,
            layer=result.layer,
            priority=priority,
            violations=result.violations,
            current_metrics=result.metrics,
            target_metrics=target_metrics,
            code_snapshot=code_snapshot
        )

        self.optimization_queue.append(candidate)
        self._save_optimization_queue()

        print(f"   ➕ Added to optimization queue (priority: {priority}/10)")

    def _calculate_priority(self, result: AuditResult) -> int:
        """Calculate optimization priority (1-10)"""
        priority = 5  # Base priority

        # Increase priority for severe violations
        if result.metrics.get("error_rate", 0) > 0.1:
            priority += 3  # High error rate

        # Duration violations
        threshold = result.threshold
        if threshold.max_duration_ms:
            duration_ratio = result.metrics.get("avg_duration_ms", 0) / threshold.max_duration_ms
            if duration_ratio > 2.0:
                priority += 2
            elif duration_ratio > 1.5:
                priority += 1

        # Memory violations
        if threshold.max_memory_mb:
            memory_ratio = result.metrics.get("peak_memory_mb", 0) / threshold.max_memory_mb
            if memory_ratio > 2.0:
                priority += 2
            elif memory_ratio > 1.5:
                priority += 1

        # Multiple violations
        if len(result.violations) > 2:
            priority += 1

        return min(10, max(1, priority))  # Clamp to 1-10

    def get_optimization_queue(self, min_priority: int = 1) -> List[OptimizationCandidate]:
        """
        Get optimization queue sorted by priority.

        Args:
            min_priority: Minimum priority to include

        Returns:
            List of optimization candidates
        """
        candidates = [c for c in self.optimization_queue if c.priority >= min_priority]
        return sorted(candidates, key=lambda c: c.priority, reverse=True)

    def generate_audit_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate comprehensive audit report.

        Args:
            output_path: Optional file path to save report

        Returns:
            Markdown-formatted audit report
        """
        sections = []

        # Header
        sections.append("# Performance Audit Report")
        sections.append(f"\n**Session:** {self.session_id}\n")

        # Summary
        total_audited = len(self.audit_results)
        passed = sum(1 for r in self.audit_results if r.passed)
        failed = total_audited - passed

        sections.append("## Executive Summary\n")
        sections.append(f"- **Total Components Audited:** {total_audited}")
        sections.append(f"- **Passed:** {passed} ({passed/total_audited*100:.1f}%)" if total_audited > 0 else "- **Passed:** 0")
        sections.append(f"- **Failed:** {failed} ({failed/total_audited*100:.1f}%)" if total_audited > 0 else "- **Failed:** 0")
        sections.append(f"- **Queued for Optimization:** {len(self.optimization_queue)}\n")

        # Audit results by layer
        sections.append("## Audit Results by Layer\n")

        layers = {}
        for result in self.audit_results:
            if result.layer not in layers:
                layers[result.layer] = {"passed": 0, "failed": 0, "results": []}

            if result.passed:
                layers[result.layer]["passed"] += 1
            else:
                layers[result.layer]["failed"] += 1

            layers[result.layer]["results"].append(result)

        for layer, data in sorted(layers.items()):
            sections.append(f"### {layer.upper()} Layer\n")
            sections.append(f"- Passed: {data['passed']}")
            sections.append(f"- Failed: {data['failed']}\n")

            # Failed components
            if data["failed"] > 0:
                sections.append("**Failed Components:**\n")
                for result in data["results"]:
                    if not result.passed:
                        sections.append(f"- **{result.component_name}**")
                        for violation in result.violations:
                            sections.append(f"  - ❌ {violation}")
                        sections.append(f"  - 💡 {result.recommendation}")
                        sections.append("")

        # Optimization queue
        if self.optimization_queue:
            sections.append("\n## Optimization Queue\n")
            sections.append(f"Components queued for optimization (sorted by priority):\n")

            queue = self.get_optimization_queue()
            for i, candidate in enumerate(queue, 1):
                sections.append(f"{i}. **{candidate.component_name}** ({candidate.layer}) - Priority: {candidate.priority}/10\n")
                sections.append("   **Violations:**")
                for violation in candidate.violations:
                    sections.append(f"   - {violation}")

                sections.append("\n   **Current Metrics:**")
                for key, value in candidate.current_metrics.items():
                    if "rate" in key:
                        sections.append(f"   - {key}: {value:.1%}")
                    else:
                        sections.append(f"   - {key}: {value:.2f}")

                sections.append("\n   **Target Metrics:**")
                for key, value in candidate.target_metrics.items():
                    if "rate" in key:
                        sections.append(f"   - {key}: {value:.1%}")
                    else:
                        sections.append(f"   - {key}: {value:.2f}")

                sections.append("\n")

        # Performance data summary (from collector)
        sections.append("\n## Detailed Performance Data\n")
        perf_report = self.collector.generate_optimization_report(min_executions=1)
        sections.append(perf_report)

        markdown = "\n".join(sections)

        if output_path:
            Path(output_path).write_text(markdown)

        return markdown

    def _load_optimization_queue(self):
        """Load optimization queue from file"""
        if self.optimization_queue_path.exists():
            try:
                with open(self.optimization_queue_path, 'r') as f:
                    data = json.load(f)
                    self.optimization_queue = [
                        OptimizationCandidate(**item) for item in data
                    ]
            except Exception as e:
                print(f"⚠️  Failed to load optimization queue: {e}")

    def _save_optimization_queue(self):
        """Save optimization queue to file"""
        try:
            with open(self.optimization_queue_path, 'w') as f:
                json.dump(
                    [asdict(c) for c in self.optimization_queue],
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"⚠️  Failed to save optimization queue: {e}")

    def close(self):
        """Close auditor and save state"""
        self._save_optimization_queue()
        self.collector.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
