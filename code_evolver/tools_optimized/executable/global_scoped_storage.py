#!/usr/bin/env python3
"""
Global-Scoped Storage
System-wide shared key-value storage using Python's shelve.
"""

import sys
import json
import shelve
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import filelock

# Storage directory
STORAGE_DIR = Path.home() / ".code_evolver" / "storage" / "global"
STORAGE_FILE = "global"


class GlobalScopedStorage:
    """Global key-value storage with file-based persistence."""

    def __init__(self):
        # Ensure storage directory exists
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions
        os.chmod(STORAGE_DIR, 0o700)

    def _get_storage_path(self) -> Path:
        """Get storage file path."""
        return STORAGE_DIR / STORAGE_FILE

    def _get_lock_path(self) -> Path:
        """Get lock file path."""
        return STORAGE_DIR / f"{STORAGE_FILE}.lock"

    def get(self, key: str, default: Any = None) -> Dict[str, Any]:
        """Get value from global storage."""
        lock_path = self._get_lock_path()
        storage_path = self._get_storage_path()

        try:
            with filelock.FileLock(lock_path, timeout=5):
                with shelve.open(str(storage_path), flag="c") as db:
                    value = db.get(key, default)
                    exists = key in db

            return {
                "success": True,
                "operation": "get",
                "key": key,
                "value": value,
                "exists": exists,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set(self, key: str, value: Any) -> Dict[str, Any]:
        """Set value in global storage."""
        if len(key) > 256:
            return {"success": False, "error": "Key too long (max 256 chars)"}

        # Estimate value size (rough check)
        try:
            value_json = json.dumps(value)
            if len(value_json) > 10 * 1024 * 1024:  # 10 MB
                return {"success": False, "error": "Value too large (max 10 MB)"}
        except (TypeError, ValueError) as e:
            return {"success": False, "error": f"Value not JSON-serializable: {e}"}

        lock_path = self._get_lock_path()
        storage_path = self._get_storage_path()

        try:
            with filelock.FileLock(lock_path, timeout=5):
                with shelve.open(str(storage_path), flag="c") as db:
                    db[key] = value

            # Set restrictive permissions on storage file
            os.chmod(storage_path, 0o600)

            return {"success": True, "operation": "set", "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete(self, key: str) -> Dict[str, Any]:
        """Delete key from global storage."""
        lock_path = self._get_lock_path()
        storage_path = self._get_storage_path()

        try:
            with filelock.FileLock(lock_path, timeout=5):
                with shelve.open(str(storage_path), flag="c") as db:
                    if key in db:
                        del db[key]
                        deleted = True
                    else:
                        deleted = False

            return {
                "success": True,
                "operation": "delete",
                "key": key,
                "deleted": deleted,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def exists(self, key: str) -> Dict[str, Any]:
        """Check if key exists in global storage."""
        lock_path = self._get_lock_path()
        storage_path = self._get_storage_path()

        try:
            with filelock.FileLock(lock_path, timeout=5):
                with shelve.open(str(storage_path), flag="c") as db:
                    exists = key in db

            return {
                "success": True,
                "operation": "exists",
                "key": key,
                "exists": exists,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_keys(self) -> Dict[str, Any]:
        """List all keys in global storage."""
        lock_path = self._get_lock_path()
        storage_path = self._get_storage_path()

        try:
            with filelock.FileLock(lock_path, timeout=5):
                with shelve.open(str(storage_path), flag="c") as db:
                    keys = list(db.keys())

            return {
                "success": True,
                "operation": "list",
                "keys": keys,
                "size": len(keys),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def size(self) -> Dict[str, Any]:
        """Get number of keys in global storage."""
        result = self.list_keys()
        if result["success"]:
            return {
                "success": True,
                "operation": "size",
                "size": result["size"],
            }
        return result

    def clear(self) -> Dict[str, Any]:
        """Clear all data from global storage."""
        lock_path = self._get_lock_path()
        storage_path = self._get_storage_path()

        try:
            with filelock.FileLock(lock_path, timeout=5):
                with shelve.open(str(storage_path), flag="c") as db:
                    db.clear()

            return {"success": True, "operation": "clear"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute storage operation."""
        operation = input_data.get("operation")

        if operation == "get":
            key = input_data.get("key")
            if not key:
                return {"success": False, "error": "key is required for get"}
            default = input_data.get("default")
            return self.get(key, default)

        elif operation == "set":
            key = input_data.get("key")
            if not key:
                return {"success": False, "error": "key is required for set"}
            if "value" not in input_data:
                return {"success": False, "error": "value is required for set"}
            value = input_data["value"]
            return self.set(key, value)

        elif operation == "delete":
            key = input_data.get("key")
            if not key:
                return {"success": False, "error": "key is required for delete"}
            return self.delete(key)

        elif operation == "exists":
            key = input_data.get("key")
            if not key:
                return {"success": False, "error": "key is required for exists"}
            return self.exists(key)

        elif operation in ("list", "keys"):
            return self.list_keys()

        elif operation == "size":
            return self.size()

        elif operation == "clear":
            return self.clear()

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}


def main():
    """Main entry point."""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()
        if not input_text:
            print(json.dumps({"success": False, "error": "No input provided"}))
            sys.exit(1)

        # Parse JSON input
        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid JSON: {e}"}))
            sys.exit(1)

        # Execute operation
        storage = GlobalScopedStorage()
        result = storage.execute(input_data)

        # Output result
        print(json.dumps(result, indent=2))

        # Exit with appropriate code
        sys.exit(0 if result.get("success") else 1)

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
