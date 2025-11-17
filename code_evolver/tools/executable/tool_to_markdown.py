#!/usr/bin/env python3
"""
Tool to Markdown Documentation Generator

Generates comprehensive markdown documentation from tool definitions.
Recursively follows and documents all referenced subtools.

Features:
- Reads tool definitions from tools/index.json
- Recursively documents subtools
- Generates well-formatted markdown
- Security guardrails (output only to 'output/' directory)
- Handles LLM, executable, and workflow tool types

Input:
{
    "tool_id": "tool_name",  # required
    "output_file": "relative/path/in/output/dir.md",  # required
    "include_subtools": true,  # optional, default: true
    "max_depth": 3  # optional, default: 3 (prevent infinite recursion)
}

Output:
{
    "file_path": "output/relative/path.md",
    "tools_documented": ["tool1", "tool2"],
    "success": true
}
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import logging

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolToMarkdownGenerator:
    """Generates markdown documentation from tool definitions."""

    def __init__(self, tools_index_path: Path):
        """Initialize with tools index."""
        self.tools_index_path = tools_index_path
        self.tools_index = self._load_tools_index()
        self.documented_tools: Set[str] = set()

    def _load_tools_index(self) -> Dict[str, Any]:
        """Load tools index from JSON file."""
        try:
            with open(self.tools_index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tools index: {e}")
            return {}

    def validate_output_path(self, output_file: str, base_dir: str = "output") -> Path:
        """
        Validate and secure output file path.

        Security guardrails:
        - Must be under output/ directory
        - Cannot use .. to escape
        - Cannot use absolute paths outside output/
        - Must have .md extension

        Args:
            output_file: Requested output file path
            base_dir: Base directory (default: output)

        Returns:
            Validated absolute Path

        Raises:
            ValueError: If path is invalid or insecure
        """
        # Ensure base_dir exists
        base_path = Path(base_dir).resolve()
        base_path.mkdir(parents=True, exist_ok=True)

        # Clean the output_file path
        output_file = output_file.strip()

        # Remove leading slashes (no absolute paths allowed)
        while output_file.startswith('/'):
            output_file = output_file[1:]

        # Resolve the full path
        full_path = (base_path / output_file).resolve()

        # Security check: ensure the resolved path is under base_dir
        try:
            full_path.relative_to(base_path)
        except ValueError:
            raise ValueError(
                f"Security violation: Output path must be under {base_dir}/ directory. "
                f"Attempted path: {output_file}"
            )

        # Ensure .md extension
        if not full_path.suffix == '.md':
            raise ValueError(
                f"Invalid file extension. Only .md files allowed. "
                f"Got: {full_path.suffix}"
            )

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Validated output path: {full_path}")
        return full_path

    def get_tool_definition(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool definition from index."""
        return self.tools_index.get(tool_id)

    def extract_subtools(self, tool_def: Dict[str, Any]) -> List[str]:
        """
        Extract referenced subtools from a tool definition.

        Args:
            tool_def: Tool definition dictionary

        Returns:
            List of subtool IDs
        """
        subtools = []

        # Check for subtools in various locations
        metadata = tool_def.get("metadata", {})

        # Check for workflow steps (workflows may reference other tools)
        if "steps" in metadata:
            for step in metadata["steps"]:
                if isinstance(step, dict) and "tool" in step:
                    subtools.append(step["tool"])

        # Check for dependencies
        if "dependencies" in metadata:
            deps = metadata["dependencies"]
            if isinstance(deps, list):
                subtools.extend(deps)

        # Check for called_tools
        if "called_tools" in metadata:
            called = metadata["called_tools"]
            if isinstance(called, list):
                subtools.extend(called)

        return list(set(subtools))  # Remove duplicates

    def tool_to_markdown(
        self,
        tool_id: str,
        depth: int = 0,
        max_depth: int = 3,
        include_subtools: bool = True
    ) -> str:
        """
        Convert a tool definition to markdown documentation.

        Args:
            tool_id: Tool identifier
            depth: Current recursion depth
            max_depth: Maximum recursion depth
            include_subtools: Whether to include subtool documentation

        Returns:
            Markdown formatted documentation
        """
        # Prevent infinite recursion
        if depth > max_depth:
            return f"*Maximum documentation depth reached for {tool_id}*\n\n"

        # Prevent duplicate documentation
        if tool_id in self.documented_tools:
            return f"*See documentation for `{tool_id}` above*\n\n"

        # Get tool definition
        tool_def = self.get_tool_definition(tool_id)
        if not tool_def:
            return f"*Tool `{tool_id}` not found in registry*\n\n"

        # Mark as documented
        self.documented_tools.add(tool_id)

        # Build markdown
        md_lines = []

        # Header
        indent = "#" * (depth + 1)
        tool_name = tool_def.get("name", tool_id)
        md_lines.append(f"{indent} {tool_name}")
        md_lines.append("")

        # Tool ID and Type
        tool_type = tool_def.get("tool_type", "unknown")
        md_lines.append(f"**Tool ID:** `{tool_id}`  ")
        md_lines.append(f"**Type:** `{tool_type}`  ")
        md_lines.append("")

        # Description
        description = tool_def.get("description", "No description available")
        md_lines.append("## Description")
        md_lines.append("")
        md_lines.append(description)
        md_lines.append("")

        # Tags
        tags = tool_def.get("tags", [])
        if tags:
            md_lines.append("## Tags")
            md_lines.append("")
            md_lines.append(", ".join(f"`{tag}`" for tag in tags))
            md_lines.append("")

        # Parameters
        parameters = tool_def.get("parameters", {})
        if parameters:
            md_lines.append("## Parameters")
            md_lines.append("")
            for param_name, param_info in parameters.items():
                if isinstance(param_info, dict):
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    required = param_info.get("required", False)
                    req_label = " *(required)*" if required else " *(optional)*"
                    md_lines.append(f"- **`{param_name}`** ({param_type}){req_label}: {param_desc}")
                else:
                    md_lines.append(f"- **`{param_name}`**: {param_info}")
            md_lines.append("")

        # Metadata
        metadata = tool_def.get("metadata", {})
        if metadata:
            md_lines.append("## Metadata")
            md_lines.append("")

            # Version
            version = metadata.get("version", tool_def.get("version", "unknown"))
            md_lines.append(f"- **Version:** {version}")

            # Cost tier
            if "cost_tier" in metadata:
                md_lines.append(f"- **Cost Tier:** {metadata['cost_tier']}")

            # Speed tier
            if "speed_tier" in metadata:
                md_lines.append(f"- **Speed Tier:** {metadata['speed_tier']}")

            # Quality tier
            if "quality_tier" in metadata:
                md_lines.append(f"- **Quality Tier:** {metadata['quality_tier']}")

            # Command (for executable tools)
            if "command" in metadata:
                command = metadata["command"]
                args = metadata.get("args", [])
                full_command = f"{command} {' '.join(args)}" if args else command
                md_lines.append(f"- **Command:** `{full_command}`")

            md_lines.append("")

        # Usage statistics
        usage = tool_def.get("current_usage", {})
        if usage and usage.get("calls_count", 0) > 0:
            md_lines.append("## Usage Statistics")
            md_lines.append("")
            md_lines.append(f"- **Total Calls:** {usage.get('calls_count', 0)}")
            md_lines.append(f"- **Storage (MB):** {usage.get('storage_mb', 0):.2f}")
            md_lines.append(f"- **Memory (MB):** {usage.get('memory_mb', 0):.2f}")
            md_lines.append("")

        # Constraints
        constraints = tool_def.get("constraints", {})
        if constraints:
            md_lines.append("## Constraints")
            md_lines.append("")
            for constraint_name, constraint_value in constraints.items():
                md_lines.append(f"- **{constraint_name}:** {constraint_value}")
            md_lines.append("")

        # Extract and document subtools
        if include_subtools:
            subtools = self.extract_subtools(tool_def)
            if subtools:
                md_lines.append("## Referenced Tools")
                md_lines.append("")
                md_lines.append(f"This tool references {len(subtools)} subtool(s):")
                md_lines.append("")
                for subtool in subtools:
                    md_lines.append(f"- `{subtool}`")
                md_lines.append("")

                # Recursively document subtools
                md_lines.append("### Subtool Documentation")
                md_lines.append("")
                for subtool in subtools:
                    subtool_md = self.tool_to_markdown(
                        subtool,
                        depth=depth + 1,
                        max_depth=max_depth,
                        include_subtools=include_subtools
                    )
                    md_lines.append(subtool_md)

        # Separator
        md_lines.append("---")
        md_lines.append("")

        return "\n".join(md_lines)

    def generate_documentation(
        self,
        tool_id: str,
        include_subtools: bool = True,
        max_depth: int = 3
    ) -> str:
        """
        Generate complete documentation for a tool.

        Args:
            tool_id: Tool identifier
            include_subtools: Whether to include subtool documentation
            max_depth: Maximum recursion depth

        Returns:
            Complete markdown documentation
        """
        # Reset documented tools tracker
        self.documented_tools.clear()

        # Generate header
        md_lines = [
            f"# Tool Documentation: {tool_id}",
            "",
            f"*Auto-generated documentation*",
            "",
            f"**Generated:** {self._get_timestamp()}",
            "",
            "---",
            ""
        ]

        # Generate tool documentation
        tool_md = self.tool_to_markdown(
            tool_id,
            depth=0,
            max_depth=max_depth,
            include_subtools=include_subtools
        )

        md_lines.append(tool_md)

        # Add summary footer
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        md_lines.append(f"**Total tools documented:** {len(self.documented_tools)}")
        md_lines.append("")
        md_lines.append("**Tools list:**")
        for documented_tool in sorted(self.documented_tools):
            md_lines.append(f"- `{documented_tool}`")

        return "\n".join(md_lines)

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()


