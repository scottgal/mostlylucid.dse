"""
Factory for creating LLM clients based on configuration.
Supports Ollama, OpenAI, Anthropic, Azure OpenAI, and LM Studio backends.
"""
import logging
from typing import Optional, Dict, Any

from .llm_client_base import LLMClientBase
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .azure_client import AzureOpenAIClient
from .lmstudio_client import LMStudioClient

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """
    Factory for creating LLM clients.

    Supports multiple backends and handles configuration-based instantiation.
    """

    # Registry of available backend types
    BACKENDS = {
        "ollama": OllamaClient,
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "azure": AzureOpenAIClient,
        "lmstudio": LMStudioClient,
    }

    @staticmethod
    def create_client(
        backend: str,
        config_manager: Optional[Any] = None,
        **kwargs
    ) -> LLMClientBase:
        """
        Create an LLM client for the specified backend.

        Args:
            backend: Backend type (ollama, openai, anthropic, azure, lmstudio)
            config_manager: Optional ConfigManager instance
            **kwargs: Backend-specific parameters

        Returns:
            Initialized LLM client

        Raises:
            ValueError: If backend is not supported
        """
        backend_lower = backend.lower()

        if backend_lower not in LLMClientFactory.BACKENDS:
            available = ", ".join(LLMClientFactory.BACKENDS.keys())
            raise ValueError(
                f"Unsupported backend: {backend}. "
                f"Available backends: {available}"
            )

        client_class = LLMClientFactory.BACKENDS[backend_lower]
        client = client_class(config_manager=config_manager, **kwargs)

        logger.info(f"Created {backend} client")
        return client

    @staticmethod
    def create_from_config(
        config_manager: Any,
        backend: Optional[str] = None
    ) -> LLMClientBase:
        """
        Create an LLM client from ConfigManager settings.

        Args:
            config_manager: ConfigManager instance with backend configuration
            backend: Optional backend override (uses config default if not specified)

        Returns:
            Initialized LLM client

        Configuration format in config.yaml:
            llm:
              backend: "ollama"  # or openai, anthropic, azure, lmstudio

              ollama:
                base_url: "http://localhost:11434"

              openai:
                api_key: "${OPENAI_API_KEY}"  # or actual key
                base_url: "https://api.openai.com/v1"
                organization: null

              anthropic:
                api_key: "${ANTHROPIC_API_KEY}"
                base_url: "https://api.anthropic.com"

              azure:
                api_key: "${AZURE_OPENAI_API_KEY}"
                endpoint: "${AZURE_OPENAI_ENDPOINT}"
                deployment_name: "gpt-4"
                api_version: "2024-02-15-preview"

              lmstudio:
                base_url: "http://localhost:1234/v1"
        """
        # Get backend from parameter or config
        if not backend:
            backend = config_manager.config.get("llm", {}).get("backend", "ollama")

        backend_lower = backend.lower()
        llm_config = config_manager.config.get("llm", {})
        backend_config = llm_config.get(backend_lower, {})

        logger.info(f"Creating {backend} client from config")

        # Create client based on backend type
        if backend_lower == "ollama":
            return OllamaClient(
                base_url=backend_config.get("base_url", "http://localhost:11434"),
                config_manager=config_manager
            )

        elif backend_lower == "openai":
            return OpenAIClient(
                api_key=backend_config.get("api_key"),
                base_url=backend_config.get("base_url", "https://api.openai.com/v1"),
                organization=backend_config.get("organization"),
                config_manager=config_manager
            )

        elif backend_lower == "anthropic":
            return AnthropicClient(
                api_key=backend_config.get("api_key"),
                base_url=backend_config.get("base_url", "https://api.anthropic.com"),
                config_manager=config_manager
            )

        elif backend_lower == "azure":
            return AzureOpenAIClient(
                api_key=backend_config.get("api_key"),
                endpoint=backend_config.get("endpoint"),
                deployment_name=backend_config.get("deployment_name"),
                api_version=backend_config.get("api_version", "2024-02-15-preview"),
                config_manager=config_manager
            )

        elif backend_lower == "lmstudio":
            return LMStudioClient(
                base_url=backend_config.get("base_url", "http://localhost:1234/v1"),
                config_manager=config_manager
            )

        else:
            raise ValueError(f"Unsupported backend: {backend}")

    @staticmethod
    def get_available_backends() -> list:
        """
        Get list of available backend types.

        Returns:
            List of backend names
        """
        return list(LLMClientFactory.BACKENDS.keys())

    @staticmethod
    def create_multi_backend_client(
        config_manager: Any,
        primary_backend: Optional[str] = None,
        fallback_backends: Optional[list] = None
    ) -> 'MultiBackendClient':
        """
        Create a client that can use multiple backends with fallback support.

        Args:
            config_manager: ConfigManager instance
            primary_backend: Primary backend to use
            fallback_backends: List of fallback backends (in order of preference)

        Returns:
            MultiBackendClient instance
        """
        return MultiBackendClient(
            config_manager=config_manager,
            primary_backend=primary_backend,
            fallback_backends=fallback_backends
        )

    @staticmethod
    def create_routing_client(config_manager: Any) -> 'RoutingClient':
        """
        Create a client that automatically routes requests to the correct backend
        based on model metadata.

        Args:
            config_manager: ConfigManager instance

        Returns:
            RoutingClient instance
        """
        return RoutingClient(config_manager=config_manager)


