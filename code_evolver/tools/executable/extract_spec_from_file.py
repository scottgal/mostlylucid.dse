#!/usr/bin/env python3
"""
Extract Spec From File

Extracts and processes specifications from text files for the overseer.
Handles large files and formats them for workflow generation.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List


def extract_sections(content: str) -> Dict[str, str]:
    """
    Extract sections from structured text.

    Looks for:
    - ## Headers
    - **Bold markers**
    - Numbered lists
    - Code blocks
    """
    sections = {
        "overview": "",
        "requirements": [],
        "constraints": [],
        "examples": [],
        "code_blocks": [],
        "full_text": content
    }

    lines = content.split('\n')
    current_section = "overview"
    current_content = []

    for line in lines:
        # Section headers
        if line.startswith('##'):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content)
                current_content = []

            # Determine new section
            header_lower = line.lower()
            if 'requirement' in header_lower:
                current_section = "requirements"
            elif 'constraint' in header_lower or 'limitation' in header_lower:
                current_section = "constraints"
            elif 'example' in header_lower:
                current_section = "examples"
            else:
                current_section = header_lower.strip('#').strip().replace(' ', '_')

        # Code blocks
        elif line.strip().startswith('```'):
            if line.strip() != '```':
                # Extract language
                lang = line.strip()[3:].strip()
                sections["code_blocks"].append({"language": lang, "code": ""})
            continue

        else:
            current_content.append(line)

    # Save final section
    if current_content:
        sections[current_section] = '\n'.join(current_content)

    return sections


def summarize_for_overseer(content: str, max_length: int = 10000) -> str:
    """
    Create overseer-friendly summary of large specification.

    Args:
        content: Full specification text
        max_length: Maximum length for overseer (default: 10000 chars)

    Returns:
        Summarized specification optimized for overseer planning
    """
    # If content is short enough, return as-is
    if len(content) <= max_length:
        return content

    # Extract sections
    sections = extract_sections(content)

    # Build prioritized summary
    summary_parts = []

    # 1. First paragraph (overview)
    first_para = content.split('\n\n')[0]
    summary_parts.append(f"## Overview\n{first_para}")

    # 2. Requirements (critical)
    if sections.get("requirements"):
        summary_parts.append(f"\n## Requirements\n{sections['requirements'][:2000]}")

    # 3. Constraints (important)
    if sections.get("constraints"):
        summary_parts.append(f"\n## Constraints\n{sections['constraints'][:1000]}")

    # 4. Examples (helpful)
    if sections.get("examples"):
        summary_parts.append(f"\n## Examples\n{sections['examples'][:2000]}")

    # 5. Key bullet points from full text
    bullets = [line for line in content.split('\n') if line.strip().startswith('-') or line.strip().startswith('*')]
    if bullets:
        summary_parts.append(f"\n## Key Points\n" + '\n'.join(bullets[:20]))

    # Join and truncate if needed
    summary = '\n'.join(summary_parts)

    if len(summary) > max_length:
        summary = summary[:max_length] + "\n\n...(truncated, see full spec for details)"

    # Add note about truncation
    summary += f"\n\n---\n*Full specification: {len(content)} characters, {len(content.split())} words*"

    return summary


def extract_spec_from_file(
    file_path: str,
    summarize: bool = True,
    max_length: int = 10000
) -> Dict[str, Any]:
    """
    Extract specification from a text file.

    Args:
        file_path: Path to specification file
        summarize: Whether to create overseer-friendly summary
        max_length: Max length for summary

    Returns:
        Extracted specification data
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }

        # Read file
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract sections
        sections = extract_sections(content)

        # Create overseer summary if requested
        overseer_spec = summarize_for_overseer(content, max_length) if summarize else content

        return {
            "success": True,
            "file_path": str(path.absolute()),
            "file_size": len(content),
            "word_count": len(content.split()),
            "overseer_spec": overseer_spec,
            "full_spec": content,
            "sections": {
                k: v for k, v in sections.items()
                if isinstance(v, str) and v.strip()
            },
            "message": f"Extracted {len(content)} characters from {path.name}"
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": f"File encoding error. File must be UTF-8 text: {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read file: {str(e)}"
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
        file_path = input_data.get("file_path")
        summarize = input_data.get("summarize", True)
        max_length = input_data.get("max_length", 10000)

        if not file_path:
            print(json.dumps({
                "success": False,
                "error": "Missing required parameter: file_path"
            }))
            sys.exit(1)

        # Extract spec
        result = extract_spec_from_file(file_path, summarize, max_length)

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