def main():
    """Main entry point."""
    try:
        # Read input
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "error": f"Invalid JSON input: {str(e)}",
                "success": False
            }))
            sys.exit(1)

        # Extract parameters
        tool_id = input_data.get("tool_id")
        if not tool_id:
            print(json.dumps({
                "error": "Missing required parameter: tool_id",
                "success": False
            }))
            sys.exit(1)

        output_file = input_data.get("output_file")
        if not output_file:
            print(json.dumps({
                "error": "Missing required parameter: output_file",
                "success": False
            }))
            sys.exit(1)

        include_subtools = input_data.get("include_subtools", True)
        max_depth = input_data.get("max_depth", 3)

        # Initialize generator
        tools_index_path = Path(__file__).parent.parent / "index.json"

        if not tools_index_path.exists():
            print(json.dumps({
                "error": f"Tools index not found at: {tools_index_path}",
                "success": False
            }))
            sys.exit(1)

        generator = ToolToMarkdownGenerator(tools_index_path)

        # Validate output path (security check)
        try:
            validated_path = generator.validate_output_path(output_file)
        except ValueError as e:
            print(json.dumps({
                "error": f"Invalid output path: {str(e)}",
                "success": False
            }))
            sys.exit(1)

        # Generate documentation
        documentation = generator.generate_documentation(
            tool_id=tool_id,
            include_subtools=include_subtools,
            max_depth=max_depth
        )

        # Write to file
        with open(validated_path, 'w', encoding='utf-8') as f:
            f.write(documentation)

        logger.info(f"Wrote {len(documentation)} characters to {validated_path}")

        # Build result
        result = {
            "file_path": str(validated_path),
            "content_length": len(documentation),
            "tools_documented": list(generator.documented_tools),
            "success": True,
            "message": f"Successfully documented {len(generator.documented_tools)} tool(s)"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception("Fatal error in tool_to_markdown")
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
