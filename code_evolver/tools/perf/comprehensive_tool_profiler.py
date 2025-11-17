#!/usr/bin/env python3
"""
Comprehensive Tool Profiler - Orchestrates complete tool analysis and RAG tagging.
Combines performance testing, static analysis, regression evaluation, and RAG updates.
"""
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ComprehensiveToolProfiler:
    """
    Orchestrates complete tool profiling workflow:
    1. Benchmark performance (timeit_optimizer)
    2. Run static analysis (performance_regression_evaluator)
    3. Evaluate regressions if old version exists
    4. Tag tool in RAG with all metadata
    5. Generate documentation
    """

    def __init__(self, tools_path: str = "./code_evolver/tools"):
        self.tools_path = Path(tools_path)
        self.perf_tools_path = self.tools_path / "perf"

    def profile_tool(
        self,
        tool_id: str,
        tool_code: str,
        test_input: Optional[Dict[str, Any]] = None,
        requirement: str = "",
        old_version_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run complete profiling workflow for a tool.

        Args:
            tool_id: Tool identifier
            tool_code: Source code of the tool
            test_input: Sample input for testing
            requirement: Current requirement specification
            old_version_data: Optional old version data for regression comparison

        Returns:
            Complete profiling results
        """
        results = {
            "tool_id": tool_id,
            "timestamp": datetime.now().isoformat(),
            "workflow_steps": []
        }

        # Step 1: Run performance benchmark
        print(f"[1/5] Running performance benchmark...", file=sys.stderr)
        benchmark_result = self._run_benchmark(tool_id, tool_code, test_input)
        results["workflow_steps"].append({
            "step": "benchmark",
            "status": "completed" if benchmark_result["success"] else "failed",
            "data": benchmark_result
        })

        if not benchmark_result["success"]:
            results["status"] = "failed"
            results["error"] = "Benchmark failed"
            return results

        # Step 2: Run static analysis
        print(f"[2/5] Running static analysis...", file=sys.stderr)
        static_analysis = self._run_static_analysis(tool_code)
        results["workflow_steps"].append({
            "step": "static_analysis",
            "status": "completed",
            "data": static_analysis
        })

        # Step 3: Evaluate regression (if old version exists)
        regression_evaluation = None
        if old_version_data:
            print(f"[3/5] Evaluating performance regression...", file=sys.stderr)
            regression_evaluation = self._evaluate_regression(
                old_version_data,
                benchmark_result,
                static_analysis,
                requirement,
                old_version_data.get("code", ""),
                tool_code
            )
            results["workflow_steps"].append({
                "step": "regression_evaluation",
                "status": "completed" if regression_evaluation["success"] else "failed",
                "data": regression_evaluation
            })

            # Check if regression is acceptable
            if regression_evaluation["success"]:
                eval_result = regression_evaluation["evaluation"]
                if eval_result["recommendation"] == "REJECT":
                    results["status"] = "rejected"
                    results["reason"] = f"Regression rejected: {eval_result['reasoning']}"
                    return results
                elif eval_result["recommendation"] == "REVIEW":
                    results["status"] = "review_required"
                    results["reason"] = f"Human review needed: {eval_result['reasoning']}"
        else:
            print(f"[3/5] Skipping regression evaluation (no old version)", file=sys.stderr)
            results["workflow_steps"].append({
                "step": "regression_evaluation",
                "status": "skipped",
                "reason": "No old version data"
            })

        # Step 4: Build comprehensive metadata
        print(f"[4/5] Building comprehensive metadata...", file=sys.stderr)
        metadata = self._build_metadata(
            benchmark_result,
            static_analysis,
            regression_evaluation,
            tool_code,
            requirement
        )
        results["metadata"] = metadata

        # Step 5: Update RAG
        print(f"[5/5] Updating RAG with comprehensive metadata...", file=sys.stderr)
        rag_update = self._update_rag(tool_id, metadata)
        results["workflow_steps"].append({
            "step": "rag_update",
            "status": "completed" if rag_update["success"] else "failed",
            "data": rag_update
        })

        results["status"] = "completed"
        return results

    def _run_benchmark(
        self,
        tool_id: str,
        tool_code: str,
        test_input: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run performance benchmark using timeit_optimizer."""
        try:
            benchmark_input = {
                "command": "benchmark",
                "tool_code": tool_code,
                "tool_id": tool_id,
                "test_input": test_input
            }

            result = subprocess.run(
                [sys.executable, str(self.perf_tools_path / "timeit_optimizer.py"), "benchmark"],
                input=json.dumps(benchmark_input),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run_static_analysis(self, tool_code: str) -> Dict[str, Any]:
        """Run static analysis using performance_regression_evaluator."""
        try:
            analysis_input = {
                "command": "analyze",
                "code": tool_code
            }

            result = subprocess.run(
                [sys.executable, str(self.perf_tools_path / "performance_regression_evaluator.py"), "analyze"],
                input=json.dumps(analysis_input),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _evaluate_regression(
        self,
        old_version_data: Dict[str, Any],
        new_benchmark: Dict[str, Any],
        new_static_analysis: Dict[str, Any],
        new_requirement: str,
        old_code: str,
        new_code: str
    ) -> Dict[str, Any]:
        """Evaluate performance regression."""
        try:
            # Extract old metrics
            old_metadata = old_version_data.get("metadata", {})
            old_perf = old_metadata.get("performance", {})
            old_static = old_metadata.get("static_analysis", {})

            # Extract new metrics
            new_best_run = new_benchmark.get("best_run", {})

            # Build requirement change
            requirement_change = {
                "previous_requirement": old_version_data.get("requirement", "Unknown"),
                "new_requirement": new_requirement,
                "change_summary": "Version update with possible requirement changes",
                "feature_additions": [],
                "feature_removals": [],
                "breaking_changes": []
            }

            evaluation_input = {
                "command": "evaluate",
                "old_metrics": {
                    "execution_time_ms": old_perf.get("execution_time_ms", 0),
                    "memory_usage_kb": old_perf.get("memory_usage_kb", 0),
                    "timestamp": old_perf.get("last_benchmarked", ""),
                    "version": old_version_data.get("version", "1.0.0"),
                    "security_issues": old_static.get("security", {}).get("total_issues", 0)
                },
                "new_metrics": {
                    "execution_time_ms": new_best_run.get("execution_time_ms", 0),
                    "memory_usage_kb": new_best_run.get("memory_usage_kb", 0),
                    "timestamp": new_best_run.get("timestamp", ""),
                    "version": old_version_data.get("version", "2.0.0"),
                    "security_issues": new_static_analysis.get("analysis", {}).get("security", {}).get("total_issues", 0)
                },
                "requirement_change": requirement_change,
                "old_code": old_code,
                "new_code": new_code
            }

            result = subprocess.run(
                [sys.executable, str(self.perf_tools_path / "performance_regression_evaluator.py"), "evaluate"],
                input=json.dumps(evaluation_input),
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _build_metadata(
        self,
        benchmark_result: Dict[str, Any],
        static_analysis: Dict[str, Any],
        regression_evaluation: Optional[Dict[str, Any]],
        tool_code: str,
        requirement: str
    ) -> Dict[str, Any]:
        """Build comprehensive metadata for RAG."""
        best_run = benchmark_result.get("best_run", {})
        analysis = static_analysis.get("analysis", {})

        metadata = {
            "performance": {
                "execution_time_ms": best_run.get("execution_time_ms", 0),
                "memory_usage_kb": best_run.get("memory_usage_kb", 0),
                "last_benchmarked": best_run.get("timestamp", ""),
                "test_runs": len(benchmark_result.get("all_runs", [])),
                "test_script": benchmark_result.get("test_script", "")
            },
            "static_analysis": {
                "complexity": analysis.get("complexity", {}),
                "security": analysis.get("security", {}),
                "correctness": analysis.get("correctness", {}),
                "code_quality": analysis.get("code_quality", {})
            },
            "source": tool_code,
            "requirement": requirement,
            "last_updated": datetime.now().isoformat()
        }

        # Add regression evaluation if available
        if regression_evaluation and regression_evaluation.get("success"):
            metadata["performance"]["regression_evaluation"] = regression_evaluation.get("evaluation", {})

        return metadata

    def _update_rag(self, tool_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update tool registry with comprehensive metadata."""
        try:
            tools_index_path = self.tools_path / "index.json"

            if tools_index_path.exists():
                with open(tools_index_path, 'r') as f:
                    registry = json.load(f)

                # Update or create tool entry
                if tool_id in registry:
                    if "metadata" not in registry[tool_id]:
                        registry[tool_id]["metadata"] = {}
                    registry[tool_id]["metadata"].update(metadata)
                else:
                    registry[tool_id] = {
                        "tool_id": tool_id,
                        "metadata": metadata
                    }

                # Save updated registry
                with open(tools_index_path, 'w') as f:
                    json.dump(registry, f, indent=2)

                return {"success": True, "tool_id": tool_id}

            return {"success": False, "error": "Tool registry not found"}

        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    """CLI interface for comprehensive tool profiler."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: comprehensive_tool_profiler.py <tool_id>",
            "description": "Provide tool data via stdin as JSON"
        }))
        sys.exit(1)

    tool_id = sys.argv[1]

    # Read tool data from stdin
    try:
        tool_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        sys.exit(1)

    tool_code = tool_data.get("tool_code", "")
    test_input = tool_data.get("test_input")
    requirement = tool_data.get("requirement", "")
    old_version_data = tool_data.get("old_version_data")

    profiler = ComprehensiveToolProfiler()

    result = profiler.profile_tool(
        tool_id,
        tool_code,
        test_input,
        requirement,
        old_version_data
    )

    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    if result.get("status") == "completed":
        sys.exit(0)
    elif result.get("status") == "review_required":
        sys.exit(2)  # Requires review
    else:
        sys.exit(1)  # Failed


if __name__ == "__main__":
    main()
