#!/usr/bin/env python3
"""
Evolve Tool

Evolves a failing tool by regenerating it with mutations.
Creates a new version promoted for the current workflow.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def evolve_tool(
    tool_id: str,
    error_message: str,
    mutation_hint: str,
    dynamic_schema: bool = False
) -> Dict[str, Any]:
    """
    Evolve a tool that's failing.

    Args:
        tool_id: ID of the tool to evolve
        error_message: Error that occurred
        mutation_hint: User hint for what to fix/change
        dynamic_schema: Whether to make output schema dynamic

    Returns:
        Result with evolved tool info
    """
    sys.path.insert(0, '.')

    try:
        from src.tools_manager import ToolsManager
        from src.config_manager import ConfigManager
        from src.ollama_client import OllamaClient
        from src.rag_memory import RAGMemory, ArtifactType
        from src.cumulative_changelog import CumulativeChangelog
        from src.test_evolution_tracker import TestEvolutionTracker
        from node_runtime import call_tool_resilient, call_llm

        # Initialize
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)
        tools = ToolsManager(config, client, rag)
        changelog = CumulativeChangelog(
            storage_dir=config.get("evolution_logs_dir", "evolution_logs")
        )
        test_tracker = TestEvolutionTracker()

        # Get the failing tool
        tool = tools.get_tool(tool_id)
        if not tool:
            return {
                "success": False,
                "error": f"Tool not found: {tool_id}"
            }

        # Read tool files (Python + YAML)
        tool_dir = Path("tools/executable")
        py_file = tool_dir / f"{tool_id}.py"
        yaml_file = tool_dir / f"{tool_id}.yaml"

        if not py_file.exists():
            return {
                "success": False,
                "error": f"Tool Python file not found: {py_file}"
            }

        # Read current implementation
        with open(py_file, 'r', encoding='utf-8') as f:
            current_code = f.read()

        # Read YAML if exists
        current_yaml = ""
        if yaml_file.exists():
            with open(yaml_file, 'r', encoding='utf-8') as f:
                current_yaml = f.read()

        # Read test file if exists
        test_file = tool_dir / f"test_{tool_id}.py"
        current_test_code = ""
        if test_file.exists():
            with open(test_file, 'r', encoding='utf-8') as f:
                current_test_code = f.read()

        # Get evolution history from cumulative changelog
        evolution_history = changelog.format_for_evolution_prompt(tool_id)
        print(f"Retrieved evolution history for {tool_id}", file=sys.stderr)

        # Create mutation prompt for code generator
        mutation_prompt = f"""Fix and evolve this tool that's currently failing.

**Tool:** {tool_id}
**Error:** {error_message}
**User Hint:** {mutation_hint}

**Current Implementation:**
```python
{current_code}
```

**Current YAML Config:**
```yaml
{current_yaml}
```

**Current Tests:**
```python
{current_test_code if current_test_code else "# No tests found"}
```

{evolution_history}

**Requirements:**
1. Fix the error: {error_message}
2. Apply the mutation: {mutation_hint}
3. {"Make output schema dynamic (flexible JSON)" if dynamic_schema else "Keep output schema structure"}
4. Maintain backward compatibility where possible
5. Add tests to prevent regression
6. DO NOT repeat failed mutations from evolution history
7. Build on successful patterns from evolution history
8. Ensure test coverage is maintained or improved

**Output:**
Generate the evolved tool with:
- Fixed Python code
- Updated YAML configuration (if needed)
- Test cases (must maintain or improve coverage)
- Version bump (increment minor version)

