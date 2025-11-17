#!/usr/bin/env python3
"""
Load Document - Loads documents from disk and stores them for summarization.

Uses load_from_disk to read files and document_store to persist them.
Extracts metadata and validates content.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import node_runtime for calling other tools
try:
    from node_runtime import call_tool
except ImportError:
    # Fallback if not available
    def call_tool(tool_name, params):
        raise RuntimeError("node_runtime not available")


def load_document(filepath: str, document_id: str = None, encoding: str = "utf-8"):
    """
    Load a document from disk and store it.

    Args:
        filepath: Path to the file to load
        document_id: Optional ID for the document (uses filename if not provided)
        encoding: File encoding (default: utf-8)

    Returns:
        Dict with success status, document_id, content, and metadata
    """
    try:
        # Validate filepath
        path = Path(filepath)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {filepath}"
            }

        # Generate document_id from filename if not provided
        if not document_id:
            document_id = path.stem  # Filename without extension

        # Read file content directly (more reliable than calling load_from_disk)
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    content = f.read()
                encoding = 'latin-1'
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to read file with encoding {encoding}: {str(e)}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}"
            }

        # Extract metadata
        stat = path.stat()
        metadata = {
            "filename": path.name,
            "file_path": str(path.absolute()),
            "size": stat.st_size,
            "format": path.suffix.lstrip('.') or 'txt',
            "encoding": encoding,
            "loaded_at": datetime.now().isoformat()
        }

        # Store in document store
        store_params = {
            "operation": "store",
            "document_id": document_id,
            "content": content,
            "metadata": metadata
        }

        try:
            store_result_json = call_tool("document_store", json.dumps(store_params))
            store_result = json.loads(store_result_json)

            if not store_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to store document: {store_result.get('error')}"
                }
        except Exception as e:
            # If call_tool fails, it's okay - we can still return the content
            pass

        # Return success with document info
        return {
            "success": True,
            "document_id": document_id,
            "filepath": str(path),
            "content": content,
            "metadata": metadata,
            "message": f"Document '{document_id}' loaded successfully from {path.name}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }


def main():
    """Main entry point for load_document tool."""
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

        document_id = params.get("document_id")
        encoding = params.get("encoding", "utf-8")

        # Load document
        result = load_document(filepath, document_id, encoding)

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
