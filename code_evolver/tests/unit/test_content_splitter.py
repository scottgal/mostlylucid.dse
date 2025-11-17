#!/usr/bin/env python3
"""
Unit Tests for Content Splitter Tool
"""

import pytest
import json
import subprocess
import sys
from pathlib import Path


def test_content_splitter_paragraph_strategy():
    """Test paragraph splitting strategy."""
    # Create content with multiple paragraphs that will definitely split
    content = """Paragraph one is here with lots of additional text to make it longer and ensure we exceed the chunk size limit when combined with other paragraphs.

Paragraph two is here with lots of additional text to make it longer and ensure we exceed the chunk size limit when combined with other paragraphs.

Paragraph three is here with lots of additional text to make it longer and ensure we exceed the chunk size limit when combined with other paragraphs.

Paragraph four is here with lots of additional text to make it longer and ensure we exceed the chunk size limit when combined with other paragraphs."""

    input_data = {
        "content": content,
        "max_chunk_size": 100,  # 100 tokens = ~400 chars per chunk
        "strategy": "paragraph"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Failed with: {result.stderr}"

    output = json.loads(result.stdout)

    assert "chunks" in output
    assert "num_chunks" in output
    assert output["strategy_used"] == "paragraph"
    assert output["num_chunks"] >= 1  # At least one chunk
    assert len(output["chunks"]) == output["num_chunks"]


def test_content_splitter_sentence_strategy():
    """Test sentence splitting strategy."""
    content = "First sentence. Second sentence. Third sentence. Fourth sentence."

    input_data = {
        "content": content,
        "max_chunk_size": 20,  # Small chunks
        "strategy": "sentence"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["strategy_used"] == "sentence"
    assert output["num_chunks"] >= 2


def test_content_splitter_fixed_strategy():
    """Test fixed-size splitting strategy."""
    content = "A" * 1000  # 1000 character string

    input_data = {
        "content": content,
        "max_chunk_size": 50,  # 200 chars
        "strategy": "fixed"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["strategy_used"] == "fixed"
    assert output["num_chunks"] >= 5  # 1000 chars / 200 chars = 5 chunks


def test_content_splitter_empty_content():
    """Test handling of empty content."""
    input_data = {
        "content": "",
        "max_chunk_size": 100,
        "strategy": "paragraph"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["num_chunks"] == 1  # Empty string results in 1 chunk
    assert output["chunks"][0] == ""


def test_content_splitter_metadata():
    """Test metadata in output."""
    content = "Test content for metadata checking."

    input_data = {
        "content": content,
        "max_chunk_size": 100,
        "strategy": "paragraph"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert "metadata" in output
    assert "avg_chunk_length" in output["metadata"]
    assert "max_chunk_length" in output["metadata"]
    assert "min_chunk_length" in output["metadata"]
    assert "chunk_lengths" in output


def test_content_splitter_default_strategy():
    """Test default strategy when not specified."""
    content = "Test content."

    input_data = {
        "content": content,
        "max_chunk_size": 100
        # No strategy specified
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    # Default should be paragraph
    assert output["strategy_used"] == "paragraph"


def test_content_splitter_large_content():
    """Test with large content."""
    # Create 100k character string
    content = "Lorem ipsum dolor sit amet. " * 4000

    input_data = {
        "content": content,
        "max_chunk_size": 8000,  # ~32k chars per chunk
        "strategy": "paragraph"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/content_splitter.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10  # Should complete within 10 seconds
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["num_chunks"] >= 1
    assert output["original_length"] == len(content)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
