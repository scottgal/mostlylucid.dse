#!/usr/bin/env python3
"""
Workflow Datastore - Persistent storage for workflow data.

Usage:
    python workflow_datastore.py <action> <key> [data]

Actions:
    save <key> <data>  - Save data to key
    load <key>         - Load data from key
"""
import sys
import json
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing arguments. Usage: workflow_datastore.py <action> <key> [data]"}))
        sys.exit(1)

    action = sys.argv[1]
    key = sys.argv[2]

    # Datastore directory
    datastore_dir = Path(__file__).parent.parent.parent / "workflow_datastore"
    datastore_dir.mkdir(exist_ok=True)

    # Sanitize key for filesystem
    safe_key = "".join(c for c in key if c.isalnum() or c in "_-.")
    data_file = datastore_dir / f"{safe_key}.json"

    if action == "save":
        # Get data from stdin or argument
        if len(sys.argv) > 3:
            data = sys.argv[3]
            try:
                # Try to parse as JSON
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                # Store as string
                parsed_data = data
        else:
            # Read from stdin
            try:
                parsed_data = json.load(sys.stdin)
            except json.JSONDecodeError:
                parsed_data = sys.stdin.read()

        # Save to file
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2)

        print(json.dumps({"success": True, "key": key, "message": f"Data saved to {safe_key}"}))

    elif action == "load":
        # Load from file
        if not data_file.exists():
            print(json.dumps({"error": f"Key '{key}' not found"}))
            sys.exit(1)

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(json.dumps({"success": True, "key": key, "data": data}))

    elif action == "list":
        # List all keys
        keys = [f.stem for f in datastore_dir.glob("*.json")]
        print(json.dumps({"success": True, "keys": keys}))

    elif action == "delete":
        # Delete key
        if data_file.exists():
            data_file.unlink()
            print(json.dumps({"success": True, "key": key, "message": f"Deleted {safe_key}"}))
        else:
            print(json.dumps({"error": f"Key '{key}' not found"}))
            sys.exit(1)

    else:
        print(json.dumps({"error": f"Unknown action: {action}. Use 'save', 'load', 'list', or 'delete'"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
