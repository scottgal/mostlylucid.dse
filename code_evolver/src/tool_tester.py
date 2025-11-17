#!/usr/bin/env python3
"""
Tool Tester - Discover and Run Tests for Tools

Automatically discovers and runs unit tests, integration tests,
and BDD tests for tools and their dependencies.

Features:
- Test discovery (unit, integration, BDD)
- Dependency testing
- Test result aggregation
- Coverage reporting

USAGE:
    from src.tool_tester import ToolTester

    tester = ToolTester(tools_manager)
    result = tester.test_tool("content_splitter", test_dependencies=True)
"""

import os
import sys
import json
import time
import subprocess
import importlib.util
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


@dataclass
class TestResult:
    """Result from a test run."""
    tool_name: str
    test_type: str  # unit, integration, bdd
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration: float
    errors: List[str]
    output: str


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    BDD = "bdd"
    FUNCTIONAL = "functional"


class ToolTester:
    """
    Discovers and runs tests for tools.

    Supports multiple test types and dependency testing.
    """

    def __init__(
        self,
        tools_manager,
        verbose: bool = True
    ):
        """
        Initialize tool tester.

        Args:
            tools_manager: Tools manager instance
            verbose: Whether to print progress
        """
        self.tools = tools_manager
        self.verbose = verbose

        self.test_dirs = [
            Path("tests"),
            Path("tests/unit"),
            Path("tests/integration"),
            Path("tests/bdd"),
            Path("tools/tests")
        ]

    def test_all_tools(self) -> List[Dict[str, Any]]:
        """
        Test all tools in the ecosystem.

        Returns:
            List of test results
        """
        results = []

        if self.verbose:
            print(f"\n[TEST] Testing {len(self.tools.tools)} tools...")

        for tool_id in self.tools.tools:
            try:
                result = self.test_tool(tool_id, test_dependencies=False)
                results.append(result)
            except Exception as e:
                if self.verbose:
                    print(f"[ERROR] Failed to test {tool_id}: {e}")
                results.append({
                    "tool_name": tool_id,
                    "passed": False,
                    "error": str(e)
                })

        return results

    def test_tool(
        self,
        tool_name: str,
        test_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Test a specific tool and optionally its dependencies.

        Steps:
        1. Discover tests for tool
        2. Run unit tests
        3. Run integration tests
        4. Run BDD tests
        5. If test_dependencies, test sub-tools
        6. Aggregate results

        Args:
            tool_name: Tool to test
            test_dependencies: Whether to test dependencies

        Returns:
            Test result
        """
        if self.verbose:
            print(f"\n[TEST] Testing tool: {tool_name}")

        # Get tool
        tool = self.tools.get_tool(tool_name)
        if not tool:
            return {
                "tool_name": tool_name,
                "passed": False,
                "error": "Tool not found"
            }

        start_time = time.time()

        # Discover tests
        tests = self._discover_tests(tool_name)

        if self.verbose:
            print(f"  Found {len(tests)} test file(s)")

        # Run tests
        test_results = []

        for test_file in tests:
            result = self._run_test_file(test_file, tool_name)
            test_results.append(result)

            if self.verbose:
                status = "PASS" if result.passed else "FAIL"
                print(f"  [{status}] {test_file.name}: {result.passed_tests}/{result.total_tests}")

        # Test dependencies if requested
        dependency_results = []
        if test_dependencies:
            dependencies = self._get_tool_dependencies(tool)

            if dependencies and self.verbose:
                print(f"  Testing {len(dependencies)} dependencies...")

            for dep in dependencies:
                dep_result = self.test_tool(dep, test_dependencies=False)
                dependency_results.append(dep_result)

        # Aggregate results
        duration = time.time() - start_time

        total_tests = sum(r.total_tests for r in test_results)
        passed_tests = sum(r.passed_tests for r in test_results)
        failed_tests = sum(r.failed_tests for r in test_results)

        all_passed = all(r.passed for r in test_results)

        if test_dependencies:
            all_passed = all_passed and all(r.get("passed", False) for r in dependency_results)

        return {
            "tool_name": tool_name,
            "passed": all_passed,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "duration": duration,
            "test_results": [self._result_to_dict(r) for r in test_results],
            "dependency_results": dependency_results
        }

    def _discover_tests(self, tool_name: str) -> List[Path]:
        """
        Discover test files for a tool.

        Looks for:
        - test_<tool_name>.py
        - test_<tool_name>_*.py
        - <tool_name>_test.py
        - <tool_name>.test.py

        Args:
            tool_name: Tool to find tests for

        Returns:
            List of test file paths
        """
        test_files = []

        # Normalize tool name
        normalized = tool_name.lower().replace(" ", "_")

        # Search patterns
        patterns = [
            f"test_{normalized}.py",
            f"test_{normalized}_*.py",
            f"{normalized}_test.py",
            f"{normalized}.test.py"
        ]

        for test_dir in self.test_dirs:
            if not test_dir.exists():
                continue

            for pattern in patterns:
                matches = list(test_dir.glob(pattern))
                test_files.extend(matches)

        return test_files

    def _run_test_file(self, test_file: Path, tool_name: str) -> TestResult:
        """
        Run a single test file.

        Args:
            test_file: Path to test file
            tool_name: Tool being tested

        Returns:
            Test result
        """
        start_time = time.time()

        # Determine test type
        test_type = self._determine_test_type(test_file)

        if self.verbose:
            print(f"    Running {test_type.value} test: {test_file.name}")

        # Run with pytest
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            output = result.stdout + result.stderr

            # Parse pytest output
            total, passed, failed = self._parse_pytest_output(output)

            return TestResult(
                tool_name=tool_name,
                test_type=test_type.value,
                passed=result.returncode == 0,
                total_tests=total,
                passed_tests=passed,
                failed_tests=failed,
                duration=time.time() - start_time,
                errors=self._extract_errors(output) if failed > 0 else [],
                output=output
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                tool_name=tool_name,
                test_type=test_type.value,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                duration=time.time() - start_time,
                errors=["Test timed out after 5 minutes"],
                output=""
            )

        except Exception as e:
            return TestResult(
                tool_name=tool_name,
                test_type=test_type.value,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                duration=time.time() - start_time,
                errors=[str(e)],
                output=""
            )

    def _determine_test_type(self, test_file: Path) -> TestType:
        """
        Determine test type from file path or name.

        Args:
            test_file: Test file path

        Returns:
            Test type
        """
        path_str = str(test_file).lower()

        if "integration" in path_str:
            return TestType.INTEGRATION
        elif "bdd" in path_str or "behave" in path_str:
            return TestType.BDD
        elif "functional" in path_str:
            return TestType.FUNCTIONAL
        else:
            return TestType.UNIT

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """
        Parse pytest output to extract test counts.

        Args:
            output: Pytest output

        Returns:
            (total, passed, failed)
        """
        import re

        # Look for summary line like "5 passed, 1 failed in 2.5s"
        match = re.search(r'(\d+) passed', output)
        passed = int(match.group(1)) if match else 0

        match = re.search(r'(\d+) failed', output)
        failed = int(match.group(1)) if match else 0

        total = passed + failed

        return (total, passed, failed)

    def _extract_errors(self, output: str) -> List[str]:
        """
        Extract error messages from test output.

        Args:
            output: Test output

        Returns:
            List of error messages
        """
        errors = []

        lines = output.split('\n')

        # Find FAILED lines
        for line in lines:
            if 'FAILED' in line or 'ERROR' in line:
                errors.append(line.strip())

        return errors[:10]  # Limit to first 10 errors

    def _get_tool_dependencies(self, tool: Any) -> List[str]:
        """
        Get dependencies for a tool.

        Args:
            tool: Tool to analyze

        Returns:
            List of dependency tool names
        """
        dependencies = set()

        # Check workflow steps
        if hasattr(tool, "workflow") and tool.workflow:
            steps = tool.workflow.get("steps", [])
            for step in steps:
                if isinstance(step, dict) and "tool" in step:
                    dependencies.add(step["tool"])

        # Check metadata
        if hasattr(tool, "metadata") and tool.metadata:
            deps = tool.metadata.get("dependencies", [])
            dependencies.update(deps)

        return list(dependencies)

    def _result_to_dict(self, result: TestResult) -> Dict[str, Any]:
        """
        Convert TestResult to dictionary.

        Args:
            result: Test result

        Returns:
            Dictionary representation
        """
        return {
            "tool_name": result.tool_name,
            "test_type": result.test_type,
            "passed": result.passed,
            "total_tests": result.total_tests,
            "passed_tests": result.passed_tests,
            "failed_tests": result.failed_tests,
            "duration": result.duration,
            "errors": result.errors
        }

    def create_test_template(self, tool_name: str, test_type: TestType = TestType.UNIT):
        """
        Create a test template for a tool.

        Args:
            tool_name: Tool to create test for
            test_type: Type of test
        """
        tool = self.tools.get_tool(tool_name)
        if not tool:
            print(f"Tool not found: {tool_name}")
            return

        # Determine test file path
        test_dir = Path("tests") / test_type.value
        test_dir.mkdir(parents=True, exist_ok=True)

        normalized = tool_name.lower().replace(" ", "_")
        test_file = test_dir / f"test_{normalized}.py"

        if test_file.exists():
            print(f"Test file already exists: {test_file}")
            return

        # Generate template
        template = self._generate_test_template(tool, test_type)

        # Write file
        with open(test_file, 'w') as f:
            f.write(template)

        print(f"Created test template: {test_file}")

    def _generate_test_template(self, tool: Any, test_type: TestType) -> str:
        """
        Generate test template content.

        Args:
            tool: Tool to test
            test_type: Test type

        Returns:
            Test template code
        """
        tool_name = tool.name.replace(" ", "_")

        if tool.type == "executable":
            return f'''#!/usr/bin/env python3
"""
{test_type.value.upper()} Tests for {tool.name}
"""

import pytest
import json
import subprocess


def test_{tool_name}_basic():
    """Test basic functionality."""
    input_data = {{
        # TODO: Add test input
    }}

    result = subprocess.run(
        ["python", "tools/executable/{tool_name}.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    # TODO: Add assertions


def test_{tool_name}_edge_cases():
    """Test edge cases."""
    # TODO: Implement edge case tests
    pass


def test_{tool_name}_error_handling():
    """Test error handling."""
    # TODO: Implement error handling tests
    pass
'''

        elif tool.type == "llm":
            return f'''#!/usr/bin/env python3
"""
{test_type.value.upper()} Tests for {tool.name}
"""

import pytest
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager
from src.ollama_client import OllamaClient


@pytest.fixture
def tools_manager():
    """Create tools manager."""
    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    return ToolsManager(config_manager=config, ollama_client=client)


def test_{tool_name}_basic(tools_manager):
    """Test basic functionality."""
    tool = tools_manager.get_tool("{tool_name}")
    assert tool is not None

    # TODO: Add test prompt
    prompt = "test prompt"

    # TODO: Execute and verify
    # result = tools_manager.execute_tool("{tool_name}", prompt)
    # assert result is not None


def test_{tool_name}_quality(tools_manager):
    """Test output quality."""
    # TODO: Implement quality tests
    pass
'''

        else:
            return f'''#!/usr/bin/env python3
"""
{test_type.value.upper()} Tests for {tool.name}
"""

import pytest


def test_{tool_name}_basic():
    """Test basic functionality."""
    # TODO: Implement test
    assert True


def test_{tool_name}_advanced():
    """Test advanced functionality."""
    # TODO: Implement test
    pass
'''


def main():
    """Test the tester."""
    from src.tools_manager import ToolsManager
    from src.config_manager import ConfigManager
    from src.ollama_client import OllamaClient
    from src.rag_memory import RAGMemory

    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    rag = RAGMemory(ollama_client=client)
    tools = ToolsManager(config_manager=config, rag_memory=rag, ollama_client=client)

    tester = ToolTester(tools, verbose=True)

    # Test specific tool
    result = tester.test_tool("content_splitter", test_dependencies=True)

    print("\n" + "="*60)
    print("TEST RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