The evolved tool should be drop-in compatible but better.
IMPORTANT: Review the evolution history to avoid repeating mistakes.
"""

        # Generate evolved tool using code generator
        print(f"Generating evolved version of {tool_id}...", file=sys.stderr)

        # Use resilient call to find best code generator
        evolved_code_result = call_tool_resilient(
            scenario="evolve python tool with fix and mutation",
            input_data={
                "tool_id": tool_id,
                "current_code": current_code,
                "current_yaml": current_yaml,
                "error": error_message,
                "mutation": mutation_hint,
                "dynamic_schema": dynamic_schema,
                "prompt": mutation_prompt
            },
            tags=["code", "generator", "python"],
            max_attempts=3
        )

        evolved_code = json.loads(evolved_code_result)

        # Extract generated code
        if "code" in evolved_code:
            new_code = evolved_code["code"]
        elif "python_code" in evolved_code:
            new_code = evolved_code["python_code"]
        else:
            # Parse from result
            new_code = evolved_code_result

        # Create new version
        new_version = increment_version(tool.version)

        # Save evolved tool as versioned file
        evolved_py = tool_dir / f"{tool_id}_v{new_version.replace('.', '_')}.py"
        with open(evolved_py, 'w', encoding='utf-8') as f:
            f.write(new_code)

        # Update YAML with new version
        if dynamic_schema and yaml_file.exists():
            import yaml

            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            # Make output schema dynamic
            yaml_data["output_schema"] = {
                "type": "object",
                "description": "Dynamic output (flexible schema)",
                "additionalProperties": True
            }

            # Update version
            yaml_data["version"] = new_version

            # Save updated YAML
            evolved_yaml = tool_dir / f"{tool_id}_v{new_version.replace('.', '_')}.yaml"
            with open(evolved_yaml, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, default_flow_style=False)

        # Create workflow-local promotion file
        # This makes the evolved tool available in THIS workflow
        promotion_file = Path(".tool_promotions.json")

        promotions = {}
        if promotion_file.exists():
            with open(promotion_file, 'r', encoding='utf-8') as f:
                promotions = json.load(f)

        promotions[tool_id] = {
            "evolved_version": new_version,
            "evolved_file": str(evolved_py),
            "original_version": tool.version,
            "reason": f"Evolved to fix: {error_message}",
            "mutation": mutation_hint,
            "promoted_at": datetime.utcnow().isoformat() + "Z"
        }

        with open(promotion_file, 'w', encoding='utf-8') as f:
            json.dump(promotions, f, indent=2)

        # Store evolution in RAG
        evolution_id = f"evolution_{tool_id}_{new_version}"
        rag.store_artifact(
            artifact_id=evolution_id,
            artifact_type=ArtifactType.PATTERN,
            name=f"Tool Evolution: {tool_id} v{new_version}",
            description=f"Evolved {tool_id} to fix: {error_message}",
            content=f"""Tool Evolution

Original Version: {tool.version}
New Version: {new_version}

Error Fixed: {error_message}
Mutation Applied: {mutation_hint}

Original Code:
{current_code[:500]}...

Evolved Code:
{new_code[:500]}...
""",
            tags=["evolution", "tool_mutation", tool_id, f"v{new_version}"],
            metadata={
                "tool_id": tool_id,
                "original_version": tool.version,
                "new_version": new_version,
                "error": error_message,
                "mutation": mutation_hint,
                "dynamic_schema": dynamic_schema
            },
            auto_embed=True
        )

        # Record mutation in cumulative changelog
        # Note: We assume success here, but in a real scenario we'd test first
        changes_description = f"Fixed error: {error_message}. Applied mutation: {mutation_hint}"

        changelog.record_mutation(
            artifact_id=tool_id,
            version=new_version,
            parent_id=tool_id,
            mutation_type="tool_evolution",
            changes_description=changes_description,
            success=True,  # Assumed success; would be validated by testing
            metadata={
                "error": error_message,
                "mutation_hint": mutation_hint,
                "dynamic_schema": dynamic_schema,
                "evolved_file": str(evolved_py)
            }
        )
        print(f"Recorded evolution in changelog", file=sys.stderr)

        return {
            "success": True,
            "tool_id": tool_id,
            "original_version": tool.version,
            "new_version": new_version,
            "evolved_file": str(evolved_py),
            "promotion_file": str(promotion_file),
            "message": f"Evolved {tool_id} from v{tool.version} to v{new_version}",
            "usage": f"The evolved tool is now active in this workflow. Use {tool_id} normally."
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def increment_version(version: str) -> str:
    """Increment minor version (1.0.0 -> 1.1.0)."""
    parts = version.split('.')
    if len(parts) >= 2:
        parts[1] = str(int(parts[1]) + 1)
        if len(parts) >= 3:
            parts[2] = '0'  # Reset patch
        return '.'.join(parts)
    return version + ".1"


def main():
    """Main entry point."""
    try:
        # Read input
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "error": f"Invalid JSON input: {str(e)}"
            }))
            sys.exit(1)

        # Extract parameters
        tool_id = input_data.get("tool_id")
        error_message = input_data.get("error_message", "Unknown error")
        mutation_hint = input_data.get("mutation_hint", "Fix the error")
        dynamic_schema = input_data.get("dynamic_schema", False)

        if not tool_id:
            print(json.dumps({
                "success": False,
                "error": "Missing required parameter: tool_id"
            }))
            sys.exit(1)

        # Evolve tool
        result = evolve_tool(tool_id, error_message, mutation_hint, dynamic_schema)

        # Output result
        print(json.dumps(result, indent=2))

        if not result["success"]:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Fatal error: {str(e)}"
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
