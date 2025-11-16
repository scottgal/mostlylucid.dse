"""
Integration tests for unified LLM config with real config files.
"""
import pytest
from pathlib import Path
from src.config_manager import ConfigManager


def test_load_base_config():
    """Test loading the main config.yaml."""
    config = ConfigManager("config.yaml")

    # Test that defaults work
    assert config.get_model("default", "god") == "deepseek_16b"
    assert config.get_model("default", "general") == "llama3"
    assert config.get_model("default", "veryfast") == "tinyllama"

    # Test that code role overrides work
    assert config.get_model("code", "general") == "codellama_7b"
    assert config.get_model("code", "fast") == "qwen_3b"
    assert config.get_model("code", "god") == "deepseek_16b"  # Inherited

    # Test metadata resolution
    metadata = config.resolve_model("code", "general")
    assert metadata["model_key"] == "codellama_7b"
    assert metadata["name"] == "codellama:7b"
    assert metadata["backend"] == "ollama"
    assert metadata["context_window"] == 16384
    assert metadata["specialization"] == "code"


def test_load_local_config():
    """Test loading config.local.yaml."""
    config = ConfigManager("config.local.yaml")

    # Should be identical to base config
    assert config.get_model("default", "general") == "llama3"
    assert config.get_model("code", "general") == "codellama_7b"

    # Test metadata
    metadata = config.resolve_model("default", "fast")
    assert metadata["model_key"] == "gemma3_4b"
    assert metadata["backend"] == "ollama"


def test_load_anthropic_config():
    """Test loading config.anthropic.yaml."""
    config = ConfigManager("config.anthropic.yaml")

    # Test that Anthropic models are used
    assert config.get_model("default", "god") == "claude_opus"
    assert config.get_model("default", "general") == "claude_sonnet"
    assert config.get_model("default", "fast") == "claude_haiku"
    assert config.get_model("default", "veryfast") == "tinyllama"  # Still local

    # Test that ALL roles use Anthropic by default
    assert config.get_model("content", "general") == "claude_sonnet"
    assert config.get_model("analysis", "escalation") == "claude_sonnet"

    # Test metadata resolution
    metadata = config.resolve_model("default", "general")
    assert metadata["model_key"] == "claude_sonnet"
    assert metadata["name"] == "claude-3-5-sonnet-20241022"
    assert metadata["backend"] == "anthropic"
    assert metadata["context_window"] == 200000


def test_context_window_resolution():
    """Test context window resolution for all configs."""
    configs = ["config.yaml", "config.local.yaml", "config.anthropic.yaml"]

    for config_file in configs:
        config = ConfigManager(config_file)

        # Test Ollama models
        if config_file != "config.anthropic.yaml":
            assert config.get_context_window("llama3") == 8192
            assert config.get_context_window("codellama:7b") == 16384
            assert config.get_context_window("deepseek-coder-v2:16b") == 131072

        # Test Anthropic models (only in anthropic config)
        if config_file == "config.anthropic.yaml":
            assert config.get_context_window("claude-3-5-sonnet-20241022") == 200000
            assert config.get_context_window("claude-3-haiku-20240307") == 200000


def test_all_roles_and_levels():
    """Test that all combinations of roles and levels resolve correctly."""
    config = ConfigManager("config.yaml")

    roles = ["default", "code", "content", "analysis"]
    levels = ["god", "escalation", "general", "fast", "veryfast"]

    for role in roles:
        for level in levels:
            model_key = config.get_model(role, level)
            assert model_key is not None, f"No model for {role}.{level}"

            # Verify metadata exists
            metadata = config.get_model_metadata(model_key)
            assert "name" in metadata
            assert "backend" in metadata
            assert "context_window" in metadata

            # Verify full resolution works
            resolved = config.resolve_model(role, level)
            assert resolved["model_key"] == model_key
            assert "name" in resolved


def test_embedding_model():
    """Test that embedding model is correctly configured."""
    configs = ["config.yaml", "config.local.yaml", "config.anthropic.yaml"]

    for config_file in configs:
        config = ConfigManager(config_file)

        # Embedding should always be nomic_embed
        embedding_model = config.get("llm.embedding.default")
        assert embedding_model == "nomic_embed"

        # Verify it's protected
        allow_override = config.get("llm.embedding.allow_override")
        assert allow_override == "force"


def test_backward_compatibility():
    """Test that old property accessors still work."""
    config = ConfigManager("config.yaml")

    # Old properties should still work (via legacy mapping)
    # These may return the actual model names from old structure if present
    # or None if not configured in old format
    overseer = config.overseer_model
    generator = config.generator_model

    # These should work regardless
    assert config.ollama_url == "http://localhost:11434"


def test_cost_and_metadata():
    """Test that all models have proper cost/speed/quality metadata."""
    config = ConfigManager("config.yaml")

    models = config.get("llm.models", {})

    for model_key, model_config in models.items():
        # All models should have these fields
        assert "name" in model_config, f"{model_key} missing 'name'"
        assert "backend" in model_config, f"{model_key} missing 'backend'"
        assert "context_window" in model_config, f"{model_key} missing 'context_window'"
        assert "cost" in model_config, f"{model_key} missing 'cost'"
        assert "speed" in model_config, f"{model_key} missing 'speed'"
        assert "quality" in model_config, f"{model_key} missing 'quality'"

        # Verify valid values
        assert model_config["cost"] in ["very-low", "low", "medium", "high", "very-high"]
        assert model_config["speed"] in ["very-fast", "fast", "medium", "slow", "very-slow"]
        assert model_config["quality"] in ["basic", "good", "excellent", "exceptional"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])