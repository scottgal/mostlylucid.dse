"""
Anthropic API client for interacting with Claude models.
Supports Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku, and other models.
"""
import requests
import json
import logging
import os
from typing import Optional, Dict, Any, List

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)


class AnthropicClient(LLMClientBase):
    """Client for communicating with Anthropic's Claude API."""

    # Anthropic API version
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com",
        config_manager: Optional[Any] = None
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (reads from ANTHROPIC_API_KEY env var if not provided)
            base_url: Base URL for API (default: Anthropic)
            config_manager: Optional ConfigManager
        """
        super().__init__(config_manager=config_manager)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.backend_type = "anthropic"

        if not self.api_key:
            logger.warning("No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable.")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self.API_VERSION,
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if Anthropic API is accessible.

        Note: Anthropic doesn't have a models list endpoint, so we test with a minimal request.

        Args:
            endpoint: Optional specific endpoint to check

        Returns:
            True if API is accessible, False otherwise
        """
        url = endpoint or self.base_url
        try:
            # Make a minimal test request
            response = requests.post(
                f"{url}/v1/messages",
                headers=self._get_headers(),
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}]
                },
                timeout=10
            )
            # Both 200 (success) and 400 (bad request) indicate the API is accessible
            # 401 would mean auth issue but API is reachable
            if response.status_code in [200, 400, 401]:
                logger.info(f"✓ Connected to Anthropic API at {url}")
                return True
            else:
                logger.error(f"✗ Unexpected response from Anthropic API: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to Anthropic API at {url}: {e}")
            return False

    def list_models(self, endpoint: Optional[str] = None) -> List[str]:
        """
        List available models.

        Note: Anthropic doesn't provide a models list endpoint,
        so we return a hardcoded list of known models.

        Args:
            endpoint: Optional specific endpoint (unused)

        Returns:
            List of known model IDs
        """
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]

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
        Generate text using Anthropic Messages API.

        Args:
            model: Model name (e.g., 'claude-3-5-sonnet-20241022')
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response (not implemented)
            endpoint: Optional specific endpoint URL
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier for timeout calculation
            max_tokens: Maximum tokens to generate (default: 4096)
            **kwargs: Additional Anthropic-specific parameters

        Returns:
            Generated text response
        """
        url = endpoint or self.base_url
        messages_url = f"{url}/v1/messages"

        # Build messages array
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature
        }

        # Add system prompt if provided
        if system:
            payload["system"] = system

        # Add any additional kwargs
        payload.update(kwargs)

        try:
            timeout = self.calculate_timeout(model, model_key, speed_tier)
            logger.info(f"Generating with Anthropic model '{model}' (timeout: {timeout}s)...")

            logger.debug(f"Request to {messages_url}:")
            logger.debug(f"  Model: {model}")
            logger.debug(f"  Prompt: {prompt}")
            logger.debug(f"  Temperature: {temperature}")
            if system:
                logger.debug(f"  System: {system}")

            response = requests.post(
                messages_url,
                headers=self._get_headers(),
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract response from content
            if "content" in data and len(data["content"]) > 0:
                result = data["content"][0]["text"]
            else:
                logger.error(f"Unexpected response format: {data}")
                return ""

            logger.debug(f"Response from {messages_url}:")
            logger.debug(f"  Length: {len(result)} characters")
            logger.debug(f"  Full response: {result}")

            logger.info(f"✓ Generated {len(result)} characters")
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for {messages_url}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating response from {messages_url}: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")
            return ""

    def _get_default_context_window(self, model: str) -> int:
        """Get default context window for Anthropic models."""
        context_windows = {
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-5-sonnet-20240620": 200000,
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000
        }

        # Check for exact match
        if model in context_windows:
            return context_windows[model]

        # Check for prefix match
        for key, window in context_windows.items():
            if model.startswith(key):
                return window

        # Default for Claude 3 family
        return 200000

    def _get_default_code_model(self) -> str:
        """Get default model for code generation."""
        return "claude-3-5-sonnet-20241022"

    def _get_default_eval_model(self) -> str:
        """Get default model for evaluation."""
        return "claude-3-5-sonnet-20241022"

    def _get_default_triage_model(self) -> str:
        """Get default model for triage."""
        return "claude-3-haiku-20240307"
