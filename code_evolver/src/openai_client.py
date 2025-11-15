"""
OpenAI API client for interacting with OpenAI models.
Supports GPT-4, GPT-3.5, and other OpenAI models.
Compatible with OpenAPI-compatible endpoints (e.g., local proxies).
"""
import requests
import json
import logging
import os
from typing import Optional, Dict, Any, List

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClientBase):
    """Client for communicating with OpenAI API or OpenAPI-compatible services."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        config_manager: Optional[Any] = None,
        organization: Optional[str] = None
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (reads from OPENAI_API_KEY env var if not provided)
            base_url: Base URL for API (default: OpenAI, can be custom endpoint)
            config_manager: Optional ConfigManager
            organization: Optional organization ID
        """
        super().__init__(config_manager=config_manager)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.organization = organization
        self.backend_type = "openai"

        if not self.api_key:
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if OpenAI API is accessible.

        Args:
            endpoint: Optional specific endpoint to check

        Returns:
            True if API is accessible, False otherwise
        """
        url = endpoint or self.base_url
        try:
            response = requests.get(
                f"{url}/models",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"✓ Connected to OpenAI API at {url}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to OpenAI API at {url}: {e}")
            return False

    def list_models(self, endpoint: Optional[str] = None) -> List[str]:
        """
        List available models from OpenAI API.

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
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
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
        Generate text using OpenAI Chat Completions API.

        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response
            endpoint: Optional specific endpoint URL
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier for timeout calculation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters

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
            logger.info(f"Generating with OpenAI model '{model}' (timeout: {timeout}s)...")

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

            # Extract response from choices
            if "choices" in data and len(data["choices"]) > 0:
                result = data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected response format: {data}")
                return ""

            logger.debug(f"Response from {chat_url}:")
            logger.debug(f"  Length: {len(result)} characters")
            logger.debug(f"  Full response: {result}")

            logger.info(f"✓ Generated {len(result)} characters")
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for {chat_url}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating response from {chat_url}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")
            return ""

    def _get_default_context_window(self, model: str) -> int:
        """Get default context window for OpenAI models."""
        context_windows = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385,
            "gpt-3.5": 4096,
            "text-davinci-003": 4096,
            "text-davinci-002": 4096,
        }

        # Check for exact match
        if model in context_windows:
            return context_windows[model]

        # Check for prefix match (e.g., gpt-4-0125-preview)
        for key, window in context_windows.items():
            if model.startswith(key):
                return window

        # Default
        return 8192

    def _get_default_code_model(self) -> str:
        """Get default model for code generation."""
        return "gpt-4"

    def _get_default_eval_model(self) -> str:
        """Get default model for evaluation."""
        return "gpt-4"

    def _get_default_triage_model(self) -> str:
        """Get default model for triage."""
        return "gpt-3.5-turbo"
