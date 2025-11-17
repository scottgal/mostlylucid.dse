#!/usr/bin/env python3
"""
Mark Tool Failure

Records when a tool fails for a specific scenario, enabling:
- Demotion in search rankings for similar scenarios
- Tag refinement to narrow tool use cases
- Failure pattern learning
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path


def mark_tool_failure(
    tool_id: str,
    scenario: str,
    error_message: str,
    severity: str = "medium"
) -> dict:
    """
    Mark a tool as failing for a specific scenario.

    Args:
        tool_id: The tool that failed
        scenario: Description of what was attempted (used for similarity matching)
        error_message: The error that occurred
        severity: low, medium, high (affects demotion strength)

    Returns:
        Result with failure recording and demotion info
    """
    sys.path.insert(0, '.')

    try:
        from src.rag_memory import RAGMemory, ArtifactType
        from src.ollama_client import OllamaClient
        from src.config_manager import ConfigManager

        # Initialize RAG
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)

        # Create failure artifact
        failure_id = f"failure_{tool_id}_{int(datetime.utcnow().timestamp() * 1000)}"

        failure_content = f"""Tool Failure Report

Tool: {tool_id}
Scenario: {scenario}
Error: {error_message}
Severity: {severity}
Timestamp: {datetime.utcnow().isoformat()}Z

This tool was attempted for the scenario above but failed.
Future searches for similar scenarios should demote this tool.
"""

        # Store failure in RAG
        rag.store_artifact(
            artifact_id=failure_id,
            artifact_type=ArtifactType.FAILURE,  # Use specific FAILURE type
            name=f"Failure: {tool_id}",
            description=f"Tool failure for scenario: {scenario[:100]}",
            content=failure_content,
            tags=["failure", "tool_failure", tool_id, f"severity_{severity}"],
            metadata={
                "tool_id": tool_id,
                "scenario": scenario,
                "error": error_message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "failure_type": "execution"
            },
            auto_embed=True  # Enable semantic search on failures
        )

        # Get tool artifact to update
        tool_artifact = rag.get_artifact(tool_id)

        demotion_applied = False
        tag_refinement = None

        if tool_artifact:
            # Count failures for this tool
            failure_count = rag.search_by_tags(["tool_failure", tool_id], limit=100)
            num_failures = len(failure_count)

            # Apply demotion based on severity and failure count
            severity_multipliers = {
                "low": 0.01,
                "medium": 0.05,
                "high": 0.10
            }

            demotion = severity_multipliers.get(severity, 0.05)

            # Additional demotion for repeated failures
            if num_failures > 5:
                demotion += 0.05
            if num_failures > 10:
                demotion += 0.10

            # Apply demotion to quality score
            current_score = tool_artifact.quality_score or 1.0
            new_score = max(0.0, current_score - demotion)

            rag.update_quality_score(tool_id, new_score)
            demotion_applied = True

            # Tag refinement: Add negative tags
            current_tags = set(tool_artifact.tags or [])

            # Extract key words from scenario to create negative tags
            scenario_words = scenario.lower().split()
            negative_tags = []

            # Add specific negative tags based on scenario
            for word in scenario_words[:5]:  # First 5 words
                if len(word) > 4 and word not in ['with', 'that', 'this', 'from', 'have']:
                    negative_tags.append(f"not-for-{word}")

            if negative_tags:
                new_tags = list(current_tags) + negative_tags[:3]  # Max 3 negative tags
                rag.update_artifact_metadata(
                    tool_id,
                    {
                        "tags": new_tags,
                        "last_failure": datetime.utcnow().isoformat() + "Z",
                        "failure_count": num_failures
                    }
                )
                tag_refinement = negative_tags[:3]

        return {
            "success": True,
            "failure_id": failure_id,
            "tool_id": tool_id,
            "scenario": scenario,
            "severity": severity,
            "demotion_applied": demotion_applied,
            "new_quality_score": new_score if demotion_applied else None,
            "tag_refinement": tag_refinement,
            "total_failures": num_failures if tool_artifact else 1,
            "message": f"Marked {tool_id} as failing for scenario: {scenario[:50]}..."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to mark tool failure: {str(e)}"
        }


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
        scenario = input_data.get("scenario")
        error_message = input_data.get("error_message", "Unknown error")
        severity = input_data.get("severity", "medium")

        if not tool_id or not scenario:
            print(json.dumps({
                "success": False,
                "error": "Missing required parameters: tool_id, scenario"
            }))
            sys.exit(1)

        # Mark failure
        result = mark_tool_failure(tool_id, scenario, error_message, severity)

        # Output result
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Fatal error: {str(e)}"
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
