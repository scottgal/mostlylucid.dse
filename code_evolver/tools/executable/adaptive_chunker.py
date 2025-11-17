#!/usr/bin/env python3
"""
Adaptive Document Chunker - Context-window-aware document chunking.

Intelligently chunks documents based on model tier and context windows.
Preserves context with overlapping chunks.
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import node_runtime for calling other tools
try:
    from node_runtime import call_tool
except ImportError:
    def call_tool(tool_name, params):
        raise RuntimeError("node_runtime not available")

# Try to import YAML for reading tier configuration
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Context window configurations for each tier
TIER_CONTEXT_WINDOWS = {
    "tier_1": 8192,    # Fast tier (Gemma2:2b)
    "tier_2": 8192,    # Standard tier (Llama3)
    "tier_3": 128000,  # Advanced tier (Mistral-nemo)
}

# Reserve tokens for summarization prompt and output
PROMPT_RESERVE = 1000
OUTPUT_RESERVE = 1024


class AdaptiveChunker:
    """Chunks documents adaptively based on context window."""

    def __init__(
        self,
        tier: str = "tier_2",
        max_chunk_tokens: Optional[int] = None,
        overlap_tokens: int = 200,
        chunk_by: str = "paragraphs"
    ):
        """Initialize the adaptive chunker."""
        self.tier = tier
        self.overlap_tokens = overlap_tokens
        self.chunk_by = chunk_by

        # Determine context window
        self.context_window = TIER_CONTEXT_WINDOWS.get(tier, 8192)

        # Calculate max chunk tokens (reserve space for prompt and output)
        if max_chunk_tokens:
            self.max_chunk_tokens = max_chunk_tokens
        else:
            self.max_chunk_tokens = self.context_window - PROMPT_RESERVE - OUTPUT_RESERVE

        # Ensure max_chunk_tokens is reasonable
        self.max_chunk_tokens = max(500, min(self.max_chunk_tokens, self.context_window - 2000))

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from text.

        Uses a simple heuristic: ~4 characters per token on average.
        This is conservative for better safety.
        """
        return len(text) // 4

    def chunk_by_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        Chunk text by paragraphs, respecting token limits.

        Args:
            paragraphs: List of paragraphs

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            # If single paragraph exceeds limit, split it
            if para_tokens > self.max_chunk_tokens:
                # Flush current chunk if not empty
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split large paragraph into sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sent_chunk = []
                sent_tokens = 0

                for sent in sentences:
                    sent_tok = self.estimate_tokens(sent)
                    if sent_tokens + sent_tok > self.max_chunk_tokens:
                        if sent_chunk:
                            chunks.append(" ".join(sent_chunk))
                        sent_chunk = [sent]
                        sent_tokens = sent_tok
                    else:
                        sent_chunk.append(sent)
                        sent_tokens += sent_tok

                if sent_chunk:
                    chunks.append(" ".join(sent_chunk))

            # If adding paragraph exceeds limit, start new chunk
            elif current_tokens + para_tokens > self.max_chunk_tokens:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens

            # Otherwise, add to current chunk
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def add_overlap(self, chunks: List[str]) -> List[str]:
        """
        Add overlap between chunks for context preservation.

        Args:
            chunks: List of chunks without overlap

        Returns:
            List of chunks with overlap
        """
        if len(chunks) <= 1 or self.overlap_tokens <= 0:
            return chunks

        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk - no prefix overlap
                overlapped.append(chunk)
            else:
                # Add suffix from previous chunk as prefix
                prev_chunk = chunks[i - 1]
                # Get last N tokens worth of characters from previous chunk
                overlap_chars = self.overlap_tokens * 4  # ~4 chars per token
                prefix = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk

                # Find last sentence boundary in prefix
                match = re.search(r'[.!?]\s+', prefix)
                if match:
                    prefix = prefix[match.end():]

                overlapped.append(f"{prefix}\n\n{chunk}")

        return overlapped

    def chunk(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk document content.

        Args:
            content: Extracted content with paragraphs/sentences

        Returns:
            List of chunk objects
        """
        # Get paragraphs or raw text
        if self.chunk_by == "paragraphs" and content.get("paragraphs"):
            paragraphs = content["paragraphs"]
            chunks = self.chunk_by_paragraphs(paragraphs)
        elif self.chunk_by == "sentences" and content.get("sentences"):
            # Treat sentences like paragraphs
            sentences = content["sentences"]
            chunks = self.chunk_by_paragraphs(sentences)
        else:
            # Fall back to raw text
            raw_text = content.get("raw_text", "")
            # Split into paragraphs
            paragraphs = re.split(r'\n\s*\n', raw_text)
            chunks = self.chunk_by_paragraphs(paragraphs)

        # Add overlap between chunks
        chunks = self.add_overlap(chunks)

        # Create chunk objects
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            chunk_objects.append({
                "chunk_id": i,
                "content": chunk_text,
                "token_count": self.estimate_tokens(chunk_text),
                "char_count": len(chunk_text)
            })

        return chunk_objects


def adaptive_chunk(
    document_id: str,
    tier: str = "tier_2",
    max_chunk_tokens: Optional[int] = None,
    overlap_tokens: int = 200,
    chunk_by: str = "paragraphs"
) -> Dict[str, Any]:
    """
    Chunk a document adaptively based on context window.

    Args:
        document_id: ID of the document in the store
        tier: Summarization tier
        max_chunk_tokens: Override max tokens per chunk
        overlap_tokens: Overlap between chunks
        chunk_by: Chunking strategy

    Returns:
        Dict with chunks and metadata
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

            metadata = retrieve_result.get("metadata", {})

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to retrieve document from store: {str(e)}"
            }

        # Check if document has been extracted
        if not metadata.get("extracted"):
            return {
                "success": False,
                "error": "Document has not been extracted. Run extract_text_content first."
            }

        # Get extracted content
        extract_params = {
            "operation": "retrieve",
            "document_id": document_id
        }

        # For chunking, we need the extracted content structure
        # Let's create a simple content structure from the raw text
        content = retrieve_result.get("content", "")

        # Simple paragraph extraction
        paragraphs = re.split(r'\n\s*\n', content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        content_obj = {
            "raw_text": content,
            "paragraphs": paragraphs
        }

        # Create chunker
        chunker = AdaptiveChunker(tier, max_chunk_tokens, overlap_tokens, chunk_by)

        # Chunk the document
        chunks = chunker.chunk(content_obj)

        # Calculate total tokens
        total_tokens = sum(c["token_count"] for c in chunks)

        # Store chunks in metadata
        metadata["chunked"] = True
        metadata["chunk_count"] = len(chunks)
        metadata["tier"] = tier
        metadata["context_window"] = chunker.context_window

        # Update document with chunking metadata
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

        # Store chunks as separate document
        chunks_doc_id = f"{document_id}_chunks"
        chunks_params = {
            "operation": "store",
            "document_id": chunks_doc_id,
            "content": json.dumps(chunks, indent=2),
            "metadata": {
                "type": "chunks",
                "parent_document": document_id,
                "tier": tier,
                "chunk_count": len(chunks)
            }
        }

        try:
            call_tool("document_store", json.dumps(chunks_params))
        except Exception:
            # Non-fatal if storage fails
            pass

        return {
            "success": True,
            "document_id": document_id,
            "tier": tier,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "total_tokens": total_tokens,
            "context_window": chunker.context_window,
            "metadata": metadata,
            "message": f"Created {len(chunks)} chunks from document '{document_id}' "
                      f"for {tier} (context: {chunker.context_window} tokens)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def main():
    """Main entry point for adaptive_chunker tool."""
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

        tier = params.get("tier", "tier_2")
        max_chunk_tokens = params.get("max_chunk_tokens")
        overlap_tokens = params.get("overlap_tokens", 200)
        chunk_by = params.get("chunk_by", "paragraphs")

        # Chunk document
        result = adaptive_chunk(
            document_id,
            tier,
            max_chunk_tokens,
            overlap_tokens,
            chunk_by
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
