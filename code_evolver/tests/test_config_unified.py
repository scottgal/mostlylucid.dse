"""
Unit tests for unified LLM config system with cascading defaults.
"""
import pytest
import yaml
from pathlib import Path
from src.config_manager import ConfigManager


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    return tmp_path


@pytest.fixture
def unified_config_yaml():
    """Sample unified config structure."""
    return {
        "llm": {
            "models": {
                "tinyllama": {
                    "name": "tinyllama",
                    "backend": "ollama",
                    "context_window": 2048,
                    "cost": "very-low",
                    "speed": "very-fast",
                    "quality": "basic"
                },
                "llama3": {
                    "name": "llama3",
                    "backend": "ollama",
                    "context_window": 8192,
                    "cost": "medium",
                    "speed": "fast",
                    "quality": "excellent"
                },
                "codellama_7b": {
                    "name": "codellama:7b",
                    "backend": "ollama",
                    "context_window": 16384,
                    "cost": "medium",
                    "speed": "fast",
                    "quality": "excellent",
                    "specialization": "code"
                },
                "qwen_14b": {
                    "name": "qwen2.5-coder:14b",
                    "backend": "ollama",
                    "context_window": 32768,
                    "cost": "high",
                    "speed": "medium",
                    "quality": "excellent",
                    "specialization": "code"
                },
                "claude_haiku": {
                    "name": "claude-3-haiku-20240307",
                    "backend": "anthropic",
                    "context_window": 200000,
                    "cost": "low",
                    "speed": "very-fast",
                    "quality": "excellent"
                },
                "claude_sonnet": {
                    "name": "claude-3-5-sonnet-20241022",
                    "backend": "anthropic",
                    "context_window": 200000,
                    "cost": "medium",
                    "speed": "fast",
                    "quality": "exceptional"
                }
            },
            "defaults": {
                "god": "qwen_14b",
                "escalation": "qwen_14b",
                "general": "llama3",
                "fast": "llama3",
                "veryfast": "tinyllama"
            },
            "roles": {
                "default": {},
                "code": {
                    "general": "codellama_7b"
                },
                "content": {},
                "analysis": {}
            },
            "embedding": {
                "default": "nomic_embed",
                "allow_override": "force"
            },
            "backends": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "enabled": True
                },
                "anthropic": {
                    "api_key": "${ANTHROPIC_API_KEY}",
                    "enabled": False
                }
            }
        }
    }


@pytest.fixture
def anthropic_override_yaml():
    """Sample Anthropic override config."""
    return {
        "llm": {
            "backends": {
                "anthropic": {
                    "enabled": True
                }
            },
            "defaults": {
                "god": "claude_sonnet",
                "escalation": "claude_sonnet",
                "general": "claude_sonnet",
                "fast": "claude_haiku"
                # veryfast not overridden - should keep tinyllama
            }
        }
    }


def test_basic_defaults(temp_config_dir, unified_config_yaml):
    """Test that defaults cascade to all roles."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Test default role uses defaults
    assert config.get_model("default", "god") == "qwen_14b"
    assert config.get_model("default", "general") == "llama3"
    assert config.get_model("default", "fast") == "llama3"
    assert config.get_model("default", "veryfast") == "tinyllama"

    # Test content role uses defaults (no overrides)
    assert config.get_model("content", "god") == "qwen_14b"
    assert config.get_model("content", "general") == "llama3"


def test_role_specific_override(temp_config_dir, unified_config_yaml):
    """Test that role-specific overrides work."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Code role should override general but inherit others
    assert config.get_model("code", "general") == "codellama_7b"  # Overridden
    assert config.get_model("code", "god") == "qwen_14b"  # Inherited from defaults
    assert config.get_model("code", "fast") == "llama3"  # Inherited from defaults
    assert config.get_model("code", "veryfast") == "tinyllama"  # Inherited from defaults


def test_model_metadata_lookup(temp_config_dir, unified_config_yaml):
    """Test model metadata retrieval."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Get metadata for llama3
    metadata = config.get_model_metadata("llama3")
    assert metadata["name"] == "llama3"
    assert metadata["backend"] == "ollama"
    assert metadata["context_window"] == 8192
    assert metadata["cost"] == "medium"
    assert metadata["speed"] == "fast"
    assert metadata["quality"] == "excellent"

    # Get metadata for code model
    metadata = config.get_model_metadata("codellama_7b")
    assert metadata["name"] == "codellama:7b"
    assert metadata["specialization"] == "code"
    assert metadata["context_window"] == 16384


def test_resolve_model_full(temp_config_dir, unified_config_yaml):
    """Test full resolution from role+level to metadata."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Resolve code.general (should use codellama_7b override)
    metadata = config.resolve_model("code", "general")
    assert metadata["model_key"] == "codellama_7b"
    assert metadata["name"] == "codellama:7b"
    assert metadata["context_window"] == 16384
    assert metadata["specialization"] == "code"

    # Resolve default.general (should use llama3 from defaults)
    metadata = config.resolve_model("default", "general")
    assert metadata["model_key"] == "llama3"
    assert metadata["name"] == "llama3"
    assert metadata["context_window"] == 8192


