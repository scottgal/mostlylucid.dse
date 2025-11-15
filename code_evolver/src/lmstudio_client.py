"""
LM Studio client for interacting with locally-hosted LM Studio models.
LM Studio provides an OpenAI-compatible API for local models.
"""
import requests
import json
import logging
from typing import Optional, Dict, Any, List

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)


class LMStudioClient(LLMClientBase):
    """Client for communicating with LM Studio's local server."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        config_manager: Optional[Any] = None
    ):
        """
        Initialize LM Studio client.

        Args:
            base_url: Base URL for LM Studio API (default: http://localhost:1234/v1)
            config_manager: Optional ConfigManager
        """
        super().__init__(config_manager=config_manager)
        self.base_url = base_url.rstrip("/")
        self.backend_type = "lmstudio"

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Content-Type": "application/json",
        }

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if LM Studio server is running and accessible.

        Args:
            endpoint: Optional specific endpoint to check

        Returns:
            True if server is accessible, False otherwise
        """
        url = endpoint or self.base_url
        try:
            response = requests.get(
                f"{url}/models",
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"✓ Connected to LM Studio at {url}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to LM Studio at {url}: {e}")
            return False

    def list_models(self, endpoint: Optional[str] = None) -> List[str]:
        """
        List available models in LM Studio.

        Args:
            endpoint: Optional specific endpoint

        Returns:
            List of model IDs
        """
        url = endpoint or self.base_url
        try:
            response = requests.get(
                f"{url}/models",
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            # LM Studio returns OpenAI-compatible format
            models = [model['id'] for model in data.get('data', [])]
            return models
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing models from {url}: {e}")
            return []

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False,
        endpoint: Optional[str] = None,
        model_key: Optional[str] = None,
        speed_tier: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using LM Studio Chat Completions API.

        Args:
            model: Model name (or use loaded model if not specified)
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response
            endpoint: Optional specific endpoint URL
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier for timeout calculation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text response
        """
        url = endpoint or self.base_url
        chat_url = f"{url}/chat/completions"

        # Build messages array
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        # Add max_tokens if specified
        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Add any additional kwargs
        payload.update(kwargs)

        try:
            timeout = self.calculate_timeout(model, model_key, speed_tier)
            logger.info(f"Generating with LM Studio model '{model}' (timeout: {timeout}s)...")

            logger.debug(f"Request to {chat_url}:")
            logger.debug(f"  Model: {model}")
            logger.debug(f"  Messages: {messages}")
            logger.debug(f"  Temperature: {temperature}")

            response = requests.post(
                chat_url,
                headers=self._get_headers(),
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract response from choices (OpenAI-compatible format)
            if "choices" in data and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected response format: {data}")
                return ""

            logger.debug(f"Response from LM Studio:")
            logger.debug(f"  Length: {len(result)} characters")
            logger.debug(f"  Full response: {result}")

            logger.info(f"✓ Generated {len(result)} characters")
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for {chat_url}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating response from {chat_url}: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")
            return ""

    def _get_default_context_window(self, model: str) -> int:
        """
        Get default context window for LM Studio models.

        Note: Context windows vary by model. Common defaults:
        - Small models (7B): 4096-8192
        - Medium models (13B): 8192-16384
        - Large models (70B+): 32768-131072
        """
        # Try to infer from model name
        model_lower = model.lower()

        if "128k" in model_lower or "131k" in model_lower:
            return 131072
        elif "32k" in model_lower:
            return 32768
        elif "16k" in model_lower:
            return 16384
        elif "8k" in model_lower:
            return 8192
        elif "4k" in model_lower:
            return 4096

        # Size-based defaults
        if "70b" in model_lower or "65b" in model_lower:
            return 32768
        elif "34b" in model_lower or "33b" in model_lower:
            return 16384
        elif "13b" in model_lower or "14b" in model_lower:
            return 8192
        elif "7b" in model_lower or "8b" in model_lower:
            return 8192
        elif "3b" in model_lower or "2b" in model_lower:
            return 4096

        # Model family defaults
        if "mistral" in model_lower:
            return 32768
        elif "llama-3" in model_lower or "llama3" in model_lower:
            return 8192
        elif "qwen" in model_lower:
            return 32768
        elif "phi" in model_lower:
            return 4096
        elif "gemma" in model_lower:
            return 8192

        # Default
        return 8192

    def _get_default_code_model(self) -> str:
        """Get default model for code generation."""
        # Try to find a code-specific model
        models = self.list_models()
        for model in models:
            if any(keyword in model.lower() for keyword in ["code", "coder", "codellama"]):
                return model

        # Fall back to first available model or default
        return models[0] if models else "default"

    def _get_default_eval_model(self) -> str:
        """Get default model for evaluation."""
        # Use the first available model
        models = self.list_models()
        return models[0] if models else "default"

    def _get_default_triage_model(self) -> str:
        """Get default model for triage."""
        # Try to find a small/fast model for triage
        models = self.list_models()
        for model in models:
            if any(keyword in model.lower() for keyword in ["tiny", "small", "7b", "3b", "2b"]):
                return model

        # Fall back to first available
        return models[0] if models else "default"
