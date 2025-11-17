#!/usr/bin/env python3
"""
Performance testing and optimization tool using timeit.
Generates benchmark scripts, runs performance tests with mocking, and updates RAG metadata.
"""
import json
import sys
import time
import timeit
import tracemalloc
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass, asdict
import importlib.util


@dataclass
class PerformanceMetrics:
    """Performance metrics for a tool/function."""
    execution_time_ms: float
    memory_usage_kb: float
    calls_to_mocked_tools: List[str]
    test_run_number: int
    timestamp: str


@dataclass
class BenchmarkResult:
    """Result from running performance benchmarks."""
    tool_id: str
    best_run: PerformanceMetrics
    all_runs: List[PerformanceMetrics]
    test_script: str
    success: bool
    error: Optional[str] = None


class ToolMocker:
    """Handles mocking of tool calls and external services."""

    def __init__(self):
        self.mocked_calls = []

    def mock_tool_call(self, tool_name: str) -> Mock:
        """Create a mock for a tool call."""
        self.mocked_calls.append(tool_name)
        mock = Mock()
        mock.return_value = {"status": "success", "mocked": True}
        return mock

    def mock_external_service(self, service_name: str) -> Mock:
        """Create a mock for an external service/endpoint."""
        self.mocked_calls.append(f"external:{service_name}")
        mock = Mock()
        mock.return_value = {"status": "ok", "data": {}, "mocked": True}
        return mock

    def extract_tool_calls_from_code(self, code: str) -> List[str]:
        """Extract tool calls from code using AST analysis."""
        try:
            tree = ast.parse(code)
            tool_calls = []

            for node in ast.walk(tree):
                # Look for function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        # Common patterns for tool calls
                        if any(pattern in func_name.lower() for pattern in
                               ['call_tool', 'execute_tool', 'run_tool', 'tool_']):
                            tool_calls.append(func_name)
                    elif isinstance(node, ast.Attribute):
                        # Handle method calls like client.call()
                        if node.func.attr in ['call', 'execute', 'run']:
                            tool_calls.append(f"{node.func.value.id}.{node.func.attr}")

            return tool_calls
        except Exception as e:
            print(f"Warning: Could not parse code for tool calls: {e}", file=sys.stderr)
            return []

    def extract_external_calls_from_code(self, code: str) -> List[str]:
        """Extract external service calls (requests, httpx, etc.)."""
        external_patterns = [
            r'requests\.(get|post|put|delete|patch)',
            r'httpx\.(get|post|put|delete|patch)',
            r'urllib\.request\.',
            r'aiohttp\.ClientSession',
            r'ollama\.generate',
            r'openai\.',
            r'anthropic\.'
        ]

        external_calls = []
        for pattern in external_patterns:
            matches = re.findall(pattern, code)
            external_calls.extend(matches)

        return external_calls


