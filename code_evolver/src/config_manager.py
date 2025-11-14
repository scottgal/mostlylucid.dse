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
                "escalation": "llama3"  # Higher-level LLM for fixing issues
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

        Args:
            config_path: Path to save to (uses current path if None)
        """
        path = Path(config_path) if config_path else self.config_path

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

        Args:
            model_key: Model key (e.g., "overseer", "generator")

        Returns:
            Endpoint URL for the model
        """
        _, endpoint = self._parse_model_config(model_key, "")
        return endpoint

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
        model, _ = self._parse_model_config("escalation", "llama3")
        return model

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
