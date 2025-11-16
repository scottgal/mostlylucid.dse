#!/usr/bin/env python3
"""
Find Code Fix Pattern

Searches for similar code errors and suggests proven fixes.
Used to fix issues earlier by applying previously successful solutions.
"""

import json
import sys
import os
from typing import Dict, Any, List


def find_code_fix_pattern(
    error_message: str,
    broken_code: str = "",
    error_type: str = "",
    language: str = "python",
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Find similar code fix patterns from RAG memory

    Args:
        error_message: The error message to search for
        broken_code: The broken code (optional, helps with similarity)
        error_type: Category of error (optional)
        language: Programming language
        top_k: Number of similar patterns to return

    Returns:
        Result with found patterns and suggested fixes
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
        search_query = error_message
        if broken_code:
            search_query += f"\n\nBroken code:\n{broken_code}"

        # Search by tags first for exact matches
        tags = ['code-fix-pattern', language]
        if error_type:
            tags.append(error_type)

        tag_matches = rag.find_by_tags(tags, limit=top_k * 2)

        # Search by semantic similarity
        similar_patterns = rag.find_similar(
            search_query,
            artifact_type=ArtifactType.PATTERN,
            top_k=top_k * 3,
            tags=['code-fix-pattern']
        )

        # Combine and deduplicate results
        all_patterns = {}

        # Add tag matches with high priority
        for artifact in tag_matches:
            pattern_id = artifact.artifact_id
            if pattern_id.startswith('fix_pattern_'):
                all_patterns[pattern_id] = {
                    'artifact': artifact,
                    'similarity': 1.0,  # Perfect tag match
                    'match_type': 'tag'
                }

        # Add semantic matches
        for artifact, similarity in similar_patterns:
            pattern_id = artifact.artifact_id
            if pattern_id.startswith('fix_pattern_'):
                if pattern_id not in all_patterns or all_patterns[pattern_id]['similarity'] < similarity:
                    all_patterns[pattern_id] = {
                        'artifact': artifact,
                        'similarity': similarity,
                        'match_type': 'semantic'
                    }

        # Sort by USAGE COUNT first (most successful fixes), then similarity
        # This ranks proven fixes higher than untested ones
        sorted_patterns = sorted(
            all_patterns.values(),
            key=lambda x: (
                x['artifact'].usage_count,  # Primary: usage count (most proven)
                x['similarity'],            # Secondary: similarity
                x['artifact'].quality_score  # Tertiary: quality score
            ),
            reverse=True
        )[:top_k]

        if not sorted_patterns:
            return {
                'success': True,
                'found': False,
                'message': 'No similar fix patterns found',
                'suggestions': [
                    'This might be a new error type',
                    'Use LLM-based code fixing',
                    'After fixing, store the pattern for future use'
                ]
            }

        # Extract fix patterns
        patterns = []
        for item in sorted_patterns:
            artifact = item['artifact']
            metadata = artifact.metadata or {}

            # Extract broken and fixed code from content
            content = artifact.content
            broken_code_section = ""
            fixed_code_section = ""
            fix_desc = artifact.description

            # Parse markdown sections
            if "### Broken Code" in content:
                parts = content.split("### Broken Code")
                if len(parts) > 1:
                    broken_section = parts[1].split("```")[1] if "```" in parts[1] else ""
                    broken_code_section = broken_section.strip()

            if "### Fixed Code" in content:
                parts = content.split("### Fixed Code")
                if len(parts) > 1:
                    fixed_section = parts[1].split("```")[1] if "```" in parts[1] else ""
                    fixed_code_section = fixed_section.strip()

            if "### Fix Description" in content:
                parts = content.split("### Fix Description")
                if len(parts) > 1:
                    desc_section = parts[1].split("###")[0].strip()
                    fix_desc = desc_section

            patterns.append({
                'pattern_id': artifact.artifact_id,
                'similarity': item['similarity'],
                'match_type': item['match_type'],
                'error_message': metadata.get('error_message', ''),
                'error_type': metadata.get('error_type', ''),
                'broken_code': broken_code_section,
                'fixed_code': fixed_code_section,
                'fix_description': fix_desc,
                'debug_info': metadata.get('debug_info', {}),
                'tags': artifact.tags,
                'quality_score': artifact.quality_score,
                'usage_count': artifact.usage_count,
                'context': metadata.get('context', {}),
                'rank_score': artifact.usage_count * 10 + item['similarity']  # Combined ranking
            })

        # Determine best match
        best_match = patterns[0] if patterns else None

        return {
            'success': True,
            'found': True,
            'pattern_count': len(patterns),
            'best_match': best_match,
            'all_patterns': patterns,
            'recommendation': (
                f"Apply fix from pattern {best_match['pattern_id']} "
                f"(similarity: {best_match['similarity']:.0%})"
            ) if best_match else "No recommendation",
            'how_to_apply': [
                '1. Review the broken vs fixed code comparison',
                '2. Identify the transformation pattern',
                '3. Apply similar transformation to your code',
                '4. Test the fix',
                '5. If successful, increment pattern usage'
            ]
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
        error_message = input_data.get('error_message', '')
        broken_code = input_data.get('broken_code', '')
        error_type = input_data.get('error_type', '')
        language = input_data.get('language', 'python')
        top_k = input_data.get('top_k', 3)

        if not error_message:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: error_message'
            }))
            sys.exit(1)

        # Find patterns
        result = find_code_fix_pattern(
            error_message=error_message,
            broken_code=broken_code,
            error_type=error_type,
            language=language,
            top_k=top_k
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
