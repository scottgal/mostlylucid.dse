#!/usr/bin/env python3
"""
Trim Tool Versions

Keeps tools tidy by retaining only:
- Original version (v1.0.0) - always kept
- Current YAML definition - ultimate backup
- Last 2-3 versions for rollback

Older versions are archived or deleted.
"""

import json
import sys
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string like '1.2.3' into (1, 2, 3)"""
    parts = version_str.split('.')
    return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0, int(parts[2]) if len(parts) > 2 else 0)


def get_tool_versions(tool_dir: Path, tool_id: str) -> List[Dict[str, Any]]:
    """
    Get all versions of a tool

    Returns:
        List of version info dicts sorted by version number
    """
    versions = []

    # Pattern: tool_id_v1_2_3.py
    pattern = re.compile(rf"{re.escape(tool_id)}_v(\d+)_(\d+)_(\d+)\.py")

    for file in tool_dir.glob(f"{tool_id}_v*.py"):
        match = pattern.match(file.name)
        if match:
            major, minor, patch = match.groups()
            version_str = f"{major}.{minor}.{patch}"

            versions.append({
                'file': file,
                'version': version_str,
                'version_tuple': (int(major), int(minor), int(patch)),
                'size': file.stat().st_size,
                'modified': datetime.fromtimestamp(file.stat().st_mtime)
            })

    # Sort by version (oldest first)
    versions.sort(key=lambda x: x['version_tuple'])

    return versions


def trim_tool_versions(
    tool_id: str,
    keep_recent: int = 3,
    archive_old: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Trim old versions of a tool, keeping only recent ones

    Args:
        tool_id: ID of the tool to trim
        keep_recent: Number of recent versions to keep (default: 3)
        archive_old: Archive instead of delete (default: True)
        dry_run: Don't actually delete, just report what would happen

    Returns:
        Result with trimmed files and statistics
    """
    try:
        # Find tool directory
        tools_root = Path('tools/executable')
        tool_dir = tools_root / tool_id

        if not tool_dir.exists():
            # Tool might be in flat structure (old style)
            tool_dir = tools_root

        # Get all versions
        versions = get_tool_versions(tool_dir, tool_id)

        if len(versions) <= keep_recent + 1:  # +1 for original
            return {
                'success': True,
                'tool_id': tool_id,
                'total_versions': len(versions),
                'kept': len(versions),
                'trimmed': 0,
                'message': f'No trimming needed ({len(versions)} versions <= {keep_recent + 1} threshold)'
            }

        # Determine which to keep
        original = versions[0]  # Always keep v1.0.0
        recent = versions[-(keep_recent):]  # Keep last N versions
        to_trim = [v for v in versions[1:-keep_recent]]  # Trim middle versions

        kept_versions = [original] + recent

        # Perform trimming
        trimmed_files = []
        archive_dir = tool_dir / 'archived_versions'

        for version in to_trim:
            file_path = version['file']

            if dry_run:
                trimmed_files.append({
                    'file': str(file_path),
                    'version': version['version'],
                    'action': 'would_archive' if archive_old else 'would_delete',
                    'size': version['size']
                })
            else:
                if archive_old:
                    # Move to archive
                    archive_dir.mkdir(exist_ok=True)
                    archive_path = archive_dir / file_path.name
                    shutil.move(str(file_path), str(archive_path))

                    trimmed_files.append({
                        'file': str(file_path),
                        'version': version['version'],
                        'action': 'archived',
                        'archived_to': str(archive_path),
                        'size': version['size']
                    })
                else:
                    # Delete
                    file_path.unlink()

                    trimmed_files.append({
                        'file': str(file_path),
                        'version': version['version'],
                        'action': 'deleted',
                        'size': version['size']
                    })

        # Calculate space saved
        space_saved = sum(f['size'] for f in trimmed_files)

        return {
            'success': True,
            'tool_id': tool_id,
            'total_versions': len(versions),
            'kept': len(kept_versions),
            'trimmed': len(trimmed_files),
            'kept_versions': [v['version'] for v in kept_versions],
            'trimmed_files': trimmed_files,
            'space_saved_bytes': space_saved,
            'space_saved_kb': space_saved / 1024,
            'archive_location': str(archive_dir) if archive_old else None,
            'dry_run': dry_run,
            'message': f'Kept {len(kept_versions)} versions, trimmed {len(trimmed_files)}'
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def trim_all_tools(
    keep_recent: int = 3,
    archive_old: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Trim versions for ALL tools

    Returns:
        Summary of all tools trimmed
    """
    tools_root = Path('tools/executable')

    results = []
    total_saved = 0
    total_trimmed = 0

    # Find all tool directories
    for tool_dir in tools_root.iterdir():
        if tool_dir.is_dir():
            tool_id = tool_dir.name

            # Skip special directories
            if tool_id.startswith('.') or tool_id == 'archived_versions':
                continue

            result = trim_tool_versions(tool_id, keep_recent, archive_old, dry_run)

            if result['success'] and result['trimmed'] > 0:
                results.append(result)
                total_saved += result['space_saved_bytes']
                total_trimmed += result['trimmed']

    return {
        'success': True,
        'tools_processed': len(results),
        'total_trimmed': total_trimmed,
        'total_space_saved_bytes': total_saved,
        'total_space_saved_kb': total_saved / 1024,
        'total_space_saved_mb': total_saved / (1024 * 1024),
        'results': results,
        'dry_run': dry_run
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

        # Extract parameters
        tool_id = input_data.get('tool_id', '')
        keep_recent = input_data.get('keep_recent', 3)
        archive_old = input_data.get('archive_old', True)
        dry_run = input_data.get('dry_run', False)
        trim_all = input_data.get('trim_all', False)

        # Trim single tool or all tools
        if trim_all:
            result = trim_all_tools(keep_recent, archive_old, dry_run)
        else:
            if not tool_id:
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameter: tool_id (or set trim_all: true)'
                }))
                sys.exit(1)

            result = trim_tool_versions(tool_id, keep_recent, archive_old, dry_run)

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
