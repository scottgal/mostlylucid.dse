"""
Base abstraction for LLM clients.
Defines the interface that all LLM backends must implement.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class LLMClientBase(ABC):
    """
    Abstract base class for all LLM clients.

    All backend implementations (Ollama, OpenAI, Anthropic, Azure, LM Studio)
    must implement these methods to ensure compatibility with the system.
    """

    def __init__(
        self,
        config_manager: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize LLM client.

        Args:
            config_manager: Optional ConfigManager for accessing configuration
            **kwargs: Additional backend-specific parameters
        """
        self.config_manager = config_manager
        self.backend_type = "base"  # Override in subclasses

    @abstractmethod
    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """
        Check if the LLM service is accessible.

        Args:
            endpoint: Optional specific endpoint to check

        Returns:
            True if service is accessible, False otherwise
        """
        pass

    @abstractmethod
    def list_models(self, endpoint: Optional[str] = None) -> List[str]:
        """
        List available models from the service.

        Args:
            endpoint: Optional specific endpoint

        Returns:
            List of model names/identifiers
        """
        pass

    @abstractmethod
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
        Generate text using the specified model.

        Args:
            model: Model name/identifier
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response
            endpoint: Optional specific endpoint URL
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier for timeout calculation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional backend-specific parameters

        Returns:
            Generated text response
        """
        pass

    def generate_code(
        self,
        prompt: str,
        constraints: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Generate code using appropriate model.

        Default implementation uses generate() with code-specific settings.
        Subclasses can override for backend-specific optimizations.

        Args:
            prompt: Code generation prompt
            constraints: Optional additional constraints
            model: Optional model override

        Returns:
            Generated code
        """
        system_prompt = (
            "You are a precise code generator. "
            "Produce safe, deterministic Python code only. "
            "Return only code, no commentary or markdown."
        )

        full_prompt = prompt
        if constraints:
            full_prompt = f"{prompt}\n\nConstraints:\n{constraints}"

        # Get model name from config if available
        model_name = model
        if not model_name and self.config_manager:
            model_name = getattr(self.config_manager, 'generator_model', None)
        if not model_name:
            model_name = self._get_default_code_model()

        return self.generate(
            model=model_name,
            prompt=full_prompt,
            system=system_prompt,
            temperature=0.3,
            model_key="generator"
        )

    def evaluate(
        self,
        code_summary: str,
        metrics: Dict[str, Any],
        model: Optional[str] = None
    ) -> str:
        """
        Evaluate code and metrics.

        Default implementation uses generate() with evaluation-specific settings.
        Subclasses can override for backend-specific optimizations.

        Args:
            code_summary: Summary of the code and its outputs
            metrics: Execution metrics dictionary
            model: Optional model override

        Returns:
            Evaluation response (ideally JSON)
        """
        import json

        system_prompt = (
            "You are a rigorous evaluator of Python program outputs and performance. "
            "Return only valid JSON."
        )

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
        model_name = model
        if not model_name and self.config_manager:
            model_name = getattr(self.config_manager, 'evaluator_model', None)
        if not model_name:
            model_name = self._get_default_eval_model()

        return self.generate(
            model=model_name,
            prompt=prompt,
            system=system_prompt,
            temperature=0.5,
            model_key="evaluator"
        )

    def triage(
        self,
        metrics: Dict[str, Any],
        targets: Dict[str, Any],
        model: Optional[str] = None
    ) -> str:
        """
        Quick triage for pass/fail decisions.

        Default implementation uses generate() with triage-specific settings.
        Subclasses can override for backend-specific optimizations.

        Args:
            metrics: Execution metrics
            targets: Target thresholds
            model: Optional model override

        Returns:
            Pass/fail verdict with reason
        """
        import json

        system_prompt = "Quick triage. Decide pass/fail from metrics only. Be concise."

        prompt = f"""Metrics: {json.dumps(metrics)}
Targets: {json.dumps(targets)}

Return "pass: reason" or "fail: reason"."""

        # Get model name from config if available
        model_name = model
        if not model_name and self.config_manager:
            model_name = getattr(self.config_manager, 'triage_model', None)
        if not model_name:
            model_name = self._get_default_triage_model()

        return self.generate(
            model=model_name,
            prompt=prompt,
            system=system_prompt,
            temperature=0.1,
            model_key="triage"
        )

    def truncate_prompt(
        self,
        prompt: str,
        model: str,
        max_ratio: float = 0.8
    ) -> str:
        """
        Truncate prompt if it exceeds the model's context window.

        Args:
            prompt: The prompt text
            model: Model name
            max_ratio: Use max_ratio of context window

        Returns:
            Truncated prompt if necessary
        """
        if not self.config_manager:
            return prompt

        # Get context window size for model
        context_window = self._get_context_window(model)

        # Rough approximation: 4 chars per token
        max_chars = int(context_window * max_ratio * 4)

        if len(prompt) > max_chars:
            logger.warning(
                f"Prompt length ({len(prompt)} chars) exceeds max for {model} "
                f"({max_chars} chars). Truncating."
            )
            truncated = prompt[:max_chars - 100]
            truncated += "\n\n[... prompt truncated due to length ...]"
            return truncated

        return prompt

    def calculate_timeout(
        self,
        model: str,
        model_key: Optional[str] = None,
        speed_tier: Optional[str] = None
    ) -> int:
        """
        Calculate dynamic timeout based on model speed.

        Args:
            model: Model name
            model_key: Optional model key for config lookup
            speed_tier: Optional speed tier

        Returns:
            Timeout in seconds
        """
        TIER_TIMEOUTS = {
            "very-fast": 30,
            "fast": 60,
            "medium": 120,
            "slow": 240,
            "very-slow": 480
        }

        if speed_tier and speed_tier in TIER_TIMEOUTS:
            return TIER_TIMEOUTS[speed_tier]

        return 120  # Default

    def _get_context_window(self, model: str) -> int:
        """
        Get context window size for a model.

        Args:
            model: Model name

        Returns:
            Context window size in tokens
        """
        if self.config_manager and hasattr(self.config_manager, 'get_context_window'):
            return self.config_manager.get_context_window(model)

        # Default context windows for common models
        return self._get_default_context_window(model)

    @abstractmethod
    def _get_default_context_window(self, model: str) -> int:
        """Get default context window for a model (backend-specific)."""
        pass

    @abstractmethod
    def _get_default_code_model(self) -> str:
        """Get default model for code generation (backend-specific)."""
        pass

    @abstractmethod
    def _get_default_eval_model(self) -> str:
        """Get default model for evaluation (backend-specific)."""
        pass

    @abstractmethod
    def _get_default_triage_model(self) -> str:
        """Get default model for triage (backend-specific)."""
        pass
