#!/usr/bin/env python3
"""
Selective File Copier
Copies only required files for tree-shaken deployments
"""
import json
import sys
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any


def copy_files(file_list: List[str], source_root: str, dest_root: str) -> Dict[str, Any]:
    """
    Copy files maintaining directory structure

    Args:
        file_list: List of file paths relative to source_root
        source_root: Source directory root
        dest_root: Destination directory root

    Returns:
        Dictionary with copy results
    """
    source_path = Path(source_root)
    dest_path = Path(dest_root)

    results = {
        'success': True,
        'copied_files': [],
        'failed_files': [],
        'created_dirs': [],
        'total_size_bytes': 0
    }

    # Create destination root
    dest_path.mkdir(parents=True, exist_ok=True)

    for file_rel in file_list:
        try:
            src_file = source_path / file_rel
            dst_file = dest_path / file_rel

            # Skip if source doesn't exist
            if not src_file.exists():
                results['failed_files'].append({
                    'file': file_rel,
                    'reason': 'Source file not found'
                })
                continue

            # Create destination directory
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            if str(dst_file.parent) not in results['created_dirs']:
                results['created_dirs'].append(str(dst_file.parent))

            # Copy file
            shutil.copy2(src_file, dst_file)

            # Track results
            file_size = src_file.stat().st_size
            results['copied_files'].append({
                'file': file_rel,
                'size_bytes': file_size
            })
            results['total_size_bytes'] += file_size

        except Exception as e:
            results['failed_files'].append({
                'file': file_rel,
                'reason': str(e)
            })
            results['success'] = False

    # Add statistics
    results['stats'] = {
        'total_files': len(file_list),
        'copied': len(results['copied_files']),
        'failed': len(results['failed_files']),
        'total_size_mb': round(results['total_size_bytes'] / (1024 * 1024), 2)
    }

    return results


def create_init_files(dest_root: str, python_dirs: List[str]):
    """Create __init__.py files in Python package directories"""
    dest_path = Path(dest_root)

    for py_dir in python_dirs:
        dir_path = dest_path / py_dir
        if dir_path.exists() and dir_path.is_dir():
            init_file = dir_path / '__init__.py'
            if not init_file.exists():
                init_file.touch()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'Missing configuration JSON argument'
        }))
        sys.exit(1)

    try:
        # Parse configuration
        config = json.loads(sys.argv[1])
        file_list = config.get('file_list', [])
        source_root = config.get('source_root', '.')
        dest_root = config.get('dest_root')

        if not dest_root:
            print(json.dumps({
                'error': 'dest_root is required'
            }))
            sys.exit(1)

        if not file_list:
            print(json.dumps({
                'error': 'file_list is required and must not be empty'
            }))
            sys.exit(1)

        # Copy files
        results = copy_files(file_list, source_root, dest_root)

        # Create __init__.py files
        python_dirs = [
            'code_evolver',
            'code_evolver/src',
            'code_evolver/tools',
            'code_evolver/tools/llm',
            'code_evolver/tools/executable',
            'code_evolver/tools/openapi'
        ]
        create_init_files(dest_root, python_dirs)

        # Output result
        print(json.dumps(results))

        if not results['success']:
            sys.exit(1)

    except json.JSONDecodeError as e:
        print(json.dumps({
            'error': f'Invalid JSON configuration: {e}'
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            'error': f'Error copying files: {e}'
        }))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
