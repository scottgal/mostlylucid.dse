#!/usr/bin/env python3
"""
Unit tests for filesystem_manager.py tool.
Tests filesystem management functionality with security controls.
"""

import json
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.executable.filesystem_manager import FilesystemManager


class TestFilesystemManager(unittest.TestCase):
    """Test cases for FilesystemManager class."""

    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = FilesystemManager(
            base_path=self.temp_dir,
            max_file_size_mb=1,
            max_total_size_mb=10
        )

    def tearDown(self):
        """Clean up temporary directory."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test FilesystemManager initialization."""
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertEqual(self.manager.max_file_size_bytes, 1 * 1024 * 1024)
        self.assertEqual(self.manager.max_total_size_bytes, 10 * 1024 * 1024)

    def test_get_scope_path(self):
        """Test getting scope path."""
        scope = "test_tool"
        scope_path = self.manager.get_scope_path(scope)

        self.assertTrue(scope_path.exists())
        self.assertTrue(str(scope_path).endswith("test_tool"))

    def test_get_scope_path_sanitization(self):
        """Test scope name sanitization."""
        scope = "test/../malicious"
        scope_path = self.manager.get_scope_path(scope)

        # Should sanitize the .. characters
        self.assertNotIn("..", str(scope_path))

    def test_resolve_path_valid(self):
        """Test resolving valid path."""
        scope = "test_tool"
        path = "subdir/file.txt"

        resolved = self.manager.resolve_path(scope, path)

        self.assertIsInstance(resolved, Path)
        self.assertTrue(str(resolved).endswith("file.txt"))

    def test_resolve_path_absolute_not_allowed(self):
        """Test that absolute paths are rejected by default."""
        scope = "test_tool"
        path = "/etc/passwd"

        with self.assertRaises(ValueError) as cm:
            self.manager.resolve_path(scope, path)

        self.assertIn("Absolute paths", str(cm.exception))

    def test_resolve_path_parent_traversal_not_allowed(self):
        """Test that parent traversal is rejected by default."""
        scope = "test_tool"
        path = "../escape/file.txt"

        with self.assertRaises(ValueError) as cm:
            self.manager.resolve_path(scope, path)

        self.assertIn("Parent directory traversal", str(cm.exception))

    def test_resolve_path_escape_attempt(self):
        """Test that paths escaping scope are rejected."""
        scope = "test_tool"
        # Even with allowed parent traversal, should not escape scope
        manager = FilesystemManager(
            base_path=self.temp_dir,
            allow_parent_traversal=True
        )

        # This should still be caught by the scope escape check
        path = "subdir/../../../../../../etc/passwd"

        with self.assertRaises(ValueError):
            manager.resolve_path(scope, path)

    def test_validate_extension_allowed(self):
        """Test validating allowed extension."""
        path = Path("test.txt")
        # Should not raise
        self.manager.validate_extension(path)

    def test_validate_extension_not_allowed(self):
        """Test validating disallowed extension."""
        path = Path("test.exe")

        with self.assertRaises(ValueError) as cm:
            self.manager.validate_extension(path)

        self.assertIn("not allowed", str(cm.exception))

    def test_validate_extension_case_insensitive(self):
        """Test that extension validation is case-insensitive."""
        path = Path("test.TXT")
        # Should not raise
        self.manager.validate_extension(path)

    def test_validate_file_size_within_limit(self):
        """Test validating file size within limit."""
        size = 500 * 1024  # 500KB
        # Should not raise
        self.manager.validate_file_size(size)

    def test_validate_file_size_exceeds_limit(self):
        """Test validating file size exceeding limit."""
        size = 2 * 1024 * 1024  # 2MB (limit is 1MB)

        with self.assertRaises(ValueError) as cm:
            self.manager.validate_file_size(size)

        self.assertIn("exceeds limit", str(cm.exception))

    def test_write_file(self):
        """Test writing a file."""
        scope = "test_tool"
        path = "test.txt"
        content = "Hello, World!"

        # Create the write operation
        resolved_path = self.manager.resolve_path(scope, path)
        self.manager.validate_extension(resolved_path)
        self.manager.validate_file_size(len(content.encode()))

        # Write file
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content)

        # Verify
        self.assertTrue(resolved_path.exists())
        self.assertEqual(resolved_path.read_text(), content)

    def test_read_file(self):
        """Test reading a file."""
        scope = "test_tool"
        path = "test.txt"
        content = "Hello, World!"

        # Create file first
        resolved_path = self.manager.resolve_path(scope, path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content)

        # Read file
        read_content = resolved_path.read_text()

        self.assertEqual(read_content, content)

    def test_delete_file(self):
        """Test deleting a file."""
        scope = "test_tool"
        path = "test.txt"
        content = "Hello, World!"

        # Create file first
        resolved_path = self.manager.resolve_path(scope, path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content)

        # Delete file
        resolved_path.unlink()

        # Verify
        self.assertFalse(resolved_path.exists())

    def test_list_files(self):
        """Test listing files in a scope."""
        scope = "test_tool"

        # Create some files
        for i in range(3):
            path = f"file{i}.txt"
            resolved_path = self.manager.resolve_path(scope, path)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_path.write_text(f"Content {i}")

        # List files
        scope_path = self.manager.get_scope_path(scope)
        files = list(scope_path.glob("*.txt"))

        self.assertEqual(len(files), 3)


class TestFilesystemManagerEdgeCases(unittest.TestCase):
    """Test edge cases for FilesystemManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_allow_absolute_paths(self):
        """Test allowing absolute paths when configured."""
        manager = FilesystemManager(
            base_path=self.temp_dir,
            allow_absolute_paths=True
        )

        # This should work now (though it may still fail scope escape check)
        try:
            manager.resolve_path("test", "/tmp/test.txt")
        except ValueError as e:
            # May fail for other reasons, but not for absolute path
            self.assertNotIn("Absolute paths", str(e))

    def test_allow_parent_traversal(self):
        """Test allowing parent traversal when configured."""
        manager = FilesystemManager(
            base_path=self.temp_dir,
            allow_parent_traversal=True
        )

        # This should work now (as long as it doesn't escape scope)
        scope = "test_tool"
        path = "subdir/../file.txt"

        try:
            resolved = manager.resolve_path(scope, path)
            # Should be able to resolve
            self.assertIsInstance(resolved, Path)
        except ValueError as e:
            # Should not fail for parent traversal specifically
            self.assertNotIn("Parent directory traversal", str(e))

    def test_no_extension_restrictions(self):
        """Test with no extension restrictions."""
        manager = FilesystemManager(
            base_path=self.temp_dir,
            allowed_extensions=None
        )

        # Any extension should be allowed
        path = Path("test.exe")
        # Should not raise
        manager.validate_extension(path)


if __name__ == "__main__":
    unittest.main()
