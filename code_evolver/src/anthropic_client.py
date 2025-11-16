"""
Anthropic API client for interacting with Claude models.
Supports Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku, and other models.

Uses the official Anthropic Python SDK for better reliability and error handling.
"""
import logging
import os
from typing import Optional, Dict, Any, List

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError, AuthenticationError

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)

# Import status manager for live status updates
try:
    from .status_manager import get_status_manager
    STATUS_MANAGER_AVAILABLE = True
except ImportError:
    STATUS_MANAGER_AVAILABLE = False


class AnthropicClient(LLMClientBase):
    """Client for communicating with Anthropic's Claude API using official SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com",
        config_manager: Optional[Any] = None
    ):
        """
        Initialize Anthropic client using official SDK.

        Args:
            api_key: Anthropic API key (reads from ANTHROPIC_API_KEY env var if not provided)
            base_url: Base URL for API (default: Anthropic, rarely needs changing)
            config_manager: Optional ConfigManager
        """
        super().__init__(config_manager=config_manager)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.backend_type = "anthropic"

        if not self.api_key:
            logger.warning("No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable.")

        # Initialize official Anthropic client
        try:
            self.client = Anthropic(api_key=self.api_key, base_url=self.base_url)
            logger.debug("Initialized Anthropic SDK client")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            self.client = None

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if Anthropic API is accessible.

        Args:
            endpoint: Optional specific endpoint to check (not used with official SDK)

        Returns:
            True if API is accessible, False otherwise
        """
        if not self.client:
            logger.error("✗ Anthropic client not initialized")
            return False

        try:
            # Make a minimal test request using official SDK
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}]
            )
            logger.info(f"✓ Connected to Anthropic API")
            return True
        except AuthenticationError as e:
            logger.error(f"✗ Authentication failed: {e}")
            return False
        except APIConnectionError as e:
            logger.error(f"✗ Cannot connect to Anthropic API: {e}")
            return False
        except APIError as e:
            logger.error(f"✗ Anthropic API error: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error connecting to Anthropic: {e}")
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
        Generate text using Anthropic Messages API via official SDK.

        Args:
            model: Model name (e.g., 'claude-3-5-sonnet-20241022')
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response (not implemented)
            endpoint: Optional specific endpoint URL (not used with official SDK)
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier for timeout calculation
            max_tokens: Maximum tokens to generate (default: 4096)
            **kwargs: Additional Anthropic-specific parameters

        Returns:
            Generated text response
        """
        if not self.client:
            logger.error("Anthropic client not initialized. Check API key.")
            return ""

        # Build messages array
        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature
        }

        # Add system prompt if provided
        if system:
            request_params["system"] = system

        # Add any additional kwargs (but filter out our custom ones)
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['endpoint', 'model_key', 'speed_tier']}
        request_params.update(filtered_kwargs)

        try:
            timeout = self.calculate_timeout(model, model_key, speed_tier)
            logger.info(f"Generating with Anthropic model '{model}' (timeout: {timeout}s)...")

            logger.debug(f"Request to Anthropic API:")
            logger.debug(f"  Model: {model}")
            logger.debug(f"  Prompt: {prompt[:100]}...")
            logger.debug(f"  Temperature: {temperature}")
            if system:
                logger.debug(f"  System: {system[:100]}...")

            # Show live status update
            if STATUS_MANAGER_AVAILABLE:
                status_mgr = get_status_manager()
                status_mgr.llm_call(model, "anthropic", "generate")

            # Use official SDK to create message
            message = self.client.messages.create(**request_params)

            # Extract response from content
            if message.content and len(message.content) > 0:
                result = message.content[0].text
            else:
                logger.error(f"Unexpected response format: {message}")
                return ""

            logger.debug(f"Response from Anthropic API:")
            logger.debug(f"  Length: {len(result)} characters")

            # Clear status after success
            if STATUS_MANAGER_AVAILABLE:
                get_status_manager().clear()

            logger.info(f"✓ Generated {len(result)} characters")
            return result

        except AuthenticationError as e:
            # Clear status on error
            if STATUS_MANAGER_AVAILABLE:
                get_status_manager().clear()
            logger.error(f"Authentication failed: {e}")
            logger.error("Check that ANTHROPIC_API_KEY is set correctly")
            return ""
        except RateLimitError as e:
            if STATUS_MANAGER_AVAILABLE:
                get_status_manager().clear()
            logger.error(f"Rate limit exceeded: {e}")
            return ""
        except APIConnectionError as e:
            if STATUS_MANAGER_AVAILABLE:
                get_status_manager().clear()
            logger.error(f"Connection error: {e}")
            return ""
        except APIError as e:
            if STATUS_MANAGER_AVAILABLE:
                get_status_manager().clear()
            logger.error(f"Anthropic API error: {e}")
            return ""
        except Exception as e:
            if STATUS_MANAGER_AVAILABLE:
                get_status_manager().clear()
            logger.error(f"Unexpected error generating response: {e}")
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