class PerformanceTestGenerator:
    """Generates performance test scripts for tools."""

    def __init__(self):
        self.mocker = ToolMocker()

    def generate_test_script(
        self,
        tool_code: str,
        tool_id: str,
        test_input: Optional[Dict[str, Any]] = None,
        mock_tools: bool = True,
        mock_external: bool = True
    ) -> str:
        """
        Generate a self-contained performance test script.

        Args:
            tool_code: The tool's Python code
            tool_id: Identifier for the tool
            test_input: Sample input data for testing
            mock_tools: Whether to mock other tool calls
            mock_external: Whether to mock external service calls

        Returns:
            A complete Python script that can be executed standalone
        """
        # Extract function name from code
        func_name = self._extract_main_function(tool_code)

        # Extract dependencies
        tool_calls = self.mocker.extract_tool_calls_from_code(tool_code) if mock_tools else []
        external_calls = self.mocker.extract_external_calls_from_code(tool_code) if mock_external else []

        # Generate mock setup code
        mock_setup = self._generate_mock_setup(tool_calls, external_calls)

        # Generate test input
        if test_input is None:
            test_input = {"input": "test_data"}

        test_script = f'''#!/usr/bin/env python3
"""
Auto-generated performance test for tool: {tool_id}
Generated at: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
import json
import sys
import time
import timeit
import tracemalloc
import traceback
from unittest.mock import Mock, patch
from typing import Dict, Any

# Tool code under test
{tool_code}

{mock_setup}

def run_performance_test():
    """Run the performance test with mocking."""
    test_input = {json.dumps(test_input, indent=4)}

    # Start memory tracking
    tracemalloc.start()

    # Time the execution
    start_time = time.perf_counter()

    try:
        result = {func_name}(**test_input)

        # End timing
        end_time = time.perf_counter()

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        execution_time_ms = (end_time - start_time) * 1000
        memory_usage_kb = peak / 1024

        return {{
            "success": True,
            "execution_time_ms": execution_time_ms,
            "memory_usage_kb": memory_usage_kb,
            "result": result
        }}
    except Exception as e:
        tracemalloc.stop()
        return {{
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }}

if __name__ == "__main__":
    # Run 3 times and report all results
    results = []
    for run_num in range(3):
        print(f"Run {{run_num + 1}}/3...", file=sys.stderr)
        result = run_performance_test()
        result["run_number"] = run_num + 1
        results.append(result)
        time.sleep(0.1)  # Brief pause between runs

    # Find best run (lowest execution time among successful runs)
    successful_runs = [r for r in results if r.get("success", False)]
    if successful_runs:
        best_run = min(successful_runs, key=lambda r: r["execution_time_ms"])
        output = {{
            "best_run": best_run,
            "all_runs": results,
            "tool_id": "{tool_id}"
        }}
    else:
        output = {{
            "best_run": None,
            "all_runs": results,
            "tool_id": "{tool_id}",
            "error": "All runs failed"
        }}

    print(json.dumps(output, indent=2))
'''
        return test_script

    def _extract_main_function(self, code: str) -> str:
        """Extract the main function name from tool code."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Return the first function that's not private
                    if not node.name.startswith('_'):
                        return node.name
            return "main"
        except Exception:
            return "main"

    def _generate_mock_setup(self, tool_calls: List[str], external_calls: List[str]) -> str:
        """Generate mock setup code for tools and external services."""
        if not tool_calls and not external_calls:
            return "# No mocking required"

        mock_code = "# Mock setup for tools and external services\n"

        if tool_calls:
            mock_code += "# Mock tool calls\n"
            for tool in tool_calls:
                mock_code += f"{tool} = Mock(return_value={{'status': 'success', 'mocked': True}})\n"

        if external_calls:
            mock_code += "\n# Mock external service calls\n"
            # Generate patches for common external libraries
            if any('requests' in call for call in external_calls):
                mock_code += "@patch('requests.get', return_value=Mock(json=lambda: {}, status_code=200))\n"
                mock_code += "@patch('requests.post', return_value=Mock(json=lambda: {}, status_code=200))\n"
            if any('httpx' in call for call in external_calls):
                mock_code += "@patch('httpx.get', return_value=Mock(json=lambda: {}, status_code=200))\n"
            if any('ollama' in call for call in external_calls):
                mock_code += "@patch('ollama.generate', return_value={'response': 'mocked'})\n"

        return mock_code


class TimeitOptimizer:
    """Main optimizer class for performance testing and optimization."""

    def __init__(self, rag_memory_path: Optional[str] = None):
        self.test_generator = PerformanceTestGenerator()
        self.rag_memory_path = rag_memory_path or "./rag_memory"

    def benchmark_tool(
        self,
        tool_code: str,
        tool_id: str,
        test_input: Optional[Dict[str, Any]] = None,
        num_runs: int = 3
    ) -> BenchmarkResult:
        """
        Benchmark a tool's performance.

        Args:
            tool_code: The tool's source code
            tool_id: Tool identifier
            test_input: Test input data
            num_runs: Number of benchmark runs (default: 3)

        Returns:
            BenchmarkResult with performance metrics
        """
        # Generate test script
        test_script = self.test_generator.generate_test_script(
            tool_code, tool_id, test_input
        )

        # Save test script to temp file and execute
        test_file = Path(f"/tmp/perf_test_{tool_id}.py")
        test_file.write_text(test_script)

        try:
            # Execute the test script
            import subprocess
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                output = json.loads(result.stdout)

                # Convert to PerformanceMetrics objects
                all_runs = []
                for run_data in output.get("all_runs", []):
                    if run_data.get("success"):
                        metrics = PerformanceMetrics(
                            execution_time_ms=run_data["execution_time_ms"],
                            memory_usage_kb=run_data["memory_usage_kb"],
                            calls_to_mocked_tools=[],
                            test_run_number=run_data["run_number"],
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                        )
                        all_runs.append(metrics)

                best_run_data = output.get("best_run")
                if best_run_data:
                    best_run = PerformanceMetrics(
                        execution_time_ms=best_run_data["execution_time_ms"],
                        memory_usage_kb=best_run_data["memory_usage_kb"],
                        calls_to_mocked_tools=[],
                        test_run_number=best_run_data["run_number"],
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                    )

                    return BenchmarkResult(
                        tool_id=tool_id,
                        best_run=best_run,
                        all_runs=all_runs,
                        test_script=test_script,
                        success=True
                    )

            # Handle failures
            error_msg = result.stderr or result.stdout
            return BenchmarkResult(
                tool_id=tool_id,
                best_run=None,
                all_runs=[],
                test_script=test_script,
                success=False,
                error=error_msg
            )

        except Exception as e:
            return BenchmarkResult(
                tool_id=tool_id,
                best_run=None,
                all_runs=[],
                test_script=test_script,
                success=False,
                error=str(e)
            )

    def update_rag_metadata(
        self,
        tool_id: str,
        benchmark_result: BenchmarkResult
    ) -> bool:
        """
        Update the tool's RAG metadata with performance metrics.

        Args:
            tool_id: Tool identifier
            benchmark_result: Benchmark results to store

        Returns:
            True if update succeeded, False otherwise
        """
        if not benchmark_result.success or not benchmark_result.best_run:
            print(f"Warning: Cannot update RAG for failed benchmark", file=sys.stderr)
            return False

        try:
            # Load tool registry
            tools_index_path = Path("./code_evolver/tools/index.json")
            if tools_index_path.exists():
                with open(tools_index_path, 'r') as f:
                    registry = json.load(f)

                # Update tool metadata
                if tool_id in registry:
                    if "metadata" not in registry[tool_id]:
                        registry[tool_id]["metadata"] = {}

                    registry[tool_id]["metadata"]["performance"] = {
                        "execution_time_ms": benchmark_result.best_run.execution_time_ms,
                        "memory_usage_kb": benchmark_result.best_run.memory_usage_kb,
                        "last_benchmarked": benchmark_result.best_run.timestamp,
                        "test_runs": len(benchmark_result.all_runs)
                    }

                    # Save updated registry
                    with open(tools_index_path, 'w') as f:
                        json.dump(registry, f, indent=2)

                    return True

            return False

        except Exception as e:
            print(f"Error updating RAG metadata: {e}", file=sys.stderr)
            return False


def main():
    """CLI interface for timeit optimizer."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: timeit_optimizer.py <command> [args...]",
            "commands": {
                "generate": "Generate test script",
                "benchmark": "Run benchmark",
                "update_rag": "Update RAG metadata"
            }
        }))
        sys.exit(1)

    command = sys.argv[1]

    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}

    optimizer = TimeitOptimizer()

    if command == "generate":
        # Generate test script
        tool_code = input_data.get("tool_code", "")
        tool_id = input_data.get("tool_id", "unknown")
        test_input = input_data.get("test_input")

        test_script = optimizer.test_generator.generate_test_script(
            tool_code, tool_id, test_input
        )

        print(json.dumps({
            "test_script": test_script,
            "tool_id": tool_id
        }, indent=2))

    elif command == "benchmark":
        # Run benchmark
        tool_code = input_data.get("tool_code", "")
        tool_id = input_data.get("tool_id", "unknown")
        test_input = input_data.get("test_input")

        result = optimizer.benchmark_tool(tool_code, tool_id, test_input)

        output = {
            "tool_id": result.tool_id,
            "success": result.success,
            "test_script": result.test_script
        }

        if result.success and result.best_run:
            output["best_run"] = asdict(result.best_run)
            output["all_runs"] = [asdict(run) for run in result.all_runs]
        else:
            output["error"] = result.error

        print(json.dumps(output, indent=2))

    elif command == "update_rag":
        # Update RAG metadata
        tool_id = input_data.get("tool_id", "unknown")

        # This expects benchmark results in input
        if "best_run" in input_data:
            best_run = PerformanceMetrics(**input_data["best_run"])
            all_runs = [PerformanceMetrics(**r) for r in input_data.get("all_runs", [])]

            result = BenchmarkResult(
                tool_id=tool_id,
                best_run=best_run,
                all_runs=all_runs,
                test_script=input_data.get("test_script", ""),
                success=True
            )

            success = optimizer.update_rag_metadata(tool_id, result)
            print(json.dumps({
                "success": success,
                "tool_id": tool_id,
                "message": "RAG metadata updated" if success else "Failed to update RAG"
            }))
        else:
            print(json.dumps({
                "success": False,
                "error": "Missing benchmark results in input"
            }))

    else:
        print(json.dumps({
            "error": f"Unknown command: {command}",
            "available_commands": ["generate", "benchmark", "update_rag"]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