class MultiBackendClient(LLMClientBase):
    """
    Client that supports multiple backends with automatic fallback.

    Tries the primary backend first, then falls back to alternatives if the primary fails.
    """

    def __init__(
        self,
        config_manager: Any,
        primary_backend: Optional[str] = None,
        fallback_backends: Optional[list] = None
    ):
        """
        Initialize multi-backend client.

        Args:
            config_manager: ConfigManager instance
            primary_backend: Primary backend name
            fallback_backends: List of fallback backend names
        """
        super().__init__(config_manager=config_manager)
        self.config_manager = config_manager
        self.backend_type = "multi"

        # Get backends from config or parameters
        llm_config = config_manager.config.get("llm", {})
        self.primary_backend = primary_backend or llm_config.get("backend", "ollama")
        self.fallback_backends = fallback_backends or llm_config.get("fallback_backends", [])

        # Create clients
        self.primary_client = LLMClientFactory.create_from_config(
            config_manager, self.primary_backend
        )

        self.fallback_clients = [
            LLMClientFactory.create_from_config(config_manager, backend)
            for backend in self.fallback_backends
        ]

        logger.info(
            f"Initialized multi-backend client: "
            f"primary={self.primary_backend}, "
            f"fallbacks={self.fallback_backends}"
        )

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """Check if primary backend is accessible."""
        return self.primary_client.check_connection(endpoint)

    def list_models(self, endpoint: Optional[str] = None) -> list:
        """List models from primary backend."""
        return self.primary_client.list_models(endpoint)

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
        Generate text with automatic fallback support.

        Tries primary backend first, then fallbacks if it fails.
        """
        # Try primary backend
        try:
            result = self.primary_client.generate(
                model=model,
                prompt=prompt,
                system=system,
                temperature=temperature,
                stream=stream,
                endpoint=endpoint,
                model_key=model_key,
                speed_tier=speed_tier,
                max_tokens=max_tokens,
                **kwargs
            )
            if result:
                return result
        except Exception as e:
            logger.warning(f"Primary backend {self.primary_backend} failed: {e}")

        # Try fallback backends
        for i, client in enumerate(self.fallback_clients):
            backend_name = self.fallback_backends[i]
            try:
                logger.info(f"Trying fallback backend: {backend_name}")
                result = client.generate(
                    model=model,
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    stream=stream,
                    endpoint=endpoint,
                    model_key=model_key,
                    speed_tier=speed_tier,
                    max_tokens=max_tokens,
                    **kwargs
                )
                if result:
                    logger.info(f"✓ Fallback backend {backend_name} succeeded")
                    return result
            except Exception as e:
                logger.warning(f"Fallback backend {backend_name} failed: {e}")
                continue

        logger.error("All backends failed")
        return ""

    def _get_default_context_window(self, model: str) -> int:
        """Get context window from primary client."""
        return self.primary_client._get_default_context_window(model)

    def _get_default_code_model(self) -> str:
        """Get default code model from primary client."""
        return self.primary_client._get_default_code_model()

    def _get_default_eval_model(self) -> str:
        """Get default eval model from primary client."""
        return self.primary_client._get_default_eval_model()

    def _get_default_triage_model(self) -> str:
        """Get default triage model from primary client."""
        return self.primary_client._get_default_triage_model()


class RoutingClient(LLMClientBase):
    """
    Client that automatically routes requests to the correct backend based on model metadata.

    This client inspects the model's backend field in the config and routes to the appropriate
    client (Ollama, Anthropic, OpenAI, etc.). This allows mixing models from different backends
    in a single configuration.
    """

    def __init__(self, config_manager: Any):
        """
        Initialize routing client with all enabled backends.

        Args:
            config_manager: ConfigManager instance
        """
        super().__init__(config_manager=config_manager)
        self.config_manager = config_manager
        self.backend_type = "routing"

        # Initialize clients for all enabled backends
        self.clients: Dict[str, LLMClientBase] = {}

        backends_config = config_manager.get("llm.backends", {})
        for backend_name, backend_cfg in backends_config.items():
            if isinstance(backend_cfg, dict) and backend_cfg.get("enabled", False):
                try:
                    self.clients[backend_name] = LLMClientFactory.create_from_config(
                        config_manager, backend_name
                    )
                    logger.info(f"Initialized {backend_name} client for routing")
                except Exception as e:
                    logger.warning(f"Failed to initialize {backend_name} client: {e}")

        if not self.clients:
            logger.warning("No backends enabled! Routing client has no clients to route to.")

    def _get_backend_for_model(self, model: str, model_key: Optional[str] = None) -> Optional[str]:
        """
        Determine which backend to use for a given model.

        Args:
            model: Model name (e.g., 'claude-3-haiku-20240307' or 'llama3')
            model_key: Optional model key to look up metadata

        Returns:
            Backend name (e.g., 'anthropic', 'ollama') or None if not found
        """
        # If model_key is provided, look up the model's backend from metadata
        if model_key:
            metadata = self.config_manager.get_model_metadata(model_key)
            backend = metadata.get("backend")
            if backend:
                logger.debug(f"Model '{model_key}' uses backend: {backend}")
                return backend

        # Otherwise, try to infer from model name by checking all registered models
        models = self.config_manager.get("llm.models", {})
        for key, model_config in models.items():
            if isinstance(model_config, dict):
                model_name = model_config.get("name")
                if model_name == model:
                    backend = model_config.get("backend", "ollama")
                    logger.debug(f"Model '{model}' uses backend: {backend}")
                    return backend

        # Fallback: guess based on model name patterns
        if model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gpt"):
            return "openai"
        else:
            return "ollama"  # Default to ollama

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """Check if at least one backend is accessible."""
        for backend_name, client in self.clients.items():
            if client.check_connection(endpoint):
                logger.info(f"✓ {backend_name} backend is accessible")
                return True
        return False

    def list_models(self, endpoint: Optional[str] = None) -> list:
        """List models from all backends."""
        all_models = []
        for backend_name, client in self.clients.items():
            try:
                models = client.list_models(endpoint)
                all_models.extend(models)
            except Exception as e:
                logger.warning(f"Failed to list models from {backend_name}: {e}")
        return all_models

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
        Generate text by routing to the appropriate backend based on model.

        Args:
            model: Model name
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature
            stream: Whether to stream response
            endpoint: Optional specific endpoint
            model_key: Optional model key for metadata lookup
            speed_tier: Optional speed tier
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text response
        """
        # Determine which backend to use
        backend = self._get_backend_for_model(model, model_key)

        if not backend:
            logger.error(f"Could not determine backend for model: {model}")
            return ""

        if backend not in self.clients:
            logger.error(f"Backend '{backend}' not available (enabled backends: {list(self.clients.keys())})")
            return ""

        # Route to appropriate client
        client = self.clients[backend]
        logger.debug(f"Routing model '{model}' to {backend} backend")

        return client.generate(
            model=model,
            prompt=prompt,
            system=system,
            temperature=temperature,
            stream=stream,
            endpoint=endpoint,
            model_key=model_key,
            speed_tier=speed_tier,
            max_tokens=max_tokens,
            **kwargs
        )

    def _get_default_context_window(self, model: str) -> int:
        """Get context window from model metadata."""
        backend = self._get_backend_for_model(model)
        if backend and backend in self.clients:
            return self.clients[backend]._get_default_context_window(model)
        return 4096  # Default

    def _get_default_code_model(self) -> str:
        """Get default code model from config."""
        return self.config_manager.get("llm.defaults.general", "llama3")

    def _get_default_eval_model(self) -> str:
        """Get default eval model from config."""
        return self.config_manager.get("llm.defaults.general", "llama3")

    def _get_default_triage_model(self) -> str:
        """Get default triage model from config."""
        return self.config_manager.get("llm.defaults.veryfast", "tinyllama")
