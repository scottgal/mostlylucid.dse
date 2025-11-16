#!/usr/bin/env python3
"""Base class for custom tools with standardized interfaces."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseCustomTool(ABC):
    """
    Base class for custom tools implemented in Python.

    Provides:
    - Consistent initialization
    - Standardized response formats
    - Configuration management
    - Error handling patterns
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize custom tool.

        Args:
            config: Tool-specific configuration dictionary
        """
        self.config = config or {}
        self.tool_name = self.__class__.__name__

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool's main logic.

        This method must be implemented by subclasses.

        Args:
            input_data: Validated input parameters

        Returns:
            Result dictionary with 'status', 'message', and optional 'data'
        """
        pass

    def validate_action(self, action: str, valid_actions: list) -> bool:
        """
        Validate that an action is in the list of valid actions.

        Args:
            action: Action to validate
            valid_actions: List of valid action strings

        Returns:
            True if valid, False otherwise
        """
        return action in valid_actions

    def success(self, message: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        Create standardized success response.

        Args:
            message: Success message
            data: Result data
            **kwargs: Additional fields to include

        Returns:
            Success response dictionary
        """
        response = {
            "status": "success",
            "message": message,
            "tool": self.tool_name
        }

        if data is not None:
            response["data"] = data

        response.update(kwargs)
        return response

    def error(self, message: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        Create standardized error response.

        Args:
            message: Error message
            data: Additional error data
            **kwargs: Additional fields to include

        Returns:
            Error response dictionary
        """
        response = {
            "status": "error",
            "message": message,
            "tool": self.tool_name
        }

        if data is not None:
            response["data"] = data

        response.update(kwargs)
        return response

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with optional default.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def validate_required_fields(self, data: Dict[str, Any],
                                 required_fields: list) -> tuple[bool, Optional[str]]:
        """
        Validate that required fields are present.

        Args:
            data: Input data dictionary
            required_fields: List of required field names

        Returns:
            (is_valid, error_message)
        """
        missing = [field for field in required_fields if field not in data]

        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

        return True, None