def test_anthropic_override(temp_config_dir, unified_config_yaml, anthropic_override_yaml):
    """Test that Anthropic override correctly cascades."""
    # Create base config
    base_path = temp_config_dir / "config.base.yaml"
    with open(base_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    # Create override config that merges with base
    override_path = temp_config_dir / "config.anthropic.yaml"

    # Merge configs manually (simulating --config loading)
    merged = unified_config_yaml.copy()
    # Update defaults
    merged["llm"]["defaults"].update(anthropic_override_yaml["llm"]["defaults"])
    # Update backends
    merged["llm"]["backends"]["anthropic"]["enabled"] = True

    with open(override_path, 'w') as f:
        yaml.dump(merged, f)

    config = ConfigManager(str(override_path))

    # Test that defaults were overridden
    assert config.get_model("default", "god") == "claude_sonnet"
    assert config.get_model("default", "general") == "claude_sonnet"
    assert config.get_model("default", "fast") == "claude_haiku"
    assert config.get_model("default", "veryfast") == "tinyllama"  # Not overridden

    # Test that ALL roles inherit the new defaults
    assert config.get_model("content", "god") == "claude_sonnet"
    assert config.get_model("analysis", "general") == "claude_sonnet"

    # Test that code role's override is preserved
    assert config.get_model("code", "general") == "codellama_7b"  # Still uses override
    assert config.get_model("code", "god") == "claude_sonnet"  # Inherits new default


def test_context_window_resolution(temp_config_dir, unified_config_yaml):
    """Test context window resolution from model registry."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Test context window lookup by model name
    assert config.get_context_window("tinyllama") == 2048
    assert config.get_context_window("llama3") == 8192
    assert config.get_context_window("codellama:7b") == 16384
    assert config.get_context_window("qwen2.5-coder:14b") == 32768
    assert config.get_context_window("claude-3-5-sonnet-20241022") == 200000

    # Test unknown model falls back to default
    assert config.get_context_window("unknown-model") == 4096


def test_missing_model_warning(temp_config_dir, unified_config_yaml):
    """Test that missing model configurations trigger warnings."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Request a level that doesn't exist
    model = config.get_model("default", "nonexistent")
    assert model is None

    # Get metadata for non-existent model
    metadata = config.get_model_metadata("nonexistent_model")
    assert metadata["name"] == "nonexistent_model"  # Falls back to key as name
    assert metadata["backend"] == "ollama"  # Default backend
    assert metadata["context_window"] == 4096  # Default context


def test_backward_compatibility(temp_config_dir):
    """Test that old config format still works."""
    old_config = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "models": {
                "overseer": "llama3",
                "generator": "codellama",
                "triage": "tinyllama",
                "escalation": "qwen2.5-coder:14b"
            },
            "context_windows": {
                "llama3": 8192,
                "codellama": 16384,
                "tinyllama": 2048,
                "qwen2.5-coder:14b": 32768,
                "default": 4096
            }
        }
    }

    config_path = temp_config_dir / "config.old.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(old_config, f)

    config = ConfigManager(str(config_path))

    # Test that old properties still work
    assert config.overseer_model == "llama3"
    assert config.generator_model == "codellama"
    assert config.triage_model == "tinyllama"
    assert config.escalation_model == "qwen2.5-coder:14b"

    # Test context window lookup with old structure
    assert config.get_context_window("llama3") == 8192
    assert config.get_context_window("codellama") == 16384


def test_cascade_priority(temp_config_dir, unified_config_yaml):
    """Test that resolution priority is correct: role > defaults."""
    config_path = temp_config_dir / "config.yaml"

    # Add conflicting override
    unified_config_yaml["llm"]["roles"]["code"]["god"] = "codellama_7b"  # Override god level for code

    with open(config_path, 'w') as f:
        yaml.dump(unified_config_yaml, f)

    config = ConfigManager(str(config_path))

    # Code role should use its override, not the default
    assert config.get_model("code", "god") == "codellama_7b"  # Role override wins
    assert config.get_model("default", "god") == "qwen_14b"  # Default role uses defaults


if __name__ == "__main__":
    pytest.main([__file__, "-v"])