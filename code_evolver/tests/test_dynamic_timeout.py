"""
Unit tests for dynamic timeout calculation in OllamaClient.
"""
import pytest
from src.ollama_client import OllamaClient
from src.config_manager import ConfigManager


class TestDynamicTimeout:
    """Test dynamic timeout calculation based on model and speed tier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ConfigManager()
        self.client = OllamaClient(config_manager=self.config)

    def test_timeout_for_tinyllama(self):
        """Test that tinyllama gets a short timeout."""
        timeout = self.client.calculate_timeout("tinyllama")
        assert timeout == 30, "tinyllama should have 30s timeout"

    def test_timeout_for_gemma3(self):
        """Test that gemma3:4b gets appropriate timeout."""
        timeout = self.client.calculate_timeout("gemma3:4b")
        assert timeout == 60, "gemma3:4b should have 60s timeout"

    def test_timeout_for_llama3(self):
        """Test that llama3 gets a medium timeout."""
        timeout = self.client.calculate_timeout("llama3")
        assert timeout == 120, "llama3 should have 120s timeout"

    def test_timeout_for_qwen(self):
        """Test that qwen2.5-coder:14b gets a long timeout."""
        timeout = self.client.calculate_timeout("qwen2.5-coder:14b")
        assert timeout == 240, "qwen2.5-coder:14b should have 240s timeout"

    def test_timeout_for_mistral_nemo(self):
        """Test that mistral-nemo gets appropriate timeout."""
        timeout = self.client.calculate_timeout("mistral-nemo")
        assert timeout == 60, "mistral-nemo should have 60s timeout"

    def test_timeout_with_very_fast_tier(self):
        """Test timeout calculation with very-fast speed tier."""
        timeout = self.client.calculate_timeout("unknown_model", speed_tier="very-fast")
        assert timeout == 30, "very-fast tier should have 30s timeout"

    def test_timeout_with_fast_tier(self):
        """Test timeout calculation with fast speed tier."""
        timeout = self.client.calculate_timeout("unknown_model", speed_tier="fast")
        assert timeout == 60, "fast tier should have 60s timeout"

    def test_timeout_with_medium_tier(self):
        """Test timeout calculation with medium speed tier."""
        timeout = self.client.calculate_timeout("unknown_model", speed_tier="medium")
        assert timeout == 120, "medium tier should have 120s timeout"

    def test_timeout_with_slow_tier(self):
        """Test timeout calculation with slow speed tier."""
        timeout = self.client.calculate_timeout("unknown_model", speed_tier="slow")
        assert timeout == 240, "slow tier should have 240s timeout"

    def test_timeout_with_very_slow_tier(self):
        """Test timeout calculation with very-slow speed tier."""
        timeout = self.client.calculate_timeout("unknown_model", speed_tier="very-slow")
        assert timeout == 480, "very-slow tier should have 480s timeout"

    def test_timeout_default_fallback(self):
        """Test that unknown models get default timeout."""
        timeout = self.client.calculate_timeout("completely_unknown_model")
        assert timeout == 120, "unknown models should default to 120s timeout"

    def test_model_timeout_overrides_tier(self):
        """Test that model-specific timeout overrides speed tier."""
        # Even if we pass a different tier, model-specific should win
        timeout = self.client.calculate_timeout("tinyllama", speed_tier="very-slow")
        assert timeout == 30, "model-specific timeout should override tier"

    def test_timeout_with_model_key_lookup(self):
        """Test timeout calculation using model_key for config lookup."""
        # This would require the config to have tool metadata
        # For now, just verify it doesn't crash
        timeout = self.client.calculate_timeout("some_model", model_key="generator")
        assert isinstance(timeout, int), "should return an integer timeout"
        assert timeout > 0, "timeout should be positive"
