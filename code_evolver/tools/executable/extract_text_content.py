#!/usr/bin/env python3
"""
Extract Text Content - Structured text extraction from documents.

Parses documents into paragraphs, sentences, and other structures.
Handles various text formats with robust error handling.
"""

import json
import sys
import re
from typing import Dict, Any, List, Optional

# Import node_runtime for calling other tools
try:
    from node_runtime import call_tool
except ImportError:
    def call_tool(tool_name, params):
        raise RuntimeError("node_runtime not available")


class TextExtractor:
    """Extracts structured text from raw content."""

    def __init__(self, min_paragraph_length: int = 50, preserve_formatting: bool = False):
        """Initialize the text extractor."""
        self.min_paragraph_length = min_paragraph_length
        self.preserve_formatting = preserve_formatting

    def extract_paragraphs(self, text: str) -> List[str]:
        """
        Extract paragraphs from text.

        Paragraphs are separated by blank lines or double newlines.
        """
        if self.preserve_formatting:
            # Split on double newlines
            paragraphs = re.split(r'\n\s*\n', text)
        else:
            # Split on double newlines and clean
            paragraphs = re.split(r'\n\s*\n', text)
            paragraphs = [p.replace('\n', ' ').strip() for p in paragraphs]

        # Filter out short paragraphs and empty ones
        paragraphs = [
            p for p in paragraphs
            if p.strip() and len(p.strip()) >= self.min_paragraph_length
        ]

        return paragraphs

    def extract_sentences(self, text: str) -> List[str]:
        """
        Extract sentences from text.

        Uses basic sentence boundary detection.
        """
        # Simple sentence splitting (can be enhanced with NLTK if needed)
        # Split on period, exclamation, question mark followed by space/newline
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def count_words(self, text: str) -> int:
        """Count words in text."""
        return len(re.findall(r'\b\w+\b', text))

    def extract(self, text: str, structure_level: str = "paragraphs") -> Dict[str, Any]:
        """
        Extract structured content from text.

        Args:
            text: Raw text content
            structure_level: Level of extraction ('paragraphs', 'sentences', 'raw')

        Returns:
            Dict with structured content and metadata
        """
        try:
            # Clean text if not preserving formatting
            if not self.preserve_formatting:
                # Remove excessive whitespace
                text = re.sub(r'[ \t]+', ' ', text)
                text = re.sub(r'\n{3,}', '\n\n', text)

            # Extract based on structure level
            paragraphs = []
            sentences = []

            if structure_level in ["paragraphs", "sentences"]:
                paragraphs = self.extract_paragraphs(text)

            if structure_level == "sentences":
                # Extract sentences from each paragraph
                for para in paragraphs:
                    para_sentences = self.extract_sentences(para)
                    sentences.extend(para_sentences)

            # Count statistics
            word_count = self.count_words(text)
            paragraph_count = len(paragraphs)
            sentence_count = len(sentences) if sentences else sum(
                len(self.extract_sentences(p)) for p in paragraphs
            )

            return {
                "raw_text": text,
                "paragraphs": paragraphs,
                "sentences": sentences,
                "word_count": word_count,
                "paragraph_count": paragraph_count,
                "sentence_count": sentence_count
            }

        except Exception as e:
            raise RuntimeError(f"Text extraction failed: {str(e)}")


def extract_text_content(
    document_id: str,
    structure_level: str = "paragraphs",
    min_paragraph_length: int = 50,
    preserve_formatting: bool = False
) -> Dict[str, Any]:
    """
    Extract structured text content from a stored document.

    Args:
        document_id: ID of the document in the store
        structure_level: Level of extraction
        min_paragraph_length: Minimum paragraph length
        preserve_formatting: Whether to preserve formatting

    Returns:
        Dict with extracted content and metadata
    """
    try:
        # Retrieve document from store
        retrieve_params = {
            "operation": "retrieve",
            "document_id": document_id
        }

        try:
            retrieve_result_json = call_tool("document_store", json.dumps(retrieve_params))
            retrieve_result = json.loads(retrieve_result_json)

            if not retrieve_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to retrieve document: {retrieve_result.get('error')}"
                }

            content = retrieve_result.get("content", "")
            metadata = retrieve_result.get("metadata", {})

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to retrieve document from store: {str(e)}"
            }

        # Extract text content
        extractor = TextExtractor(min_paragraph_length, preserve_formatting)
        extracted = extractor.extract(content, structure_level)

        # Store extracted content back in document store (as metadata)
        metadata["extracted"] = True
        metadata["structure_level"] = structure_level
        metadata["extraction_stats"] = {
            "word_count": extracted["word_count"],
            "paragraph_count": extracted["paragraph_count"],
            "sentence_count": extracted["sentence_count"]
        }

        # Update document with extraction metadata
        update_params = {
            "operation": "store",
            "document_id": document_id,
            "content": content,
            "metadata": metadata
        }

        try:
            call_tool("document_store", json.dumps(update_params))
        except Exception:
            # Non-fatal if update fails
            pass

        return {
            "success": True,
            "document_id": document_id,
            "structure_level": structure_level,
            "content": extracted,
            "metadata": metadata,
            "message": f"Extracted {extracted['paragraph_count']} paragraphs, "
                      f"{extracted['word_count']} words from document '{document_id}'"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def main():
    """Main entry point for extract_text_content tool."""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        params = json.loads(input_data) if input_data.strip() else {}

        # Get parameters
        document_id = params.get("document_id")
        if not document_id:
            result = {
                "success": False,
                "error": "Missing required parameter: document_id"
            }
            print(json.dumps(result, indent=2))
            return

        structure_level = params.get("structure_level", "paragraphs")
        min_paragraph_length = params.get("min_paragraph_length", 50)
        preserve_formatting = params.get("preserve_formatting", False)

        # Extract text content
        result = extract_text_content(
            document_id,
            structure_level,
            min_paragraph_length,
            preserve_formatting
        )

        # Output result
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except json.JSONDecodeError as e:
        result = {
            "success": False,
            "error": f"Invalid JSON input: {str(e)}"
        }
        print(json.dumps(result, indent=2))

    except Exception as e:
        result = {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
