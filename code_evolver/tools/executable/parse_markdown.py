#!/usr/bin/env python3
"""
Parse Markdown to JSON Structure

Parses markdown documents and returns a structured JSON representation.
Extracts headers, lists, code blocks, links, and other markdown elements.

Features:
- Comprehensive markdown parsing
- Hierarchical header structure
- Code block extraction with language detection
- List parsing (ordered and unordered)
- Link and image extraction
- Table parsing
- Blockquote extraction
- Safe parsing with error handling

Input:
{
    "source": "file_path or markdown_text",  # required
    "source_type": "file|text",  # optional, default: "text"
    "include_raw_content": false  # optional, default: false
}

Output:
{
    "structure": {
        "headers": [...],
        "code_blocks": [...],
        "lists": [...],
        "links": [...],
        "images": [...],
        "tables": [...],
        "blockquotes": [...]
    },
    "metadata": {
        "total_headers": 5,
        "total_code_blocks": 3,
        ...
    },
    "success": true
}
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkdownParser:
    """Parses markdown into structured JSON."""

    # Regex patterns
    HEADER_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r'```(\w*)\n(.*?)\n```', re.DOTALL)
    INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')
    UNORDERED_LIST_PATTERN = re.compile(r'^[\*\-\+]\s+(.+)$', re.MULTILINE)
    ORDERED_LIST_PATTERN = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)
    LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
    IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')
    BLOCKQUOTE_PATTERN = re.compile(r'^>\s+(.+)$', re.MULTILINE)
    TABLE_ROW_PATTERN = re.compile(r'^\|(.+)\|$', re.MULTILINE)
    BOLD_PATTERN = re.compile(r'\*\*([^\*]+)\*\*')
    ITALIC_PATTERN = re.compile(r'\*([^\*]+)\*')
    STRIKETHROUGH_PATTERN = re.compile(r'~~([^~]+)~~')

    def __init__(self, include_raw_content: bool = False):
        """Initialize parser."""
        self.include_raw_content = include_raw_content

    def parse(self, markdown_text: str) -> Dict[str, Any]:
        """
        Parse markdown text into structured JSON.

        Args:
            markdown_text: Markdown content

        Returns:
            Structured representation
        """
        structure = {
            "headers": self._parse_headers(markdown_text),
            "code_blocks": self._parse_code_blocks(markdown_text),
            "lists": self._parse_lists(markdown_text),
            "links": self._parse_links(markdown_text),
            "images": self._parse_images(markdown_text),
            "tables": self._parse_tables(markdown_text),
            "blockquotes": self._parse_blockquotes(markdown_text)
        }

        # Add formatting elements
        structure["formatting"] = {
            "bold": self._extract_bold(markdown_text),
            "italic": self._extract_italic(markdown_text),
            "strikethrough": self._extract_strikethrough(markdown_text),
            "inline_code": self._extract_inline_code(markdown_text)
        }

        # Build metadata
        metadata = {
            "total_headers": len(structure["headers"]),
            "total_code_blocks": len(structure["code_blocks"]),
            "total_lists": len(structure["lists"]),
            "total_links": len(structure["links"]),
            "total_images": len(structure["images"]),
            "total_tables": len(structure["tables"]),
            "total_blockquotes": len(structure["blockquotes"]),
            "total_characters": len(markdown_text),
            "total_lines": markdown_text.count('\n') + 1
        }

        # Word count (approximate)
        metadata["word_count"] = len(re.findall(r'\w+', markdown_text))

        result = {
            "structure": structure,
            "metadata": metadata
        }

        if self.include_raw_content:
            result["raw_content"] = markdown_text

        return result

    def _parse_headers(self, text: str) -> List[Dict[str, Any]]:
        """Parse markdown headers."""
        headers = []
        for match in self.HEADER_PATTERN.finditer(text):
            level = len(match.group(1))
            content = match.group(2).strip()
            headers.append({
                "level": level,
                "content": content,
                "position": match.start()
            })
        return headers

    def _parse_code_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Parse code blocks."""
        code_blocks = []
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or "plaintext"
            code = match.group(2)
            code_blocks.append({
                "language": language,
                "code": code,
                "position": match.start(),
                "lines": code.count('\n') + 1
            })
        return code_blocks

    def _parse_lists(self, text: str) -> List[Dict[str, Any]]:
        """Parse lists (both ordered and unordered)."""
        lists = []

        # Parse unordered lists
        unordered_items = []
        for match in self.UNORDERED_LIST_PATTERN.finditer(text):
            unordered_items.append({
                "content": match.group(1).strip(),
                "position": match.start()
            })

        if unordered_items:
            lists.append({
                "type": "unordered",
                "items": unordered_items,
                "count": len(unordered_items)
            })

        # Parse ordered lists
        ordered_items = []
        for match in self.ORDERED_LIST_PATTERN.finditer(text):
            ordered_items.append({
                "content": match.group(1).strip(),
                "position": match.start()
            })

        if ordered_items:
            lists.append({
                "type": "ordered",
                "items": ordered_items,
                "count": len(ordered_items)
            })

        return lists

    def _parse_links(self, text: str) -> List[Dict[str, Any]]:
        """Parse links."""
        links = []
        for match in self.LINK_PATTERN.finditer(text):
            text_content = match.group(1)
            url = match.group(2)
            links.append({
                "text": text_content,
                "url": url,
                "position": match.start()
            })
        return links

    def _parse_images(self, text: str) -> List[Dict[str, Any]]:
        """Parse images."""
        images = []
        for match in self.IMAGE_PATTERN.finditer(text):
            alt_text = match.group(1)
            url = match.group(2)
            images.append({
                "alt_text": alt_text,
                "url": url,
                "position": match.start()
            })
        return images

    def _parse_tables(self, text: str) -> List[Dict[str, Any]]:
        """Parse tables."""
        tables = []
        lines = text.split('\n')

        table_start = None
        table_rows = []

        for i, line in enumerate(lines):
            if self.TABLE_ROW_PATTERN.match(line):
                if table_start is None:
                    table_start = i
                    table_rows = []

                # Parse row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                table_rows.append(cells)

            elif table_start is not None:
                # End of table
                if table_rows:
                    # Check if second row is separator
                    is_valid_table = len(table_rows) >= 2
                    if is_valid_table and all(
                        set(cell.strip()) <= {'-', ':', ' '}
                        for cell in table_rows[1]
                    ):
                        # Valid table
                        tables.append({
                            "headers": table_rows[0],
                            "rows": table_rows[2:],  # Skip separator row
                            "total_rows": len(table_rows) - 2,
                            "total_columns": len(table_rows[0]),
                            "position": table_start
                        })

                table_start = None
                table_rows = []

        # Handle table at end of document
        if table_start is not None and table_rows:
            is_valid_table = len(table_rows) >= 2
            if is_valid_table and all(
                set(cell.strip()) <= {'-', ':', ' '}
                for cell in table_rows[1]
            ):
                tables.append({
                    "headers": table_rows[0],
                    "rows": table_rows[2:],
                    "total_rows": len(table_rows) - 2,
                    "total_columns": len(table_rows[0]),
                    "position": table_start
                })

        return tables

    def _parse_blockquotes(self, text: str) -> List[Dict[str, Any]]:
        """Parse blockquotes."""
        blockquotes = []
        for match in self.BLOCKQUOTE_PATTERN.finditer(text):
            content = match.group(1).strip()
            blockquotes.append({
                "content": content,
                "position": match.start()
            })
        return blockquotes

    def _extract_bold(self, text: str) -> List[str]:
        """Extract bold text."""
        return [match.group(1) for match in self.BOLD_PATTERN.finditer(text)]

    def _extract_italic(self, text: str) -> List[str]:
        """Extract italic text."""
        return [match.group(1) for match in self.ITALIC_PATTERN.finditer(text)]

    def _extract_strikethrough(self, text: str) -> List[str]:
        """Extract strikethrough text."""
        return [match.group(1) for match in self.STRIKETHROUGH_PATTERN.finditer(text)]

    def _extract_inline_code(self, text: str) -> List[str]:
        """Extract inline code."""
        return [match.group(1) for match in self.INLINE_CODE_PATTERN.finditer(text)]


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
        source = input_data.get("source")
        if not source:
            print(json.dumps({
                "error": "Missing required parameter: source",
                "success": False
            }))
            sys.exit(1)

        source_type = input_data.get("source_type", "text")
        include_raw_content = input_data.get("include_raw_content", False)

        # Get markdown text
        if source_type == "file":
            source_path = Path(source)
            if not source_path.exists():
                print(json.dumps({
                    "error": f"File not found: {source}",
                    "success": False
                }))
                sys.exit(1)

            try:
                markdown_text = source_path.read_text(encoding='utf-8')
            except Exception as e:
                print(json.dumps({
                    "error": f"Error reading file: {str(e)}",
                    "success": False
                }))
                sys.exit(1)
        else:
            markdown_text = source

        # Parse markdown
        parser = MarkdownParser(include_raw_content=include_raw_content)
        result = parser.parse(markdown_text)

        # Add success flag
        result["success"] = True
        result["message"] = f"Successfully parsed markdown ({result['metadata']['word_count']} words)"

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception("Fatal error in parse_markdown")
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
