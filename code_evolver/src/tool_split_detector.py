"""
Tool Split Detector - Detects When Tool Versions Diverge Into Different Tools

This module identifies "tool splits" where different versions of a tool have
diverged so significantly that they're actually different tools:

1. Compares unit tests between versions
2. Compares specifications/interfaces
3. If differences exceed threshold, it's a split
4. Suggests new tool name
5. Creates deprecation pointer from old to new
6. Enables gradual migration while maintaining compatibility

Example of a split:
- parse_cron v1.0: Simple cron parser (returns dict)
- parse_cron v2.0: Advanced parser + validator + optimizer (returns CronSchedule object)

  These are fundamentally different tools! Should be:
  - parse_cron v1.0 (deprecated, points to parse_cron_simple)
  - parse_cron_advanced v1.0 (new tool)
  - parse_cron_simple v1.0 (renamed from v1.0)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import difflib
import json
import re

from .versioned_tool_manager import VersionedToolManager
from .tools_manager import Tool
from .rag_cluster_optimizer import ArtifactVariant

logger = logging.getLogger(__name__)


@dataclass
class TestSuite:
    """Represents a tool's test suite."""
    test_names: Set[str]  # Names of test functions
    test_code: str  # Full test code
    assertions: List[str]  # Assertion statements
    edge_cases: List[str]  # Edge case descriptions
    coverage: float  # Test coverage percentage


@dataclass
class ToolSpecification:
    """Represents a tool's specification."""
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    preconditions: List[str]
    postconditions: List[str]
    error_cases: List[str]
    performance_requirements: Dict[str, Any]
    behavioral_contracts: List[str]  # e.g., "must handle empty input"


@dataclass
class SplitEvidence:
    """Evidence that two versions should be split into different tools."""
    test_divergence: float  # 0.0-1.0, how different the tests are
    spec_divergence: float  # 0.0-1.0, how different the specs are
    behavioral_changes: List[str]  # Specific behavioral changes
    breaking_changes: List[str]  # Breaking API changes
    confidence: float  # Overall confidence this is a split (0.0-1.0)


@dataclass
class ToolSplit:
    """Represents a detected tool split."""
    original_tool_id: str
    original_version: str
    diverged_version: str
    evidence: SplitEvidence
    suggested_new_name: str  # Suggested name for the diverged version
    migration_strategy: str  # How to migrate users


@dataclass
class DeprecationPointer:
    """Pointer from deprecated tool to its replacement."""
    deprecated_tool_id: str
    replacement_tool_id: str
    reason: str
    migration_guide: str
    deprecation_date: str
    removal_date: Optional[str] = None


