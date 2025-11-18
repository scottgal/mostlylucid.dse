"""
Interactive Input Collector

Collects workflow inputs interactively from the user using LLM-generated prompts.
Uses a fast 1B LLM to generate natural language questions from parameter specs.

Features:
- Reads workflow input specifications
- Uses gemma3:1b to generate friendly prompts from parameter names/descriptions
- Validates input types
- Applies default values
- Rich terminal UI with colors and formatting

Usage:
    collector = InteractiveInputCollector(ollama_client)
    inputs = await collector.collect_inputs(workflow_spec)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich import box

logger = logging.getLogger(__name__)


class InteractiveInputCollector:
    """
    Collects workflow inputs interactively using LLM-generated prompts.

    Uses a small, fast LLM (gemma3:1b) to convert parameter specs
    into natural, user-friendly questions.
    """

    def __init__(self, ollama_client):
        """
        Initialize the input collector.

        Args:
            ollama_client: OllamaClient for LLM prompt generation
        """
        self.client = ollama_client
        self.console = Console()
        self.prompt_model = "gemma3:1b"  # Fast 1B model for prompt generation

    def collect_inputs(
        self,
        workflow_spec: Dict[str, Any],
        provided_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect all required inputs for a workflow interactively.

        Args:
            workflow_spec: The workflow specification containing input definitions
            provided_inputs: Optional pre-provided inputs (won't prompt for these)

        Returns:
            Dict mapping input names to values
        """
        inputs = provided_inputs.copy() if provided_inputs else {}
        input_specs = workflow_spec.get("inputs", {})

        if not input_specs:
            return inputs

        # Display workflow info
        workflow_id = workflow_spec.get("workflow_id", "workflow")
        description = workflow_spec.get("description", "")

        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]{workflow_id}[/bold cyan]\n{description}",
            title="[bold]Workflow Inputs Required[/bold]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        self.console.print()

        # Collect each missing required input
        for param_name, param_spec in input_specs.items():
            # Skip if already provided
            if param_name in inputs:
                continue

            # Check if required
            required = param_spec.get("required", False)
            default_value = param_spec.get("default")

            # Skip optional params without defaults (user can leave empty)
            if not required and default_value is None:
                prompt_text = self._generate_prompt(param_name, param_spec)
                self.console.print(f"[dim]{prompt_text} (optional, press Enter to skip)[/dim]")
                value = Prompt.ask("", default="", console=self.console)
                if value:
                    inputs[param_name] = self._convert_type(value, param_spec)
                continue

            # Generate friendly prompt using LLM
            prompt_text = self._generate_prompt(param_name, param_spec)

            # Get user input
            value = self._prompt_for_value(
                param_name,
                param_spec,
                prompt_text,
                default_value
            )

            inputs[param_name] = value

        # Apply defaults for any missing optional parameters
        for param_name, param_spec in input_specs.items():
            if param_name not in inputs and "default" in param_spec:
                inputs[param_name] = param_spec["default"]

        return inputs

    def _generate_prompt(
        self,
        param_name: str,
        param_spec: Dict[str, Any]
    ) -> str:
        """
        Generate a natural language prompt using the 1B LLM.

        Args:
            param_name: The parameter name (e.g., "url", "max_length")
            param_spec: The parameter specification containing type, description, etc.

        Returns:
            A friendly, natural language prompt
        """
        description = param_spec.get("description", "")
        param_type = param_spec.get("type", "string")
        required = param_spec.get("required", False)

        # Build system prompt for the LLM
        system_prompt = """You are a helpful assistant that creates clear, friendly prompts for collecting user input.

Given a parameter name and description, create a natural, conversational question to ask the user.

Rules:
- Be concise and friendly
- Use natural language
- Don't include technical jargon unless necessary
- Make it sound like a conversation, not a form
- Don't include the parameter name unless it adds clarity
- Keep it to one sentence if possible

Examples:
Parameter: url, Description: "URL to fetch and analyze"
Output: Please enter the URL you want me to analyze

Parameter: max_length, Description: "Maximum summary length in words"
Output: How many words should the summary be? (maximum)

Parameter: topic, Description: "Topic for blog post generation"
Output: What topic would you like me to write about?

Parameter: api_key, Description: "API key for authentication"
Output: Please provide your API key

Parameter: output_format, Description: "Output format (json, csv, xml)"
Output: What output format would you like? (json, csv, or xml)
"""

        user_prompt = f"""Parameter: {param_name}
Type: {param_type}
Description: {description}
Required: {required}

Generate a friendly prompt:"""

        try:
            # Call LLM to generate prompt
            generated_prompt = self.client.generate(
                model=self.prompt_model,
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.3  # Low temperature for consistency
            )

            generated_prompt = generated_prompt.strip()

            # Fallback if LLM doesn't produce good output
            if not generated_prompt or len(generated_prompt) < 10:
                return self._fallback_prompt(param_name, description, param_type)

            return generated_prompt

        except Exception as e:
            logger.warning(f"Failed to generate LLM prompt: {e}")
            return self._fallback_prompt(param_name, description, param_type)

    def _fallback_prompt(
        self,
        param_name: str,
        description: str,
        param_type: str
    ) -> str:
        """
        Fallback prompt generation if LLM fails.

        Args:
            param_name: Parameter name
            description: Parameter description
            param_type: Parameter type

        Returns:
            A basic prompt string
        """
        if description:
            return f"Please enter {description}"
        else:
            # Convert snake_case to Title Case
            friendly_name = param_name.replace("_", " ").title()
            return f"Please enter {friendly_name}"

    def _prompt_for_value(
        self,
        param_name: str,
        param_spec: Dict[str, Any],
        prompt_text: str,
        default_value: Any = None
    ) -> Any:
        """
        Prompt the user for a value with type validation.

        Args:
            param_name: Parameter name
            param_spec: Parameter specification
            prompt_text: The prompt text to display
            default_value: Optional default value

        Returns:
            The validated input value
        """
        param_type = param_spec.get("type", "string")

        # Special handling for boolean
        if param_type == "boolean":
            default_bool = default_value if default_value is not None else False
            return Confirm.ask(
                prompt_text,
                default=default_bool,
                console=self.console
            )

        # Build prompt with default
        if default_value is not None:
            display_default = str(default_value)
        else:
            display_default = None

        while True:
            try:
                # Get raw input
                raw_value = Prompt.ask(
                    f"[bold cyan]{prompt_text}[/bold cyan]",
                    default=display_default,
                    console=self.console
                )

                # Convert and validate type
                value = self._convert_type(raw_value, param_spec)

                # Additional validation
                if not self._validate_value(value, param_spec):
                    self.console.print("[red]Invalid value. Please try again.[/red]")
                    continue

                return value

            except (ValueError, TypeError) as e:
                self.console.print(f"[red]Invalid input: {e}. Please try again.[/red]")

    def _convert_type(self, value: str, param_spec: Dict[str, Any]) -> Any:
        """
        Convert string input to the appropriate type.

        Args:
            value: The raw string value
            param_spec: Parameter specification

        Returns:
            The converted value

        Raises:
            ValueError: If conversion fails
        """
        param_type = param_spec.get("type", "string")

        if param_type == "string":
            return value

        elif param_type == "number":
            # Try float first, then int
            try:
                if "." in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                raise ValueError(f"'{value}' is not a valid number")

        elif param_type == "integer":
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"'{value}' is not a valid integer")

        elif param_type == "boolean":
            lower_val = value.lower()
            if lower_val in ("true", "yes", "y", "1"):
                return True
            elif lower_val in ("false", "no", "n", "0"):
                return False
            else:
                raise ValueError(f"'{value}' is not a valid boolean (use true/false)")

        elif param_type == "array":
            # Try to parse as JSON array
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, list):
                    raise ValueError("Expected an array/list")
                return parsed
            except json.JSONDecodeError:
                # Fallback: split by comma
                return [item.strip() for item in value.split(",")]

        elif param_type == "object":
            # Parse as JSON object
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise ValueError("Expected a JSON object")
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON object: {e}")

        else:
            # Unknown type, treat as string
            return value

    def _validate_value(self, value: Any, param_spec: Dict[str, Any]) -> bool:
        """
        Validate a value against parameter constraints.

        Args:
            value: The value to validate
            param_spec: Parameter specification with constraints

        Returns:
            True if valid, False otherwise
        """
        # Check minimum/maximum for numbers
        if isinstance(value, (int, float)):
            min_val = param_spec.get("minimum")
            max_val = param_spec.get("maximum")

            if min_val is not None and value < min_val:
                self.console.print(f"[yellow]Value must be at least {min_val}[/yellow]")
                return False

            if max_val is not None and value > max_val:
                self.console.print(f"[yellow]Value must be at most {max_val}[/yellow]")
                return False

        # Check string length
        if isinstance(value, str):
            min_len = param_spec.get("min_length")
            max_len = param_spec.get("max_length")

            if min_len is not None and len(value) < min_len:
                self.console.print(f"[yellow]Must be at least {min_len} characters[/yellow]")
                return False

            if max_len is not None and len(value) > max_len:
                self.console.print(f"[yellow]Must be at most {max_len} characters[/yellow]")
                return False

            # Check enum/allowed values
            enum_values = param_spec.get("enum", [])
            if enum_values and value not in enum_values:
                self.console.print(f"[yellow]Must be one of: {', '.join(enum_values)}[/yellow]")
                return False

        # Check pattern (regex)
        pattern = param_spec.get("pattern")
        if pattern and isinstance(value, str):
            import re
            if not re.match(pattern, value):
                self.console.print(f"[yellow]Must match pattern: {pattern}[/yellow]")
                return False

        return True

    def collect_inputs_sync(
        self,
        workflow_spec: Dict[str, Any],
        provided_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of collect_inputs for compatibility.
        (This is now just an alias since collect_inputs is synchronous)

        Args:
            workflow_spec: The workflow specification
            provided_inputs: Optional pre-provided inputs

        Returns:
            Dict mapping input names to values
        """
        return self.collect_inputs(workflow_spec, provided_inputs)
