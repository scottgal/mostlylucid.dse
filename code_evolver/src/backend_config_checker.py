"""
Backend Configuration Checker

Validates LLM backend configurations and checks which backends are ready to use.
Verifies API keys, endpoints, and other required settings.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class BackendStatus(Enum):
    """Status of a backend configuration."""
    READY = "ready"  # Fully configured and ready to use
    MISSING_CONFIG = "missing_config"  # Backend not configured
    MISSING_API_KEY = "missing_api_key"  # API key not set
    INVALID_CONFIG = "invalid_config"  # Configuration is invalid
    UNAVAILABLE = "unavailable"  # Backend service not available


@dataclass
class BackendCheckResult:
    """Result of checking a backend configuration."""
    backend: str
    status: BackendStatus
    message: str
    details: Dict[str, Any]
    ready: bool


class BackendConfigChecker:
    """
    Checks LLM backend configurations for validity and readiness.

    Verifies:
    - API keys are set (from env vars or config)
    - Required configuration fields are present
    - Connection can be established (optional)
    """

    def __init__(self, config_manager):
        """
        Initialize backend config checker.

        Args:
            config_manager: ConfigManager instance
        """
        self.config = config_manager

    def check_all_backends(self, test_connection: bool = False) -> Dict[str, BackendCheckResult]:
        """
        Check all configured backends.

        Args:
            test_connection: If True, attempt to connect to each backend

        Returns:
            Dictionary mapping backend name to check result
        """
        results = {}

        # Import factory to get list of available backends
        try:
            from .llm_client_factory import LLMClientFactory
            available_backends = LLMClientFactory.get_available_backends()
        except ImportError:
            available_backends = ["ollama", "openai", "anthropic", "azure", "lmstudio"]

        for backend in available_backends:
            results[backend] = self.check_backend(backend, test_connection)

        return results

    def check_backend(self, backend: str, test_connection: bool = False) -> BackendCheckResult:
        """
        Check a specific backend configuration.

        Args:
            backend: Backend name (e.g., "openai", "anthropic")
            test_connection: If True, attempt to connect to the backend

        Returns:
            BackendCheckResult with status and details
        """
        backend_lower = backend.lower()

        # Check if backend is configured
        llm_config = self.config.config.get("llm", {})
        backends_config = llm_config.get("backends", {})
        backend_config = backends_config.get(backend_lower, {})

        if not backend_config:
            return BackendCheckResult(
                backend=backend,
                status=BackendStatus.MISSING_CONFIG,
                message=f"{backend} is not configured",
                details={"configured": False},
                ready=False
            )

        # Check based on backend type
        if backend_lower == "ollama":
            return self._check_ollama(backend_config, test_connection)
        elif backend_lower == "openai":
            return self._check_openai(backend_config, test_connection)
        elif backend_lower == "anthropic":
            return self._check_anthropic(backend_config, test_connection)
        elif backend_lower == "azure":
            return self._check_azure(backend_config, test_connection)
        elif backend_lower == "lmstudio":
            return self._check_lmstudio(backend_config, test_connection)
        else:
            return BackendCheckResult(
                backend=backend,
                status=BackendStatus.INVALID_CONFIG,
                message=f"Unknown backend: {backend}",
                details={"backend": backend},
                ready=False
            )

    def _check_ollama(self, config: Dict, test_connection: bool) -> BackendCheckResult:
        """Check Ollama backend configuration."""
        # Ollama doesn't need API keys, just endpoint
        base_url = config.get("base_url", "http://localhost:11434")

        details = {
            "base_url": base_url,
            "configured": True
        }

        # Optionally test connection
        if test_connection:
            try:
                from .ollama_client import OllamaClient
                client = OllamaClient(base_url, config_manager=self.config)
                connected = client.check_connection()
                details["connection_test"] = "success" if connected else "failed"

                if not connected:
                    return BackendCheckResult(
                        backend="ollama",
                        status=BackendStatus.UNAVAILABLE,
                        message=f"Ollama not running at {base_url}",
                        details=details,
                        ready=False
                    )
            except Exception as e:
                details["connection_error"] = str(e)
                return BackendCheckResult(
                    backend="ollama",
                    status=BackendStatus.UNAVAILABLE,
                    message=f"Cannot connect to Ollama: {e}",
                    details=details,
                    ready=False
                )

        return BackendCheckResult(
            backend="ollama",
            status=BackendStatus.READY,
            message=f"Ollama configured at {base_url}",
            details=details,
            ready=True
        )

    def _check_openai(self, config: Dict, test_connection: bool) -> BackendCheckResult:
        """Check OpenAI backend configuration."""
        # Check for API key
        api_key = config.get("api_key", "")

        # Resolve environment variable if needed
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var, "")

        details = {
            "api_key_configured": bool(api_key),
            "api_key_source": "environment" if config.get("api_key", "").startswith("${") else "config",
            "models": config.get("models", {}),
            "configured": True
        }

        if not api_key:
            env_var_name = config.get("api_key", "${OPENAI_API_KEY}")[2:-1] if "${" in config.get("api_key", "") else "OPENAI_API_KEY"
            return BackendCheckResult(
                backend="openai",
                status=BackendStatus.MISSING_API_KEY,
                message=f"OpenAI API key not set. Set {env_var_name} environment variable.",
                details=details,
                ready=False
            )

        # Mask API key in details (show only first/last 4 chars)
        if len(api_key) > 8:
            details["api_key_preview"] = f"{api_key[:4]}...{api_key[-4:]}"

        # Optionally test connection
        if test_connection:
            try:
                from .openai_client import OpenAIClient
                client = OpenAIClient(api_key=api_key, config_manager=self.config)
                models = client.list_models()
                details["connection_test"] = "success"
                details["available_models"] = len(models)
            except Exception as e:
                details["connection_error"] = str(e)
                return BackendCheckResult(
                    backend="openai",
                    status=BackendStatus.UNAVAILABLE,
                    message=f"Cannot connect to OpenAI: {e}",
                    details=details,
                    ready=False
                )

        return BackendCheckResult(
            backend="openai",
            status=BackendStatus.READY,
            message="OpenAI configured with valid API key",
            details=details,
            ready=True
        )

    def _check_anthropic(self, config: Dict, test_connection: bool) -> BackendCheckResult:
        """Check Anthropic backend configuration."""
        # Check for API key
        api_key = config.get("api_key", "")

        # Resolve environment variable if needed
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var, "")

        details = {
            "api_key_configured": bool(api_key),
            "api_key_source": "environment" if config.get("api_key", "").startswith("${") else "config",
            "models": config.get("models", {}),
            "configured": True
        }

        if not api_key:
            env_var_name = config.get("api_key", "${ANTHROPIC_API_KEY}")[2:-1] if "${" in config.get("api_key", "") else "ANTHROPIC_API_KEY"
            return BackendCheckResult(
                backend="anthropic",
                status=BackendStatus.MISSING_API_KEY,
                message=f"Anthropic API key not set. Set {env_var_name} environment variable.",
                details=details,
                ready=False
            )

        # Mask API key in details
        if len(api_key) > 8:
            details["api_key_preview"] = f"{api_key[:8]}...{api_key[-4:]}"

        # Optionally test connection
        if test_connection:
            try:
                from .anthropic_client import AnthropicClient
                client = AnthropicClient(api_key=api_key, config_manager=self.config)
                models = client.list_models()
                details["connection_test"] = "success"
                details["available_models"] = len(models)
            except Exception as e:
                details["connection_error"] = str(e)
                return BackendCheckResult(
                    backend="anthropic",
                    status=BackendStatus.UNAVAILABLE,
                    message=f"Cannot connect to Anthropic: {e}",
                    details=details,
                    ready=False
                )

        return BackendCheckResult(
            backend="anthropic",
            status=BackendStatus.READY,
            message="Anthropic configured with valid API key",
            details=details,
            ready=True
        )

    def _check_azure(self, config: Dict, test_connection: bool) -> BackendCheckResult:
        """Check Azure OpenAI backend configuration."""
        # Check for API key
        api_key = config.get("api_key", "")
        endpoint = config.get("endpoint", "")

        # Resolve environment variables
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var, "")

        if endpoint.startswith("${") and endpoint.endswith("}"):
            env_var = endpoint[2:-1]
            endpoint = os.getenv(env_var, "")

        details = {
            "api_key_configured": bool(api_key),
            "endpoint_configured": bool(endpoint),
            "deployments": config.get("deployments", {}),
            "configured": True
        }

        if not api_key:
            env_var_name = config.get("api_key", "${AZURE_OPENAI_API_KEY}")[2:-1] if "${" in config.get("api_key", "") else "AZURE_OPENAI_API_KEY"
            return BackendCheckResult(
                backend="azure",
                status=BackendStatus.MISSING_API_KEY,
                message=f"Azure API key not set. Set {env_var_name} environment variable.",
                details=details,
                ready=False
            )

        if not endpoint:
            return BackendCheckResult(
                backend="azure",
                status=BackendStatus.INVALID_CONFIG,
                message="Azure endpoint not configured",
                details=details,
                ready=False
            )

        # Mask API key in details
        if len(api_key) > 8:
            details["api_key_preview"] = f"{api_key[:4]}...{api_key[-4:]}"
        details["endpoint"] = endpoint

        return BackendCheckResult(
            backend="azure",
            status=BackendStatus.READY,
            message="Azure OpenAI configured with API key and endpoint",
            details=details,
            ready=True
        )

    def _check_lmstudio(self, config: Dict, test_connection: bool) -> BackendCheckResult:
        """Check LM Studio backend configuration."""
        # LM Studio is like Ollama - local with OpenAI-compatible API
        base_url = config.get("base_url", "http://localhost:1234")

        details = {
            "base_url": base_url,
            "configured": True
        }

        # Optionally test connection
        if test_connection:
            try:
                from .lmstudio_client import LMStudioClient
                client = LMStudioClient(base_url=base_url, config_manager=self.config)
                connected = client.check_connection()
                details["connection_test"] = "success" if connected else "failed"

                if not connected:
                    return BackendCheckResult(
                        backend="lmstudio",
                        status=BackendStatus.UNAVAILABLE,
                        message=f"LM Studio not running at {base_url}",
                        details=details,
                        ready=False
                    )
            except Exception as e:
                details["connection_error"] = str(e)
                return BackendCheckResult(
                    backend="lmstudio",
                    status=BackendStatus.UNAVAILABLE,
                    message=f"Cannot connect to LM Studio: {e}",
                    details=details,
                    ready=False
                )

        return BackendCheckResult(
            backend="lmstudio",
            status=BackendStatus.READY,
            message=f"LM Studio configured at {base_url}",
            details=details,
            ready=True
        )

    def get_ready_backends(self) -> List[str]:
        """
        Get list of backends that are ready to use.

        Returns:
            List of backend names that are fully configured
        """
        results = self.check_all_backends(test_connection=False)
        return [backend for backend, result in results.items() if result.ready]

    def get_primary_backend(self) -> Optional[str]:
        """
        Get the primary backend configured in config.

        Returns:
            Primary backend name or None
        """
        return self.config.config.get("llm", {}).get("backend", None)

    def suggest_setup_commands(self, backend: str) -> List[str]:
        """
        Suggest commands to set up a backend.

        Args:
            backend: Backend name

        Returns:
            List of command suggestions
        """
        suggestions = []

        if backend == "openai":
            suggestions.append("export OPENAI_API_KEY='sk-...'")
            suggestions.append("# Or add to config.yaml:")
            suggestions.append("llm:")
            suggestions.append("  openai:")
            suggestions.append("    api_key: '${OPENAI_API_KEY}'")

        elif backend == "anthropic":
            suggestions.append("export ANTHROPIC_API_KEY='sk-ant-...'")
            suggestions.append("# Or add to config.yaml:")
            suggestions.append("llm:")
            suggestions.append("  anthropic:")
            suggestions.append("    api_key: '${ANTHROPIC_API_KEY}'")

        elif backend == "azure":
            suggestions.append("export AZURE_OPENAI_API_KEY='...'")
            suggestions.append("export AZURE_OPENAI_ENDPOINT='https://....openai.azure.com'")
            suggestions.append("# Or add to config.yaml:")
            suggestions.append("llm:")
            suggestions.append("  azure:")
            suggestions.append("    api_key: '${AZURE_OPENAI_API_KEY}'")
            suggestions.append("    endpoint: '${AZURE_OPENAI_ENDPOINT}'")

        elif backend == "ollama":
            suggestions.append("# Start Ollama server:")
            suggestions.append("ollama serve")
            suggestions.append("# Or configure custom endpoint in config.yaml:")
            suggestions.append("llm:")
            suggestions.append("  ollama:")
            suggestions.append("    base_url: 'http://your-server:11434'")

        elif backend == "lmstudio":
            suggestions.append("# Start LM Studio and enable the API server")
            suggestions.append("# Or configure custom endpoint in config.yaml:")
            suggestions.append("llm:")
            suggestions.append("  lmstudio:")
            suggestions.append("    base_url: 'http://localhost:1234'")

        return suggestions
