#!/usr/bin/env python3
"""Base class for executable tools with standardized error handling and I/O."""

import json
import sys
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    Base class for all executable tools.

    Provides:
    - Standardized JSON input/output
    - Consistent error handling
    - Input validation support
    - Logging integration
    """

    def __init__(self):
        """Initialize base tool."""
        self.tool_name = self.__class__.__name__

    def read_input(self) -> Dict[str, Any]:
        """
        Read and parse JSON input from stdin.

        Returns:
            Parsed input dictionary

        Raises:
            SystemExit: If input is invalid
        """
        try:
            input_text = sys.stdin.read().strip()

            if not input_text:
                self.exit_error("No input provided")

            data = json.loads(input_text)
            return data

        except json.JSONDecodeError as e:
            self.exit_error(f"Invalid JSON input: {str(e)}")

    def validate_required_fields(self, data: Dict[str, Any],
                                 required_fields: list) -> Tuple[bool, Optional[str]]:
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

    def success(self, result: Any, **kwargs) -> Dict[str, Any]:
        """
        Create standardized success response.

        Args:
            result: The result data
            **kwargs: Additional fields to include

        Returns:
            Success response dictionary
        """
        response = {
            "success": True,
            "result": result,
            "tool": self.tool_name
        }
        response.update(kwargs)
        return response

    def error(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        Create standardized error response.

        Args:
            message: Error message
            **kwargs: Additional fields to include

        Returns:
            Error response dictionary
        """
        response = {
            "success": False,
            "error": message,
            "tool": self.tool_name
        }
        response.update(kwargs)
        return response

    def output_json(self, data: Dict[str, Any]) -> None:
        """
        Output JSON response to stdout.

        Args:
            data: Dictionary to output as JSON
        """
        print(json.dumps(data, indent=2))

    def exit_success(self, result: Any, **kwargs) -> None:
        """
        Output success response and exit with code 0.

        Args:
            result: The result data
            **kwargs: Additional fields to include
        """
        self.output_json(self.success(result, **kwargs))
        sys.exit(0)

    def exit_error(self, message: str, **kwargs) -> None:
        """
        Output error response and exit with code 1.

        Args:
            message: Error message
            **kwargs: Additional fields to include
        """
        response = self.error(message, **kwargs)
        print(json.dumps(response), file=sys.stderr)
        sys.exit(1)

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool's main logic.

        This method must be implemented by subclasses.

        Args:
            input_data: Validated input parameters

        Returns:
            Result dictionary (will be wrapped in success/error response)
        """
        pass

    def run(self) -> None:
        """
        Main execution wrapper.

        Handles:
        - Input reading and parsing
        - Execution
        - Error handling
        - Output formatting
        """
        try:
            # Read and parse input
            input_data = self.read_input()

            # Execute tool logic
            result = self.execute(input_data)

            # Check if result is already a success/error response
            if isinstance(result, dict) and "success" in result:
                self.output_json(result)
                sys.exit(0 if result["success"] else 1)
            else:
                # Wrap result in success response
                self.exit_success(result)

        except KeyboardInterrupt:
            self.exit_error("Operation cancelled by user")

        except Exception as e:
            self.exit_error(f"Unexpected error: {str(e)}", exception_type=type(e).__name__)


class BaseValidatorTool(BaseTool):
    """
    Base class for validation tools.

    Extends BaseTool with validation-specific helpers.
    """

    def validation_result(self, is_valid: bool, message: str,
                         details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create standardized validation result.

        Args:
            is_valid: Whether validation passed
            message: Validation message
            details: Additional validation details

        Returns:
            Validation result dictionary
        """
        result = {
            "valid": is_valid,
            "message": message
        }

        if details:
            result["details"] = details

        if is_valid:
            return self.success(result)
        else:
            return self.error(message, validation_details=details)


class BaseCalculatorTool(BaseTool):
    """
    Base class for calculator/computation tools.

    Extends BaseTool with computation-specific helpers.
    """

    def validate_numeric(self, value: Any, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a value is numeric.

        Args:
            value: Value to validate
            name: Name of the parameter (for error messages)

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(value, (int, float)):
            return False, f"{name} must be a number, got {type(value).__name__}"

        return True, None
