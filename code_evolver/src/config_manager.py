"""
Configuration management for Code Evolver.
Loads and validates settings from YAML config file.
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

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
            "default_timeout_ms": 5000,
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
            "prompt": "CodeEvolver> ",
            "history_file": ".code_evolver_history",
            "max_history": 1000,
            "show_thinking": False,
            "show_metrics": True,
            "auto_save_context": True
        },
        "build": {
            "app_name": "CodeEvolver",
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

            # Merge with defaults
            merged = self._merge_configs(self.DEFAULT_CONFIG, config)
            logger.info(f"✓ Loaded configuration from {self.config_path}")
            return merged

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()

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
        """Get overseer model name."""
        model, _ = self._parse_model_config("overseer", "llama3")
        return model

    @property
    def generator_model(self) -> str:
        """Get code generator model name."""
        model, _ = self._parse_model_config("generator", "codellama")
        return model

    @property
    def evaluator_model(self) -> str:
        """Get evaluator model name."""
        model, _ = self._parse_model_config("evaluator", "llama3")
        return model

    @property
    def triage_model(self) -> str:
        """Get triage model name."""
        model, _ = self._parse_model_config("triage", "tiny")
        return model

    @property
    def escalation_model(self) -> str:
        """Get escalation model name for fixing issues."""
        model, _ = self._parse_model_config("escalation", "qwen2.5-coder:14b")
        return model

    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        model, _ = self._parse_model_config("embedding", "nomic-embed-text")
        return model

    @property
    def embedding_vector_size(self) -> int:
        """Get embedding vector size."""
        return self.get("ollama.embedding.vector_size", 768)

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
        # Get the context_windows dictionary directly to handle model names with special chars (e.g., colons)
        context_windows = self.get("ollama.context_windows", {})

        # Try direct lookup in dictionary (handles colons in model names like "qwen2.5-coder:14b")
        if model_name in context_windows:
            return context_windows[model_name]

        # Fall back to default
        return context_windows.get("default", 4096)

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
