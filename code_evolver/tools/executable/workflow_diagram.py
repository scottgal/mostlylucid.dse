#!/usr/bin/env python3
"""
Workflow Diagram Generator

Generates visual workflow diagrams showing tool flow and decisions.
Uses Mermaid syntax for beautiful, renderable diagrams.

USAGE:
    echo '{"tool_name": "content_summarizer"}' | python workflow_diagram.py

INPUT:
    {
        "tool_name": "content_summarizer",
        "format": "mermaid",  # or "ascii"
        "show_details": true
    }

OUTPUT:
    {
        "diagram": "graph TD\n  A[Start]...",
        "format": "mermaid",
        "tool_count": 5
    }
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict


class WorkflowDiagramGenerator:
    """
    Generates visual diagrams of tool workflows.
    """

    def __init__(self, tools_dir: Path = Path("tools")):
        """
        Initialize generator.

        Args:
            tools_dir: Directory containing tool definitions
        """
        self.tools_dir = tools_dir
        self.tools: Dict[str, Dict[str, Any]] = {}

    def load_tools(self):
        """Load all tool definitions."""
        for yaml_file in self.tools_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    tool_def = yaml.safe_load(f)

                if tool_def and "name" in tool_def:
                    tool_id = tool_def.get("name", "").replace(" ", "_").lower()
                    self.tools[tool_id] = tool_def

            except Exception:
                pass

    def generate_mermaid(
        self,
        tool_name: str,
        show_details: bool = True,
        max_depth: int = 3
    ) -> str:
        """
        Generate Mermaid diagram for tool workflow.

        Args:
            tool_name: Tool to diagram
            show_details: Include parameter details
            max_depth: Maximum dependency depth

        Returns:
            Mermaid diagram syntax
        """
        if tool_name not in self.tools:
            return f"graph TD\n  Error[Tool '{tool_name}' not found]"

        tool = self.tools[tool_name]

        # Build diagram
        lines = ["graph TD"]

        # Add start node
        lines.append(f"  Start([User Request]) --> {self._node_id(tool_name)}")

        # Add tool node
        tool_label = self._format_tool_label(tool, show_details)
        tool_type = tool.get("type", "unknown")

        # Different shapes for different types
        if tool_type == "workflow":
            lines.append(f"  {self._node_id(tool_name)}[/{tool_label}/]")
        elif tool_type == "llm":
            lines.append(f"  {self._node_id(tool_name)}[{tool_label}]")
        else:
            lines.append(f"  {self._node_id(tool_name)}[({tool_label})]")

        # Add workflow steps if present
        workflow = tool.get("workflow", {})
        steps = workflow.get("steps", [])

        visited = set([tool_name])
        self._add_workflow_steps(lines, tool_name, steps, visited, show_details, max_depth, 0)

        # Add final result
        lines.append(f"  {self._node_id(tool_name)} --> Result{{{{Result}}}}")

        # Add style classes
        lines.append("")
        lines.append("  classDef llmClass fill:#e1f5ff,stroke:#01579b")
        lines.append("  classDef workflowClass fill:#fff3e0,stroke:#e65100")
        lines.append("  classDef execClass fill:#e8f5e9,stroke:#1b5e20")
        lines.append("  classDef decisionClass fill:#fce4ec,stroke:#880e4f")

        # Apply styles
        for tool_id in visited:
            if tool_id in self.tools:
                tool_type = self.tools[tool_id].get("type", "unknown")
                if tool_type == "llm":
                    lines.append(f"  class {self._node_id(tool_id)} llmClass")
                elif tool_type == "workflow":
                    lines.append(f"  class {self._node_id(tool_id)} workflowClass")
                elif tool_type == "executable":
                    lines.append(f"  class {self._node_id(tool_id)} execClass")

        return "\n".join(lines)

    def generate_ascii(
        self,
        tool_name: str,
        show_details: bool = False
    ) -> str:
        """
        Generate ASCII art diagram.

        Args:
            tool_name: Tool to diagram
            show_details: Include details

        Returns:
            ASCII diagram
        """
        if tool_name not in self.tools:
            return f"ERROR: Tool '{tool_name}' not found"

        tool = self.tools[tool_name]

        lines = []
        lines.append("┌─────────────────────────────────────┐")
        lines.append("│         WORKFLOW DIAGRAM            │")
        lines.append("└─────────────────────────────────────┘")
        lines.append("")
        lines.append("        ┌─────────┐")
        lines.append("        │  START  │")
        lines.append("        └────┬────┘")
        lines.append("             │")

        # Main tool
        tool_label = tool.get("name", tool_name)
        tool_type = tool.get("type", "?")

        lines.append(f"        ┌────────────────────┐")
        lines.append(f"        │ {tool_label[:18].center(18)} │")
        lines.append(f"        │ [{tool_type[:16].center(16)}] │")
        lines.append(f"        └────────┬───────────┘")

        # Workflow steps
        workflow = tool.get("workflow", {})
        steps = workflow.get("steps", [])

        if steps:
            lines.append("             │")

            for i, step in enumerate(steps):
                step_tool = step.get("tool", "unknown") if isinstance(step, dict) else str(step)

                lines.append(f"        ┌────────────────────┐")
                lines.append(f"        │ {step_tool[:18].center(18)} │")

                if i < len(steps) - 1:
                    lines.append(f"        └────────┬───────────┘")
                    lines.append("                 │")
                else:
                    lines.append(f"        └────────┬───────────┘")

        lines.append("             │")
        lines.append("        ┌────┴────┐")
        lines.append("        │ RESULT  │")
        lines.append("        └─────────┘")

        return "\n".join(lines)

    def _add_workflow_steps(
        self,
        lines: List[str],
        parent_id: str,
        steps: List[Any],
        visited: Set[str],
        show_details: bool,
        max_depth: int,
        depth: int
    ):
        """
        Recursively add workflow steps to diagram.

        Args:
            lines: Diagram lines to append to
            parent_id: Parent tool ID
            steps: Workflow steps
            visited: Already visited tools
            show_details: Include details
            max_depth: Max recursion depth
            depth: Current depth
        """
        if depth >= max_depth:
            return

        prev_node = self._node_id(parent_id)

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue

            step_name = step.get("name", f"step_{i}")
            step_tool = step.get("tool")
            condition = step.get("condition")

            # Add condition node if present
            if condition:
                cond_id = f"{parent_id}_cond_{i}"
                lines.append(f"  {prev_node} --> {cond_id}{{{{{condition}}}}}")
                prev_node = cond_id

            if step_tool and step_tool in self.tools:
                # Add tool node
                sub_tool = self.tools[step_tool]
                tool_label = self._format_tool_label(sub_tool, show_details)
                tool_type = sub_tool.get("type", "unknown")

                tool_node_id = self._node_id(step_tool)

                if tool_type == "workflow":
                    lines.append(f"  {prev_node} --> {tool_node_id}[/{tool_label}/]")
                elif tool_type == "llm":
                    lines.append(f"  {prev_node} --> {tool_node_id}[{tool_label}]")
                else:
                    lines.append(f"  {prev_node} --> {tool_node_id}[({tool_label})]")

                prev_node = tool_node_id

                # Recurse into sub-workflow
                if step_tool not in visited:
                    visited.add(step_tool)
                    sub_workflow = sub_tool.get("workflow", {})
                    sub_steps = sub_workflow.get("steps", [])

                    if sub_steps:
                        self._add_workflow_steps(
                            lines,
                            step_tool,
                            sub_steps,
                            visited,
                            show_details,
                            max_depth,
                            depth + 1
                        )

            else:
                # Generic step
                step_node_id = f"{parent_id}_{step_name}"
                lines.append(f"  {prev_node} --> {step_node_id}[{step_name}]")
                prev_node = step_node_id

    def _node_id(self, tool_name: str) -> str:
        """Generate valid Mermaid node ID."""
        return tool_name.replace("-", "_").replace(" ", "_").replace(".", "_")

    def _format_tool_label(self, tool: Dict[str, Any], show_details: bool) -> str:
        """Format tool label for diagram."""
        name = tool.get("name", "Unknown")

        if not show_details:
            return name

        # Add type badge
        tool_type = tool.get("type", "?")
        return f"{name}<br/><small>{tool_type}</small>"


def main():
    """Main entry point."""
    try:
        # Read input
        input_data = sys.stdin.read()

        if not input_data.strip():
            print(json.dumps({"error": "No input provided"}), file=sys.stdout)
            sys.exit(1)

        # Parse JSON
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            # Treat as tool name
            data = {"tool_name": input_data.strip()}

        tool_name = data.get("tool_name")
        format_type = data.get("format", "mermaid")
        show_details = data.get("show_details", True)
        max_depth = data.get("max_depth", 3)

        if not tool_name:
            print(json.dumps({"error": "tool_name required"}), file=sys.stdout)
            sys.exit(1)

        # Generate diagram
        generator = WorkflowDiagramGenerator()
        generator.load_tools()

        if format_type == "ascii":
            diagram = generator.generate_ascii(tool_name, show_details)
        else:
            diagram = generator.generate_mermaid(tool_name, show_details, max_depth)

        # Count tools in diagram
        tool_count = diagram.count("-->")

        # Output
        result = {
            "diagram": diagram,
            "format": format_type,
            "tool_count": tool_count,
            "tool_name": tool_name
        }

        print(json.dumps(result, indent=2), file=sys.stdout)
        sys.exit(0)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
