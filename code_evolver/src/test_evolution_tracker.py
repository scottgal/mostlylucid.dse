"""
Test Evolution Tracker - Ensures test coverage only increases during optimization.

Tracks test changes across evolution and ensures that useful tests are preserved
and coverage is never reduced.
"""
import logging
import difflib
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class TestEvolutionTracker:
    """
    Tracks test evolution to ensure coverage improvements.

    Analyzes test changes between versions and generates guidance for
    maintaining or improving test coverage during evolution.
    """

    def __init__(self):
        """Initialize test evolution tracker."""
        pass

    def extract_test_changes(
        self,
        old_test_code: str,
        new_test_code: str
    ) -> Dict[str, Any]:
        """
        Extract meaningful changes between old and new test code.

        Args:
            old_test_code: Original test code
            new_test_code: New test code

        Returns:
            Dictionary with test changes analysis
        """
        # Generate unified diff
        diff = list(difflib.unified_diff(
            old_test_code.splitlines(keepends=True),
            new_test_code.splitlines(keepends=True),
            fromfile='old_tests',
            tofile='new_tests',
            lineterm=''
        ))

        # Analyze changes
        added_lines = [line for line in diff if line.startswith('+') and not line.startswith('+++')]
        removed_lines = [line for line in diff if line.startswith('-') and not line.startswith('---')]

        # Detect test function changes
        old_test_functions = self._extract_test_functions(old_test_code)
        new_test_functions = self._extract_test_functions(new_test_code)

        added_tests = set(new_test_functions) - set(old_test_functions)
        removed_tests = set(old_test_functions) - set(new_test_functions)
        preserved_tests = set(old_test_functions) & set(new_test_functions)

        return {
            "diff": ''.join(diff),
            "added_lines_count": len(added_lines),
            "removed_lines_count": len(removed_lines),
            "added_test_functions": list(added_tests),
            "removed_test_functions": list(removed_tests),
            "preserved_test_functions": list(preserved_tests),
            "total_old_tests": len(old_test_functions),
            "total_new_tests": len(new_test_functions),
            "coverage_change": len(new_test_functions) - len(old_test_functions)
        }

    def _extract_test_functions(self, test_code: str) -> List[str]:
        """
        Extract test function names from test code.

        Args:
            test_code: Test code to analyze

        Returns:
            List of test function names
        """
        import re
        # Match test functions (e.g., def test_something(...):)
        pattern = r'^\s*def\s+(test_\w+)\s*\('
        matches = re.findall(pattern, test_code, re.MULTILINE)
        return matches

    def analyze_test_coverage(
        self,
        old_test_code: str,
        new_test_code: str,
        old_tool_code: str,
        new_tool_code: str
    ) -> Dict[str, Any]:
        """
        Analyze test coverage changes between versions.

        Args:
            old_test_code: Original test code
            new_test_code: New test code
            old_tool_code: Original tool code
            new_tool_code: New tool code

        Returns:
            Coverage analysis results
        """
        test_changes = self.extract_test_changes(old_test_code, new_test_code)

        # Analyze if coverage decreased
        coverage_decreased = test_changes["coverage_change"] < 0
        tests_removed = len(test_changes["removed_test_functions"]) > 0

        # Extract functions from tool code
        old_functions = self._extract_functions(old_tool_code)
        new_functions = self._extract_functions(new_tool_code)

        added_functions = set(new_functions) - set(old_functions)

        # Check if new functions need tests
        new_functions_without_tests = []
        for func in added_functions:
            # Check if there's a corresponding test
            test_name = f"test_{func}"
            if test_name not in test_changes["added_test_functions"]:
                new_functions_without_tests.append(func)

        return {
            "coverage_decreased": coverage_decreased,
            "tests_removed": tests_removed,
            "test_changes": test_changes,
            "new_functions_without_tests": new_functions_without_tests,
            "old_function_count": len(old_functions),
            "new_function_count": len(new_functions),
            "coverage_adequate": not coverage_decreased and len(new_functions_without_tests) == 0
        }

    def _extract_functions(self, code: str) -> List[str]:
        """
        Extract function names from code.

        Args:
            code: Code to analyze

        Returns:
            List of function names
        """
        import re
        # Match function definitions (excluding private functions starting with _)
        pattern = r'^\s*def\s+([a-z]\w*)\s*\('
        matches = re.findall(pattern, code, re.MULTILINE)
        # Filter out test functions and private functions
        return [m for m in matches if not m.startswith('test_') and not m.startswith('_')]

    def generate_test_improvement_prompt(
        self,
        old_test_code: str,
        new_test_code: str,
        old_tool_code: str,
        new_tool_code: str,
        coverage_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a prompt to guide test improvement during evolution.

        Args:
            old_test_code: Original test code
            new_test_code: New test code
            old_tool_code: Original tool code
            new_tool_code: New tool code
            coverage_analysis: Optional pre-computed coverage analysis

        Returns:
            Formatted prompt for test improvement
        """
        if coverage_analysis is None:
            coverage_analysis = self.analyze_test_coverage(
                old_test_code, new_test_code, old_tool_code, new_tool_code
            )

        test_changes = coverage_analysis["test_changes"]

        prompt_lines = [
            "## Test Coverage Requirements",
            "",
            "You MUST ensure that test coverage only increases, never decreases.",
            ""
        ]

        # Report current state
        if coverage_analysis["coverage_decreased"]:
            prompt_lines.append("⚠️ **WARNING: Test coverage has DECREASED!**")
            prompt_lines.append(f"- Old tests: {test_changes['total_old_tests']}")
            prompt_lines.append(f"- New tests: {test_changes['total_new_tests']}")
            prompt_lines.append(f"- Change: {test_changes['coverage_change']}")
            prompt_lines.append("")

        if test_changes["removed_test_functions"]:
            prompt_lines.append("### Tests Removed (MUST be restored or replaced):")
            for test in test_changes["removed_test_functions"]:
                prompt_lines.append(f"- {test}")
            prompt_lines.append("")

        if test_changes["preserved_test_functions"]:
            prompt_lines.append("### Tests Preserved (Good!):")
            prompt_lines.append(f"- {len(test_changes['preserved_test_functions'])} tests maintained")
            prompt_lines.append("")

        if test_changes["added_test_functions"]:
            prompt_lines.append("### New Tests Added:")
            for test in test_changes["added_test_functions"]:
                prompt_lines.append(f"- {test}")
            prompt_lines.append("")

        if coverage_analysis["new_functions_without_tests"]:
            prompt_lines.append("### Functions Missing Tests:")
            for func in coverage_analysis["new_functions_without_tests"]:
                prompt_lines.append(f"- {func} (needs test_{func})")
            prompt_lines.append("")

        # Add requirements
        prompt_lines.extend([
            "### Requirements:",
            "1. **Restore** any removed tests or replace them with equivalent coverage",
            "2. **Add tests** for all new functions",
            "3. **Maintain** all existing test coverage",
            "4. **Ensure** total test count >= original test count",
            "5. **Preserve** useful test cases from the original suite",
            ""
        ])

        # Add context
        if test_changes["diff"]:
            prompt_lines.extend([
                "### Test Changes Diff:",
                "```diff",
                test_changes["diff"],
                "```",
                ""
            ])

        return "\n".join(prompt_lines)

    def validate_test_evolution(
        self,
        old_test_code: str,
        new_test_code: str,
        old_tool_code: str,
        new_tool_code: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate that test evolution meets requirements.

        Args:
            old_test_code: Original test code
            new_test_code: New test code
            old_tool_code: Original tool code
            new_tool_code: New tool code

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        coverage_analysis = self.analyze_test_coverage(
            old_test_code, new_test_code, old_tool_code, new_tool_code
        )

        issues = []

        # Check if coverage decreased
        if coverage_analysis["coverage_decreased"]:
            issues.append(
                f"Test coverage decreased by {abs(coverage_analysis['test_changes']['coverage_change'])} tests"
            )

        # Check if tests were removed
        if coverage_analysis["test_changes"]["removed_test_functions"]:
            removed = coverage_analysis["test_changes"]["removed_test_functions"]
            issues.append(
                f"Tests removed without replacement: {', '.join(removed)}"
            )

        # Check if new functions have tests
        if coverage_analysis["new_functions_without_tests"]:
            missing = coverage_analysis["new_functions_without_tests"]
            issues.append(
                f"New functions without tests: {', '.join(missing)}"
            )

        is_valid = len(issues) == 0

        return is_valid, issues

    def merge_test_suites(
        self,
        old_test_code: str,
        new_test_code: str,
        prefer_new: bool = True
    ) -> str:
        """
        Merge two test suites, preserving the best from both.

        Args:
            old_test_code: Original test code
            new_test_code: New test code
            prefer_new: If True, prefer new tests on conflicts

        Returns:
            Merged test code
        """
        old_functions = self._extract_test_functions(old_test_code)
        new_functions = self._extract_test_functions(new_test_code)

        # Start with the preferred suite
        if prefer_new:
            base_code = new_test_code
            missing_functions = set(old_functions) - set(new_functions)
            source_code = old_test_code
        else:
            base_code = old_test_code
            missing_functions = set(new_functions) - set(old_functions)
            source_code = new_test_code

        # Extract missing test function implementations
        for func_name in missing_functions:
            func_impl = self._extract_function_implementation(source_code, func_name)
            if func_impl:
                # Append to base code
                base_code += "\n\n" + func_impl

        return base_code

    def _extract_function_implementation(self, code: str, function_name: str) -> Optional[str]:
        """
        Extract the full implementation of a function from code.

        Args:
            code: Source code
            function_name: Name of function to extract

        Returns:
            Function implementation or None if not found
        """
        import re

        # Find the function definition
        pattern = rf'^\s*def\s+{re.escape(function_name)}\s*\([^)]*\):'
        lines = code.split('\n')

        func_start = None
        for i, line in enumerate(lines):
            if re.match(pattern, line):
                func_start = i
                break

        if func_start is None:
            return None

        # Extract function body (until next function or end of file)
        func_lines = [lines[func_start]]
        indent = len(lines[func_start]) - len(lines[func_start].lstrip())

        for i in range(func_start + 1, len(lines)):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                func_lines.append(line)
                continue

            # Check if we've hit another function at same or higher level
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= indent and line.strip().startswith('def '):
                break

            func_lines.append(line)

        return '\n'.join(func_lines)
