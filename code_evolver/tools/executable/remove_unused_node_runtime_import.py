#!/usr/bin/env python3
"""
Remove Unused node_runtime Import Tool

Detects and removes unused 'from node_runtime import call_tool' imports
and related path setup code when call_tool is not actually used.

This fixes the common error where generated code imports node_runtime
but never calls any tools, causing ModuleNotFoundError in tests.
"""
import sys
import json
import re
import ast


def check_call_tool_usage(code: str) -> bool:
    """
    Check if call_tool() is actually called in the code.

    Args:
        code: Python source code as string

    Returns:
        True if call_tool is called, False otherwise
    """
    try:
        tree = ast.parse(code)

        # Walk AST looking for Call nodes with func.id == 'call_tool'
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check direct function call: call_tool(...)
                if isinstance(node.func, ast.Name) and node.func.id == 'call_tool':
                    return True
                # Check method call: obj.call_tool(...)
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'call_tool':
                    return True

        return False
    except SyntaxError:
        # If we can't parse, fall back to regex
        return bool(re.search(r'\bcall_tool\s*\(', code))


def remove_node_runtime_import(code: str) -> tuple[str, list[str]]:
    """
    Remove node_runtime import and related setup if call_tool is not used.

    Args:
        code: Python source code

    Returns:
        Tuple of (cleaned_code, list_of_changes)
    """
    changes = []

    # Check if call_tool is actually used
    if check_call_tool_usage(code):
        return code, ["call_tool is used - keeping import"]

    # call_tool is NOT used - remove the import
    lines = code.split('\n')
    cleaned_lines = []
    skip_next = False
    removed_pathlib = False
    removed_syspath = False
    removed_import = False
    removed_logging_import = False
    removed_logging_config = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Remove: from node_runtime import call_tool
        if 'from node_runtime import' in line:
            changes.append("Removed: from node_runtime import call_tool")
            removed_import = True
            i += 1
            continue

        # Remove: from pathlib import Path (if followed by sys.path.insert)
        if 'from pathlib import Path' in line or 'import pathlib' in line:
            # Look ahead to see if next non-empty line is sys.path.insert
            next_relevant = i + 1
            while next_relevant < len(lines) and not lines[next_relevant].strip():
                next_relevant += 1

            if next_relevant < len(lines) and 'sys.path.insert' in lines[next_relevant]:
                changes.append("Removed: pathlib import (unused)")
                removed_pathlib = True
                i += 1
                continue

        # Remove: sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        if 'sys.path.insert' in line and 'Path(__file__)' in line:
            changes.append("Removed: sys.path.insert for node_runtime")
            removed_syspath = True
            i += 1
            continue

        # Remove: import logging (if only used for debug logging added by repair)
        if stripped == 'import logging' and i + 1 < len(lines):
            # Check if logging is ONLY used for basicConfig (repair system adds this)
            logging_usage_count = sum(1 for l in lines if 'logging.' in l)
            if logging_usage_count <= 2:  # Just import and basicConfig
                changes.append("Removed: import logging (added by repair, not needed)")
                removed_logging_import = True
                i += 1
                continue

        # Remove: logging.basicConfig(...) (added by repair system)
        if 'logging.basicConfig' in line:
            changes.append("Removed: logging.basicConfig (added by repair)")
            removed_logging_config = True
            i += 1
            continue

        # Remove: logging.debug(...) calls (added by repair system)
        if 'logging.debug' in line or 'logging.exception' in line:
            changes.append(f"Removed: {stripped[:50]}...")
            i += 1
            continue

        # Remove try/except that ONLY wraps logging
        if stripped == 'try:' and i + 1 < len(lines):
            # Look for except with logging.exception
            except_line_idx = None
            for j in range(i + 1, min(i + 20, len(lines))):
                if 'except' in lines[j] and 'logging.exception' in '\n'.join(lines[i:j+3]):
                    except_line_idx = j
                    break

            if except_line_idx:
                # This is a try/except added by repair - remove it but keep the content
                changes.append("Removed: try/except wrapper (added by repair)")
                # Keep lines between try and except, unindent them
                for j in range(i + 1, except_line_idx):
                    if lines[j].strip() and not 'logging.' in lines[j]:
                        # Unindent by removing 4 spaces
                        cleaned_lines.append(lines[j][4:] if lines[j].startswith('    ') else lines[j])
                # Skip to after except block
                i = except_line_idx + 2  # Skip except line and logging.exception line
                continue

        cleaned_lines.append(line)
        i += 1

    cleaned_code = '\n'.join(cleaned_lines)

    # Remove multiple consecutive blank lines
    cleaned_code = re.sub(r'\n\n\n+', '\n\n', cleaned_code)

    if not changes:
        changes.append("No unused imports found")

    return cleaned_code, changes


def main():
    """Main entry point for CLI usage."""
    # Read input
    input_data = json.load(sys.stdin)

    if 'code' not in input_data:
        print(json.dumps({
            "error": "Missing 'code' field in input",
            "success": False
        }))
        return

    code = input_data['code']

    # Process
    cleaned_code, changes = remove_node_runtime_import(code)

    # Output
    result = {
        "success": True,
        "original_code": code,
        "cleaned_code": cleaned_code,
        "changes": changes,
        "was_modified": len([c for c in changes if "Removed:" in c]) > 0
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
