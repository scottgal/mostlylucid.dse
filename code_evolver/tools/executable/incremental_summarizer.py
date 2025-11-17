#!/usr/bin/env python3
"""
Incremental Summarizer - Chunk-by-chunk document summarization.

Implements incremental summarization approach:
1. Process first chunk -> get summary
2. Feed summary + next chunk -> get updated summary
3. Repeat until all chunks processed
4. Return final summary
"""

import json
import sys
import time
from typing import Dict, Any, List, Optional

# Import node_runtime for calling other tools
try:
    from node_runtime import call_tool
except ImportError:
    def call_tool(tool_name, params):
        raise RuntimeError("node_runtime not available")


# Map tiers to summarizer tools
TIER_SUMMARIZERS = {
    "tier_1": "summarizer_fast",
    "tier_2": "summarizer_medium",
    "tier_3": "summarizer_large"
}


class IncrementalSummarizer:
    """Incrementally summarizes documents chunk by chunk."""

    def __init__(
        self,
        tier: str = "tier_2",
        summarizer_tool: Optional[str] = None,
        max_summary_length: int = 1024,
        detailed: bool = False
    ):
        """Initialize the incremental summarizer."""
        self.tier = tier
        self.max_summary_length = max_summary_length
        self.detailed = detailed

        # Select summarizer tool
        self.summarizer_tool = summarizer_tool or TIER_SUMMARIZERS.get(tier, "summarizer_medium")

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return len(text) // 4

    def summarize_chunk(
        self,
        content: str,
        previous_summary: str = ""
    ) -> str:
        """
        Summarize a chunk with optional previous summary.

        Args:
            content: The chunk content to summarize
            previous_summary: Previous summary to integrate

        Returns:
            New summary integrating previous summary and new content
        """
        # Build prompt
        if previous_summary:
            prompt = f"""Previous Summary:
{previous_summary}

---

New Content:
{content}

---

Create an updated summary that integrates the previous summary with the new content above. Maintain a cohesive narrative.

Summary:"""
        else:
            prompt = f"""{content}

---

Create a concise summary of the above text. Focus on the main ideas and key points.

Summary:"""

        # Call summarizer tool
        try:
            params = {
                "content": content,
                "previous_summary": f"Previous Summary:\n{previous_summary}\n\n---\n\n" if previous_summary else ""
            }
            result_json = call_tool(self.summarizer_tool, json.dumps(params))

            # Parse result - it might be a direct string or JSON
            try:
                result = json.loads(result_json)
                if isinstance(result, dict):
                    summary = result.get("summary") or result.get("content") or result_json
                else:
                    summary = result_json
            except json.JSONDecodeError:
                # Direct string response
                summary = result_json

            # Clean up summary
            if isinstance(summary, str):
                summary = summary.strip()
                # Remove common prefixes
                for prefix in ["Summary:", "summary:", "SUMMARY:"]:
                    if summary.startswith(prefix):
                        summary = summary[len(prefix):].strip()

            return summary

        except Exception as e:
            raise RuntimeError(f"Failed to summarize chunk: {str(e)}")

    def compress_summary(self, summary: str) -> str:
        """
        Compress summary if it exceeds max length.

        Args:
            summary: The summary to compress

        Returns:
            Compressed summary
        """
        summary_tokens = self.estimate_tokens(summary)

        if summary_tokens <= self.max_summary_length:
            return summary

        # Need to compress - summarize the summary
        try:
            params = {
                "content": summary,
                "previous_summary": ""
            }
            result_json = call_tool(self.summarizer_tool, json.dumps(params))

            try:
                result = json.loads(result_json)
                if isinstance(result, dict):
                    compressed = result.get("summary") or result.get("content") or result_json
                else:
                    compressed = result_json
            except json.JSONDecodeError:
                compressed = result_json

            if isinstance(compressed, str):
                compressed = compressed.strip()

            return compressed

        except Exception:
            # If compression fails, truncate
            target_chars = self.max_summary_length * 4
            return summary[:target_chars]

    def summarize(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Incrementally summarize all chunks.

        Args:
            chunks: List of chunk objects with 'content' field

        Returns:
            Dict with final summary and metadata
        """
        start_time = time.time()

        if not chunks:
            return {
                "summary": "",
                "iterations": 0,
                "processing_time": 0
            }

        # Track progress
        current_summary = ""
        iterations = 0

        # Process each chunk
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            if not content:
                continue

            # Summarize with previous summary
            current_summary = self.summarize_chunk(content, current_summary)
            iterations += 1

            # Compress if summary is getting too long and we have more chunks
            if i < len(chunks) - 1:  # Not the last chunk
                summary_tokens = self.estimate_tokens(current_summary)
                if summary_tokens > self.max_summary_length * 0.8:  # 80% threshold
                    current_summary = self.compress_summary(current_summary)

        # Final compression if needed
        current_summary = self.compress_summary(current_summary)

        processing_time = time.time() - start_time

        return {
            "summary": current_summary,
            "iterations": iterations,
            "processing_time": processing_time
        }


def incremental_summarize(
    document_id: str,
    tier: str = "tier_2",
    summarizer_tool: Optional[str] = None,
    max_summary_length: int = 1024,
    detailed: bool = False
) -> Dict[str, Any]:
    """
    Incrementally summarize a chunked document.

    Args:
        document_id: ID of the document (must have chunks)
        tier: Summarization tier
        summarizer_tool: Optional specific summarizer tool
        max_summary_length: Max summary length in tokens
        detailed: Generate detailed summary

    Returns:
        Dict with summary and metadata
    """
    try:
        # Retrieve chunks from store
        chunks_doc_id = f"{document_id}_chunks"
        retrieve_params = {
            "operation": "retrieve",
            "document_id": chunks_doc_id
        }

        try:
            retrieve_result_json = call_tool("document_store", json.dumps(retrieve_params))
            retrieve_result = json.loads(retrieve_result_json)

            if not retrieve_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to retrieve chunks: {retrieve_result.get('error')}. "
                            f"Make sure to run adaptive_chunker first."
                }

            chunks_json = retrieve_result.get("content", "[]")
            chunks = json.loads(chunks_json)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load chunks from store: {str(e)}"
            }

        if not chunks:
            return {
                "success": False,
                "error": "No chunks found for document"
            }

        # Get original document for metadata
        original_params = {
            "operation": "retrieve",
            "document_id": document_id
        }

        try:
            original_result_json = call_tool("document_store", json.dumps(original_params))
            original_result = json.loads(original_result_json)
            original_content = original_result.get("content", "")
            original_length = len(original_content)
        except Exception:
            original_length = 0

        # Create summarizer
        summarizer = IncrementalSummarizer(tier, summarizer_tool, max_summary_length, detailed)

        # Perform incremental summarization
        result = summarizer.summarize(chunks)

        summary = result["summary"]
        summary_length = len(summary)
        compression_ratio = original_length / summary_length if summary_length > 0 else 0

        # Store final summary
        summary_doc_id = f"{document_id}_summary"
        store_params = {
            "operation": "store",
            "document_id": summary_doc_id,
            "content": summary,
            "metadata": {
                "type": "summary",
                "parent_document": document_id,
                "tier": tier,
                "chunk_count": len(chunks),
                "iterations": result["iterations"],
                "compression_ratio": compression_ratio,
                "processing_time": result["processing_time"]
            }
        }

        try:
            call_tool("document_store", json.dumps(store_params))
        except Exception:
            # Non-fatal if storage fails
            pass

        return {
            "success": True,
            "document_id": document_id,
            "tier": tier,
            "summary": summary,
            "chunk_count": len(chunks),
            "iterations": result["iterations"],
            "metadata": {
                "original_length": original_length,
                "summary_length": summary_length,
                "compression_ratio": round(compression_ratio, 2),
                "processing_time": round(result["processing_time"], 2)
            },
            "message": f"Successfully summarized document '{document_id}' in {result['iterations']} iterations "
                      f"({len(chunks)} chunks, {compression_ratio:.1f}x compression)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def main():
    """Main entry point for incremental_summarizer tool."""
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
        summarizer_tool = params.get("summarizer_tool")
        max_summary_length = params.get("max_summary_length", 1024)
        detailed = params.get("detailed", False)

        # Summarize incrementally
        result = incremental_summarize(
            document_id,
            tier,
            summarizer_tool,
            max_summary_length,
            detailed
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
