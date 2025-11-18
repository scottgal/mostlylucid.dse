#!/usr/bin/env python3
"""
Mermaid Diagram Builder
Generates Mermaid diagram syntax from structured data, conversations, or tool flows.
"""

import json
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib


class MermaidBuilder:
    """Build Mermaid diagrams from various data sources."""

    def __init__(self, theme: str = "default"):
        self.theme = theme
        self.node_counter = 0
        self.node_map = {}

    def _sanitize_id(self, text: str) -> str:
        """Create a safe node ID from text."""
        # Create a hash-based ID to avoid special characters
        return f"node_{hashlib.md5(text.encode()).hexdigest()[:8]}"

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for use in Mermaid diagrams."""
        # Escape quotes and special characters
        text = text.replace('"', "'").replace("\n", " ").replace("[", "(").replace("]", ")")
        # Truncate long text
        if len(text) > 100:
            text = text[:97] + "..."
        return text

    def _get_node_id(self, key: str) -> str:
        """Get or create a node ID for a key."""
        if key not in self.node_map:
            self.node_map[key] = f"n{self.node_counter}"
            self.node_counter += 1
        return self.node_map[key]

    def build_flowchart(self, data: Dict[str, Any], direction: str = "TD", title: Optional[str] = None) -> str:
        """Build a flowchart diagram."""
        lines = []

        if title:
            lines.append(f"---\ntitle: {title}\n---")

        lines.append(f"flowchart {direction}")

        # Handle nodes
        if "nodes" in data:
            for node in data["nodes"]:
                node_id = self._get_node_id(node["id"])
                label = self._sanitize_text(node.get("label", node["id"]))
                shape = node.get("shape", "rectangle")

                # Different shapes
                if shape == "circle":
                    lines.append(f"    {node_id}(({label}))")
                elif shape == "diamond":
                    lines.append(f"    {node_id}{{{{{label}}}}}")
                elif shape == "hexagon":
                    lines.append(f"    {node_id}{{{{{{{label}}}}}}}")
                elif shape == "rounded":
                    lines.append(f"    {node_id}({label})")
                else:  # rectangle
                    lines.append(f"    {node_id}[{label}]")

        # Handle edges
        if "edges" in data:
            for edge in data["edges"]:
                from_id = self._get_node_id(edge["from"])
                to_id = self._get_node_id(edge["to"])
                label = edge.get("label", "")
                arrow = edge.get("arrow", "-->")

                if label:
                    lines.append(f"    {from_id} {arrow}|{self._sanitize_text(label)}| {to_id}")
                else:
                    lines.append(f"    {from_id} {arrow} {to_id}")

        # Add styling
        if "styles" in data:
            for style in data["styles"]:
                node_id = self._get_node_id(style["id"])
                style_def = style.get("style", "")
                lines.append(f"    style {node_id} {style_def}")

        return "\n".join(lines)

    def build_sequence_diagram(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        """Build a sequence diagram."""
        lines = []

        if title:
            lines.append(f"---\ntitle: {title}\n---")

        lines.append("sequenceDiagram")

        # Participants
        if "participants" in data:
            for participant in data["participants"]:
                pid = participant.get("id", participant.get("name"))
                name = self._sanitize_text(participant.get("name", pid))
                lines.append(f"    participant {pid} as {name}")

        # Messages
        if "messages" in data:
            for msg in data["messages"]:
                from_p = msg["from"]
                to_p = msg["to"]
                text = self._sanitize_text(msg.get("text", ""))
                arrow = msg.get("arrow", "->")

                if arrow == "->":
                    lines.append(f"    {from_p}->>{to_p}: {text}")
                elif arrow == "-->":
                    lines.append(f"    {from_p}-->>{to_p}: {text}")
                elif arrow == "-x":
                    lines.append(f"    {from_p}-x{to_p}: {text}")
                else:
                    lines.append(f"    {from_p}->{to_p}: {text}")

        # Activations
        if "activations" in data:
            for act in data["activations"]:
                lines.append(f"    activate {act['participant']}")
                if "deactivate" in act and act["deactivate"]:
                    lines.append(f"    deactivate {act['participant']}")

        # Notes
        if "notes" in data:
            for note in data["notes"]:
                position = note.get("position", "right of")
                participant = note["participant"]
                text = self._sanitize_text(note["text"])
                lines.append(f"    Note {position} {participant}: {text}")

        return "\n".join(lines)

    def build_state_diagram(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        """Build a state diagram."""
        lines = []

        if title:
            lines.append(f"---\ntitle: {title}\n---")

        lines.append("stateDiagram-v2")

        # States
        if "states" in data:
            for state in data["states"]:
                state_id = state["id"]
                if "description" in state:
                    desc = self._sanitize_text(state["description"])
                    lines.append(f"    {state_id}: {desc}")

        # Transitions
        if "transitions" in data:
            for trans in data["transitions"]:
                from_state = trans["from"]
                to_state = trans["to"]
                label = trans.get("label", "")

                if label:
                    lines.append(f"    {from_state} --> {to_state}: {self._sanitize_text(label)}")
                else:
                    lines.append(f"    {from_state} --> {to_state}")

        # Start and end states
        if "start" in data:
            lines.append(f"    [*] --> {data['start']}")
        if "end" in data:
            lines.append(f"    {data['end']} --> [*]")

        return "\n".join(lines)

    def build_conversation_diagram(self, conversation: List[Dict[str, str]], title: Optional[str] = None) -> str:
        """Build a sequence diagram from conversation messages."""
        participants = set()
        messages = []

        for msg in conversation:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Map roles to participants
            if role == "user":
                from_p = "User"
                to_p = "Assistant"
            elif role == "assistant":
                from_p = "Assistant"
                to_p = "User"
            elif role == "system":
                from_p = "System"
                to_p = "Assistant"
            else:
                from_p = role
                to_p = "Assistant"

            participants.add(from_p)
            participants.add(to_p)

            # Truncate long messages
            content_preview = content[:80] + "..." if len(content) > 80 else content

            messages.append({
                "from": from_p,
                "to": to_p,
                "text": content_preview,
                "arrow": "->"
            })

        data = {
            "participants": [{"id": p, "name": p} for p in sorted(participants)],
            "messages": messages
        }

        return self.build_sequence_diagram(data, title or "Conversation Flow")

    def build_tool_flow_diagram(self, tool_calls: List[Dict[str, Any]], title: Optional[str] = None) -> str:
        """Build a flowchart showing tool execution flow."""
        nodes = []
        edges = []
        styles = []

        # Start node
        nodes.append({"id": "start", "label": "Start", "shape": "circle"})

        prev_id = "start"
        for i, call in enumerate(tool_calls):
            tool_name = call.get("name", f"Tool {i}")
            tool_id = f"tool_{i}"

            # Tool node
            nodes.append({
                "id": tool_id,
                "label": tool_name,
                "shape": "rectangle"
            })

            edges.append({
                "from": prev_id,
                "to": tool_id,
                "label": call.get("trigger", "")
            })

            # Check for results
            if "result" in call:
                result_id = f"result_{i}"
                result = call["result"]

                if isinstance(result, dict):
                    success = result.get("success", True)
                    label = "Success" if success else "Error"
                    shape = "diamond"
                else:
                    label = "Result"
                    shape = "rounded"

                nodes.append({
                    "id": result_id,
                    "label": label,
                    "shape": shape
                })

                edges.append({
                    "from": tool_id,
                    "to": result_id
                })

                # Style based on success/failure
                if isinstance(result, dict) and not result.get("success", True):
                    styles.append({
                        "id": result_id,
                        "style": "fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px"
                    })
                else:
                    styles.append({
                        "id": result_id,
                        "style": "fill:#51cf66,stroke:#2f9e44,stroke-width:2px"
                    })

                prev_id = result_id
            else:
                prev_id = tool_id

            # Style tool nodes
            styles.append({
                "id": tool_id,
                "style": "fill:#74c0fc,stroke:#1971c2,stroke-width:2px"
            })

        # End node
        nodes.append({"id": "end", "label": "End", "shape": "circle"})
        edges.append({"from": prev_id, "to": "end"})

        data = {
            "nodes": nodes,
            "edges": edges,
            "styles": styles
        }

        return self.build_flowchart(data, "TD", title or "Tool Execution Flow")

    def build_class_diagram(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        """Build a class diagram."""
        lines = []

        if title:
            lines.append(f"---\ntitle: {title}\n---")

        lines.append("classDiagram")

        # Classes
        if "classes" in data:
            for cls in data["classes"]:
                class_name = cls["name"]

                # Attributes
                if "attributes" in cls:
                    for attr in cls["attributes"]:
                        visibility = attr.get("visibility", "+")
                        name = attr["name"]
                        type_info = attr.get("type", "")
                        lines.append(f"    class {class_name} {{{visibility}{name}: {type_info}}}")

                # Methods
                if "methods" in cls:
                    for method in cls["methods"]:
                        visibility = method.get("visibility", "+")
                        name = method["name"]
                        params = method.get("params", "")
                        return_type = method.get("return", "")
                        lines.append(f"    class {class_name} {{{visibility}{name}({params}): {return_type}}}")

        # Relationships
        if "relationships" in data:
            for rel in data["relationships"]:
                from_cls = rel["from"]
                to_cls = rel["to"]
                rel_type = rel.get("type", "association")

                if rel_type == "inheritance":
                    lines.append(f"    {from_cls} --|> {to_cls}")
                elif rel_type == "composition":
                    lines.append(f"    {from_cls} *-- {to_cls}")
                elif rel_type == "aggregation":
                    lines.append(f"    {from_cls} o-- {to_cls}")
                else:  # association
                    lines.append(f"    {from_cls} --> {to_cls}")

        return "\n".join(lines)

    def build_diagram(self, diagram_type: str, **kwargs) -> str:
        """Build a diagram of the specified type."""
        if diagram_type == "flowchart":
            return self.build_flowchart(
                kwargs.get("data", {}),
                kwargs.get("direction", "TD"),
                kwargs.get("title")
            )
        elif diagram_type == "sequence":
            return self.build_sequence_diagram(
                kwargs.get("data", {}),
                kwargs.get("title")
            )
        elif diagram_type == "state":
            return self.build_state_diagram(
                kwargs.get("data", {}),
                kwargs.get("title")
            )
        elif diagram_type == "conversation":
            return self.build_conversation_diagram(
                kwargs.get("conversation", []),
                kwargs.get("title")
            )
        elif diagram_type == "tool_flow":
            return self.build_tool_flow_diagram(
                kwargs.get("tool_calls", []),
                kwargs.get("title")
            )
        elif diagram_type == "class":
            return self.build_class_diagram(
                kwargs.get("data", {}),
                kwargs.get("title")
            )
        else:
            raise ValueError(f"Unsupported diagram type: {diagram_type}")


def main():
    """Main entry point for the mermaid builder tool."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        diagram_type = input_data.get("diagram_type")
        if not diagram_type:
            raise ValueError("diagram_type is required")

        theme = input_data.get("theme", "default")
        builder = MermaidBuilder(theme=theme)

        # Build diagram
        mermaid_syntax = builder.build_diagram(
            diagram_type=diagram_type,
            data=input_data.get("data"),
            conversation=input_data.get("conversation"),
            tool_calls=input_data.get("tool_calls"),
            direction=input_data.get("direction", "TD"),
            title=input_data.get("title")
        )

        # Return result
        result = {
            "success": True,
            "mermaid": mermaid_syntax,
            "diagram_type": diagram_type,
            "theme": theme,
            "timestamp": datetime.now().isoformat()
        }

        print(json.dumps(result, indent=2))
        sys.exit(0)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
