#!/usr/bin/env python3
"""
Text to Markdown Converter

Converts plain text to well-formatted markdown with intelligent structure detection.
Analyzes text patterns and applies appropriate markdown formatting.

Features:
- Auto-detects structure (headers, lists, code)
- Preserves code blocks
- Formats lists and bullets
- Adds proper spacing
- Handles paragraphs and line breaks
- Optional style preferences

Input:
{
    "text": "plain text content",  # required
    "auto_format": true,  # optional, default: true
    "preserve_linebreaks": false,  # optional, default: false
    "detect_code": true,  # optional, default: true
    "detect_lists": true,  # optional, default: true
    "detect_headers": true,  # optional, default: true
    "output_file": "path/to/output.md"  # optional, outputs to file if provided
}

Output:
{
    "markdown": "formatted markdown text",
    "file_path": "output.md",  # if output_file was provided
    "success": true,
    "formatting_applied": ["headers", "lists", "code_blocks"]
}
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextToMarkdownConverter:
    """Converts plain text to markdown format."""

    def __init__(
        self,
        auto_format: bool = True,
        preserve_linebreaks: bool = False,
        detect_code: bool = True,
        detect_lists: bool = True,
        detect_headers: bool = True
    ):
        """Initialize converter with preferences."""
        self.auto_format = auto_format
        self.preserve_linebreaks = preserve_linebreaks
        self.detect_code = detect_code
        self.detect_lists = detect_lists
        self.detect_headers = detect_headers
        self.formatting_applied = []

    def convert(self, text: str) -> str:
        """
        Convert plain text to markdown.

        Args:
            text: Plain text input

        Returns:
            Markdown formatted text
        """
        if not text:
            return ""

        # Reset formatting tracker
        self.formatting_applied = []

        # Process text
        result = text

        if self.auto_format:
            # Detect and format code blocks first (before other transformations)
            if self.detect_code:
                result = self._format_code_blocks(result)

            # Detect and format headers
            if self.detect_headers:
                result = self._format_headers(result)

            # Detect and format lists
            if self.detect_lists:
                result = self._format_lists(result)

            # Format paragraphs
            result = self._format_paragraphs(result)

        # Handle line breaks
        if not self.preserve_linebreaks:
            result = self._normalize_linebreaks(result)

        # Clean up extra whitespace
        result = self._cleanup_whitespace(result)

        return result

    def _format_code_blocks(self, text: str) -> str:
        """Detect and format code blocks."""
        lines = text.split('\n')
        result_lines = []
        in_code_block = False
        code_buffer = []
        code_start_index = -1

        for i, line in enumerate(lines):
            # Detect code-like patterns
            is_code_line = self._is_code_line(line)

            if is_code_line and not in_code_block:
                # Start of potential code block
                in_code_block = True
                code_start_index = i
                code_buffer = [line]
            elif is_code_line and in_code_block:
                # Continue code block
                code_buffer.append(line)
            elif not is_code_line and in_code_block:
                # Check if we have enough lines for a code block (at least 2)
                if len(code_buffer) >= 2:
                    # End code block
                    result_lines.append("```")
                    result_lines.extend(code_buffer)
                    result_lines.append("```")
                    self.formatting_applied.append("code_blocks")
                else:
                    # Not enough lines, treat as regular text
                    result_lines.extend(code_buffer)

                in_code_block = False
                code_buffer = []
                result_lines.append(line)
            else:
                # Regular line
                result_lines.append(line)

        # Handle code block at end of text
        if in_code_block and len(code_buffer) >= 2:
            result_lines.append("```")
            result_lines.extend(code_buffer)
            result_lines.append("```")
            self.formatting_applied.append("code_blocks")
        elif code_buffer:
            result_lines.extend(code_buffer)

        return '\n'.join(result_lines)

    def _is_code_line(self, line: str) -> bool:
        """Check if a line looks like code."""
        stripped = line.strip()

        if not stripped:
            return False

        # Code indicators
        code_patterns = [
            r'^\s{4,}',  # Indented (4+ spaces)
            r'^[\t]+',   # Indented (tabs)
            r'^\w+\s*=',  # Assignment
            r'def\s+\w+\(',  # Python function
            r'class\s+\w+',  # Python class
            r'import\s+\w+',  # Python import
            r'from\s+\w+\s+import',  # Python from import
            r'^\w+\(.*\)[:;]?$',  # Function call
            r'^\s*(if|for|while|return|const|let|var|function)\s+',  # Keywords
            r'[{}\[\]();]',  # Code punctuation
            r'^\s*//',  # Comments
            r'^\s*#(?!\s*[A-Z])',  # Python comment (not markdown header)
            r'^\s*<!--',  # HTML comment
        ]

        return any(re.search(pattern, line) for pattern in code_patterns)

    def _format_headers(self, text: str) -> str:
        """Detect and format headers."""
        lines = text.split('\n')
        result_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                result_lines.append(line)
                continue

            # Skip already formatted headers
            if stripped.startswith('#'):
                result_lines.append(line)
                continue

            # Skip code blocks
            if stripped.startswith('```'):
                result_lines.append(line)
                continue

            # Detect potential headers
            # 1. ALL CAPS lines (likely headers)
            if stripped.isupper() and len(stripped) > 3:
                result_lines.append(f"# {stripped.title()}")
                self.formatting_applied.append("headers")
                continue

            # 2. Title Case lines followed by blank line or separator
            if (i < len(lines) - 1 and
                stripped[0].isupper() and
                not stripped.endswith('.') and
                len(stripped.split()) <= 10):

                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

                # Check if followed by separator or blank
                if next_line == "" or set(next_line) <= {'-', '=', '_', '*'}:
                    # Determine header level
                    if set(next_line) == {'='}:
                        result_lines.append(f"# {stripped}")
                    elif set(next_line) == {'-'}:
                        result_lines.append(f"## {stripped}")
                    else:
                        result_lines.append(f"## {stripped}")
                    self.formatting_applied.append("headers")
                    continue

            result_lines.append(line)

        return '\n'.join(result_lines)

    def _format_lists(self, text: str) -> str:
        """Detect and format lists."""
        lines = text.split('\n')
        result_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                result_lines.append(line)
                continue

            # Skip already formatted lists
            if re.match(r'^[\*\-\+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
                result_lines.append(line)
                continue

            # Skip code blocks
            if stripped.startswith('```'):
                result_lines.append(line)
                continue

            # Detect bullet points
            # Patterns: "• item", "- item" (not markdown yet), "* item" (not markdown yet)
            bullet_match = re.match(r'^[•\-\*]\s+(.+)$', stripped)
            if bullet_match:
                result_lines.append(f"- {bullet_match.group(1)}")
                self.formatting_applied.append("lists")
                continue

            # Detect numbered lists
            # Patterns: "1) item", "1. item" (not markdown yet)
            numbered_match = re.match(r'^(\d+)[\.\)]\s+(.+)$', stripped)
            if numbered_match:
                num = numbered_match.group(1)
                content = numbered_match.group(2)
                result_lines.append(f"{num}. {content}")
                self.formatting_applied.append("lists")
                continue

            result_lines.append(line)

        return '\n'.join(result_lines)

    def _format_paragraphs(self, text: str) -> str:
        """Format paragraphs with proper spacing."""
        # Split into paragraphs (separated by blank lines)
        paragraphs = re.split(r'\n\s*\n', text)

        # Process each paragraph
        result_paragraphs = []
        for para in paragraphs:
            # Remove single line breaks within paragraph (unless preserving)
            if not self.preserve_linebreaks:
                para = para.replace('\n', ' ')

            # Clean up multiple spaces
            para = re.sub(r'\s+', ' ', para).strip()

            if para:
                result_paragraphs.append(para)

        # Join paragraphs with blank lines
        return '\n\n'.join(result_paragraphs)

    def _normalize_linebreaks(self, text: str) -> str:
        """Normalize line breaks."""
        # Remove excessive blank lines (max 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def _cleanup_whitespace(self, text: str) -> str:
        """Clean up whitespace."""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Don't strip lines in code blocks
            if line.strip().startswith('```'):
                cleaned_lines.append(line)
            else:
                # Remove trailing whitespace
                cleaned_lines.append(line.rstrip())

        # Join and remove trailing newlines
        result = '\n'.join(cleaned_lines).strip()

        # Add final newline
        return result + '\n'

    def validate_output_path(self, output_file: str, base_dir: str = "output") -> Path:
        """
        Validate and secure output file path.

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
        text = input_data.get("text")
        if text is None:
            print(json.dumps({
                "error": "Missing required parameter: text",
                "success": False
            }))
            sys.exit(1)

        auto_format = input_data.get("auto_format", True)
        preserve_linebreaks = input_data.get("preserve_linebreaks", False)
        detect_code = input_data.get("detect_code", True)
        detect_lists = input_data.get("detect_lists", True)
        detect_headers = input_data.get("detect_headers", True)
        output_file = input_data.get("output_file")

        # Create converter
        converter = TextToMarkdownConverter(
            auto_format=auto_format,
            preserve_linebreaks=preserve_linebreaks,
            detect_code=detect_code,
            detect_lists=detect_lists,
            detect_headers=detect_headers
        )

        # Convert to markdown
        markdown = converter.convert(text)

        # Build result
        result = {
            "markdown": markdown,
            "success": True,
            "formatting_applied": list(set(converter.formatting_applied)),
            "message": "Successfully converted text to markdown"
        }

        # Optionally write to file
        if output_file:
            try:
                validated_path = converter.validate_output_path(output_file)
                with open(validated_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                result["file_path"] = str(validated_path)
                result["message"] += f" and wrote to {validated_path}"
                logger.info(f"Wrote {len(markdown)} characters to {validated_path}")
            except ValueError as e:
                result["warning"] = f"Could not write to file: {str(e)}"

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception("Fatal error in text_to_markdown")
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
