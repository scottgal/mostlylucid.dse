#!/usr/bin/env python3
"""
Filesystem Manager - Tool-scoped filesystem operations.

Provides isolated file storage for each tool with security controls:
- Path traversal protection
- Extension filtering
- Size limits
- Automatic directory management
"""
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import glob


class FilesystemManager:
    """
    Manages tool-scoped filesystem operations.

    Each tool gets its own isolated directory under base_path/scope/.
    All file operations are validated for security and stay within the tool's scope.
    """

    def __init__(
        self,
        base_path: str = "./data/filesystem",
        max_file_size_mb: int = 100,
        max_total_size_mb: int = 1000,
        allowed_extensions: Optional[List[str]] = None,
        allow_absolute_paths: bool = False,
        allow_parent_traversal: bool = False
    ):
        """
        Initialize Filesystem Manager.

        Args:
            base_path: Base directory for all tool-scoped filesystems
            max_file_size_mb: Maximum file size in MB
            max_total_size_mb: Maximum total storage per tool scope in MB
            allowed_extensions: List of allowed file extensions (None = all allowed)
            allow_absolute_paths: Allow absolute paths (dangerous)
            allow_parent_traversal: Allow .. in paths (dangerous)
        """
        self.base_path = Path(base_path).resolve()
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_total_size_bytes = max_total_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or [
            '.txt', '.json', '.yaml', '.yml', '.md',
            '.csv', '.log', '.xml'
        ]
        self.allow_absolute_paths = allow_absolute_paths
        self.allow_parent_traversal = allow_parent_traversal

        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_scope_path(self, scope: str) -> Path:
        """
        Get the base path for a tool scope.

        Args:
            scope: Tool scope name

        Returns:
            Path to tool's scope directory
        """
        # Sanitize scope name
        scope = scope.replace('/', '_').replace('\\', '_').replace('..', '_')
        scope_path = self.base_path / scope
        scope_path.mkdir(parents=True, exist_ok=True)
        return scope_path

    def resolve_path(self, scope: str, path: str) -> Path:
        """
        Resolve and validate a path within tool scope.

        Args:
            scope: Tool scope name
            path: Relative path within scope

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is invalid or unsafe
        """
        # Check for absolute paths
        if Path(path).is_absolute() and not self.allow_absolute_paths:
            raise ValueError("Absolute paths are not allowed")

        # Check for parent traversal
        if '..' in Path(path).parts and not self.allow_parent_traversal:
            raise ValueError("Parent directory traversal (..) is not allowed")

        # Get scope directory
        scope_path = self.get_scope_path(scope)

        # Resolve full path
        full_path = (scope_path / path).resolve()

        # Ensure path is within scope directory (security check)
        try:
            full_path.relative_to(scope_path)
        except ValueError:
            raise ValueError(f"Path escapes tool scope: {path}")

        return full_path

    def validate_extension(self, path: Path) -> None:
        """
        Validate file extension.

        Args:
            path: File path

        Raises:
            ValueError: If extension is not allowed
        """
        if self.allowed_extensions is None:
            return

        ext = path.suffix.lower()
        if ext and ext not in self.allowed_extensions:
            raise ValueError(
                f"Extension {ext} not allowed. "
                f"Allowed: {', '.join(self.allowed_extensions)}"
            )

    def validate_file_size(self, size: int) -> None:
        """
        Validate file size.

        Args:
            size: File size in bytes

        Raises:
            ValueError: If file is too large
        """
        if size > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            size_mb = size / (1024 * 1024)
            raise ValueError(
                f"File size {size_mb:.1f}MB exceeds limit of {max_mb:.0f}MB"
            )

    def get_total_size(self, scope: str) -> int:
        """
        Get total storage used by a tool scope.

        Args:
            scope: Tool scope name

        Returns:
            Total size in bytes
        """
        scope_path = self.get_scope_path(scope)
        total = 0

        for root, dirs, files in os.walk(scope_path):
            for file in files:
                file_path = Path(root) / file
                try:
                    total += file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    pass

        return total

    def validate_total_size(self, scope: str, additional_size: int = 0) -> None:
        """
        Validate total storage size for scope.

        Args:
            scope: Tool scope name
            additional_size: Additional bytes to be added

        Raises:
            ValueError: If total size would exceed limit
        """
        total = self.get_total_size(scope) + additional_size

        if total > self.max_total_size_bytes:
            max_mb = self.max_total_size_bytes / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            raise ValueError(
                f"Total storage {total_mb:.1f}MB would exceed limit of {max_mb:.0f}MB"
            )

    def read(
        self,
        scope: str,
        path: str,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """
        Read file contents.

        Args:
            scope: Tool scope name
            path: File path within scope
            encoding: File encoding

        Returns:
            Result dictionary with content
        """
        try:
            full_path = self.resolve_path(scope, path)

            if not full_path.exists():
                return {
                    'status': 'error',
                    'message': f'File not found: {path}',
                    'content': None
                }

            if not full_path.is_file():
                return {
                    'status': 'error',
                    'message': f'Not a file: {path}',
                    'content': None
                }

            content = full_path.read_text(encoding=encoding)

            return {
                'status': 'success',
                'message': f'Read {len(content)} characters',
                'content': content,
                'path': str(full_path.relative_to(self.get_scope_path(scope)))
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to read file: {str(e)}',
                'content': None
            }

    def write(
        self,
        scope: str,
        path: str,
        content: str,
        encoding: str = 'utf-8',
        create_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Write file contents.

        Args:
            scope: Tool scope name
            path: File path within scope
            content: Content to write
            encoding: File encoding
            create_parents: Create parent directories if needed

        Returns:
            Result dictionary
        """
        try:
            full_path = self.resolve_path(scope, path)

            # Validate extension
            self.validate_extension(full_path)

            # Validate file size
            content_bytes = content.encode(encoding)
            self.validate_file_size(len(content_bytes))

            # Validate total size
            self.validate_total_size(scope, len(content_bytes))

            # Create parent directories
            if create_parents:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content, encoding=encoding)

            return {
                'status': 'success',
                'message': f'Wrote {len(content)} characters to {path}',
                'path': str(full_path.relative_to(self.get_scope_path(scope))),
                'size': len(content_bytes)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to write file: {str(e)}'
            }

    def append(
        self,
        scope: str,
        path: str,
        content: str,
        encoding: str = 'utf-8',
        create_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Append to file.

        Args:
            scope: Tool scope name
            path: File path within scope
            content: Content to append
            encoding: File encoding
            create_parents: Create parent directories if needed

        Returns:
            Result dictionary
        """
        try:
            full_path = self.resolve_path(scope, path)

            # Validate extension
            self.validate_extension(full_path)

            # Check new size
            current_size = full_path.stat().st_size if full_path.exists() else 0
            content_bytes = content.encode(encoding)
            new_size = current_size + len(content_bytes)

            self.validate_file_size(new_size)
            self.validate_total_size(scope, len(content_bytes))

            # Create parent directories
            if create_parents:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # Append to file
            with open(full_path, 'a', encoding=encoding) as f:
                f.write(content)

            return {
                'status': 'success',
                'message': f'Appended {len(content)} characters to {path}',
                'path': str(full_path.relative_to(self.get_scope_path(scope))),
                'size': new_size
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to append to file: {str(e)}'
            }

    def exists(self, scope: str, path: str) -> Dict[str, Any]:
        """
        Check if file or directory exists.

        Args:
            scope: Tool scope name
            path: Path within scope

        Returns:
            Result dictionary with exists flag
        """
        try:
            full_path = self.resolve_path(scope, path)

            return {
                'status': 'success',
                'message': 'Exists' if full_path.exists() else 'Not found',
                'exists': full_path.exists(),
                'is_file': full_path.is_file() if full_path.exists() else False,
                'is_dir': full_path.is_dir() if full_path.exists() else False,
                'path': str(full_path.relative_to(self.get_scope_path(scope)))
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to check existence: {str(e)}',
                'exists': False
            }

    def list_files(
        self,
        scope: str,
        path: str = "",
        pattern: str = "*",
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        List files in directory.

        Args:
            scope: Tool scope name
            path: Directory path within scope
            pattern: File pattern (e.g., '*.json')
            recursive: List recursively

        Returns:
            Result dictionary with files list
        """
        try:
            full_path = self.resolve_path(scope, path)

            if not full_path.exists():
                return {
                    'status': 'error',
                    'message': f'Directory not found: {path}',
                    'files': []
                }

            if not full_path.is_dir():
                return {
                    'status': 'error',
                    'message': f'Not a directory: {path}',
                    'files': []
                }

            # Get files
            scope_path = self.get_scope_path(scope)
            files = []

            if recursive:
                search_pattern = str(full_path / '**' / pattern)
                matches = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = str(full_path / pattern)
                matches = glob.glob(search_pattern)

            for match in matches:
                match_path = Path(match)
                rel_path = match_path.relative_to(scope_path)

                file_info = {
                    'path': str(rel_path),
                    'name': match_path.name,
                    'is_file': match_path.is_file(),
                    'is_dir': match_path.is_dir()
                }

                if match_path.is_file():
                    file_info['size'] = match_path.stat().st_size
                    file_info['modified'] = datetime.fromtimestamp(
                        match_path.stat().st_mtime
                    ).isoformat()

                files.append(file_info)

            return {
                'status': 'success',
                'message': f'Found {len(files)} items',
                'files': files,
                'path': str(full_path.relative_to(scope_path))
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to list files: {str(e)}',
                'files': []
            }

    def delete(
        self,
        scope: str,
        path: str,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        Delete file or directory.

        Args:
            scope: Tool scope name
            path: Path within scope
            recursive: Delete directories recursively

        Returns:
            Result dictionary
        """
        try:
            full_path = self.resolve_path(scope, path)

            if not full_path.exists():
                return {
                    'status': 'error',
                    'message': f'Path not found: {path}'
                }

            if full_path.is_file():
                full_path.unlink()
                return {
                    'status': 'success',
                    'message': f'Deleted file: {path}'
                }
            elif full_path.is_dir():
                if recursive:
                    shutil.rmtree(full_path)
                    return {
                        'status': 'success',
                        'message': f'Deleted directory recursively: {path}'
                    }
                else:
                    # Only delete if empty
                    full_path.rmdir()
                    return {
                        'status': 'success',
                        'message': f'Deleted empty directory: {path}'
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown file type: {path}'
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to delete: {str(e)}'
            }

    def mkdir(
        self,
        scope: str,
        path: str,
        create_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Create directory.

        Args:
            scope: Tool scope name
            path: Directory path within scope
            create_parents: Create parent directories if needed

        Returns:
            Result dictionary
        """
        try:
            full_path = self.resolve_path(scope, path)

            if full_path.exists():
                if full_path.is_dir():
                    return {
                        'status': 'success',
                        'message': f'Directory already exists: {path}',
                        'path': str(full_path.relative_to(self.get_scope_path(scope)))
                    }
                else:
                    return {
                        'status': 'error',
                        'message': f'Path exists but is not a directory: {path}'
                    }

            full_path.mkdir(parents=create_parents, exist_ok=True)

            return {
                'status': 'success',
                'message': f'Created directory: {path}',
                'path': str(full_path.relative_to(self.get_scope_path(scope)))
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create directory: {str(e)}'
            }

    def size(self, scope: str, path: str) -> Dict[str, Any]:
        """
        Get file size.

        Args:
            scope: Tool scope name
            path: File path within scope

        Returns:
            Result dictionary with size
        """
        try:
            full_path = self.resolve_path(scope, path)

            if not full_path.exists():
                return {
                    'status': 'error',
                    'message': f'Path not found: {path}',
                    'size': None
                }

            if full_path.is_file():
                size = full_path.stat().st_size
                return {
                    'status': 'success',
                    'message': f'File size: {size} bytes',
                    'size': size,
                    'size_mb': size / (1024 * 1024),
                    'path': str(full_path.relative_to(self.get_scope_path(scope)))
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Not a file: {path}',
                    'size': None
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get size: {str(e)}',
                'size': None
            }

    def metadata(self, scope: str, path: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            scope: Tool scope name
            path: File path within scope

        Returns:
            Result dictionary with metadata
        """
        try:
            full_path = self.resolve_path(scope, path)

            if not full_path.exists():
                return {
                    'status': 'error',
                    'message': f'Path not found: {path}',
                    'metadata': None
                }

            stat = full_path.stat()

            metadata = {
                'path': str(full_path.relative_to(self.get_scope_path(scope))),
                'name': full_path.name,
                'is_file': full_path.is_file(),
                'is_dir': full_path.is_dir(),
                'size': stat.st_size,
                'size_mb': stat.st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat()
            }

            if full_path.is_file():
                metadata['extension'] = full_path.suffix

            return {
                'status': 'success',
                'message': f'Retrieved metadata for: {path}',
                'metadata': metadata
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get metadata: {str(e)}',
                'metadata': None
            }

    def copy(
        self,
        scope: str,
        path: str,
        dest_path: str,
        create_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Copy file.

        Args:
            scope: Tool scope name
            path: Source file path
            dest_path: Destination file path
            create_parents: Create parent directories if needed

        Returns:
            Result dictionary
        """
        try:
            src_path = self.resolve_path(scope, path)
            dst_path = self.resolve_path(scope, dest_path)

            if not src_path.exists():
                return {
                    'status': 'error',
                    'message': f'Source not found: {path}'
                }

            if not src_path.is_file():
                return {
                    'status': 'error',
                    'message': f'Source is not a file: {path}'
                }

            # Validate destination extension
            self.validate_extension(dst_path)

            # Validate size
            src_size = src_path.stat().st_size
            self.validate_file_size(src_size)
            self.validate_total_size(scope, src_size)

            # Create parent directories
            if create_parents:
                dst_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(src_path, dst_path)

            return {
                'status': 'success',
                'message': f'Copied {path} to {dest_path}',
                'source': str(src_path.relative_to(self.get_scope_path(scope))),
                'destination': str(dst_path.relative_to(self.get_scope_path(scope)))
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to copy file: {str(e)}'
            }

    def move(
        self,
        scope: str,
        path: str,
        dest_path: str,
        create_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Move/rename file.

        Args:
            scope: Tool scope name
            path: Source file path
            dest_path: Destination file path
            create_parents: Create parent directories if needed

        Returns:
            Result dictionary
        """
        try:
            src_path = self.resolve_path(scope, path)
            dst_path = self.resolve_path(scope, dest_path)

            if not src_path.exists():
                return {
                    'status': 'error',
                    'message': f'Source not found: {path}'
                }

            # Validate destination extension
            if dst_path.suffix:
                self.validate_extension(dst_path)

            # Create parent directories
            if create_parents:
                dst_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(src_path), str(dst_path))

            return {
                'status': 'success',
                'message': f'Moved {path} to {dest_path}',
                'source': path,
                'destination': str(dst_path.relative_to(self.get_scope_path(scope)))
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to move file: {str(e)}'
            }


def main():
    """
    Main entry point for filesystem tool.

    Reads JSON input from stdin and executes the requested operation.
    """
    # Read input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(json.dumps({
            'status': 'error',
            'message': f'Invalid JSON input: {str(e)}'
        }))
        sys.exit(1)

    # Extract parameters
    operation = input_data.get('operation')
    scope = input_data.get('scope')
    path = input_data.get('path', '')

    if not operation:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing required parameter: operation'
        }))
        sys.exit(1)

    if not scope:
        print(json.dumps({
            'status': 'error',
            'message': 'Missing required parameter: scope'
        }))
        sys.exit(1)

    # Create manager (with config from environment or defaults)
    manager = FilesystemManager()

    # Execute operation
    result = None

    if operation == 'read':
        encoding = input_data.get('encoding', 'utf-8')
        result = manager.read(scope, path, encoding)

    elif operation == 'write':
        content = input_data.get('content', '')
        encoding = input_data.get('encoding', 'utf-8')
        create_parents = input_data.get('create_parents', True)
        result = manager.write(scope, path, content, encoding, create_parents)

    elif operation == 'append':
        content = input_data.get('content', '')
        encoding = input_data.get('encoding', 'utf-8')
        create_parents = input_data.get('create_parents', True)
        result = manager.append(scope, path, content, encoding, create_parents)

    elif operation == 'exists':
        result = manager.exists(scope, path)

    elif operation == 'list':
        pattern = input_data.get('pattern', '*')
        recursive = input_data.get('recursive', False)
        result = manager.list_files(scope, path, pattern, recursive)

    elif operation == 'delete':
        recursive = input_data.get('recursive', False)
        result = manager.delete(scope, path, recursive)

    elif operation == 'mkdir':
        create_parents = input_data.get('create_parents', True)
        result = manager.mkdir(scope, path, create_parents)

    elif operation == 'size':
        result = manager.size(scope, path)

    elif operation == 'metadata':
        result = manager.metadata(scope, path)

    elif operation == 'copy':
        dest_path = input_data.get('dest_path')
        if not dest_path:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: dest_path'
            }
        else:
            create_parents = input_data.get('create_parents', True)
            result = manager.copy(scope, path, dest_path, create_parents)

    elif operation == 'move':
        dest_path = input_data.get('dest_path')
        if not dest_path:
            result = {
                'status': 'error',
                'message': 'Missing required parameter: dest_path'
            }
        else:
            create_parents = input_data.get('create_parents', True)
            result = manager.move(scope, path, dest_path, create_parents)

    else:
        result = {
            'status': 'error',
            'message': f'Unknown operation: {operation}'
        }

    # Output result
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