class ToolSplitDetector:
    """
    Detects when tool versions have diverged enough to be different tools.

    Uses multiple signals:
    1. Test suite comparison
    2. Specification comparison
    3. Behavioral contract changes
    4. Performance requirement changes
    """

    def __init__(
        self,
        tool_manager: VersionedToolManager,
        test_divergence_threshold: float = 0.4,
        spec_divergence_threshold: float = 0.3,
        split_confidence_threshold: float = 0.6
    ):
        """
        Initialize split detector.

        Args:
            tool_manager: Versioned tool manager
            test_divergence_threshold: Min test difference to consider split (0.4 = 40%)
            spec_divergence_threshold: Min spec difference to consider split (0.3 = 30%)
            split_confidence_threshold: Min overall confidence to declare split (0.6 = 60%)
        """
        self.tool_manager = tool_manager
        self.test_divergence_threshold = test_divergence_threshold
        self.spec_divergence_threshold = spec_divergence_threshold
        self.split_confidence_threshold = split_confidence_threshold

        # Cache of extracted tests and specs
        self.test_suites: Dict[str, TestSuite] = {}
        self.specifications: Dict[str, ToolSpecification] = {}

    def extract_test_suite(self, tool: Tool) -> TestSuite:
        """
        Extract test suite from tool metadata or associated test files.

        Args:
            tool: Tool to extract tests from

        Returns:
            TestSuite describing the tool's tests
        """
        if tool.tool_id in self.test_suites:
            return self.test_suites[tool.tool_id]

        metadata = tool.metadata

        # Extract from metadata if available
        test_code = metadata.get('test_code', '')
        test_names = set(metadata.get('test_names', []))
        assertions = metadata.get('assertions', [])
        edge_cases = metadata.get('edge_cases', [])
        coverage = metadata.get('test_coverage', 0.0)

        # If not in metadata, try to parse from content
        if not test_code and hasattr(tool, 'implementation'):
            test_code = self._find_associated_tests(tool)

        # Parse test code to extract information
        if test_code and not test_names:
            test_names = self._parse_test_names(test_code)

        if test_code and not assertions:
            assertions = self._parse_assertions(test_code)

        suite = TestSuite(
            test_names=test_names,
            test_code=test_code,
            assertions=assertions,
            edge_cases=edge_cases,
            coverage=coverage
        )

        self.test_suites[tool.tool_id] = suite
        return suite

    def _find_associated_tests(self, tool: Tool) -> str:
        """Find test files associated with a tool."""
        # Look for test files in standard locations
        # This is a simplified version - in practice, scan test directories
        test_patterns = [
            f"test_{tool.name}.py",
            f"test_{tool.tool_id}.py",
            f"{tool.name}_test.py"
        ]

        # Check if test files exist (simplified)
        for pattern in test_patterns:
            test_path = Path("tests") / pattern
            if test_path.exists():
                return test_path.read_text()

        return ""

    def _parse_test_names(self, test_code: str) -> Set[str]:
        """Parse test function names from test code."""
        test_names = set()

        # Find all test functions (def test_*)
        pattern = r'def\s+(test_\w+)\s*\('
        matches = re.findall(pattern, test_code)
        test_names.update(matches)

        return test_names

    def _parse_assertions(self, test_code: str) -> List[str]:
        """Parse assertion statements from test code."""
        assertions = []

        # Find assert statements
        lines = test_code.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('assert '):
                assertions.append(stripped)

        return assertions

    def extract_specification(self, tool: Tool) -> ToolSpecification:
        """
        Extract specification from tool metadata.

        Args:
            tool: Tool to extract spec from

        Returns:
            ToolSpecification describing the tool's contract
        """
        if tool.tool_id in self.specifications:
            return self.specifications[tool.tool_id]

        metadata = tool.metadata

        spec = ToolSpecification(
            input_schema=metadata.get('input_schema', tool.parameters or {}),
            output_schema=metadata.get('output_schema', {}),
            preconditions=metadata.get('preconditions', []),
            postconditions=metadata.get('postconditions', []),
            error_cases=metadata.get('error_cases', []),
            performance_requirements=metadata.get('performance_requirements', {}),
            behavioral_contracts=metadata.get('behavioral_contracts', [])
        )

        self.specifications[tool.tool_id] = spec
        return spec

    def compare_test_suites(
        self,
        suite1: TestSuite,
        suite2: TestSuite
    ) -> Tuple[float, List[str]]:
        """
        Compare two test suites and calculate divergence.

        Args:
            suite1: First test suite
            suite2: Second test suite

        Returns:
            (divergence_score, list_of_changes)
            divergence_score: 0.0 (identical) to 1.0 (completely different)
        """
        changes = []
        divergence_scores = []

        # 1. Compare test names (Jaccard distance)
        all_tests = suite1.test_names | suite2.test_names
        common_tests = suite1.test_names & suite2.test_names

        if all_tests:
            test_name_divergence = 1.0 - (len(common_tests) / len(all_tests))
            divergence_scores.append(test_name_divergence)

            added = suite2.test_names - suite1.test_names
            removed = suite1.test_names - suite2.test_names

            if added:
                changes.append(f"Added tests: {', '.join(list(added)[:5])}")
            if removed:
                changes.append(f"Removed tests: {', '.join(list(removed)[:5])}")

        # 2. Compare test code (using difflib)
        if suite1.test_code and suite2.test_code:
            matcher = difflib.SequenceMatcher(None, suite1.test_code, suite2.test_code)
            code_similarity = matcher.ratio()
            code_divergence = 1.0 - code_similarity
            divergence_scores.append(code_divergence)

            if code_divergence > 0.3:
                changes.append(f"Test implementation changed significantly ({code_divergence*100:.1f}%)")

        # 3. Compare assertions
        if suite1.assertions and suite2.assertions:
            all_assertions = set(suite1.assertions) | set(suite2.assertions)
            common_assertions = set(suite1.assertions) & set(suite2.assertions)

            if all_assertions:
                assertion_divergence = 1.0 - (len(common_assertions) / len(all_assertions))
                divergence_scores.append(assertion_divergence)

                if assertion_divergence > 0.4:
                    changes.append(f"Assertion logic changed significantly")

        # 4. Compare edge cases
        if suite1.edge_cases and suite2.edge_cases:
            all_edges = set(suite1.edge_cases) | set(suite2.edge_cases)
            common_edges = set(suite1.edge_cases) & set(suite2.edge_cases)

            if all_edges:
                edge_divergence = 1.0 - (len(common_edges) / len(all_edges))
                divergence_scores.append(edge_divergence)

        # Overall divergence (weighted average)
        if divergence_scores:
            overall_divergence = sum(divergence_scores) / len(divergence_scores)
        else:
            overall_divergence = 0.0

        return overall_divergence, changes

    def compare_specifications(
        self,
        spec1: ToolSpecification,
        spec2: ToolSpecification
    ) -> Tuple[float, List[str]]:
        """
        Compare two specifications and calculate divergence.

        Args:
            spec1: First specification
            spec2: Second specification

        Returns:
            (divergence_score, list_of_breaking_changes)
        """
        changes = []
        divergence_scores = []

        # 1. Compare input schemas
        input_divergence = self._compare_schemas(
            spec1.input_schema,
            spec2.input_schema
        )
        divergence_scores.append(input_divergence)

        if input_divergence > 0.2:
            changes.append(f"Input schema changed ({input_divergence*100:.1f}%)")

        # 2. Compare output schemas
        output_divergence = self._compare_schemas(
            spec1.output_schema,
            spec2.output_schema
        )
        divergence_scores.append(output_divergence)

        if output_divergence > 0.2:
            changes.append(f"Output schema changed ({output_divergence*100:.1f}%) - BREAKING")

        # 3. Compare preconditions
        if spec1.preconditions or spec2.preconditions:
            pre_divergence = self._compare_lists(
                spec1.preconditions,
                spec2.preconditions
            )
            divergence_scores.append(pre_divergence)

            if pre_divergence > 0.3:
                changes.append(f"Preconditions changed")

        # 4. Compare postconditions
        if spec1.postconditions or spec2.postconditions:
            post_divergence = self._compare_lists(
                spec1.postconditions,
                spec2.postconditions
            )
            divergence_scores.append(post_divergence)

            if post_divergence > 0.3:
                changes.append(f"Postconditions changed - behavior may differ")

        # 5. Compare error cases
        if spec1.error_cases or spec2.error_cases:
            error_divergence = self._compare_lists(
                spec1.error_cases,
                spec2.error_cases
            )
            divergence_scores.append(error_divergence)

            if error_divergence > 0.4:
                changes.append(f"Error handling changed")

        # Overall divergence
        if divergence_scores:
            overall_divergence = sum(divergence_scores) / len(divergence_scores)
        else:
            overall_divergence = 0.0

        return overall_divergence, changes

    def _compare_schemas(self, schema1: Dict, schema2: Dict) -> float:
        """Compare two JSON schemas and return divergence (0.0-1.0)."""
        if not schema1 and not schema2:
            return 0.0

        # Convert to sets of keys for comparison
        keys1 = set(schema1.keys()) if schema1 else set()
        keys2 = set(schema2.keys()) if schema2 else set()

        all_keys = keys1 | keys2
        if not all_keys:
            return 0.0

        # Jaccard distance
        common_keys = keys1 & keys2
        divergence = 1.0 - (len(common_keys) / len(all_keys))

        # Also check if types changed for common keys
        type_changes = 0
        for key in common_keys:
            type1 = schema1.get(key, {}).get('type') if isinstance(schema1.get(key), dict) else schema1.get(key)
            type2 = schema2.get(key, {}).get('type') if isinstance(schema2.get(key), dict) else schema2.get(key)

            if type1 != type2:
                type_changes += 1

        if common_keys:
            type_change_ratio = type_changes / len(common_keys)
            # Blend structure divergence with type change ratio
            divergence = (divergence + type_change_ratio) / 2

        return min(divergence, 1.0)

    def _compare_lists(self, list1: List[str], list2: List[str]) -> float:
        """Compare two lists and return divergence (Jaccard distance)."""
        set1 = set(list1) if list1 else set()
        set2 = set(list2) if list2 else set()

        all_items = set1 | set2
        if not all_items:
            return 0.0

        common_items = set1 & set2
        return 1.0 - (len(common_items) / len(all_items))

    def detect_split(
        self,
        tool_name: str,
        version1: str,
        version2: str
    ) -> Optional[ToolSplit]:
        """
        Detect if two versions of a tool should be split into separate tools.

        Args:
            tool_name: Base tool name
            version1: First version to compare
            version2: Second version to compare

        Returns:
            ToolSplit if split detected, None otherwise
        """
        # Get tools
        tool1 = self.tool_manager.get_tool_by_version(tool_name, version1)
        tool2 = self.tool_manager.get_tool_by_version(tool_name, version2)

        if not tool1 or not tool2:
            logger.warning(f"Could not find both versions of {tool_name}")
            return None

        # Extract tests and specs
        suite1 = self.extract_test_suite(tool1)
        suite2 = self.extract_test_suite(tool2)

        spec1 = self.extract_specification(tool1)
        spec2 = self.extract_specification(tool2)

        # Compare
        test_divergence, test_changes = self.compare_test_suites(suite1, suite2)
        spec_divergence, spec_changes = self.compare_specifications(spec1, spec2)

        # Calculate confidence that this is a split
        # Higher divergence = higher confidence
        confidence_factors = []

        if test_divergence >= self.test_divergence_threshold:
            confidence_factors.append(test_divergence)

        if spec_divergence >= self.spec_divergence_threshold:
            confidence_factors.append(spec_divergence * 1.2)  # Spec changes weighted higher

        if not confidence_factors:
            return None  # Not enough evidence

        confidence = min(sum(confidence_factors) / len(confidence_factors), 1.0)

        if confidence < self.split_confidence_threshold:
            return None  # Not confident enough

        # We have a split! Create the split object
        evidence = SplitEvidence(
            test_divergence=test_divergence,
            spec_divergence=spec_divergence,
            behavioral_changes=test_changes,
            breaking_changes=spec_changes,
            confidence=confidence
        )

        # Suggest a new name based on the divergence
        suggested_name = self._suggest_new_name(tool_name, tool2, spec_changes)

        # Determine migration strategy
        migration_strategy = self._determine_migration_strategy(evidence)

        split = ToolSplit(
            original_tool_id=tool1.tool_id,
            original_version=version1,
            diverged_version=version2,
            evidence=evidence,
            suggested_new_name=suggested_name,
            migration_strategy=migration_strategy
        )

        logger.info(
            f"🔀 Split detected: {tool_name} v{version1} vs v{version2}\n"
            f"   Test divergence: {test_divergence*100:.1f}%\n"
            f"   Spec divergence: {spec_divergence*100:.1f}%\n"
            f"   Confidence: {confidence*100:.1f}%\n"
            f"   Suggested name: {suggested_name}"
        )

        return split

    def _suggest_new_name(
        self,
        base_name: str,
        tool: Tool,
        breaking_changes: List[str]
    ) -> str:
        """
        Suggest a new name for the diverged tool.

        Args:
            base_name: Original tool name
            tool: The diverged tool
            breaking_changes: List of breaking changes

        Returns:
            Suggested new name
        """
        # Analyze breaking changes to suggest appropriate suffix
        change_text = ' '.join(breaking_changes).lower()

        if 'advanced' in tool.description.lower() or 'enhanced' in tool.description.lower():
            return f"{base_name}_advanced"
        elif 'simple' in tool.description.lower() or 'basic' in tool.description.lower():
            return f"{base_name}_simple"
        elif 'async' in change_text or 'asynchronous' in change_text:
            return f"{base_name}_async"
        elif 'optimized' in change_text or 'fast' in change_text:
            return f"{base_name}_optimized"
        elif 'output' in change_text and 'changed' in change_text:
            return f"{base_name}_v2"  # Generic v2 suffix
        else:
            # Default: append version number
            return f"{base_name}_v{tool.version.split('.')[0]}"

    def _determine_migration_strategy(self, evidence: SplitEvidence) -> str:
        """
        Determine the best migration strategy based on evidence.

        Args:
            evidence: Evidence for the split

        Returns:
            Migration strategy description
        """
        if evidence.spec_divergence > 0.6:
            return "hard_fork"  # Complete rewrite, manual migration needed
        elif evidence.spec_divergence > 0.4:
            return "compatibility_layer"  # Add adapter/wrapper for old API
        else:
            return "gradual_deprecation"  # Slowly migrate over time

    def scan_all_versions(self) -> List[ToolSplit]:
        """
        Scan all tool versions to detect splits.

        Returns:
            List of detected splits
        """
        splits = []

        version_clusters = self.tool_manager.list_version_clusters()

        for tool_name, versions in version_clusters.items():
            if len(versions) < 2:
                continue

            # Compare each version with the next
            for i in range(len(versions) - 1):
                v1 = versions[i + 1]  # Older version (reversed list)
                v2 = versions[i]  # Newer version

                split = self.detect_split(tool_name, v1, v2)
                if split:
                    splits.append(split)

        return splits

    def create_deprecation_pointer(
        self,
        split: ToolSplit
    ) -> DeprecationPointer:
        """
        Create a deprecation pointer from old tool to new.

        Args:
            split: Detected tool split

        Returns:
            DeprecationPointer
        """
        from datetime import datetime, timedelta

        deprecation_date = datetime.now().isoformat()
        # Set removal date 6 months in future
        removal_date = (datetime.now() + timedelta(days=180)).isoformat()

        migration_guide = self._generate_migration_guide(split)

        pointer = DeprecationPointer(
            deprecated_tool_id=split.original_tool_id,
            replacement_tool_id=split.suggested_new_name,
            reason=f"Tool has diverged significantly ({split.evidence.confidence*100:.0f}% confidence)",
            migration_guide=migration_guide,
            deprecation_date=deprecation_date,
            removal_date=removal_date
        )

        return pointer

    def _generate_migration_guide(self, split: ToolSplit) -> str:
        """Generate migration guide for users."""
        lines = [
            f"Migration Guide: {split.original_tool_id} → {split.suggested_new_name}",
            "",
            "## Changes:",
        ]

        for change in split.evidence.breaking_changes[:5]:
            lines.append(f"  - {change}")

        lines.extend([
            "",
            "## Migration Steps:",
            f"1. Replace calls to '{split.original_tool_id}' with '{split.suggested_new_name}'",
            "2. Update parameters if schema changed",
            "3. Update tests to match new behavior",
            "4. Run validation tests",
            "",
            f"## Strategy: {split.migration_strategy}"
        ])

        return "\n".join(lines)
