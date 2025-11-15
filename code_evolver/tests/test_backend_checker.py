"""
Tests for Backend Configuration Checker
"""
import pytest
import os
from unittest.mock import Mock, patch
from src.backend_config_checker import (
    BackendConfigChecker,
    BackendStatus,
    BackendCheckResult
)


class TestBackendConfigChecker:
    """Test suite for backend configuration checker."""

    def test_check_ollama_configured(self):
        """Test checking Ollama backend when configured."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "ollama": {
                    "base_url": "http://localhost:11434"
                }
            }
        }

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("ollama", test_connection=False)

        assert result.backend == "ollama"
        assert result.status == BackendStatus.READY
        assert result.ready is True
        assert "localhost:11434" in result.message

    def test_check_ollama_not_configured(self):
        """Test checking Ollama backend when not configured."""
        config_manager = Mock()
        config_manager.config = {"llm": {}}

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("ollama", test_connection=False)

        assert result.backend == "ollama"
        assert result.status == BackendStatus.MISSING_CONFIG
        assert result.ready is False

    def test_check_openai_with_api_key(self):
        """Test checking OpenAI backend with API key set."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "openai": {
                    "api_key": "sk-test123456789"
                }
            }
        }

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("openai", test_connection=False)

        assert result.backend == "openai"
        assert result.status == BackendStatus.READY
        assert result.ready is True
        assert "valid API key" in result.message

    def test_check_openai_without_api_key(self):
        """Test checking OpenAI backend without API key."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "openai": {
                    "api_key": "${OPENAI_API_KEY}"
                }
            }
        }

        with patch.dict(os.environ, {}, clear=True):
            checker = BackendConfigChecker(config_manager)
            result = checker.check_backend("openai", test_connection=False)

        assert result.backend == "openai"
        assert result.status == BackendStatus.MISSING_API_KEY
        assert result.ready is False
        assert "not set" in result.message

    def test_check_openai_with_env_var(self):
        """Test checking OpenAI backend with API key from environment."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "openai": {
                    "api_key": "${OPENAI_API_KEY}"
                }
            }
        }

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123456789"}):
            checker = BackendConfigChecker(config_manager)
            result = checker.check_backend("openai", test_connection=False)

        assert result.backend == "openai"
        assert result.status == BackendStatus.READY
        assert result.ready is True

    def test_check_anthropic_with_api_key(self):
        """Test checking Anthropic backend with API key."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "anthropic": {
                    "api_key": "sk-ant-test123456789"
                }
            }
        }

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("anthropic", test_connection=False)

        assert result.backend == "anthropic"
        assert result.status == BackendStatus.READY
        assert result.ready is True

    def test_check_azure_with_api_key_and_endpoint(self):
        """Test checking Azure backend with API key and endpoint."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "azure": {
                    "api_key": "test-key-123",
                    "endpoint": "https://test.openai.azure.com"
                }
            }
        }

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("azure", test_connection=False)

        assert result.backend == "azure"
        assert result.status == BackendStatus.READY
        assert result.ready is True

    def test_check_azure_missing_endpoint(self):
        """Test checking Azure backend with API key but no endpoint."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "azure": {
                    "api_key": "test-key-123"
                }
            }
        }

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("azure", test_connection=False)

        assert result.backend == "azure"
        assert result.status == BackendStatus.INVALID_CONFIG
        assert result.ready is False
        assert "endpoint" in result.message.lower()

    def test_check_all_backends(self):
        """Test checking all backends at once."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "ollama": {"base_url": "http://localhost:11434"},
                "openai": {"api_key": "sk-test123"},
                "anthropic": {"api_key": "${ANTHROPIC_API_KEY}"}
            }
        }

        with patch.dict(os.environ, {}, clear=True):
            checker = BackendConfigChecker(config_manager)
            results = checker.check_all_backends(test_connection=False)

        assert len(results) == 5  # ollama, openai, anthropic, azure, lmstudio
        assert "ollama" in results
        assert "openai" in results
        assert "anthropic" in results
        assert results["ollama"].ready is True
        assert results["openai"].ready is True
        assert results["anthropic"].ready is False  # Missing env var

    def test_get_ready_backends(self):
        """Test getting list of ready backends."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "ollama": {"base_url": "http://localhost:11434"},
                "openai": {"api_key": "sk-test123"}
            }
        }

        checker = BackendConfigChecker(config_manager)
        ready = checker.get_ready_backends()

        assert "ollama" in ready
        assert "openai" in ready

    def test_get_primary_backend(self):
        """Test getting primary backend from config."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "backend": "anthropic"
            }
        }

        checker = BackendConfigChecker(config_manager)
        primary = checker.get_primary_backend()

        assert primary == "anthropic"

    def test_suggest_setup_commands_openai(self):
        """Test setup command suggestions for OpenAI."""
        config_manager = Mock()
        config_manager.config = {"llm": {}}

        checker = BackendConfigChecker(config_manager)
        suggestions = checker.suggest_setup_commands("openai")

        assert len(suggestions) > 0
        assert any("OPENAI_API_KEY" in s for s in suggestions)

    def test_suggest_setup_commands_anthropic(self):
        """Test setup command suggestions for Anthropic."""
        config_manager = Mock()
        config_manager.config = {"llm": {}}

        checker = BackendConfigChecker(config_manager)
        suggestions = checker.suggest_setup_commands("anthropic")

        assert len(suggestions) > 0
        assert any("ANTHROPIC_API_KEY" in s for s in suggestions)

    def test_api_key_preview_masking(self):
        """Test that API keys are masked in details."""
        config_manager = Mock()
        config_manager.config = {
            "llm": {
                "openai": {
                    "api_key": "sk-test123456789abcdef"
                }
            }
        }

        checker = BackendConfigChecker(config_manager)
        result = checker.check_backend("openai", test_connection=False)

        assert "api_key_preview" in result.details
        # Should show only first 4 and last 4 chars
        assert "sk-t" in result.details["api_key_preview"]
        assert "cdef" in result.details["api_key_preview"]
        assert "..." in result.details["api_key_preview"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
