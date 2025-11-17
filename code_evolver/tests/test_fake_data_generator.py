#!/usr/bin/env python3
"""
Unit tests for fake_data_generator.py tool.
Tests fake data generation functionality.
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.executable.fake_data_generator import (
    generate_fake_data,
    generate_basic_fake_data,
    main
)


class TestFakeDataGenerator(unittest.TestCase):
    """Test cases for fake data generator."""

    def test_generate_string_data(self):
        """Test generating string data."""
        schema = {"type": "string", "maxLength": 10}
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, str)
        self.assertLessEqual(len(result), 10)

    def test_generate_integer_data(self):
        """Test generating integer data."""
        schema = {"type": "integer", "minimum": 10, "maximum": 20}
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 10)
        self.assertLessEqual(result, 20)

    def test_generate_number_data(self):
        """Test generating float data."""
        schema = {"type": "number", "minimum": 0.0, "maximum": 10.0}
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 10.0)

    def test_generate_boolean_data(self):
        """Test generating boolean data."""
        schema = {"type": "boolean"}
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, bool)
        self.assertIn(result, [True, False])

    def test_generate_array_data(self):
        """Test generating array data."""
        schema = {
            "type": "array",
            "items": {"type": "integer", "minimum": 1, "maximum": 100}
        }
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for item in result:
            self.assertIsInstance(item, int)

    def test_generate_object_data(self):
        """Test generating object data."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0, "maximum": 120}
            },
            "required": ["name", "age"]
        }
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("age", result)
        self.assertIsInstance(result["name"], str)
        self.assertIsInstance(result["age"], int)

    def test_generate_null_data(self):
        """Test generating null data."""
        schema = {"type": "null"}
        result = generate_basic_fake_data(schema)

        self.assertIsNone(result)

    def test_generate_enum_data(self):
        """Test generating data from enum."""
        schema = {
            "type": "string",
            "enum": ["red", "green", "blue"]
        }
        result = generate_basic_fake_data(schema)

        self.assertIn(result, ["red", "green", "blue"])

    @patch('tools.executable.fake_data_generator.Faker')
    def test_generate_with_faker_email(self, mock_faker_class):
        """Test generating email with Faker."""
        mock_faker = MagicMock()
        mock_faker.email.return_value = "test@example.com"
        mock_faker_class.return_value = mock_faker

        schema = {"type": "string", "format": "email"}
        result = generate_fake_data(schema)

        self.assertEqual(result, "test@example.com")

    @patch('tools.executable.fake_data_generator.Faker')
    def test_generate_with_faker_url(self, mock_faker_class):
        """Test generating URL with Faker."""
        mock_faker = MagicMock()
        mock_faker.url.return_value = "https://example.com"
        mock_faker_class.return_value = mock_faker

        schema = {"type": "string", "format": "url"}
        result = generate_fake_data(schema)

        self.assertEqual(result, "https://example.com")

    @patch('tools.executable.fake_data_generator.Faker')
    def test_generate_with_faker_uuid(self, mock_faker_class):
        """Test generating UUID with Faker."""
        mock_faker = MagicMock()
        mock_faker.uuid4.return_value = "123e4567-e89b-12d3-a456-426614174000"
        mock_faker_class.return_value = mock_faker

        schema = {"type": "string", "format": "uuid"}
        result = generate_fake_data(schema)

        self.assertEqual(result, "123e4567-e89b-12d3-a456-426614174000")

    def test_generate_nested_object(self):
        """Test generating nested object structure."""
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"}
                    },
                    "required": ["name"]
                },
                "settings": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"}
                    },
                    "required": ["enabled"]
                }
            },
            "required": ["user", "settings"]
        }
        result = generate_basic_fake_data(schema)

        self.assertIsInstance(result, dict)
        self.assertIn("user", result)
        self.assertIn("settings", result)
        self.assertIsInstance(result["user"], dict)
        self.assertIsInstance(result["settings"], dict)
        self.assertIn("name", result["user"])
        self.assertIn("enabled", result["settings"])


class TestFakeDataGeneratorMain(unittest.TestCase):
    """Test cases for main function."""

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_single_item(self, mock_stdout, mock_stdin):
        """Test main function generating single item."""
        input_data = json.dumps({
            "schema": {"type": "string"},
            "count": 1
        })

        with patch('sys.stdin.read', return_value=input_data):
            try:
                main()
                output = mock_stdout.getvalue()
                result = json.loads(output)

                self.assertTrue(result.get("success"))
                self.assertIn("data", result)
                self.assertIsInstance(result["data"], str)
            except SystemExit:
                pass

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_multiple_items(self, mock_stdout, mock_stdin):
        """Test main function generating multiple items."""
        input_data = json.dumps({
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
            "count": 5
        })

        with patch('sys.stdin.read', return_value=input_data):
            try:
                main()
                output = mock_stdout.getvalue()
                result = json.loads(output)

                self.assertTrue(result.get("success"))
                self.assertIn("data", result)
                self.assertIsInstance(result["data"], list)
                self.assertEqual(len(result["data"]), 5)
            except SystemExit:
                pass

    @patch('sys.stdin', new_callable=StringIO)
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_default_schema(self, mock_stdout, mock_stdin):
        """Test main function with default schema."""
        input_data = json.dumps({})

        with patch('sys.stdin.read', return_value=input_data):
            try:
                main()
                output = mock_stdout.getvalue()
                result = json.loads(output)

                self.assertTrue(result.get("success"))
                self.assertIn("data", result)
            except SystemExit:
                pass


if __name__ == "__main__":
    unittest.main()
