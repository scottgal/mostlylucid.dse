"""
Tests for ConfigManager - Configuration loading and management.
"""
import unittest
import tempfile
import yaml
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test suite for ConfigManager."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_config(self):
        """Test loading default configuration."""
        config_path = Path(self.test_dir) / "nonexistent.yaml"
        config = ConfigManager(str(config_path))

        # Should load defaults
        self.assertEqual(config.ollama_url, "http://localhost:11434")
        self.assertEqual(config.registry_path, "./registry")

    def test_load_custom_config(self):
        """Test loading custom configuration."""
        config_data = {
            "ollama": {
                "base_url": "http://custom:11434",
                "models": {
                    "overseer": {"model": "llama3", "endpoint": None},
                    "generator": {"model": "codellama", "endpoint": None}
                }
            },
            "registry": {
                "path": "/custom/registry"
            }
        }

        config_path = Path(self.test_dir) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = ConfigManager(str(config_path))

        self.assertEqual(config.ollama_url, "http://custom:11434")
        self.assertEqual(config.registry_path, "/custom/registry")

    def test_parse_model_config_dict_format(self):
        """Test parsing model config in dict format."""
        config_data = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "models": {
                    "overseer": {
                        "model": "llama3",
                        "endpoint": "http://machine1:11434"
                    }
                }
            }
        }

        config_path = Path(self.test_dir) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = ConfigManager(str(config_path))

        model, endpoint = config._parse_model_config("overseer", "default")
        self.assertEqual(model, "llama3")
        self.assertEqual(endpoint, "http://machine1:11434")

    def test_parse_model_config_string_format(self):
        """Test parsing model config in string format."""
        config_data = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "models": {
                    "overseer": "llama3"
                }
            }
        }

        config_path = Path(self.test_dir) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = ConfigManager(str(config_path))

        model, endpoint = config._parse_model_config("overseer", "default")
        self.assertEqual(model, "llama3")
        self.assertEqual(endpoint, "http://localhost:11434")

    def test_get_model_endpoint(self):
        """Test getting model endpoint."""
        config_data = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "models": {
                    "overseer": {
                        "model": "llama3",
                        "endpoint": "http://machine1:11434"
                    },
                    "generator": {
                        "model": "codellama",
                        "endpoint": None
                    }
                }
            }
        }

        config_path = Path(self.test_dir) / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        config = ConfigManager(str(config_path))

        # Overseer should have custom endpoint
        self.assertEqual(config.get_model_endpoint("overseer"), "http://machine1:11434")

        # Generator should use base_url
        self.assertEqual(config.get_model_endpoint("generator"), "http://localhost:11434")

    def test_model_properties(self):
        """Test model property accessors."""
        config = ConfigManager()

        # Test all model properties
        self.assertIsNotNone(config.overseer_model)
        self.assertIsNotNone(config.generator_model)
        self.assertIsNotNone(config.evaluator_model)
        self.assertIsNotNone(config.triage_model)
        self.assertIsNotNone(config.escalation_model)

    def test_get_set_methods(self):
        """Test get and set methods."""
        config = ConfigManager()

        # Test get
        base_url = config.get("ollama.base_url")
        self.assertEqual(base_url, "http://localhost:11434")

        # Test get with default
        custom = config.get("nonexistent.key", "default_value")
        self.assertEqual(custom, "default_value")

        # Test set
        config.set("custom.key", "custom_value")
        self.assertEqual(config.get("custom.key"), "custom_value")

    def test_validation(self):
        """Test configuration validation."""
        config = ConfigManager()
        # Default config should be valid
        self.assertTrue(config.validate())


if __name__ == "__main__":
    unittest.main()
