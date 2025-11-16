#!/usr/bin/env python3
"""
Resilient Tool Call

Automatically recovers from tool failures by trying alternative tools.
- Marks failures
- Selects next best tool
- Retries until success or max attempts
- Fulfills the prompt at all costs
"""

import json
import sys
import os
from typing import List, Tuple, Optional, Dict, Any


def find_tools_for_scenario(
    scenario: str,
    tags: List[str] = None,
    exclude_tools: List[str] = None,
    max_candidates: int = 5
) -> List[Tuple[Any, float]]:
    """
    Find candidate tools for a scenario, ranked by suitability.

    Args:
        scenario: Description of what needs to be done
        tags: Optional tag filters
        exclude_tools: Tool IDs to exclude (failed tools)
        max_candidates: Maximum number of candidates to return

    Returns:
        List of (tool_artifact, similarity_score) tuples, ranked best to worst
    """
    sys.path.insert(0, '.')

    try:
        from src.rag_memory import RAGMemory, ArtifactType
        from src.ollama_client import OllamaClient
        from src.config_manager import ConfigManager

        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)

        # Search for tools matching scenario
        candidates = rag.find_similar(
            scenario,
            artifact_type=ArtifactType.TOOL,
            top_k=max_candidates * 3  # Get extra to filter
        )

        # Filter and rank candidates
        ranked = []

        for tool, similarity in candidates:
            tool_id = tool.artifact_id

            # Skip excluded tools
            if exclude_tools and tool_id in exclude_tools:
                continue

            # Check tag requirements
            if tags:
                tool_tags = set(tool.tags or [])
                if not any(tag in tool_tags for tag in tags):
                    continue

            # Check for failure history for this scenario
            failures = rag.find_similar(
                scenario,
                artifact_type=ArtifactType.PATTERN,
                tags=["tool_failure", tool_id],
                top_k=10
            )

            # Demote tool if it has similar failures
            demotion = 0.0
            for failure, failure_sim in failures:
                if failure_sim > 0.7:  # High similarity to a past failure
                    demotion += 0.3

            # Apply demotion
            adjusted_similarity = max(0.0, similarity - demotion)

            # Also consider quality score
            quality = tool.quality_score or 1.0
            final_score = adjusted_similarity * quality

            ranked.append((tool, final_score))

        # Sort by final score
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked[:max_candidates]

    except Exception as e:
        print(f"Error finding tools: {e}", file=sys.stderr)
        return []


def resilient_tool_call(
    scenario: str,
    input_data: Dict[str, Any],
    tags: List[str] = None,
    max_attempts: int = 5,
    mark_failures: bool = True
) -> Dict[str, Any]:
    """
    Call a tool with automatic fallback to alternatives on failure.

    Args:
        scenario: Description of what needs to be done
        input_data: Input data for the tool
        tags: Optional tag filters for tool selection
        max_attempts: Maximum number of tools to try
        mark_failures: Whether to mark failures (default: True)

    Returns:
        Result dict with success status and output
    """
    sys.path.insert(0, '.')

    from node_runtime import call_tool

    failed_tools = []
    attempts = []

    for attempt in range(max_attempts):
        # Find candidate tools (excluding failed ones)
        candidates = find_tools_for_scenario(
            scenario=scenario,
            tags=tags,
            exclude_tools=failed_tools,
            max_candidates=5
        )

        if not candidates:
            return {
                "success": False,
                "error": "No suitable tools found",
                "attempts": attempts,
                "message": f"Tried {len(failed_tools)} tools, all failed"
            }

        # Try the best candidate
        tool, score = candidates[0]
        tool_id = tool.artifact_id

        print(f"Attempt {attempt + 1}: Trying {tool_id} (score: {score:.2f})", file=sys.stderr)

        try:
            # Call the tool
            result = call_tool(
                tool_id,
                json.dumps(input_data),
                disable_tracking=False  # Track successful uses
            )

            # Success!
            attempts.append({
                "attempt": attempt + 1,
                "tool_id": tool_id,
                "score": score,
                "success": True
            })

            return {
                "success": True,
                "result": result,
                "tool_id": tool_id,
                "attempts": attempts,
                "message": f"Success with {tool_id} on attempt {attempt + 1}"
            }

        except Exception as e:
            error_msg = str(e)
            print(f"Tool {tool_id} failed: {error_msg}", file=sys.stderr)

            # Mark failure
            if mark_failures:
                try:
                    severity = "high" if attempt == 0 else "medium"
                    call_tool("mark_tool_failure", json.dumps({
                        "tool_id": tool_id,
                        "scenario": scenario,
                        "error_message": error_msg,
                        "severity": severity
                    }), disable_tracking=True)
                except:
                    pass  # Don't fail if marking failure fails

            # Record attempt
            attempts.append({
                "attempt": attempt + 1,
                "tool_id": tool_id,
                "score": score,
                "success": False,
                "error": error_msg
            })

            # Add to failed list
            failed_tools.append(tool_id)

            # Continue to next candidate

    # All attempts failed
    return {
        "success": False,
        "error": "All tool attempts failed",
        "attempts": attempts,
        "failed_tools": failed_tools,
        "message": f"Failed after {max_attempts} attempts"
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
        scenario = input_data.get("scenario")
        tool_input = input_data.get("input", {})
        tags = input_data.get("tags", [])
        max_attempts = input_data.get("max_attempts", 5)
        mark_failures = input_data.get("mark_failures", True)

        if not scenario:
            print(json.dumps({
                "success": False,
                "error": "Missing required parameter: scenario"
            }))
            sys.exit(1)

        # Execute resilient call
        result = resilient_tool_call(
            scenario=scenario,
            input_data=tool_input,
            tags=tags,
            max_attempts=max_attempts,
            mark_failures=mark_failures
        )

        # Output result
        print(json.dumps(result, indent=2))

        # Exit with error code if failed
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
