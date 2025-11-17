#!/usr/bin/env python3
"""
Unit tests for random_data_generator.py tool.
Tests random test data generation functionality.
"""

import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.executable.random_data_generator import RandomDataGenerator


class TestRandomDataGenerator(unittest.TestCase):
    """Test cases for RandomDataGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = RandomDataGenerator()

    def test_generate_string_email(self):
        """Test generating email string."""
        result = self.generator.generate_string("email")

        self.assertIsInstance(result, str)
        self.assertIn("@", result)
        self.assertTrue(result.split("@")[1] in self.generator.domains)

    def test_generate_string_name(self):
        """Test generating name string."""
        result = self.generator.generate_string("name")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_string_first_name(self):
        """Test generating first name."""
        result = self.generator.generate_string("first_name")

        self.assertIsInstance(result, str)
        self.assertIn(result, self.generator.first_names)

    def test_generate_string_last_name(self):
        """Test generating last name."""
        result = self.generator.generate_string("last_name")

        self.assertIsInstance(result, str)
        self.assertIn(result, self.generator.last_names)

    def test_generate_string_text(self):
        """Test generating text content."""
        result = self.generator.generate_string("text")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertTrue(result.endswith("."))

    def test_generate_string_url(self):
        """Test generating URL."""
        result = self.generator.generate_string("url")

        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("https://"))

    def test_generate_string_phone(self):
        """Test generating phone number."""
        result = self.generator.generate_string("phone")

        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("+1-555-"))

    def test_generate_string_address(self):
        """Test generating address."""
        result = self.generator.generate_string("address")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_string_city(self):
        """Test generating city."""
        result = self.generator.generate_string("city")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_string_country(self):
        """Test generating country."""
        result = self.generator.generate_string("country")

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_string_language(self):
        """Test generating language code."""
        result = self.generator.generate_string("language")

        self.assertIsInstance(result, str)
        self.assertIn(result, self.generator.languages + self.generator.language_names)

    def test_generate_number_age(self):
        """Test generating age number."""
        result = self.generator.generate_number("age")

        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 18)
        self.assertLessEqual(result, 80)

    def test_generate_number_price(self):
        """Test generating price."""
        result = self.generator.generate_number("price")

        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 9.99)
        self.assertLessEqual(result, 999.99)

    def test_generate_number_year(self):
        """Test generating year."""
        result = self.generator.generate_number("year")

        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 1900)
        self.assertLessEqual(result, 2024)

    def test_generate_number_beam_size(self):
        """Test generating beam size."""
        result = self.generator.generate_number("beam_size")

        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 1)
        self.assertLessEqual(result, 10)

    def test_generate_number_default(self):
        """Test generating default number."""
        result = self.generator.generate_number("random_field")

        self.assertIsInstance(result, (int, float))
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 100)

    def test_generate_boolean(self):
        """Test generating boolean."""
        result = self.generator.generate_boolean("test_field")

        self.assertIsInstance(result, bool)
        self.assertIn(result, [True, False])

    def test_generate_array_strings(self):
        """Test generating array of strings."""
        result = self.generator.generate_array("names", item_type="string", min_items=2, max_items=5)

        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 2)
        self.assertLessEqual(len(result), 5)
        for item in result:
            self.assertIsInstance(item, str)

    def test_generate_array_numbers(self):
        """Test generating array of numbers."""
        result = self.generator.generate_array("ages", item_type="number", min_items=1, max_items=3)

        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        self.assertLessEqual(len(result), 3)
        for item in result:
            self.assertIsInstance(item, (int, float))

    def test_generate_from_schema_simple(self):
        """Test generating from simple schema."""
        schema = {
            "name": "string",
            "age": "number",
            "email": "string"
        }
        result = self.generator.generate_from_schema(schema)

        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("age", result)
        self.assertIn("email", result)
        self.assertIsInstance(result["name"], str)
        self.assertIsInstance(result["age"], (int, float))
        self.assertIsInstance(result["email"], str)

    def test_generate_from_schema_nested(self):
        """Test generating from nested schema."""
        schema = {
            "user": {
                "name": "string",
                "email": "string"
            },
            "settings": {
                "enabled": "boolean"
            }
        }
        result = self.generator.generate_from_schema(schema)

        self.assertIsInstance(result, dict)
        self.assertIn("user", result)
        self.assertIn("settings", result)
        self.assertIsInstance(result["user"], dict)
        self.assertIn("name", result["user"])
        self.assertIn("email", result["user"])

    def test_parse_natural_language_translation(self):
        """Test parsing natural language for translation."""
        description = "Generate data for translating text from English to Spanish"
        result = self.generator.parse_natural_language(description)

        self.assertIsInstance(result, dict)
        self.assertIn("text", result)

    def test_parse_natural_language_user_profile(self):
        """Test parsing natural language for user profile."""
        description = "Generate user profile with name, email, and age"
        result = self.generator.parse_natural_language(description)

        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("email", result)
        self.assertIn("age", result)

    def test_parse_natural_language_article(self):
        """Test parsing natural language for article content."""
        description = "Generate article with title and content"
        result = self.generator.parse_natural_language(description)

        self.assertIsInstance(result, dict)
        self.assertIn("title", result)
        self.assertIn("content", result)

    def test_parse_natural_language_generic(self):
        """Test parsing generic natural language."""
        description = "Generate some test data"
        result = self.generator.parse_natural_language(description)

        self.assertIsInstance(result, dict)
        # Should have at least some fields
        self.assertGreater(len(result), 0)


class TestRandomDataGeneratorMain(unittest.TestCase):
    """Test cases for main function."""

    @patch('sys.argv', ['random_data_generator.py', '{"name": "string", "age": "number"}'])
    @patch('sys.stdout', new_callable=lambda: open('/dev/null', 'w'))
    def test_main_with_json_schema(self, mock_stdout):
        """Test main function with JSON schema."""
        from tools.executable.random_data_generator import main

        try:
            main()
        except SystemExit:
            pass

    @patch('sys.argv', ['random_data_generator.py', 'Generate user profile data'])
    @patch('sys.stdout', new_callable=lambda: open('/dev/null', 'w'))
    def test_main_with_natural_language(self, mock_stdout):
        """Test main function with natural language."""
        from tools.executable.random_data_generator import main

        try:
            main()
        except SystemExit:
            pass

    @patch('sys.argv', ['random_data_generator.py'])
    def test_main_with_no_arguments(self):
        """Test main function with no arguments."""
        from tools.executable.random_data_generator import main

        with self.assertRaises(SystemExit):
            main()


if __name__ == "__main__":
    unittest.main()
