#!/usr/bin/env python3
"""
Workflow Documentation Generator

Generates comprehensive documentation for a workflow and saves it to README.txt
in the workflow's directory.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool


def main():
    """
    Generate documentation for a workflow and save to README.txt

    Input JSON:
    {
        "workflow_path": "/path/to/workflow/main.py",
        "workflow_name": "Optional workflow name",
        "description": "Optional description"
    }
    """
    try:
        input_data = json.load(sys.stdin)

        # Get workflow path
        workflow_path = input_data.get("workflow_path", "")
        if not workflow_path:
            print(json.dumps({
                "error": "workflow_path is required",
                "success": False
            }))
            return

        workflow_file = Path(workflow_path)
        if not workflow_file.exists():
            print(json.dumps({
                "error": f"Workflow file not found: {workflow_path}",
                "success": False
            }))
            return

        # Read workflow code
        workflow_code = workflow_file.read_text(encoding='utf-8')

        # Get workflow directory
        workflow_dir = workflow_file.parent

        # Extract workflow name (use provided name or derive from directory)
        workflow_name = input_data.get("workflow_name", "")
        if not workflow_name:
            # Try to extract from directory name or file name
            workflow_name = workflow_dir.name.replace("_", " ").title()

        # Get description (use provided or try to extract from code)
        description = input_data.get("description", "")
        if not description:
            # Try to extract from docstring
            lines = workflow_code.split('\n')
            for i, line in enumerate(lines):
                if '"""' in line or "'''" in line:
                    # Found docstring start
                    if i + 1 < len(lines):
                        description = lines[i + 1].strip()
                        break

            if not description:
                description = f"Workflow for {workflow_name}"

        # Build context information
        context_info = []

        # Detect input fields
        import re
        input_fields = set()
        for line in workflow_code.split('\n'):
            matches = re.findall(r'input_data\.get\(["\']([^"\']+)["\']', line)
            input_fields.update(matches)

        if input_fields:
            context_info.append(f"Detected inputs: {', '.join(input_fields)}")

        # Detect tool calls
        tool_calls = set()
        for line in workflow_code.split('\n'):
            matches = re.findall(r'call_tool\(["\']([^"\']+)["\']', line)
            tool_calls.update(matches)

        if tool_calls:
            context_info.append(f"Tools used: {', '.join(tool_calls)}")
        else:
            context_info.append("Tools used: None (pure Python)")

        # Estimate speed based on tools
        if not tool_calls:
            context_info.append("Estimated speed: Very fast")
        elif any('llm' in tool.lower() or 'content' in tool.lower() for tool in tool_calls):
            context_info.append("Estimated speed: Medium (LLM calls)")
        else:
            context_info.append("Estimated speed: Fast")

        context = "\n".join(context_info)

        # Call the workflow_documenter LLM tool
        doc_prompt = json.dumps({
            "workflow_name": workflow_name,
            "description": description,
            "code": workflow_code,
            "context": context
        })

        print(json.dumps({
            "status": "Generating documentation...",
            "workflow_name": workflow_name,
            "workflow_path": str(workflow_path)
        }), file=sys.stderr)

        # Generate documentation
        documentation = call_tool("workflow_documenter", doc_prompt)

        # Write to README.txt in workflow directory
        readme_path = workflow_dir / "README.txt"
        readme_path.write_text(documentation, encoding='utf-8')

        # Success
        print(json.dumps({
            "success": True,
            "workflow_name": workflow_name,
            "documentation_path": str(readme_path),
            "documentation_length": len(documentation),
            "preview": documentation[:500] + "..." if len(documentation) > 500 else documentation
        }))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "success": False
        }))
        return


if __name__ == "__main__":
    main()
