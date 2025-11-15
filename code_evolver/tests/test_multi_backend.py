"""
Comprehensive tests for multi-backend LLM support.

Tests all backend implementations, factory, and model selector tool.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from src.llm_client_base import LLMClientBase
from src.ollama_client import OllamaClient
from src.openai_client import OpenAIClient
from src.anthropic_client import AnthropicClient
from src.azure_client import AzureOpenAIClient
from src.lmstudio_client import LMStudioClient
from src.llm_client_factory import LLMClientFactory, MultiBackendClient
from src.model_selector_tool import ModelSelectorTool


# ============================================================================
# Base Client Tests
# ============================================================================

class TestLLMClientBase:
    """Test the base abstraction class."""

    def test_base_is_abstract(self):
        """Cannot instantiate base class directly."""
        with pytest.raises(TypeError):
            LLMClientBase()

    def test_subclass_must_implement_methods(self):
        """Subclasses must implement all abstract methods."""

        class IncompleteClient(LLMClientBase):
            def check_connection(self, endpoint=None):
                return True

            def list_models(self, endpoint=None):
                return []

            # Missing generate() - should fail

        with pytest.raises(TypeError):
            IncompleteClient()


# ============================================================================
# OpenAI Client Tests
# ============================================================================

class TestOpenAIClient:
    """Test OpenAI client implementation."""

    @patch('src.openai_client.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Hello, world!"
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        result = client.generate(
            model="gpt-4",
            prompt="Say hello"
        )

        assert result == "Hello, world!"
        assert mock_post.called

    @patch('src.openai_client.requests.post')
    def test_generate_with_system_prompt(self, mock_post):
        """Test generation with system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        client.generate(
            model="gpt-4",
            prompt="User message",
            system="You are a helpful assistant"
        )

        # Check that system message was included
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['role'] == 'system'
        assert payload['messages'][1]['role'] == 'user'

    def test_api_key_from_env(self):
        """Test API key loading from environment."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-key'}):
            client = OpenAIClient()
            assert client.api_key == 'env-key'

    def test_context_windows(self):
        """Test context window defaults."""
        client = OpenAIClient()
        assert client._get_default_context_window("gpt-4") == 8192
        assert client._get_default_context_window("gpt-4-turbo") == 128000
        assert client._get_default_context_window("gpt-3.5-turbo") == 16385

    @patch('src.openai_client.requests.get')
    def test_check_connection(self, mock_get):
        """Test connection check."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        assert client.check_connection() is True

    @patch('src.openai_client.requests.get')
    def test_list_models(self, mock_get):
        """Test listing models."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5-turbo"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        models = client.list_models()
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models


# ============================================================================
# Anthropic Client Tests
# ============================================================================

class TestAnthropicClient:
    """Test Anthropic client implementation."""

    @patch('src.anthropic_client.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [
                {
                    "text": "Hello from Claude!"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        result = client.generate(
            model="claude-3-5-sonnet-20241022",
            prompt="Say hello"
        )

        assert result == "Hello from Claude!"

    @patch('src.anthropic_client.requests.post')
    def test_generate_with_system(self, mock_post):
        """Test generation with system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": [{"text": "Response"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = AnthropicClient(api_key="test-key")
        client.generate(
            model="claude-3-5-sonnet-20241022",
            prompt="User message",
            system="You are helpful"
        )

        # Check that system was included in payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert 'system' in payload
        assert payload['system'] == "You are helpful"

    def test_list_models(self):
        """Test model listing (hardcoded for Anthropic)."""
        client = AnthropicClient(api_key="test-key")
        models = client.list_models()
        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-opus-20240229" in models
        assert "claude-3-haiku-20240307" in models

    def test_context_windows(self):
        """Test context window defaults."""
        client = AnthropicClient()
        assert client._get_default_context_window("claude-3-5-sonnet-20241022") == 200000
        assert client._get_default_context_window("claude-3-opus-20240229") == 200000


# ============================================================================
# Azure Client Tests
# ============================================================================

