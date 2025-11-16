#!/usr/bin/env python3
"""
Tool Validator - Validates tool definitions against standards.

Checks for:
- Required metadata fields
- Schema consistency
- Documentation quality
- Example validity
- Naming conventions
"""

import yaml
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any


class ToolValidator:
    """Validates tool definitions against standards."""

    REQUIRED_FIELDS = ["name", "type", "description", "version"]
    REQUIRED_METADATA = ["cost_tier", "speed_tier", "quality_tier", "priority"]
    REQUIRED_CONSTRAINTS = ["timeout_ms", "max_memory_mb"]

    VALID_COST_TIERS = ["free", "low", "medium", "high", "variable"]
    VALID_SPEED_TIERS = ["very-fast", "fast", "medium", "slow"]
    VALID_QUALITY_TIERS = ["basic", "good", "excellent", "perfect"]

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_tool(self, tool_path: Path) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a single tool definition.

        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Load tool
        try:
            with open(tool_path) as f:
                tool = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load YAML: {e}")
            return False, self.errors, self.warnings

        # Run validation checks
        self._check_required_fields(tool)
        self._check_metadata(tool)
        self._check_constraints(tool)
        self._check_schemas(tool)
        self._check_documentation(tool)
        self._check_examples(tool)
        self._check_tags(tool)
        self._check_version(tool)

        is_valid = len(self.errors) == 0

        return is_valid, self.errors, self.warnings

    def _check_required_fields(self, tool: Dict):
        """Check required top-level fields."""
        for field in self.REQUIRED_FIELDS:
            if field not in tool:
                self.errors.append(f"Missing required field: {field}")

    def _check_metadata(self, tool: Dict):
        """Check performance metadata."""
        for field in self.REQUIRED_METADATA:
            if field not in tool:
                self.warnings.append(f"Missing metadata field: {field}")

        # Validate tier values
        if "cost_tier" in tool and tool["cost_tier"] not in self.VALID_COST_TIERS:
            self.errors.append(f"Invalid cost_tier: {tool['cost_tier']}")

        if "speed_tier" in tool and tool["speed_tier"] not in self.VALID_SPEED_TIERS:
            self.errors.append(f"Invalid speed_tier: {tool['speed_tier']}")

        if "quality_tier" in tool and tool["quality_tier"] not in self.VALID_QUALITY_TIERS:
            self.errors.append(f"Invalid quality_tier: {tool['quality_tier']}")

        # Validate priority
        if "priority" in tool:
            if not isinstance(tool["priority"], int) or not (1 <= tool["priority"] <= 200):
                self.errors.append("priority must be integer between 1-200")

    def _check_constraints(self, tool: Dict):
        """Check resource constraints."""
        if "constraints" not in tool:
            self.warnings.append("Missing 'constraints' section")
            return

        constraints = tool["constraints"]
        for field in self.REQUIRED_CONSTRAINTS:
            if field not in constraints:
                self.warnings.append(f"Missing constraint: {field}")

    def _check_schemas(self, tool: Dict):
        """Check input/output schemas."""
        if "input_schema" not in tool:
            self.warnings.append("Missing input_schema")
        else:
            schema = tool["input_schema"]
            if "type" not in schema or "properties" not in schema:
                self.errors.append("input_schema must have 'type' and 'properties'")

        if "output_schema" not in tool:
            self.warnings.append("Missing output_schema")

    def _check_documentation(self, tool: Dict):
        """Check documentation quality."""
        description = tool.get("description", "")
        if len(description) < 20:
            self.errors.append("description too short (minimum 20 characters)")

        if len(description) > 500:
            self.warnings.append("description very long (>500 characters)")

        # Check for usage notes in complex tools
        tool_type = tool.get("type", "")
        if tool_type in ["llm", "custom", "openapi"]:
            if "usage_notes" not in tool:
                self.warnings.append("Complex tools should have usage_notes")

    def _check_examples(self, tool: Dict):
        """Check examples are provided and valid."""
        if "examples" not in tool:
            self.warnings.append("No examples provided")
            return

        examples = tool["examples"]
        if not isinstance(examples, list) or len(examples) == 0:
            self.warnings.append("examples should be non-empty list")
            return

        for i, example in enumerate(examples):
            if not isinstance(example, dict):
                self.errors.append(f"Example {i}: should be a dictionary")
                continue

            if "input" not in example:
                self.errors.append(f"Example {i}: missing 'input'")

            if "output" not in example:
                self.warnings.append(f"Example {i}: missing 'output'")

    def _check_tags(self, tool: Dict):
        """Check tags are provided."""
        if "tags" not in tool:
            self.warnings.append("No tags provided")
        elif not isinstance(tool["tags"], list) or len(tool["tags"]) == 0:
            self.warnings.append("tags should be non-empty list")

    def _check_version(self, tool: Dict):
        """Check version format."""
        if "version" not in tool:
            return

        version = tool["version"]
        parts = version.split(".")
        if len(parts) != 3:
            self.errors.append(f"version should be semver (X.Y.Z), got: {version}")
        else:
            try:
                for part in parts:
                    int(part)
            except ValueError:
                self.errors.append(f"version parts should be integers: {version}")

    def validate_all_tools(self, tools_dir: str = "tools_optimized") -> Dict[str, List]:
        """
        Validate all tools in directory.

        Returns:
            Dictionary of {tool_path: (is_valid, errors, warnings)}
        """
        results = {}
        tools_path = Path(tools_dir)

        for category in ["executable", "llm", "custom", "openapi"]:
            category_path = tools_path / category
            if not category_path.exists():
                continue

            for tool_file in category_path.glob("*.yaml"):
                is_valid, errors, warnings = self.validate_tool(tool_file)
                if not is_valid or errors or warnings:
                    results[str(tool_file)] = (is_valid, errors, warnings)

        return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate tool definitions")
    parser.add_argument("--dir", default="tools_optimized", help="Tools directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    validator = ToolValidator()
    results = validator.validate_all_tools(args.dir)

    if not results:
        print("✓ All tools validated successfully!")
        return 0

    # Print results
    print("Tool Validation Results:\n")

    error_count = 0
    warning_count = 0

    for tool_path, (is_valid, errors, warnings) in results.items():
        print(f"\n{tool_path}:")

        if errors:
            error_count += len(errors)
            for error in errors:
                print(f"  ✗ ERROR: {error}")

        if warnings:
            warning_count += len(warnings)
            for warning in warnings:
                print(f"  ⚠ WARNING: {warning}")

    print(f"\n{'='*70}")
    print(f"Summary: {error_count} errors, {warning_count} warnings")

    if error_count > 0:
        print("❌ Validation FAILED")
        return 1
    elif warning_count > 0 and args.strict:
        print("❌ Validation FAILED (warnings in strict mode)")
        return 1
    else:
        print("✓ Validation PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
