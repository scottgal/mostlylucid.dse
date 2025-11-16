#!/usr/bin/env python3
"""
Inline Tool

Bakes tool code directly into a workflow script with special comments
that tie the inlined code to a specific version in RAG. This enables:
- Enterprise reproducibility (workflow contains all dependencies)
- Version pinning (inlined version protected from trimming)
- Force updates (can extract and re-inline updated version)
- Offline execution (no external tool dependencies)
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib


def get_tool_code(tool_id: str, version: str = "current") -> Dict[str, Any]:
    """
    Get tool code for a specific version

    Args:
        tool_id: ID of the tool
        version: Version to retrieve (or "current" for latest)

    Returns:
        Dict with tool code, version info, and metadata
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

        # Get tool artifact
        tool_artifact = rag.get_artifact(tool_id)
        if not tool_artifact:
            return {
                'success': False,
                'error': f'Tool not found: {tool_id}'
            }

        # Determine version
        if version == "current":
            version = tool_artifact.metadata.get('version', '1.0.0')

        # Find tool file
        tools_root = Path('tools/executable')
        tool_dir = tools_root / tool_id

        if not tool_dir.exists():
            tool_dir = tools_root  # Flat structure

        # Try to find versioned file
        version_safe = version.replace('.', '_')
        version_file = tool_dir / f"{tool_id}_v{version_safe}.py"

        if not version_file.exists():
            # Try current symlink
            current_file = tool_dir / f"{tool_id}.py"
            if current_file.exists():
                version_file = current_file
            else:
                return {
                    'success': False,
                    'error': f'Tool file not found: {version_file}'
                }

        # Read tool code
        with open(version_file, 'r', encoding='utf-8') as f:
            tool_code = f.read()

        return {
            'success': True,
            'tool_id': tool_id,
            'version': version,
            'code': tool_code,
            'file_path': str(version_file),
            'metadata': tool_artifact.metadata,
            'rag_artifact_id': tool_artifact.artifact_id
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def inline_tool_into_workflow(
    workflow_file: str,
    tool_id: str,
    version: str = "current",
    position: str = "top",
    pin_version: bool = True
) -> Dict[str, Any]:
    """
    Inline tool code into a workflow script

    Args:
        workflow_file: Path to workflow script to modify
        tool_id: ID of tool to inline
        version: Version to inline (or "current")
        position: Where to insert ("top" or "bottom")
        pin_version: Whether to pin this version in RAG

    Returns:
        Result with inlined code information
    """
    try:
        # Get tool code
        tool_info = get_tool_code(tool_id, version)
        if not tool_info['success']:
            return tool_info

        tool_code = tool_info['code']
        version = tool_info['version']
        rag_id = tool_info.get('rag_artifact_id', tool_id)

        # Read workflow file
        workflow_path = Path(workflow_file)
        if not workflow_path.exists():
            return {
                'success': False,
                'error': f'Workflow file not found: {workflow_file}'
            }

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_code = f.read()

        # Generate inline section
        inline_marker_id = hashlib.md5(f"{tool_id}@{version}".encode()).hexdigest()[:8]
        inlined_at = datetime.utcnow().isoformat() + 'Z'

        inline_section = f'''
# ==================== INLINED TOOL: {tool_id}@{version} ====================
# INLINE_MARKER: {inline_marker_id}
# TOOL_ID: {tool_id}
# VERSION: {version}
# RAG_ARTIFACT_ID: {rag_id}
# INLINED_AT: {inlined_at}
# PINNED: {str(pin_version).lower()}
#
# This tool has been inlined for enterprise reproducibility.
# The code below is tied to {tool_id} v{version} in the RAG memory.
# This version is protected from trimming.
#
# To extract this tool back out:
#   python tools/executable/inline_tool.py extract {workflow_file} {inline_marker_id}
#
# To update to a newer version:
#   python tools/executable/inline_tool.py update {workflow_file} {inline_marker_id} --version <new_version>
# ==================== CODE START ====================

{tool_code}

# ==================== CODE END: {tool_id}@{version} ====================

'''

        # Insert at top or bottom
        if position == "top":
            # Insert after shebang and module docstring if present
            lines = workflow_code.split('\n')
            insert_pos = 0

            # Skip shebang
            if lines and lines[0].startswith('#!'):
                insert_pos = 1

            # Skip module docstring
            if insert_pos < len(lines) and lines[insert_pos].strip().startswith('"""'):
                # Find end of docstring
                for i in range(insert_pos + 1, len(lines)):
                    if '"""' in lines[i]:
                        insert_pos = i + 1
                        break

            # Insert inline section
            lines.insert(insert_pos, inline_section)
            modified_code = '\n'.join(lines)
        else:
            # Append to bottom
            modified_code = workflow_code + '\n' + inline_section

        # Write modified workflow
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(modified_code)

        # Pin version in RAG if requested
        if pin_version:
            sys.path.insert(0, '.')
            from src.config_manager import ConfigManager
            from src.ollama_client import OllamaClient
            from src.rag_memory import RAGMemory

            config = ConfigManager()
            client = OllamaClient(config_manager=config)
            rag = RAGMemory(ollama_client=client)

            # Tag as pinned and inlined
            version_tag = f"pinned:{tool_id}@{version}"
            inline_tag = f"inlined:{inline_marker_id}"

            try:
                rag.add_tags(rag_id, [version_tag, 'pinned', 'inlined', inline_tag])
            except:
                pass  # Artifact might not exist in RAG yet

        return {
            'success': True,
            'tool_id': tool_id,
            'version': version,
            'workflow_file': str(workflow_path),
            'inline_marker_id': inline_marker_id,
            'position': position,
            'pinned': pin_version,
            'message': f'Inlined {tool_id}@{version} into {workflow_file}',
            'code_size_bytes': len(tool_code),
            'code_size_lines': len(tool_code.split('\n'))
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def extract_inlined_tool(
    workflow_file: str,
    inline_marker_id: str
) -> Dict[str, Any]:
    """
    Extract an inlined tool back out of a workflow

    Args:
        workflow_file: Path to workflow with inlined tool
        inline_marker_id: Marker ID of the inlined section

    Returns:
        Result with extracted tool information
    """
    try:
        workflow_path = Path(workflow_file)
        if not workflow_path.exists():
            return {
                'success': False,
                'error': f'Workflow file not found: {workflow_file}'
            }

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_code = f.read()

        # Find inline section
        start_marker = f'# INLINE_MARKER: {inline_marker_id}'
        if start_marker not in workflow_code:
            return {
                'success': False,
                'error': f'Inline marker not found: {inline_marker_id}'
            }

        # Extract section
        lines = workflow_code.split('\n')
        start_idx = None
        end_idx = None
        tool_id = None
        version = None

        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i - 1  # Include header line
            elif start_idx is not None:
                if 'TOOL_ID:' in line:
                    tool_id = line.split('TOOL_ID:')[1].strip()
                elif 'VERSION:' in line:
                    version = line.split('VERSION:')[1].strip()
                elif '# ==================== CODE END:' in line:
                    end_idx = i + 1
                    break

        if start_idx is None or end_idx is None:
            return {
                'success': False,
                'error': f'Could not find complete inline section for marker: {inline_marker_id}'
            }

        # Remove section
        extracted_lines = lines[start_idx:end_idx]
        remaining_lines = lines[:start_idx] + lines[end_idx:]

        # Write modified workflow
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(remaining_lines))

        return {
            'success': True,
            'tool_id': tool_id,
            'version': version,
            'inline_marker_id': inline_marker_id,
            'workflow_file': str(workflow_path),
            'extracted_lines': len(extracted_lines),
            'message': f'Extracted {tool_id}@{version} from {workflow_file}'
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def update_inlined_tool(
    workflow_file: str,
    inline_marker_id: str,
    new_version: str
) -> Dict[str, Any]:
    """
    Update an inlined tool to a new version

    Args:
        workflow_file: Path to workflow with inlined tool
        inline_marker_id: Marker ID of the inlined section
        new_version: New version to inline

    Returns:
        Result with update information
    """
    try:
        # Extract old version
        extract_result = extract_inlined_tool(workflow_file, inline_marker_id)
        if not extract_result['success']:
            return extract_result

        tool_id = extract_result['tool_id']
        old_version = extract_result['version']

        # Inline new version
        inline_result = inline_tool_into_workflow(
            workflow_file=workflow_file,
            tool_id=tool_id,
            version=new_version,
            position='top',
            pin_version=True
        )

        if inline_result['success']:
            inline_result['update'] = {
                'old_version': old_version,
                'new_version': new_version,
                'message': f'Updated {tool_id} from v{old_version} to v{new_version}'
            }

        return inline_result

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def list_inlined_tools(workflow_file: str) -> Dict[str, Any]:
    """
    List all inlined tools in a workflow

    Args:
        workflow_file: Path to workflow script

    Returns:
        List of inlined tools with their information
    """
    try:
        workflow_path = Path(workflow_file)
        if not workflow_path.exists():
            return {
                'success': False,
                'error': f'Workflow file not found: {workflow_file}'
            }

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_code = f.read()

        # Find all inline sections
        inlined_tools = []
        lines = workflow_code.split('\n')

        current_tool = None
        for line in lines:
            if '# INLINE_MARKER:' in line:
                marker_id = line.split('# INLINE_MARKER:')[1].strip()
                current_tool = {'inline_marker_id': marker_id}
            elif current_tool is not None:
                if 'TOOL_ID:' in line:
                    current_tool['tool_id'] = line.split('TOOL_ID:')[1].strip()
                elif 'VERSION:' in line:
                    current_tool['version'] = line.split('VERSION:')[1].strip()
                elif 'INLINED_AT:' in line:
                    current_tool['inlined_at'] = line.split('INLINED_AT:')[1].strip()
                elif 'PINNED:' in line:
                    current_tool['pinned'] = line.split('PINNED:')[1].strip() == 'true'
                elif '# ==================== CODE END:' in line:
                    inlined_tools.append(current_tool)
                    current_tool = None

        return {
            'success': True,
            'workflow_file': str(workflow_path),
            'inlined_tools': inlined_tools,
            'count': len(inlined_tools),
            'message': f'Found {len(inlined_tools)} inlined tool(s)'
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
        operation = input_data.get('operation', 'inline')
        workflow_file = input_data.get('workflow_file', '')
        tool_id = input_data.get('tool_id', '')
        version = input_data.get('version', 'current')
        inline_marker_id = input_data.get('inline_marker_id', '')
        position = input_data.get('position', 'top')
        pin_version = input_data.get('pin_version', True)

        # Execute operation
        if operation == 'inline':
            if not workflow_file or not tool_id:
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameters: workflow_file, tool_id'
                }))
                sys.exit(1)

            result = inline_tool_into_workflow(
                workflow_file=workflow_file,
                tool_id=tool_id,
                version=version,
                position=position,
                pin_version=pin_version
            )

        elif operation == 'extract':
            if not workflow_file or not inline_marker_id:
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameters: workflow_file, inline_marker_id'
                }))
                sys.exit(1)

            result = extract_inlined_tool(workflow_file, inline_marker_id)

        elif operation == 'update':
            if not workflow_file or not inline_marker_id or version == 'current':
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameters: workflow_file, inline_marker_id, version'
                }))
                sys.exit(1)

            result = update_inlined_tool(workflow_file, inline_marker_id, version)

        elif operation == 'list':
            if not workflow_file:
                print(json.dumps({
                    'success': False,
                    'error': 'Missing required parameter: workflow_file'
                }))
                sys.exit(1)

            result = list_inlined_tools(workflow_file)

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
