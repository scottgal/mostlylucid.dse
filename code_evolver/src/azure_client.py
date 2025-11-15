"""
Azure OpenAI Service client for interacting with Azure-hosted OpenAI models.
Supports GPT-4, GPT-3.5, and other models deployed on Azure.
"""
import requests
import json
import logging
import os
from typing import Optional, Dict, Any, List

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)


class AzureOpenAIClient(LLMClientBase):
    """Client for communicating with Azure OpenAI Service."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
        config_manager: Optional[Any] = None
    ):
        """
        Initialize Azure OpenAI client.

        Args:
            api_key: Azure API key (reads from AZURE_OPENAI_API_KEY env var if not provided)
            endpoint: Azure endpoint URL (reads from AZURE_OPENAI_ENDPOINT env var if not provided)
            deployment_name: Default deployment name for models
            api_version: Azure API version
            config_manager: Optional ConfigManager
        """
        super().__init__(config_manager=config_manager)
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = (endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.backend_type = "azure"

        if not self.api_key:
            logger.warning("No Azure API key provided. Set AZURE_OPENAI_API_KEY environment variable.")
        if not self.endpoint:
            logger.warning("No Azure endpoint provided. Set AZURE_OPENAI_ENDPOINT environment variable.")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers

    def _build_url(self, deployment: str, operation: str = "chat/completions") -> str:
        """
        Build Azure OpenAI endpoint URL.

        Args:
            deployment: Deployment name
            operation: API operation (default: chat/completions)

        Returns:
            Full URL for the API call
        """
        return (
            f"{self.endpoint}/openai/deployments/{deployment}/"
            f"{operation}?api-version={self.api_version}"
        )

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if Azure OpenAI Service is accessible.

        Args:
            endpoint: Optional specific endpoint to check

        Returns:
            True if service is accessible, False otherwise
        """
        if not self.endpoint:
            logger.error("No Azure endpoint configured")
            return False

        # Use a test deployment if available
        test_deployment = self.deployment_name or "gpt-35-turbo"

        try:
            # Make a minimal test request
            url = self._build_url(test_deployment)
            response = requests.post(
                url,
                headers=self._get_headers(),
                json={
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 1
                },
                timeout=10
            )
            # Both 200 and some 4xx codes indicate the API is accessible
            if response.status_code in [200, 400, 401]:
                logger.info(f"✓ Connected to Azure OpenAI at {self.endpoint}")
                return True
            else:
                logger.error(f"✗ Unexpected response from Azure: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to Azure OpenAI at {self.endpoint}: {e}")
            return False

    def list_models(self, endpoint: Optional[str] = None) -> List[str]:
        """
        List available deployments.

        Note: This returns deployment names, not model names.
        Azure uses deployments which are instances of models.

        Args:
            endpoint: Optional specific endpoint (unused)

        Returns:
            List of deployment names (if configured in config_manager)
        """
        # Azure doesn't provide a simple models list API
        # Return deployments from config if available
        if self.config_manager and hasattr(self.config_manager, 'config'):
            azure_config = self.config_manager.config.get('azure', {})
            deployments = azure_config.get('deployments', {})
            return list(deployments.keys())

        # Return common deployment names
        return [
            "gpt-4",
            "gpt-4-32k",
            "gpt-35-turbo",
            "gpt-35-turbo-16k"
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
        Generate text using Azure OpenAI Chat Completions API.

        Args:
            model: Deployment name (not model name!)
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response
            endpoint: Optional specific endpoint URL
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier for timeout calculation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Azure-specific parameters

        Returns:
            Generated text response
        """
        if not self.endpoint:
            logger.error("No Azure endpoint configured")
            return ""

        # In Azure, 'model' is actually the deployment name
        deployment = model

        # Build messages array
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
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
            url = self._build_url(deployment)

            logger.info(f"Generating with Azure deployment '{deployment}' (timeout: {timeout}s)...")

            logger.debug(f"Request to {url}:")
            logger.debug(f"  Deployment: {deployment}")
            logger.debug(f"  Messages: {messages}")
            logger.debug(f"  Temperature: {temperature}")

            response = requests.post(
                url,
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

            logger.debug(f"Response from Azure:")
            logger.debug(f"  Length: {len(result)} characters")
            logger.debug(f"  Full response: {result}")

            logger.info(f"✓ Generated {len(result)} characters")
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for Azure deployment '{deployment}'")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating response from Azure: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")
            return ""

    def _get_default_context_window(self, model: str) -> int:
        """Get default context window for Azure deployments."""
        # Azure deployments are based on OpenAI models
        context_windows = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-35-turbo": 16385,
            "gpt-35-turbo-16k": 16385,
        }

        # Check for exact match or prefix
        for key, window in context_windows.items():
            if model == key or model.startswith(key):
                return window

        # Default
        return 8192

    def _get_default_code_model(self) -> str:
        """Get default deployment for code generation."""
        return self.deployment_name or "gpt-4"

    def _get_default_eval_model(self) -> str:
        """Get default deployment for evaluation."""
        return self.deployment_name or "gpt-4"

    def _get_default_triage_model(self) -> str:
        """Get default deployment for triage."""
        return self.deployment_name or "gpt-35-turbo"
