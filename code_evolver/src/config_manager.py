"""
Configuration management for mostlylucid DiSE.
Loads and validates settings from YAML config file.
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import PyInstaller utilities for resource paths
try:
    from .pyinstaller_utils import get_config_path
except ImportError:
    # Fallback if pyinstaller_utils not available
    def get_config_path():
        return Path("config.yaml")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration."""

    DEFAULT_CONFIG = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "models": {
                "overseer": "llama3",
                "generator": "codellama",
                "evaluator": "llama3",
                "triage": "tiny",
                "escalation": "qwen2.5-coder:14b"  # Higher-level code model for fixing issues
            }
        },
        "execution": {
            "default_timeout_ms": 60000,
            "max_memory_mb": 256,
            "max_retries": 3,
            "sandbox": {
                "allow_network": False,
                "allow_file_write": False,
                "temp_dir": "./temp"
            }
        },
        "testing": {
            "enabled": True,
            "generate_unit_tests": True,
            "test_frameworks": ["unittest", "pytest"],
            "min_test_coverage": 0.7,
            "auto_escalate_on_failure": True,
            "max_escalation_attempts": 3
        },
        "auto_evolution": {
            "enabled": True,
            "performance_threshold": 0.15,
            "min_runs_before_evolution": 3,
            "check_interval_minutes": 60,
            "max_versions_per_node": 10,
            "keep_best_n_versions": 3,
            "mutation_temperature": 0.7
        },
        "registry": {
            "path": "./registry",
            "backup_enabled": True,
            "backup_interval_hours": 24,
            "max_backup_count": 7
        },
        "nodes": {
            "path": "./nodes",
            "artifacts_path": "./artifacts"
        },
        "logging": {
            "level": "INFO",
            "file": "code_evolver.log",
            "max_file_size_mb": 10,
            "backup_count": 5,
            "console": {
                "enabled": True,
                "use_colors": True
            }
        },
        "chat": {
            "prompt": "DiSE> ",
            "history_file": ".code_evolver_history",
            "max_history": 1000,
            "show_thinking": False,
            "show_metrics": True,
            "auto_save_context": True
        },
        "build": {
            "app_name": "DiSE",
            "version": "0.1.0",
            "icon": None
        }
    }

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize config manager.

        Args:
            config_path: Path to YAML config file
        """
        # Use PyInstaller-aware path resolution
        if config_path == "config.yaml":
            # Default config - use PyInstaller-aware helper
            self.config_path = get_config_path()
        else:
            # Custom config path - use as-is
            self.config_path = Path(config_path)

        self.config = self._load_config()
        self._validate_code_models()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Validate YAML structure
            self._lint_config(config)

            # Merge with defaults
            merged = self._merge_configs(self.DEFAULT_CONFIG, config)
            logger.info(f"✓ Loaded configuration from {self.config_path}")
            return merged

        except yaml.YAMLError as e:
            logger.error(f"YAML syntax error in config file: {e}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()

    def _lint_config(self, config: Dict[str, Any]) -> None:
        """
        Lint configuration for common issues.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If critical configuration issues are found
        """
        warnings = []
        errors = []

        # Check LLM configuration
        if "llm" in config:
            llm_config = config["llm"]

            # Check model definitions
            if "models" in llm_config:
                models = llm_config["models"]
                for model_id, model_spec in models.items():
                    if isinstance(model_spec, dict):
                        model_name = model_spec.get("name", "")
                        backend = model_spec.get("backend", "")

                        # Check for common Ollama model name issues
                        if backend == "ollama" and model_name:
                            # Check if model name looks like it should have a colon but doesn't
                            # Common patterns: gemma3_1b should be gemma3:1b, phi3_mini should be phi3:mini
                            if "_" in model_name and ":" not in model_name:
                                # Check for common model families
                                model_families = ["gemma", "phi", "llama", "codellama", "qwen", "mistral", "deepseek"]
                                if any(family in model_name.lower() for family in model_families):
                                    warnings.append(
                                        f"Model '{model_id}' has name '{model_name}' which looks incorrect. "
                                        f"Ollama model names typically use colons (e.g., 'gemma3:1b' not 'gemma3_1b')"
                                    )

            # Check backend configuration
            if "backends" in llm_config:
                backends = llm_config["backends"]

                # Check Ollama backend
                if "ollama" in backends:
                    ollama_config = backends["ollama"]
                    if isinstance(ollama_config, dict):
                        base_url = ollama_config.get("base_url", "")
                        if base_url and not base_url.startswith("http"):
                            warnings.append(
                                f"Ollama base_url '{base_url}' should start with 'http://' or 'https://'"
                            )

        # Log warnings
        if warnings:
            logger.warning("Configuration validation warnings:")
            for warning in warnings:
                logger.warning(f"  ⚠ {warning}")

        # Log errors and raise if critical
        if errors:
            logger.error("Configuration validation errors:")
            for error in errors:
                logger.error(f"  ✗ {error}")
            raise ValueError(f"Configuration has {len(errors)} critical error(s)")

    def _merge_configs(self, default: Dict, custom: Dict) -> Dict:
        """
        Recursively merge custom config with defaults.

        Args:
            default: Default configuration
            custom: Custom configuration

        Returns:
            Merged configuration
        """
        merged = default.copy()

        for key, value in custom.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    def save_config(self, config_path: Optional[str] = None):
        """
        Save current configuration to file.

        IMPORTANT: This should ONLY be used to create new config files.
        The original config.yaml should remain immutable and never be modified by code.

        Args:
            config_path: Path to save to (must be explicitly provided, not the loaded config)
        """
        if config_path is None:
            logger.warning("Refusing to save config: config_path must be explicitly provided to prevent overwriting config.yaml")
            return

        path = Path(config_path)

        # Safety check: never overwrite the original config.yaml
        if path.resolve() == self.config_path.resolve():
            logger.warning(f"Refusing to overwrite original config file: {self.config_path}")
            logger.info("Config changes are kept in memory only. Edit config.yaml manually if needed.")
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            logger.info(f"✓ Saved configuration to {path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Path to config value (e.g., "ollama.models.overseer")
            default: Default value if not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.

        Args:
            key_path: Path to config value (e.g., "ollama.models.overseer")
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid
        """
        required_models = ["overseer", "generator", "evaluator"]
        models = self.get("ollama.models", {})

        missing = [m for m in required_models if m not in models]

        if missing:
            logger.error(f"Missing required model configurations: {', '.join(missing)}")
            return False

        logger.info("✓ Configuration is valid")
        return True

    # Convenience accessors
    @property
    def ollama_url(self) -> str:
        """Get Ollama base URL."""
        return self.get("ollama.base_url", "http://localhost:11434")

    def _parse_model_config(self, model_key: str, default_model: str) -> tuple[str, str]:
        """
        Parse model configuration which can be either a string or a dict.

        Args:
            model_key: Key in ollama.models (e.g., "overseer")
            default_model: Default model name if not found

        Returns:
            Tuple of (model_name, endpoint_url)
        """
        model_config = self.get(f"ollama.models.{model_key}")

        # Handle dict format: {model: "name", endpoint: "url"}
        if isinstance(model_config, dict):
            model_name = model_config.get("model", default_model)
            endpoint = model_config.get("endpoint")

            # Use base_url if no endpoint specified
            if not endpoint:
                endpoint = self.ollama_url

            return model_name, endpoint

        # Handle string format: just the model name
        elif isinstance(model_config, str):
            return model_config, self.ollama_url

        # Fallback to defaults
        else:
            return default_model, self.ollama_url

    def get_model_endpoint(self, model_key: str) -> str:
        """
        Get the endpoint URL for a specific model.
        If multiple endpoints configured, returns the first one.

        Args:
            model_key: Model key (e.g., "overseer", "generator")

        Returns:
            Endpoint URL for the model
        """
        endpoints = self.get_model_endpoints(model_key)
        return endpoints[0] if endpoints else self.ollama_url

    def get_model_endpoints(self, model_key: str) -> list:
        """
        Get all endpoint URLs for a specific model (supports round-robin).

        Args:
            model_key: Model key (e.g., "overseer", "generator")

        Returns:
            List of endpoint URLs for the model
        """
        model_config = self.get(f"ollama.models.{model_key}")

        # Handle dict format with potential endpoints list
        if isinstance(model_config, dict):
            # Check for 'endpoints' (plural) first - this is the new format
            endpoints = model_config.get("endpoints")
            if isinstance(endpoints, list):
                return [ep if ep else self.ollama_url for ep in endpoints]

            # Fall back to single 'endpoint' (singular)
            endpoint = model_config.get("endpoint")
            if endpoint:
                return [endpoint]
            else:
                return [self.ollama_url]

        # String format - single endpoint (base_url)
        return [self.ollama_url]

    @property
    def overseer_model(self) -> str:
        """Get overseer model name (uses general level from unified config)."""
        # Use unified config system: get general model for default role
        model_key = self.get_model(role="default", level="general")
        if model_key:
            metadata = self.get_model_metadata(model_key)
            return metadata.get("name", "llama3")

        # Fallback to legacy config
        model, _ = self._parse_model_config("overseer", "llama3")
        return model

    @property
    def overseer_model_key(self) -> Optional[str]:
        """Get overseer model key for routing."""
        return self.get_model(role="default", level="general")

    @property
    def generator_model(self) -> str:
        """Get code generator model name (uses general level for code role)."""
        # Use unified config system: get general model for code role
        model_key = self.get_model(role="code", level="general")
        if model_key:
            metadata = self.get_model_metadata(model_key)
            return metadata.get("name", "codellama")

        # Fallback to legacy config
        model, _ = self._parse_model_config("generator", "codellama")
        return model

    @property
    def generator_model_key(self) -> Optional[str]:
        """Get generator model key for routing."""
        return self.get_model(role="code", level="general")

    @property
    def evaluator_model(self) -> str:
        """Get evaluator model name (uses general level from unified config)."""
        # Use unified config system: get general model for default role
        model_key = self.get_model(role="default", level="general")
        if model_key:
            metadata = self.get_model_metadata(model_key)
            return metadata.get("name", "llama3")

        # Fallback to legacy config
        model, _ = self._parse_model_config("evaluator", "llama3")
        return model

    @property
    def evaluator_model_key(self) -> Optional[str]:
        """Get evaluator model key for routing."""
        return self.get_model(role="default", level="general")

    @property
    def triage_model(self) -> str:
        """Get triage model name (uses veryfast level from unified config)."""
        # Use unified config system: get veryfast model for default role
        model_key = self.get_model(role="default", level="veryfast")
        if model_key:
            # Resolve model key to actual model name
            metadata = self.get_model_metadata(model_key)
            return metadata.get("name", "gemma3:1b")

        # Fallback to legacy config
        model, _ = self._parse_model_config("triage", "gemma3:1b")
        return model

    @property
    def triage_model_key(self) -> Optional[str]:
        """Get triage model key for routing."""
        return self.get_model(role="default", level="veryfast")

    @property
    def escalation_model(self) -> str:
        """Get escalation model name for fixing issues (uses escalation level)."""
        # Use unified config system: get escalation model for default role
        model_key = self.get_model(role="default", level="escalation")
        if model_key:
            metadata = self.get_model_metadata(model_key)
            return metadata.get("name", "qwen2.5-coder:14b")

        # Fallback to legacy config
        model, _ = self._parse_model_config("escalation", "qwen2.5-coder:14b")
        return model

    @property
    def escalation_model_key(self) -> Optional[str]:
        """Get escalation model key for routing."""
        return self.get_model(role="default", level="escalation")

    @property
    def embedding_model(self) -> str:
        """Get embedding model name (returns the actual model name, not the key)."""
        # Check new unified structure first (llm.embedding.default gives us the key)
        model_key = self.get("llm.embedding.default")
        if model_key:
            # Resolve key to actual model name via registry
            metadata = self.get_model_metadata(model_key)
            return metadata.get("name", "nomic-embed-text")

        # Check legacy embedding.model
        model = self.get("embedding.model")
        if model:
            return model

        # Fallback to old structure
        model, _ = self._parse_model_config("embedding", "nomic-embed-text")
        return model if model else "nomic-embed-text"

    @property
    def embedding_vector_size(self) -> int:
        """Get embedding vector size."""
        # Check new unified structure first (llm.embedding.default -> model metadata)
        model_key = self.get("llm.embedding.default")
        if model_key:
            metadata = self.get_model_metadata(model_key)
            vector_size = metadata.get("vector_size")
            if vector_size:
                return vector_size

        # Check legacy structures
        return self.get("embedding.vector_size", self.get("ollama.embedding.vector_size", 768))

    def _validate_code_models(self):
        """
        Validate that code-generation roles use code-specialized models.

        Warns if general chat models (llama3, mistral, etc.) are configured
        for code generation or escalation, which would produce poor quality code.
        """
        # List of known general chat models (not code-specialized)
        general_chat_models = [
            'llama3', 'llama2', 'mistral', 'mixtral', 'phi3', 'gemma',
            'neural-chat', 'vicuna', 'orca', 'tinyllama'
        ]

        # List of known code-specialized models
        code_models = [
            'codellama', 'qwen', 'coder', 'deepseek-coder', 'starcoder',
            'wizardcoder', 'phind-codellama', 'sqlcoder'
        ]

        def is_code_model(model_name: str) -> bool:
            """Check if a model name appears to be code-specialized."""
            model_lower = model_name.lower()
            # Check if it contains any code model indicators
            if any(code_marker in model_lower for code_marker in code_models):
                return True
            # Check if it's a known general model
            if any(model_lower.startswith(general) for general in general_chat_models):
                return False
            # Unknown model - assume it might be okay but warn
            return None  # Uncertain

        # Check generator model
        generator_model = self.generator_model
        is_code = is_code_model(generator_model)
        if is_code is False:
            logger.warning(
                f"⚠️  WARNING: Generator model '{generator_model}' appears to be a general chat model.\n"
                f"   Code generation requires code-specialized models like codellama, qwen2.5-coder, etc.\n"
                f"   Please update config.yaml -> ollama.models.generator to use a code model."
            )
        elif is_code is None:
            logger.info(f"ℹ️  Using generator model '{generator_model}' (unable to verify if code-specialized)")

        # Check escalation model
        escalation_model = self.escalation_model
        is_code = is_code_model(escalation_model)
        if is_code is False:
            logger.warning(
                f"⚠️  WARNING: Escalation model '{escalation_model}' appears to be a general chat model.\n"
                f"   Code debugging requires code-specialized models like qwen2.5-coder:14b, deepseek-coder:33b, etc.\n"
                f"   Please update config.yaml -> ollama.models.escalation to use a powerful code model."
            )
        elif is_code is None:
            logger.info(f"ℹ️  Using escalation model '{escalation_model}' (unable to verify if code-specialized)")

    def get_context_window(self, model_name: str) -> int:
        """
        Get context window size for a specific model.

        Args:
            model_name: Name of the model

        Returns:
            Context window size in tokens
        """
        # Try NEW unified structure first (llm.models.{key}.context_window)
        # This handles model metadata in the registry
        models = self.get("llm.models", {})
        for model_key, model_config in models.items():
            if isinstance(model_config, dict):
                # Check if this model's name matches
                if model_config.get("name") == model_name:
                    return model_config.get("context_window", 4096)

        # Fall back to OLD structure (ollama.context_windows)
        context_windows = self.get("ollama.context_windows", {})

        # Try direct lookup in dictionary (handles colons in model names like "qwen2.5-coder:14b")
        if model_name in context_windows:
            return context_windows[model_name]

        # Fall back to default
        return context_windows.get("default", 4096)

    def get_model(self, role: str = "default", level: str = "general") -> str:
        """
        Get model for a specific role and level using cascading resolution.

        Resolution order (HIERARCHICAL with partial overrides):
        1. llm.roles.{role}.{level} (role-specific override in THIS config)
        2. llm.roles.{role}.{level} (role-specific override in BASE config if loaded)
        3. llm.defaults.{level} (global default in THIS config)
        4. llm.defaults.{level} (global default in BASE config if loaded)
        5. Return None if not found

        This allows partial overrides:
        - config.anthropic.yaml can override just "god" level
        - All other levels inherit from base config.yaml
        - Role-specific overrides also inherit from base

        Args:
            role: Role name (default, code, content, analysis, etc.)
            level: Level name (god, escalation, general, fast, veryfast)

        Returns:
            Model key (e.g., "claude_sonnet", "codellama_7b")
        """
        # Check for NEW unified structure first
        if self.get("llm.models") is not None:
            # Try role-specific override first
            role_model = self.get(f"llm.roles.{role}.{level}")
            if role_model:
                return role_model

            # Fall back to defaults
            default_model = self.get(f"llm.defaults.{level}")
            if default_model:
                return default_model

            # Not found - this is OK for partial overrides
            # The base config should have it
            logger.debug(f"No model configured for role='{role}' level='{level}' (may be in base config)")
            return None

        # Fall back to OLD structure for backward compatibility
        return self._get_legacy_model(role, level)

    def _get_legacy_model(self, role: str, level: str) -> Optional[str]:
        """
        Get model using legacy config structure for backward compatibility.

        Args:
            role: Role name
            level: Level name

        Returns:
            Model name or None
        """
        # Map old role names to new structure
        legacy_mapping = {
            ("default", "veryfast"): "triage",
            ("default", "fast"): "triage",
            ("default", "general"): "overseer",
            ("default", "escalation"): "escalation",
            ("default", "god"): "escalation",
            ("code", "veryfast"): "generator",
            ("code", "fast"): "generator",
            ("code", "general"): "generator",
            ("code", "escalation"): "escalation",
            ("code", "god"): "escalation",
        }

        key = (role, level)
        if key in legacy_mapping:
            old_key = legacy_mapping[key]
            return self.get(f"ollama.models.{old_key}")

        return None

    def get_model_metadata(self, model_key: str) -> Dict[str, Any]:
        """
        Get metadata for a model from the registry.

        Args:
            model_key: Model key (e.g., "claude_sonnet", "codellama_7b")

        Returns:
            Dictionary with model metadata (name, backend, context_window, cost, speed, quality, etc.)
        """
        # Check NEW unified structure
        model_config = self.get(f"llm.models.{model_key}")
        if model_config and isinstance(model_config, dict):
            return model_config

        # Model not found in registry
        logger.warning(f"Model '{model_key}' not found in llm.models registry")
        return {
            "name": model_key,  # Assume key is the model name
            "backend": "ollama",
            "context_window": 4096,
            "cost": "unknown",
            "speed": "unknown",
            "quality": "unknown"
        }

    def resolve_model(self, role: str = "default", level: str = "general") -> Dict[str, Any]:
        """
        Resolve a role+level to complete model metadata.

        Args:
            role: Role name (default, code, content, etc.)
            level: Level name (god, escalation, general, fast, veryfast)

        Returns:
            Complete model metadata dictionary
        """
        model_key = self.get_model(role, level)
        if not model_key:
            raise ValueError(f"No model configured for role='{role}' level='{level}'")

        metadata = self.get_model_metadata(model_key)
        metadata["model_key"] = model_key  # Include the key for reference
        return metadata

    @property
    def rag_memory_path(self) -> str:
        """Get RAG memory path."""
        return self.get("rag_memory.path", "./rag_memory")

    @property
    def use_qdrant(self) -> bool:
        """Check if Qdrant should be used for RAG memory."""
        return self.get("rag_memory.use_qdrant", False)

    @property
    def qdrant_url(self) -> str:
        """Get Qdrant server URL."""
        return self.get("rag_memory.qdrant_url", "http://localhost:6333")

    @property
    def max_embedding_content_length(self) -> int:
        """Get max content length for embeddings."""
        return self.get("rag_memory.max_embedding_content_length", 1000)

    # Loki properties
    @property
    def loki_enabled(self) -> bool:
        """Check if Loki should be used for log aggregation."""
        return self.get("loki.enabled", True)

    @property
    def loki_data_path(self) -> str:
        """Get Loki data storage path."""
        return self.get("loki.data_path", "./data/loki")

    @property
    def loki_url(self) -> str:
        """Get Loki server URL."""
        return self.get("loki.url", "http://localhost:3100")

    @property
    def loki_push_url(self) -> str:
        """Get Loki push endpoint URL."""
        return self.get("loki.push_url", f"{self.loki_url}/loki/api/v1/push")

    @property
    def loki_docker_image(self) -> str:
        """Get Loki Docker image."""
        return self.get("loki.docker.image", "grafana/loki:2.9.3")

    @property
    def loki_container_name(self) -> str:
        """Get Loki container name."""
        return self.get("loki.docker.container_name", "code_evolver_loki_standalone")

    @property
    def loki_port(self) -> int:
        """Get Loki HTTP port."""
        return self.get("loki.docker.port", 3100)

    @property
    def loki_config_file(self) -> str:
        """Get Loki config file path."""
        return self.get("loki.docker.config_file", "./loki-config.yaml")

    @property
    def loki_batch_size(self) -> int:
        """Get Loki batch size for log pushing."""
        return self.get("loki.batch.size", 10)

    @property
    def loki_batch_timeout(self) -> int:
        """Get Loki batch timeout in seconds."""
        return self.get("loki.batch.timeout_seconds", 5)

    @property
    def loki_default_labels(self) -> dict:
        """Get default labels for Loki logs."""
        return self.get("loki.default_labels", {
            "application": "code_evolver",
            "environment": "development"
        })

    # Filesystem properties
    @property
    def filesystem_enabled(self) -> bool:
        """Check if tool-scoped filesystem is enabled."""
        return self.get("filesystem.enabled", True)

    @property
    def filesystem_base_path(self) -> str:
        """Get filesystem base path."""
        return self.get("filesystem.base_path", "./data/filesystem")

    @property
    def filesystem_max_file_size_mb(self) -> int:
        """Get maximum file size in MB."""
        return self.get("filesystem.max_file_size_mb", 100)

    @property
    def filesystem_max_total_size_mb(self) -> int:
        """Get maximum total storage per tool scope in MB."""
        return self.get("filesystem.max_total_size_mb", 1000)

    @property
    def filesystem_allowed_extensions(self) -> list:
        """Get list of allowed file extensions."""
        return self.get("filesystem.allowed_extensions", [
            ".txt", ".json", ".yaml", ".yml", ".md",
            ".csv", ".log", ".xml"
        ])

    @property
    def filesystem_allow_absolute_paths(self) -> bool:
        """Check if absolute paths are allowed."""
        return self.get("filesystem.allow_absolute_paths", False)

    @property
    def filesystem_allow_parent_traversal(self) -> bool:
        """Check if parent directory traversal is allowed."""
        return self.get("filesystem.allow_parent_traversal", False)

    @property
    def registry_path(self) -> str:
        """Get registry path."""
        return self.get("registry.path", "./registry")

    @property
    def nodes_path(self) -> str:
        """Get nodes path."""
        return self.get("nodes.path", "./nodes")

    @property
    def auto_evolution_enabled(self) -> bool:
        """Check if auto-evolution is enabled."""
        return self.get("auto_evolution.enabled", True)

    @property
    def testing_enabled(self) -> bool:
        """Check if unit testing is enabled."""
        return self.get("testing.enabled", True)

    @property
    def auto_escalate(self) -> bool:
        """Check if auto-escalation on test failure is enabled."""
        return self.get("testing.auto_escalate_on_failure", True)

    def get_primary_llm_backend(self) -> str:
        """
        Determine which backend to use for LLM (not embeddings).

        Resolution order:
        1. Check llm.defaults and see which backend those models use
        2. Check which backends are enabled
        3. Default to ollama

        Returns:
            Backend name (e.g., "anthropic", "ollama", "openai")
        """
        # Get defaults to see which models are being used
        defaults = self.get("llm.defaults", {})
        if defaults:
            # Check the "general" level model to determine backend
            general_model_key = defaults.get("general")
            if general_model_key:
                metadata = self.get_model_metadata(general_model_key)
                backend = metadata.get("backend", "ollama")
                return backend

        # Fall back to checking which backends are enabled
        backends = self.get("llm.backends", {})
        for backend_name, backend_config in backends.items():
            if isinstance(backend_config, dict) and backend_config.get("enabled"):
                # Prefer anthropic over others if enabled
                if backend_name == "anthropic":
                    return "anthropic"

        # Default to ollama
        return "ollama"

    def create_default_config(self, path: str = "config.yaml"):
        """
        Create a default configuration file.

        Args:
            path: Path to create config file
        """
        config_path = Path(path)
        if config_path.exists():
            logger.warning(f"Config file already exists: {path}")
            return

        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config(str(config_path))
        logger.info(f"✓ Created default config at {path}")
