#!/usr/bin/env python3
"""Configuration value resolution with environment variable support."""

import os
import re
from typing import Any, Union


def resolve_config_value(value: Any) -> Any:
    """
    Resolve configuration values with environment variable substitution.

    Supports ${VAR} and ${VAR:-default} syntax.

    Examples:
        "${API_KEY}" -> value of API_KEY env var
        "${PORT:-8080}" -> value of PORT env var, or "8080" if not set
        "regular value" -> "regular value" (unchanged)

    Args:
        value: Configuration value (can be string, dict, list, etc.)

    Returns:
        Resolved value with environment variables substituted
    """
    if isinstance(value, str):
        # Pattern: ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r'\$\{([^:}]+)(?::-)([^}]+)?\}'

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2)

            env_value = os.getenv(var_name)

            if env_value is not None:
                return env_value
            elif default is not None:
                return default
            else:
                # Variable not set and no default
                return match.group(0)  # Return original

        return re.sub(pattern, replacer, value)

    elif isinstance(value, dict):
        # Recursively resolve dict values
        return {k: resolve_config_value(v) for k, v in value.items()}

    elif isinstance(value, list):
        # Recursively resolve list items
        return [resolve_config_value(item) for item in value]

    else:
        # Other types pass through unchanged
        return value


def load_config_with_env(config: dict) -> dict:
    """
    Load configuration and resolve all environment variables.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with environment variables resolved
    """
    return resolve_config_value(config)


def parse_boolean(value: Union[str, bool]) -> bool:
    """
    Parse boolean value from string or bool.

    Args:
        value: String or boolean value

    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')

    return bool(value)


def parse_int(value: Union[str, int], default: int = 0) -> int:
    """
    Parse integer value with default.

    Args:
        value: String or integer value
        default: Default value if parsing fails

    Returns:
        Integer value
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_float(value: Union[str, float], default: float = 0.0) -> float:
    """
    Parse float value with default.

    Args:
        value: String or float value
        default: Default value if parsing fails

    Returns:
        Float value
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