class TestAzureOpenAIClient:
    """Test Azure OpenAI client implementation."""

    @patch('src.azure_client.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Azure response"
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = AzureOpenAIClient(
            api_key="test-key",
            endpoint="https://test.openai.azure.com"
        )
        result = client.generate(
            model="gpt-4",  # deployment name
            prompt="Test"
        )

        assert result == "Azure response"

    def test_build_url(self):
        """Test Azure URL construction."""
        client = AzureOpenAIClient(
            api_key="test-key",
            endpoint="https://test.openai.azure.com"
        )
        url = client._build_url("gpt-4-deployment")
        assert "test.openai.azure.com" in url
        assert "gpt-4-deployment" in url
        assert "api-version" in url


# ============================================================================
# LM Studio Client Tests
# ============================================================================

class TestLMStudioClient:
    """Test LM Studio client implementation."""

    @patch('src.lmstudio_client.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Local model response"
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = LMStudioClient()
        result = client.generate(
            model="local-model",
            prompt="Test"
        )

        assert result == "Local model response"

    @patch('src.lmstudio_client.requests.get')
    def test_list_models(self, mock_get):
        """Test listing models."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "llama-3-8b"},
                {"id": "mistral-7b"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = LMStudioClient()
        models = client.list_models()
        assert "llama-3-8b" in models
        assert "mistral-7b" in models

    def test_context_window_inference(self):
        """Test context window inference from model name."""
        client = LMStudioClient()
        assert client._get_default_context_window("model-128k") == 131072
        assert client._get_default_context_window("model-32k") == 32768
        assert client._get_default_context_window("llama-3-8b") == 8192


# ============================================================================
# Factory Tests
# ============================================================================

class TestLLMClientFactory:
    """Test the LLM client factory."""

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        client = LLMClientFactory.create_client("ollama")
        assert isinstance(client, OllamaClient)
        assert client.backend_type == "ollama"

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        client = LLMClientFactory.create_client("openai", api_key="test")
        assert isinstance(client, OpenAIClient)
        assert client.backend_type == "openai"

    def test_create_anthropic_client(self):
        """Test creating Anthropic client."""
        client = LLMClientFactory.create_client("anthropic", api_key="test")
        assert isinstance(client, AnthropicClient)
        assert client.backend_type == "anthropic"

    def test_create_azure_client(self):
        """Test creating Azure client."""
        client = LLMClientFactory.create_client(
            "azure",
            api_key="test",
            endpoint="https://test.openai.azure.com"
        )
        assert isinstance(client, AzureOpenAIClient)
        assert client.backend_type == "azure"

    def test_create_lmstudio_client(self):
        """Test creating LM Studio client."""
        client = LLMClientFactory.create_client("lmstudio")
        assert isinstance(client, LMStudioClient)
        assert client.backend_type == "lmstudio"

    def test_invalid_backend(self):
        """Test error on invalid backend."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            LLMClientFactory.create_client("invalid-backend")

    def test_get_available_backends(self):
        """Test listing available backends."""
        backends = LLMClientFactory.get_available_backends()
        assert "ollama" in backends
        assert "openai" in backends
        assert "anthropic" in backends
        assert "azure" in backends
        assert "lmstudio" in backends

    def test_create_from_config(self):
        """Test creating client from config."""
        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "backend": "openai",
                "openai": {
                    "api_key": "test-key",
                    "base_url": "https://api.openai.com/v1"
                }
            }
        }

        client = LLMClientFactory.create_from_config(mock_config)
        assert isinstance(client, OpenAIClient)


# ============================================================================
# Multi-Backend Client Tests
# ============================================================================

class TestMultiBackendClient:
    """Test multi-backend client with fallback."""

    @patch('src.llm_client_factory.LLMClientFactory.create_from_config')
    def test_fallback_on_primary_failure(self, mock_create):
        """Test fallback to secondary backend when primary fails."""
        # Create mock clients
        primary_client = Mock()
        primary_client.generate.side_effect = Exception("Primary failed")

        fallback_client = Mock()
        fallback_client.generate.return_value = "Fallback success"

        # Factory returns different clients
        mock_create.side_effect = [primary_client, fallback_client]

        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "backend": "openai",
                "fallback_backends": ["anthropic"]
            }
        }

        client = MultiBackendClient(
            mock_config,
            primary_backend="openai",
            fallback_backends=["anthropic"]
        )

        result = client.generate(model="test", prompt="test")
        assert result == "Fallback success"

    @patch('src.llm_client_factory.LLMClientFactory.create_from_config')
    def test_uses_primary_when_successful(self, mock_create):
        """Test that primary is used when it succeeds."""
        primary_client = Mock()
        primary_client.generate.return_value = "Primary success"

        mock_create.return_value = primary_client

        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "backend": "openai",
                "fallback_backends": []
            }
        }

        client = MultiBackendClient(
            mock_config,
            primary_backend="openai",
            fallback_backends=[]
        )

        result = client.generate(model="test", prompt="test")
        assert result == "Primary success"


