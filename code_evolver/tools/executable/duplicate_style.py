#!/usr/bin/env python3
"""
Duplicate Style Skill

Analyzes writing style from a directory of content and creates a comprehensive
style guide. Uses tiered summarization for efficient processing of large content.

Features:
- Recursive directory scanning
- Smart file filtering (text, markdown, code)
- Tiered summarization (gemma2:2b, llama3, mistral-nemo)
- Context-aware chunking
- Incremental style analysis
- Review and refinement capability

Input:
{
    "directory": "/path/to/content",
    "file_patterns": ["*.md", "*.txt", "*.py"],  # optional
    "max_files": 100,  # optional, default: no limit
    "quality_requirement": 0.8,  # optional, default: 0.8
    "review_and_refine": true  # optional, default: false
}

Output:
{
    "style_guide": "Comprehensive style analysis...",
    "files_analyzed": 42,
    "total_content_length": 50000,
    "tier_used": "medium",
    "method": "progressive"
}
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ollama_client import OllamaClient
from src.summarization_system import SummarizationSystem
from src.config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StyleAnalyzer:
    """Analyzes writing style from content."""

    DEFAULT_PATTERNS = [
        "*.md", "*.txt", "*.rst", "*.py", "*.js", "*.java",
        "*.cpp", "*.c", "*.h", "*.go", "*.rs"
    ]

    # Files to skip
    SKIP_PATTERNS = [
        "__pycache__", ".git", ".pytest_cache", "node_modules",
        ".venv", "venv", "build", "dist", ".egg-info"
    ]

    def __init__(self, ollama_client: OllamaClient):
        """Initialize style analyzer."""
        self.client = ollama_client
        self.summarization = SummarizationSystem(ollama_client)

    def should_skip_path(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path)
        return any(skip in path_str for skip in self.SKIP_PATTERNS)

    def find_files(
        self,
        directory: str,
        patterns: Optional[List[str]] = None,
        max_files: Optional[int] = None
    ) -> List[Path]:
        """
        Find files matching patterns in directory.

        Args:
            directory: Directory to search
            patterns: File patterns to match
            max_files: Maximum number of files to return

        Returns:
            List of file paths
        """
        patterns = patterns or self.DEFAULT_PATTERNS
        directory_path = Path(directory)

        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Find all matching files
        files = []
        for pattern in patterns:
            for file_path in directory_path.rglob(pattern):
                if self.should_skip_path(file_path):
                    continue

                if file_path.is_file():
                    files.append(file_path)

                    if max_files and len(files) >= max_files:
                        break

            if max_files and len(files) >= max_files:
                break

        logger.info(f"Found {len(files)} files matching patterns")
        return files

    def read_file_content(self, file_path: Path) -> Optional[str]:
        """
        Read file content safely.

        Args:
            file_path: Path to file

        Returns:
            File content or None if unreadable
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                return None
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return None

    def analyze_style_incremental(
        self,
        files: List[Path],
        quality_requirement: float = 0.8
    ) -> Dict[str, Any]:
        """
        Analyze style incrementally using tiered summarization.

        Args:
            files: List of files to analyze
            quality_requirement: Quality requirement (0-1)

        Returns:
            Style analysis results
        """
        logger.info(f"Analyzing style from {len(files)} files...")

        # Build style analysis incrementally
        style_summary = None
        total_content_length = 0
        files_processed = 0

        for i, file_path in enumerate(files):
            logger.info(f"Processing file {i+1}/{len(files)}: {file_path.name}")

            # Read file content
            content = self.read_file_content(file_path)
            if not content:
                continue

            total_content_length += len(content)
            files_processed += 1

            # Create analysis prompt for this file
            file_analysis_prompt = f"""Analyze the writing style in this content:

FILE: {file_path.name}
CONTENT:
{content}

Extract style characteristics:
- Tone (formal, casual, technical, etc.)
- Sentence structure patterns
- Vocabulary level and domain-specific terms
- Writing conventions (bullet points, headers, code examples)
- Documentation patterns (if code)

Provide a concise style analysis (max 300 words):"""

            # Analyze this file
            file_result = self.summarization.summarize(
                content=file_analysis_prompt,
                quality_requirement=quality_requirement,
                max_summary_length=300
            )

            file_style = file_result['summary']

            # Merge with existing style summary
            if style_summary is None:
                style_summary = file_style
            else:
                # Use incremental summarization
                merge_result = self.summarization.summarize_with_context(
                    content=f"NEW FILE ANALYSIS ({file_path.name}):\n{file_style}",
                    previous_summary=style_summary,
                    quality_requirement=quality_requirement
                )
                style_summary = merge_result['summary']

            # Log progress every 10 files
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i+1}/{len(files)} files, "
                          f"current summary length: {len(style_summary)} chars")

        return {
            'style_summary': style_summary,
            'files_analyzed': files_processed,
            'total_content_length': total_content_length
        }

    def refine_style_guide(
        self,
        style_summary: str,
        quality_requirement: float = 0.9
    ) -> str:
        """
        Refine and structure the style guide.

        Args:
            style_summary: Raw style analysis
            quality_requirement: Quality requirement

        Returns:
            Refined style guide
        """
        logger.info("Refining style guide...")

        refinement_prompt = f"""Based on this style analysis, create a comprehensive,
well-structured style guide that captures the key writing patterns and conventions.

STYLE ANALYSIS:
{style_summary}

Create a style guide with these sections:
1. OVERVIEW: Summary of overall writing style
2. TONE & VOICE: Characteristic tone and voice
3. STRUCTURE: Common structural patterns
4. VOCABULARY: Typical word choices and domain terms
5. CONVENTIONS: Writing conventions and formatting
6. EXAMPLES: Key style patterns to follow

Style guide:"""

        # Use high-quality tier for refinement
        result = self.summarization.summarize(
            content=refinement_prompt,
            quality_requirement=quality_requirement,
            max_summary_length=1000
        )

        return result['summary']


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
        directory = input_data.get("directory")
        if not directory:
            print(json.dumps({
                "error": "Missing required parameter: directory",
                "success": False
            }))
            sys.exit(1)

        file_patterns = input_data.get("file_patterns")
        max_files = input_data.get("max_files")
        quality_requirement = input_data.get("quality_requirement", 0.8)
        review_and_refine = input_data.get("review_and_refine", False)

        # Initialize components
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        config = ConfigManager(str(config_path))
        client = OllamaClient(config.ollama_url, config_manager=config)

        # Create analyzer
        analyzer = StyleAnalyzer(client)

        # Find files
        files = analyzer.find_files(directory, file_patterns, max_files)

        if not files:
            print(json.dumps({
                "error": f"No files found in directory: {directory}",
                "success": False
            }))
            sys.exit(1)

        # Analyze style
        analysis_result = analyzer.analyze_style_incremental(
            files=files,
            quality_requirement=quality_requirement
        )

        style_guide = analysis_result['style_summary']

        # Optionally refine
        if review_and_refine:
            style_guide = analyzer.refine_style_guide(
                style_guide,
                quality_requirement=quality_requirement
            )

        # Build result
        result = {
            "style_guide": style_guide,
            "files_analyzed": analysis_result['files_analyzed'],
            "total_content_length": analysis_result['total_content_length'],
            "success": True,
            "message": f"Analyzed {analysis_result['files_analyzed']} files successfully"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception("Fatal error in duplicate_style")
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
