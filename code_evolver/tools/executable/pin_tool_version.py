#!/usr/bin/env python3
"""
Pin Tool Version

Locks a workflow to a specific tool version.
Pinned versions are protected from trimming and auto-updates.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def pin_tool_version(
    tool_id: str,
    version: str = "current",
    workflow_id: str = None,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Pin a tool to a specific version

    Args:
        tool_id: ID of the tool to pin
        version: Version to pin to (or "current" for latest)
        workflow_id: Workflow that depends on this version (optional)
        reason: Why this version is pinned

    Returns:
        Result with pin information
    """
    sys.path.insert(0, '.')

    try:
        from src.config_manager import ConfigManager
        from src.ollama_client import OllamaClient
        from src.rag_memory import RAGMemory

        # Initialize
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = RAGMemory(ollama_client=client)

        # Load pins file
        pins_file = Path('.tool_pins.json')
        pins = {}

        if pins_file.exists():
            with open(pins_file, 'r') as f:
                pins = json.load(f)

        # Get current version if "current" specified
        if version == "current":
            # Get tool metadata from RAG
            tool_artifact = rag.get_artifact(tool_id)
            if tool_artifact:
                version = tool_artifact.metadata.get('version', '1.0.0')
            else:
                return {
                    'success': False,
                    'error': f'Tool not found: {tool_id}'
                }

        # Create pin entry
        pin_key = f"{tool_id}@{version}"
        if workflow_id:
            pin_key = f"{workflow_id}:{tool_id}@{version}"

        pins[pin_key] = {
            'tool_id': tool_id,
            'version': version,
            'workflow_id': workflow_id,
            'pinned_at': datetime.utcnow().isoformat() + 'Z',
            'reason': reason,
            'pinned_by': 'user'
        }

        # Save pins
        with open(pins_file, 'w') as f:
            json.dump(pins, f, indent=2)

        # Tag in RAG to prevent trimming
        version_tag = f"pinned:{tool_id}@{version}"
        if workflow_id:
            version_tag += f":workflow:{workflow_id}"

        # Find and tag the version artifact
        tool_version_id = f"{tool_id}_v{version.replace('.', '_')}"
        try:
            rag.add_tags(tool_version_id, [version_tag, 'pinned', 'enterprise'])
        except:
            # Version might not be in RAG yet
            pass

        return {
            'success': True,
            'tool_id': tool_id,
            'version': version,
            'workflow_id': workflow_id,
            'pin_key': pin_key,
            'message': f'Pinned {tool_id} to version {version}',
            'protected_from_trimming': True
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def unpin_tool_version(
    tool_id: str,
    version: str = None,
    workflow_id: str = None
) -> Dict[str, Any]:
    """
    Unpin a tool version

    Args:
        tool_id: ID of the tool
        version: Version to unpin (or None for all versions)
        workflow_id: Workflow to unpin from (or None for all workflows)

    Returns:
        Result with unpin information
    """
    sys.path.insert(0, '.')

    try:
        # Load pins file
        pins_file = Path('.tool_pins.json')
        if not pins_file.exists():
            return {
                'success': True,
                'message': 'No pins found',
                'unpinned': 0
            }

        with open(pins_file, 'r') as f:
            pins = json.load(f)

        # Find matching pins
        to_remove = []
        for pin_key, pin_data in pins.items():
            matches = True

            if pin_data['tool_id'] != tool_id:
                matches = False

            if version and pin_data['version'] != version:
                matches = False

            if workflow_id and pin_data.get('workflow_id') != workflow_id:
                matches = False

            if matches:
                to_remove.append(pin_key)

        # Remove pins
        for pin_key in to_remove:
            del pins[pin_key]

        # Save updated pins
        with open(pins_file, 'w') as f:
            json.dump(pins, f, indent=2)

        return {
            'success': True,
            'unpinned': len(to_remove),
            'unpinned_keys': to_remove,
            'message': f'Unpinned {len(to_remove)} version(s) of {tool_id}'
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def list_pins(
    tool_id: str = None,
    workflow_id: str = None
) -> Dict[str, Any]:
    """
    List all pinned versions

    Args:
        tool_id: Filter by tool ID (optional)
        workflow_id: Filter by workflow ID (optional)

    Returns:
        List of pinned versions
    """
    try:
        # Load pins file
        pins_file = Path('.tool_pins.json')
        if not pins_file.exists():
            return {
                'success': True,
                'pins': [],
                'count': 0,
                'message': 'No pins found'
            }

        with open(pins_file, 'r') as f:
            all_pins = json.load(f)

        # Filter pins
        filtered_pins = []
        for pin_key, pin_data in all_pins.items():
            matches = True

            if tool_id and pin_data['tool_id'] != tool_id:
                matches = False

            if workflow_id and pin_data.get('workflow_id') != workflow_id:
                matches = False

            if matches:
                pin_data['pin_key'] = pin_key
                filtered_pins.append(pin_data)

        return {
            'success': True,
            'pins': filtered_pins,
            'count': len(filtered_pins),
            'message': f'Found {len(filtered_pins)} pinned version(s)'
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                'success': False,
                'error': f'Invalid JSON input: {str(e)}'
            }))
            sys.exit(1)

        # Extract operation
        operation = input_data.get('operation', 'pin')
        tool_id = input_data.get('tool_id', '')
        version = input_data.get('version', 'current')
        workflow_id = input_data.get('workflow_id')
        reason = input_data.get('reason', '')

        # Execute operation
        if operation == 'pin':
            if not tool_id:
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameter: tool_id'
                }))
                sys.exit(1)

            result = pin_tool_version(tool_id, version, workflow_id, reason)

        elif operation == 'unpin':
            if not tool_id:
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameter: tool_id'
                }))
                sys.exit(1)

            result = unpin_tool_version(tool_id, version, workflow_id)

        elif operation == 'list':
            result = list_pins(tool_id, workflow_id)

        else:
            result = {
                'success': False,
                'error': f'Unknown operation: {operation}'
            }

        # Output result
        print(json.dumps(result, indent=2))

        if not result['success']:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Fatal error: {str(e)}'
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