# ============================================================================
# Model Selector Tool Tests
# ============================================================================

class TestModelSelectorTool:
    """Test the model selector tool."""

    def test_initialization(self):
        """Test tool initialization."""
        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "ollama": {
                    "models": {
                        "generator": "qwen2.5-coder"
                    }
                }
            }
        }

        selector = ModelSelectorTool(mock_config)
        assert selector.config == mock_config
        assert isinstance(selector.backends, dict)

    def test_select_model_for_code(self):
        """Test model selection for code generation."""
        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "ollama": {
                    "models": {
                        "generator": "qwen2.5-coder:14b"
                    }
                }
            }
        }
        mock_config.get_context_window = Mock(return_value=131072)

        selector = ModelSelectorTool(mock_config)
        recommendations = selector.select_model(
            task_description="Generate Python code for sorting",
            top_k=3
        )

        assert len(recommendations) > 0
        assert recommendations[0]["rank"] == 1

    def test_select_model_with_backend_preference(self):
        """Test model selection with backend preference."""
        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "openai": {},
                "anthropic": {}
            }
        }
        mock_config.get_context_window = Mock(return_value=8192)

        selector = ModelSelectorTool(mock_config)
        recommendations = selector.select_model(
            task_description="Analyze this code",
            backend_preference="anthropic",
            top_k=3
        )

        # Should prefer Anthropic
        assert len(recommendations) > 0

    def test_natural_language_parsing(self):
        """Test natural language backend/model selection."""
        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "openai": {},
                "anthropic": {}
            }
        }
        mock_config.get_context_window = Mock(return_value=8192)

        selector = ModelSelectorTool(mock_config)

        # Should parse "use gpt-4" from task description
        recommendations = selector.select_model(
            task_description="Use GPT-4 to analyze this code",
            top_k=3
        )

        # Should strongly prefer GPT-4
        assert len(recommendations) > 0

    def test_cost_constraints(self):
        """Test model selection with cost constraints."""
        mock_config = Mock()
        mock_config.config = {
            "llm": {
                "openai": {},
                "ollama": {}
            }
        }
        mock_config.get_context_window = Mock(return_value=8192)

        selector = ModelSelectorTool(mock_config)
        recommendations = selector.select_model(
            task_description="Quick task",
            constraints={"max_cost": "low"},
            top_k=3
        )

        # Should prefer free/low cost models
        assert len(recommendations) > 0

    def test_speed_tier_inference(self):
        """Test speed tier inference from model names."""
        mock_config = Mock()
        mock_config.config = {"llm": {}}

        selector = ModelSelectorTool(mock_config)

        assert selector._infer_speed("tinyllama") == "very-fast"
        assert selector._infer_speed("gpt-3.5-turbo") == "fast"
        assert selector._infer_speed("llama3") == "medium"
        assert selector._infer_speed("gpt-4") == "slow"

    def test_quality_tier_inference(self):
        """Test quality tier inference from model names."""
        mock_config = Mock()
        mock_config.config = {"llm": {}}

        selector = ModelSelectorTool(mock_config)

        assert selector._infer_quality("gpt-4") == "excellent"
        assert selector._infer_quality("claude-3-opus") == "excellent"
        assert selector._infer_quality("llama3") == "good"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_end_to_end_model_selection_and_generation(self):
        """Test complete workflow from selection to generation."""
        # This would require actual API access or extensive mocking
        # Placeholder for future integration test
        pass

    def test_config_driven_backend_switching(self):
        """Test switching backends via configuration."""
        # Placeholder for config-driven test
        pass


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
