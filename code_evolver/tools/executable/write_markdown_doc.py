#!/usr/bin/env python3
"""
Write Markdown Documentation Skill

Generates well-formatted markdown documentation with optional style matching.
Uses tiered LLM selection for optimal quality/speed balance.

Features:
- Smart LLM tier selection based on content requirements
- Optional style guide matching (from duplicate_style)
- Review and refinement capability
- Proper markdown formatting and validation
- Security guardrails (output only to 'output/' directory)

Input:
{
    "topic": "What to write about",
    "style_guide": "Optional style guide to match",  # from duplicate_style
    "outline": "Optional outline",
    "length": "short|medium|long",  # optional, default: medium
    "output_file": "relative/path/in/output/dir.md",  # required
    "quality_requirement": 0.8,  # optional, default: 0.8
    "review_and_refine": true  # optional, default: true
}

Output:
{
    "file_path": "output/relative/path/in/output/dir.md",
    "content_length": 5000,
    "tier_used": "medium",
    "success": true
}
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import re

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ollama_client import OllamaClient
from src.summarization_system import SummarizationSystem
from src.config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generates markdown documentation with style matching."""

    # Length guidelines (in words)
    LENGTH_TARGETS = {
        "short": 500,
        "medium": 1500,
        "long": 3000
    }

    def __init__(self, ollama_client: OllamaClient):
        """Initialize markdown generator."""
        self.client = ollama_client
        self.summarization = SummarizationSystem(ollama_client)

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

    def generate_markdown(
        self,
        topic: str,
        style_guide: Optional[str] = None,
        outline: Optional[str] = None,
        length: str = "medium",
        quality_requirement: float = 0.8
    ) -> str:
        """
        Generate markdown documentation.

        Args:
            topic: What to write about
            style_guide: Optional style guide to match
            outline: Optional outline
            length: Target length (short, medium, long)
            quality_requirement: Quality requirement (0-1)

        Returns:
            Generated markdown content
        """
        logger.info(f"Generating {length} markdown document about: {topic}")

        # Build prompt
        target_words = self.LENGTH_TARGETS.get(length, 1500)

        prompt_parts = []

        # Add style guide if provided
        if style_guide:
            prompt_parts.append(f"""Follow this style guide:

STYLE GUIDE:
{style_guide}

""")

        # Add outline if provided
        if outline:
            prompt_parts.append(f"""Use this outline:

OUTLINE:
{outline}

""")

        # Main instruction
        prompt_parts.append(f"""Write a comprehensive markdown document about the following topic.
Target length: approximately {target_words} words.

TOPIC:
{topic}

Requirements:
- Use proper markdown formatting (headers, lists, code blocks, etc.)
- Include clear section headers
- Use examples where appropriate
- Be technically accurate
- Match the style guide if provided
- Follow the outline if provided

Write the complete markdown document:""")

        prompt = "\n".join(prompt_parts)

        # Choose appropriate model based on quality requirement and length
        # Longer docs need better models
        if length == "long" or quality_requirement >= 0.9:
            model = "mistral-nemo"
        elif quality_requirement >= 0.8:
            model = "llama3"
        else:
            model = "gemma2:2b"

        logger.info(f"Using model: {model}")

        # Generate content
        content = self.client.generate(
            model=model,
            prompt=prompt,
            temperature=0.7,
            max_tokens=target_words * 2  # ~2 tokens per word
        )

        return content.strip()

    def review_and_refine(
        self,
        content: str,
        topic: str,
        style_guide: Optional[str] = None
    ) -> str:
        """
        Review and refine markdown content.

        Args:
            content: Generated content
            topic: Original topic
            style_guide: Optional style guide

        Returns:
            Refined content
        """
        logger.info("Reviewing and refining content...")

        review_prompt = f"""Review and improve this markdown document.

TOPIC: {topic}

"""
        if style_guide:
            review_prompt += f"""STYLE GUIDE TO MATCH:
{style_guide}

"""

        review_prompt += f"""CURRENT CONTENT:
{content}

Review the content and provide an improved version that:
1. Fixes any markdown formatting issues
2. Improves clarity and flow
3. Ensures technical accuracy
4. Better matches the style guide (if provided)
5. Adds missing headers or structure

Provide the complete improved markdown document:"""

        # Use high-quality model for review
        refined = self.client.generate(
            model="llama3",
            prompt=review_prompt,
            temperature=0.5,
            max_tokens=len(content) * 2
        )

        return refined.strip()

    def validate_markdown(self, content: str) -> Dict[str, Any]:
        """
        Basic markdown validation.

        Args:
            content: Markdown content

        Returns:
            Validation results
        """
        issues = []

        # Check for headers
        if not re.search(r'^#+\s+', content, re.MULTILINE):
            issues.append("No headers found")

        # Check for code blocks balance
        code_block_count = content.count("```")
        if code_block_count % 2 != 0:
            issues.append("Unbalanced code blocks (```)")

        # Check for list formatting
        has_lists = bool(re.search(r'^[\*\-\+]\s+', content, re.MULTILINE))

        # Count words (approximate)
        word_count = len(re.findall(r'\w+', content))

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "has_headers": "No headers found" not in issues,
            "has_lists": has_lists,
            "word_count": word_count
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
                "error": f"Invalid JSON input: {str(e)}",
                "success": False
            }))
            sys.exit(1)

        # Extract parameters
        topic = input_data.get("topic")
        if not topic:
            print(json.dumps({
                "error": "Missing required parameter: topic",
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

        style_guide = input_data.get("style_guide")
        outline = input_data.get("outline")
        length = input_data.get("length", "medium")
        quality_requirement = input_data.get("quality_requirement", 0.8)
        review_and_refine = input_data.get("review_and_refine", True)

        # Validate length parameter
        if length not in MarkdownGenerator.LENGTH_TARGETS:
            print(json.dumps({
                "error": f"Invalid length parameter. Must be one of: "
                        f"{list(MarkdownGenerator.LENGTH_TARGETS.keys())}",
                "success": False
            }))
            sys.exit(1)

        # Initialize components
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        config = ConfigManager(str(config_path))
        client = OllamaClient(config.ollama_url, config_manager=config)

        # Create generator
        generator = MarkdownGenerator(client)

        # Validate output path (security check)
        try:
            validated_path = generator.validate_output_path(output_file)
        except ValueError as e:
            print(json.dumps({
                "error": f"Invalid output path: {str(e)}",
                "success": False
            }))
            sys.exit(1)

        # Generate content
        content = generator.generate_markdown(
            topic=topic,
            style_guide=style_guide,
            outline=outline,
            length=length,
            quality_requirement=quality_requirement
        )

        # Optionally review and refine
        if review_and_refine:
            content = generator.review_and_refine(
                content=content,
                topic=topic,
                style_guide=style_guide
            )

        # Validate markdown
        validation = generator.validate_markdown(content)
        if not validation['valid']:
            logger.warning(f"Markdown validation issues: {validation['issues']}")

        # Write to file
        with open(validated_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Wrote {len(content)} characters to {validated_path}")

        # Build result
        result = {
            "file_path": str(validated_path),
            "content_length": len(content),
            "word_count": validation['word_count'],
            "validation": validation,
            "success": True,
            "message": f"Successfully wrote markdown to {validated_path}"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception("Fatal error in write_markdown_doc")
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
