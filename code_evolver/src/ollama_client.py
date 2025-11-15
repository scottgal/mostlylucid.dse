"""
Ollama client for interacting with local Ollama models.
Supports code generation, evaluation, and triage tasks.
Supports multi-endpoint configuration for distributed inference.
"""
import requests
import json
import logging
import os
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .config_manager import ConfigManager

# Enable DEBUG logging by default (shows full LLM conversations)
# Set CODE_EVOLVER_DEBUG=0 to disable debug output
log_level = logging.INFO if os.getenv("CODE_EVOLVER_DEBUG") == "0" else logging.DEBUG
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for communicating with Ollama servers (single or multiple endpoints)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        config_manager: Optional['ConfigManager'] = None
    ):
        """
        Initialize Ollama client.

        Args:
            base_url: Default base URL for Ollama API
            config_manager: Optional ConfigManager for per-model endpoint routing
        """
        self.base_url = base_url
        self.config_manager = config_manager

        # Round-robin endpoint tracking per model_key
        self._endpoint_counters: Dict[str, int] = {}

    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if Ollama server is running and accessible.

        Args:
            endpoint: Optional specific endpoint to check (uses base_url if None)

        Returns:
            True if server is accessible, False otherwise
        """
        url = endpoint or self.base_url
        try:
            response = requests.get(f"{url}/api/tags", timeout=5)
            response.raise_for_status()
            logger.info(f"✓ Connected to Ollama server at {url}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to Ollama server at {url}: {e}")
            return False

    def list_models(self, endpoint: Optional[str] = None) -> list:
        """
        List available models in Ollama.

        Args:
            endpoint: Optional specific endpoint (uses base_url if None)

        Returns:
            List of model names
        """
        url = endpoint or self.base_url
        try:
            response = requests.get(f"{url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return models
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing models from {url}: {e}")
            return []

    def truncate_prompt(self, prompt: str, model: str, max_ratio: float = 0.8) -> str:
        """
        Truncate prompt if it exceeds the model's context window.

        Args:
            prompt: The prompt text
            model: Model name
            max_ratio: Use max_ratio of context window (default 0.8 to leave room for response)

        Returns:
            Truncated prompt if necessary
        """
        if not self.config_manager:
            return prompt

        # Get context window size for model
        context_window = self.config_manager.get_context_window(model)

        # Rough approximation: 4 chars per token (conservative estimate)
        max_chars = int(context_window * max_ratio * 4)

        if len(prompt) > max_chars:
            logger.warning(
                f"Prompt length ({len(prompt)} chars) exceeds max for {model} "
                f"({max_chars} chars, ~{context_window * max_ratio:.0f} tokens). Truncating."
            )
            # Truncate and add note
            truncated = prompt[:max_chars - 100]
            truncated += "\n\n[... prompt truncated due to length ...]"
            return truncated

        return prompt

    def _get_next_endpoint(self, model_key: str, endpoints: list) -> str:
        """
        Get next endpoint using round-robin for load balancing.

        Args:
            model_key: Model key for tracking (e.g., "generator", "overseer")
            endpoints: List of endpoint URLs

        Returns:
            Next endpoint URL from the list
        """
        if not endpoints:
            return self.base_url

        if len(endpoints) == 1:
            return endpoints[0]

        # Initialize counter for this model_key if not exists
        if model_key not in self._endpoint_counters:
            self._endpoint_counters[model_key] = 0

        # Get next endpoint using round-robin
        index = self._endpoint_counters[model_key] % len(endpoints)
        endpoint = endpoints[index]

        # Increment counter for next time
        self._endpoint_counters[model_key] += 1

        return endpoint

    def calculate_timeout(
        self,
        model: str,
        model_key: Optional[str] = None,
        speed_tier: Optional[str] = None
    ) -> int:
        """
        Calculate dynamic timeout based on model speed and characteristics.

        Args:
            model: Model name
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier (from tool metadata)

        Returns:
            Timeout in seconds
        """
        # Base timeouts by speed tier (in seconds)
        TIER_TIMEOUTS = {
            "very-fast": 30,    # tinyllama, small models
            "fast": 60,          # efficient models
            "medium": 120,       # llama3, mid-size
            "slow": 240,         # qwen2.5-coder:14b, large models
            "very-slow": 480     # huge models, complex tasks
        }

        # Model-specific timeouts (overrides tier)
        MODEL_TIMEOUTS = {
            "tinyllama": 30,
            "llama3": 120,
            "qwen2.5-coder:14b": 240,
            "codellama": 180,
            "mistral-nemo": 60,
            "nemotron-mini": 60,
        }

        # If we have a model-specific timeout, use it
        if model in MODEL_TIMEOUTS:
            timeout = MODEL_TIMEOUTS[model]
        # If we have a speed tier from tool metadata, use that
        elif speed_tier and speed_tier in TIER_TIMEOUTS:
            timeout = TIER_TIMEOUTS[speed_tier]
        # If we have a model_key, try to get config info
        elif model_key and self.config_manager:
            # Try to get the tool info from config
            try:
                tool_config = self.config_manager.config.get("tools", {}).get(model_key, {})
                tier = tool_config.get("speed_tier", "medium")
                timeout = TIER_TIMEOUTS.get(tier, 120)
            except:
                timeout = 120  # Default fallback
        else:
            # Default to medium
            timeout = 120

        logger.debug(f"Calculated timeout for model '{model}' (key: {model_key}, tier: {speed_tier}): {timeout}s")
        return timeout

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False,
        endpoint: Optional[str] = None,
        model_key: Optional[str] = None,
        speed_tier: Optional[str] = None
    ) -> str:
        """
        Generate text using specified Ollama model.
        Supports round-robin load balancing across multiple endpoints.

        Args:
            model: Model name (e.g., 'codellama', 'llama3', 'tiny')
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response (default: False)
            endpoint: Optional specific endpoint URL (overrides config and round-robin)
            model_key: Optional model key for config lookup (e.g., "overseer", "generator")
            speed_tier: Optional speed tier for timeout calculation

        Returns:
            Generated text response
        """
        # Determine endpoint to use
        target_endpoint = endpoint

        # If no endpoint specified but we have a config_manager and model_key
        if not target_endpoint and self.config_manager and model_key:
            # Get endpoints (can be single or multiple)
            endpoints = self.config_manager.get_model_endpoints(model_key)
            if endpoints:
                target_endpoint = self._get_next_endpoint(model_key, endpoints)
            else:
                target_endpoint = self.base_url

        # Fall back to base_url
        if not target_endpoint:
            target_endpoint = self.base_url

        # Truncate prompt if necessary based on model's context window
        truncated_prompt = self.truncate_prompt(prompt, model)

        generate_url = f"{target_endpoint}/api/generate"

        payload = {
            "model": model,
            "prompt": truncated_prompt,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }

        if system:
            payload["system"] = system

        try:
            # Calculate dynamic timeout based on model and speed tier
            timeout = self.calculate_timeout(model, model_key, speed_tier)

            logger.info(f"Generating with model '{model}' at {target_endpoint} (timeout: {timeout}s)...")

            # Debug logging: Log the request (full content, not truncated)
            logger.debug(f"Request to {target_endpoint}:")
            logger.debug(f"  Model: {model}")
            logger.debug(f"  Prompt: {truncated_prompt}")
            logger.debug(f"  Temperature: {temperature}")
            if system:
                logger.debug(f"  System prompt: {system}")

            response = requests.post(
                generate_url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("response", "")

            # Debug logging: Log the response (full content, not truncated)
            logger.debug(f"Response from {target_endpoint}:")
            logger.debug(f"  Length: {len(result)} characters")
            logger.debug(f"  Full response: {result}")

            logger.info(f"✓ Generated {len(result)} characters from {target_endpoint}")
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for {target_endpoint}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating response from {target_endpoint}: {e}")
            return ""

    def generate_code(self, prompt: str, constraints: Optional[str] = None) -> str:
        """
        Generate code using codellama model.

        Args:
            prompt: Code generation prompt
            constraints: Optional additional constraints

        Returns:
            Generated code
        """
        system_prompt = "You are a precise code generator. Produce safe, deterministic Python code only. Return only code, no commentary or markdown."

        full_prompt = prompt
        if constraints:
            full_prompt = f"{prompt}\n\nConstraints:\n{constraints}"

        # Get model name from config if available
        model_name = "codellama"
        if self.config_manager:
            model_name = self.config_manager.generator_model

        return self.generate(
            model=model_name,
            prompt=full_prompt,
            system=system_prompt,
            temperature=0.3,  # Lower temperature for more deterministic code
            model_key="generator"  # Route to generator endpoint
        )

    def evaluate(self, code_summary: str, metrics: Dict[str, Any]) -> str:
        """
        Evaluate code and metrics using llama3 model.

        Args:
            code_summary: Summary of the code and its outputs
            metrics: Execution metrics dictionary

        Returns:
            Evaluation response (ideally JSON)
        """
        system_prompt = "You are a rigorous evaluator of Python program outputs and performance. Return only valid JSON."

        prompt = f"""Evaluate the following code execution:

Code summary:
{code_summary}

Metrics:
{json.dumps(metrics, indent=2)}

Evaluate based on:
- Correctness: Does the code work as expected?
- Latency: Is it within target performance?
- Memory: Is memory usage acceptable?
- Robustness: Does it handle edge cases?

Return JSON with this exact structure:
{{
  "score_overall": <float 0.0-1.0>,
  "scores": {{
    "correctness": <float 0.0-1.0>,
    "latency": <float 0.0-1.0>,
    "memory": <float 0.0-1.0>,
    "robustness": <float 0.0-1.0>
  }},
  "verdict": "<pass|fail>",
  "notes": "<detailed explanation>"
}}"""

        # Get model name from config if available
        model_name = "llama3"
        if self.config_manager:
            model_name = self.config_manager.evaluator_model

        return self.generate(
            model=model_name,
            prompt=prompt,
            system=system_prompt,
            temperature=0.5,
            model_key="evaluator"  # Route to evaluator endpoint
        )

    def triage(self, metrics: Dict[str, Any], targets: Dict[str, Any]) -> str:
        """
        Quick triage using tiny model.

        Args:
            metrics: Execution metrics
            targets: Target thresholds

        Returns:
            Pass/fail verdict with reason
        """
        system_prompt = "Quick triage. Decide pass/fail from metrics only. Be concise."

        prompt = f"""Metrics: {json.dumps(metrics)}
Targets: {json.dumps(targets)}

Return "pass: reason" or "fail: reason"."""

        # Get model name from config if available
        model_name = "tiny"
        if self.config_manager:
            model_name = self.config_manager.triage_model

        return self.generate(
            model=model_name,
            prompt=prompt,
            system=system_prompt,
            temperature=0.1,
            model_key="triage"  # Route to triage endpoint
        )
