#!/usr/bin/env python3
"""
Check Tool Duplicate

Searches for semantically similar tools to avoid creating duplicates.
Uses RAG memory to find tools with similar descriptions/functionality.
"""

import json
import sys
import os
from typing import Dict, Any, List


def check_tool_duplicate(
    tool_description: str,
    tool_name: str = "",
    parameters: List[Dict[str, Any]] = None,
    category: str = "",
    similarity_threshold: float = 0.85
) -> Dict[str, Any]:
    """
    Check if a similar tool already exists

    Args:
        tool_description: What the tool does
        tool_name: Name of the proposed tool
        parameters: List of parameters the tool takes
        category: Tool category (math, text, data, etc.)
        similarity_threshold: Minimum similarity to consider a duplicate (0.0-1.0)

    Returns:
        Result with found duplicates and recommendation
    """
    sys.path.insert(0, '.')

    try:
        from src.config_manager import ConfigManager
        from src.ollama_client import OllamaClient
        from src.rag_memory import RAGMemory, ArtifactType

        # Initialize
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)

        # Build search query
        search_query = f"{tool_description}"
        if tool_name:
            search_query = f"{tool_name}: {tool_description}"

        # Search for similar tools by description
        similar_tools = rag.find_similar(
            search_query,
            artifact_type=None,  # Search all artifact types
            top_k=10
        )

        # Filter to only tool-related artifacts
        tool_artifacts = []
        for artifact, similarity in similar_tools:
            # Check if this is a tool (has tool metadata)
            metadata = artifact.metadata or {}

            # Look for tool indicators
            is_tool = (
                'tool_id' in metadata or
                'tool_type' in metadata or
                artifact.artifact_type.value == 'tool' or
                'function' in artifact.tags or
                'executable' in artifact.tags or
                'llm-tool' in artifact.tags
            )

            if is_tool and similarity >= similarity_threshold:
                tool_artifacts.append((artifact, similarity))

        # Also search by category tags if provided
        category_matches = []
        if category:
            category_tags = [category, f"category:{category}"]
            category_results = rag.find_by_tags(category_tags, limit=20)

            for artifact in category_results:
                # Calculate similarity for these results
                # (tag matches don't have similarity scores)
                tool_artifacts.append((artifact, 1.0))  # Perfect tag match

        # Deduplicate and sort by similarity
        seen_ids = set()
        unique_tools = []
        for artifact, similarity in tool_artifacts:
            if artifact.artifact_id not in seen_ids:
                seen_ids.add(artifact.artifact_id)
                unique_tools.append((artifact, similarity))

        # Sort by similarity (highest first)
        unique_tools.sort(key=lambda x: x[1], reverse=True)

        # Take top 5
        top_matches = unique_tools[:5]

        if not top_matches:
            return {
                'success': True,
                'has_duplicates': False,
                'message': 'No similar tools found - safe to create',
                'recommendation': 'create_new_tool'
            }

        # Extract tool information
        duplicates = []
        for artifact, similarity in top_matches:
            metadata = artifact.metadata or {}

            duplicates.append({
                'tool_id': metadata.get('tool_id', artifact.artifact_id),
                'name': artifact.name,
                'description': artifact.description,
                'similarity': similarity,
                'tags': artifact.tags,
                'quality_score': artifact.quality_score,
                'usage_count': artifact.usage_count,
                'parameters': metadata.get('parameters', []),
                'category': metadata.get('category', 'unknown')
            })

        # Determine if we have a strong duplicate
        best_match = duplicates[0]
        is_duplicate = best_match['similarity'] >= similarity_threshold

        if is_duplicate:
            recommendation = 'use_existing_tool'
            message = f"Found existing tool: {best_match['name']} ({best_match['similarity']:.0%} similar)"
        else:
            recommendation = 'create_new_tool'
            message = f"No strong duplicates found (best match: {best_match['similarity']:.0%})"

        return {
            'success': True,
            'has_duplicates': is_duplicate,
            'duplicate_count': len(duplicates),
            'best_match': best_match,
            'all_matches': duplicates,
            'recommendation': recommendation,
            'message': message,
            'threshold_used': similarity_threshold
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                'success': False,
                'error': f'Invalid JSON input: {str(e)}'
            }))
            sys.exit(1)

        # Extract parameters
        tool_description = input_data.get('tool_description', '')
        tool_name = input_data.get('tool_name', '')
        parameters = input_data.get('parameters', [])
        category = input_data.get('category', '')
        similarity_threshold = input_data.get('similarity_threshold', 0.85)

        if not tool_description:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: tool_description'
            }))
            sys.exit(1)

        # Check for duplicates
        result = check_tool_duplicate(
            tool_description=tool_description,
            tool_name=tool_name,
            parameters=parameters,
            category=category,
            similarity_threshold=similarity_threshold
        )

        # Output result
        print(json.dumps(result, indent=2))

        if not result['success']:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Fatal error: {str(e)}'
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
