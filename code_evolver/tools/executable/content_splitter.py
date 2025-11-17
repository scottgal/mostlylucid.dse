#!/usr/bin/env python3
"""
Content Splitter - Split Large Content for Progressive Summarization

Intelligently splits content into chunks for progressive summarization.

Features:
- Respects paragraph boundaries
- Configurable chunk size
- Maintains context between chunks
- Supports multiple splitting strategies

USAGE:
    echo '{"content": "...", "max_chunk_size": 8000}' | python content_splitter.py

INPUT (stdin):
    {
        "content": "text to split",
        "max_chunk_size": 8000,  # tokens
        "strategy": "paragraph"  # or "sentence", "fixed"
    }

OUTPUT (stdout):
    {
        "chunks": ["chunk1", "chunk2", ...],
        "num_chunks": 3,
        "strategy_used": "paragraph",
        "metadata": {...}
    }
"""

import sys
import json
import re
from typing import List, Dict, Any


def split_by_paragraphs(content: str, max_chunk_size: int) -> List[str]:
    """
    Split content by paragraphs, respecting max chunk size.

    Args:
        content: Content to split
        max_chunk_size: Max tokens per chunk

    Returns:
        List of content chunks
    """

    # Estimate chars per chunk (4 chars ~= 1 token)
    max_chars = max_chunk_size * 4

    # Split on double newlines (paragraphs)
    paragraphs = content.split('\n\n')

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_length = len(para)

        if current_length + para_length > max_chars:
            # Start new chunk
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_length = para_length
        else:
            current_chunk.append(para)
            current_length += para_length

    # Add last chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def split_by_sentences(content: str, max_chunk_size: int) -> List[str]:
    """
    Split content by sentences.

    More granular than paragraphs.
    """

    max_chars = max_chunk_size * 4

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', content)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sent_length = len(sentence)

        if current_length + sent_length > max_chars:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = sent_length
        else:
            current_chunk.append(sentence)
            current_length += sent_length

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def split_fixed(content: str, max_chunk_size: int) -> List[str]:
    """
    Split content into fixed-size chunks.

    Simple but may break in middle of sentences.
    """

    max_chars = max_chunk_size * 4
    chunks = []

    for i in range(0, len(content), max_chars):
        chunk = content[i:i + max_chars]
        chunks.append(chunk)

    return chunks


def split_content(
    content: str,
    max_chunk_size: int,
    strategy: str = "paragraph"
) -> Dict[str, Any]:
    """
    Split content with specified strategy.

    Args:
        content: Content to split
        max_chunk_size: Max tokens per chunk
        strategy: "paragraph", "sentence", or "fixed"

    Returns:
        Dict with chunks and metadata
    """

    if strategy == "paragraph":
        chunks = split_by_paragraphs(content, max_chunk_size)
    elif strategy == "sentence":
        chunks = split_by_sentences(content, max_chunk_size)
    elif strategy == "fixed":
        chunks = split_fixed(content, max_chunk_size)
    else:
        # Default to paragraph
        chunks = split_by_paragraphs(content, max_chunk_size)
        strategy = "paragraph"

    return {
        "chunks": chunks,
        "num_chunks": len(chunks),
        "strategy_used": strategy,
        "original_length": len(content),
        "chunk_lengths": [len(c) for c in chunks],
        "metadata": {
            "avg_chunk_length": sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
            "max_chunk_length": max(len(c) for c in chunks) if chunks else 0,
            "min_chunk_length": min(len(c) for c in chunks) if chunks else 0
        }
    }


def main():
    """Read from stdin, split content, output JSON."""

    try:
        # Read input
        input_data = sys.stdin.read()

        if not input_data.strip():
            print(json.dumps({
                "error": "No input provided",
                "chunks": []
            }), file=sys.stdout)
            sys.exit(1)

        # Parse JSON input
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            # Treat as raw content
            data = {
                "content": input_data,
                "max_chunk_size": 8000,
                "strategy": "paragraph"
            }

        content = data.get("content", "")
        max_chunk_size = data.get("max_chunk_size", 8000)
        strategy = data.get("strategy", "paragraph")

        # Split content
        result = split_content(content, max_chunk_size, strategy)

        # Output JSON
        print(json.dumps(result, indent=2), file=sys.stdout)

        sys.exit(0)

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "chunks": []
        }), file=sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
