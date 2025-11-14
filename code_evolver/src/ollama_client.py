"""
Ollama client for interacting with local Ollama models.
Supports code generation, evaluation, and triage tasks.
"""
import requests
import json
import logging
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for communicating with local Ollama server."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434)
        """
        self.base_url = base_url
        self.generate_endpoint = f"{base_url}/api/generate"

    def check_connection(self) -> bool:
        """
        Check if Ollama server is running and accessible.

        Returns:
            True if server is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            logger.info("✓ Connected to Ollama server")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to Ollama server: {e}")
            return False

    def list_models(self) -> list:
        """
        List available models in Ollama.

        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return models
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing models: {e}")
            return []

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Generate text using specified Ollama model.

        Args:
            model: Model name (e.g., 'codellama', 'llama3', 'tiny')
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            stream: Whether to stream response (default: False)

        Returns:
            Generated text response
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }

        if system:
            payload["system"] = system

        try:
            logger.info(f"Generating with model '{model}'...")
            response = requests.post(
                self.generate_endpoint,
                json=payload,
                timeout=300  # 5 minute timeout for code generation
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("response", "")
            logger.info(f"✓ Generated {len(result)} characters")
            return result

        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating response: {e}")
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

        return self.generate(
            model="codellama",
            prompt=full_prompt,
            system=system_prompt,
            temperature=0.3  # Lower temperature for more deterministic code
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

        return self.generate(
            model="llama3",
            prompt=prompt,
            system=system_prompt,
            temperature=0.5
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

        return self.generate(
            model="tiny",
            prompt=prompt,
            system=system_prompt,
            temperature=0.1
        )
