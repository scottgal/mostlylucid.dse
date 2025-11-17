#!/usr/bin/env python3
"""
Document Store - In-memory document management for summarization workflows.

Provides persistent in-memory storage for documents with metadata.
Shared across all tools in the summarization workflow.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Global in-memory store (persists across invocations in same process)
# For true persistence, we use a JSON file
STORE_FILE = Path.home() / ".code_evolver" / "document_store.json"


class DocumentStore:
    """In-memory document store with disk persistence."""

    def __init__(self):
        """Initialize the document store."""
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.load_from_disk()

    def load_from_disk(self):
        """Load documents from disk if available."""
        try:
            if STORE_FILE.exists():
                with open(STORE_FILE, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
        except Exception as e:
            # Start with empty store if load fails
            self.documents = {}

    def save_to_disk(self):
        """Persist documents to disk."""
        try:
            STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STORE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Non-fatal error, just log it
            print(f"Warning: Could not persist to disk: {e}", file=sys.stderr)

    def store(self, document_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Store a document with metadata."""
        if not document_id:
            return {
                "success": False,
                "error": "document_id is required"
            }

        if content is None:
            return {
                "success": False,
                "error": "content is required"
            }

        # Create document entry
        doc = {
            "content": content,
            "metadata": metadata or {},
            "stored_at": datetime.now().isoformat()
        }

        # Add size to metadata
        doc["metadata"]["size"] = len(content)

        self.documents[document_id] = doc
        self.save_to_disk()

        return {
            "success": True,
            "operation": "store",
            "document_id": document_id,
            "message": f"Document '{document_id}' stored successfully",
            "metadata": doc["metadata"]
        }

    def retrieve(self, document_id: str) -> Dict[str, Any]:
        """Retrieve a document by ID."""
        if not document_id:
            return {
                "success": False,
                "error": "document_id is required"
            }

        if document_id not in self.documents:
            return {
                "success": False,
                "error": f"Document '{document_id}' not found"
            }

        doc = self.documents[document_id]
        return {
            "success": True,
            "operation": "retrieve",
            "document_id": document_id,
            "content": doc["content"],
            "metadata": doc["metadata"]
        }

    def exists(self, document_id: str) -> Dict[str, Any]:
        """Check if a document exists."""
        if not document_id:
            return {
                "success": False,
                "error": "document_id is required"
            }

        exists = document_id in self.documents
        return {
            "success": True,
            "operation": "exists",
            "document_id": document_id,
            "exists": exists
        }

    def delete(self, document_id: str) -> Dict[str, Any]:
        """Delete a document by ID."""
        if not document_id:
            return {
                "success": False,
                "error": "document_id is required"
            }

        if document_id not in self.documents:
            return {
                "success": False,
                "error": f"Document '{document_id}' not found"
            }

        del self.documents[document_id]
        self.save_to_disk()

        return {
            "success": True,
            "operation": "delete",
            "document_id": document_id,
            "message": f"Document '{document_id}' deleted successfully"
        }

    def list_documents(self) -> Dict[str, Any]:
        """List all stored documents."""
        docs = []
        for doc_id, doc in self.documents.items():
            docs.append({
                "document_id": doc_id,
                "metadata": doc["metadata"],
                "stored_at": doc.get("stored_at"),
                "content_length": len(doc["content"])
            })

        return {
            "success": True,
            "operation": "list",
            "count": len(docs),
            "documents": docs
        }

    def clear(self) -> Dict[str, Any]:
        """Clear all documents from the store."""
        count = len(self.documents)
        self.documents = {}
        self.save_to_disk()

        return {
            "success": True,
            "operation": "clear",
            "message": f"Cleared {count} document(s) from store"
        }


def main():
    """Main entry point for document store tool."""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        params = json.loads(input_data) if input_data.strip() else {}

        # Get operation
        operation = params.get("operation")
        if not operation:
            result = {
                "success": False,
                "error": "Missing required parameter: operation"
            }
            print(json.dumps(result, indent=2))
            return

        # Create store instance
        store = DocumentStore()

        # Execute operation
        if operation == "store":
            document_id = params.get("document_id")
            content = params.get("content")
            metadata = params.get("metadata")
            result = store.store(document_id, content, metadata)

        elif operation == "retrieve":
            document_id = params.get("document_id")
            result = store.retrieve(document_id)

        elif operation == "exists":
            document_id = params.get("document_id")
            result = store.exists(document_id)

        elif operation == "delete":
            document_id = params.get("document_id")
            result = store.delete(document_id)

        elif operation == "list":
            result = store.list_documents()

        elif operation == "clear":
            result = store.clear()

        else:
            result = {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }

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
