#!/usr/bin/env python3
"""
Summarize Document - Complete document summarization workflow.

Orchestrates the full pipeline:
1. Load document from disk
2. Extract structured text content
3. Chunk adaptively based on context window
4. Incrementally summarize chunks
5. Return final summary
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Import node_runtime for calling other tools
try:
    from node_runtime import call_tool
except ImportError:
    def call_tool(tool_name, params):
        raise RuntimeError("node_runtime not available")


# Tier selection thresholds (based on character count)
TIER_THRESHOLDS = {
    "tier_1": 32000,    # < 32K chars (~8K tokens) - use fast tier
    "tier_2": 128000,   # < 128K chars (~32K tokens) - use standard tier
    "tier_3": float('inf')  # >= 128K chars - use large context tier
}


def auto_select_tier(content_size: int) -> str:
    """
    Automatically select tier based on content size.

    Args:
        content_size: Size of content in characters

    Returns:
        Tier name (tier_1, tier_2, or tier_3)
    """
    if content_size < TIER_THRESHOLDS["tier_1"]:
        return "tier_1"
    elif content_size < TIER_THRESHOLDS["tier_2"]:
        return "tier_2"
    else:
        return "tier_3"


def summarize_document(
    filepath: str,
    tier: str = "tier_2",
    auto_tier: bool = True,
    max_summary_length: int = 1024,
    detailed: bool = False,
    save_summary: bool = False,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Complete document summarization workflow.

    Args:
        filepath: Path to document file
        tier: Summarization tier
        auto_tier: Auto-select tier based on size
        max_summary_length: Max summary length
        detailed: Generate detailed summary
        save_summary: Save summary to file
        output_path: Output file path

    Returns:
        Dict with summary and metadata
    """
    start_time = time.time()
    tier_auto_selected = False

    try:
        # Validate filepath
        path = Path(filepath)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {filepath}"
            }

        # Generate document ID from filepath
        document_id = path.stem

        # Step 1: Load document
        print(f"[1/4] Loading document: {filepath}...", file=sys.stderr)
        load_params = {
            "filepath": str(path),
            "document_id": document_id
        }

        try:
            load_result_json = call_tool("load_document", json.dumps(load_params))
            load_result = json.loads(load_result_json)

            if not load_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to load document: {load_result.get('error')}"
                }

            content_size = len(load_result.get("content", ""))

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load document: {str(e)}"
            }

        # Auto-select tier if enabled
        if auto_tier:
            tier = auto_select_tier(content_size)
            tier_auto_selected = True
            print(f"   Auto-selected tier: {tier} (document size: {content_size:,} chars)", file=sys.stderr)

        # Step 2: Extract text content
        print(f"[2/4] Extracting text content...", file=sys.stderr)
        extract_params = {
            "document_id": document_id,
            "structure_level": "paragraphs"
        }

        try:
            extract_result_json = call_tool("extract_text_content", json.dumps(extract_params))
            extract_result = json.loads(extract_result_json)

            if not extract_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to extract content: {extract_result.get('error')}"
                }

            paragraph_count = extract_result.get("content", {}).get("paragraph_count", 0)
            word_count = extract_result.get("content", {}).get("word_count", 0)
            print(f"   Extracted {paragraph_count} paragraphs, {word_count:,} words", file=sys.stderr)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to extract content: {str(e)}"
            }

        # Step 3: Chunk document adaptively
        print(f"[3/4] Chunking document for {tier}...", file=sys.stderr)
        chunk_params = {
            "document_id": document_id,
            "tier": tier,
            "chunk_by": "paragraphs"
        }

        try:
            chunk_result_json = call_tool("adaptive_chunker", json.dumps(chunk_params))
            chunk_result = json.loads(chunk_result_json)

            if not chunk_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to chunk document: {chunk_result.get('error')}"
                }

            chunk_count = chunk_result.get("chunk_count", 0)
            context_window = chunk_result.get("context_window", 0)
            print(f"   Created {chunk_count} chunks (context: {context_window:,} tokens)", file=sys.stderr)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to chunk document: {str(e)}"
            }

        # Step 4: Incrementally summarize
        print(f"[4/4] Generating summary...", file=sys.stderr)
        summarize_params = {
            "document_id": document_id,
            "tier": tier,
            "max_summary_length": max_summary_length,
            "detailed": detailed
        }

        try:
            summarize_result_json = call_tool("incremental_summarizer", json.dumps(summarize_params))
            summarize_result = json.loads(summarize_result_json)

            if not summarize_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to summarize: {summarize_result.get('error')}"
                }

            summary = summarize_result.get("summary", "")
            iterations = summarize_result.get("iterations", 0)
            metadata = summarize_result.get("metadata", {})

            print(f"   Summary generated in {iterations} iterations", file=sys.stderr)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to summarize: {str(e)}"
            }

        # Calculate total processing time
        processing_time = time.time() - start_time

        # Prepare result
        result = {
            "success": True,
            "filepath": str(path),
            "document_id": document_id,
            "tier": tier,
            "summary": summary,
            "metadata": {
                "original_size": content_size,
                "summary_size": len(summary),
                "compression_ratio": metadata.get("compression_ratio", 0),
                "chunk_count": chunk_count,
                "iterations": iterations,
                "processing_time": round(processing_time, 2),
                "tier_auto_selected": tier_auto_selected
            },
            "message": f"Successfully summarized '{path.name}' "
                      f"({content_size:,} chars -> {len(summary):,} chars, "
                      f"{metadata.get('compression_ratio', 0):.1f}x compression)"
        }

        # Save summary to file if requested
        if save_summary:
            if not output_path:
                output_path = path.parent / f"{path.stem}_summary.txt"
            else:
                output_path = Path(output_path)

            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(summary)

                result["output_file"] = str(output_path)
                result["message"] += f"\nSummary saved to: {output_path}"

            except Exception as e:
                result["message"] += f"\nWarning: Failed to save summary file: {str(e)}"

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def main():
    """Main entry point for summarize_document tool."""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        params = json.loads(input_data) if input_data.strip() else {}

        # Get parameters
        filepath = params.get("filepath")
        if not filepath:
            result = {
                "success": False,
                "error": "Missing required parameter: filepath"
            }
            print(json.dumps(result, indent=2))
            return

        tier = params.get("tier", "tier_2")
        auto_tier = params.get("auto_tier", True)
        max_summary_length = params.get("max_summary_length", 1024)
        detailed = params.get("detailed", False)
        save_summary = params.get("save_summary", False)
        output_path = params.get("output_path")

        # Summarize document
        result = summarize_document(
            filepath,
            tier,
            auto_tier,
            max_summary_length,
            detailed,
            save_summary,
            output_path
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
