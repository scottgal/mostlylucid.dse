"""
Evaluation system using Ollama models for scoring node performance.
"""
import json
import logging
import re
from typing import Dict, Any, Optional
from .ollama_client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates node execution results using Ollama models."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialize evaluator.

        Args:
            ollama_client: OllamaClient instance (creates new if None)
        """
        self.client = ollama_client or OllamaClient()

    def triage(
        self,
        metrics: Dict[str, Any],
        targets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Quick triage evaluation using tiny model.

        Args:
            metrics: Execution metrics
            targets: Target thresholds (optional)

        Returns:
            Triage result with verdict
        """
        if targets is None:
            targets = {
                "latency_ms": 200,
                "memory_mb": 64,
                "exit_code": 0
            }

        logger.info("Running quick triage...")

        response = self.client.triage(metrics, targets)

        # Parse triage response
        verdict = "unknown"
        reason = response

        if "pass" in response.lower():
            verdict = "pass"
        elif "fail" in response.lower():
            verdict = "fail"

        return {
            "type": "triage",
            "model": "tiny",
            "verdict": verdict,
            "reason": reason.strip(),
            "metrics": metrics,
            "targets": targets
        }

    def evaluate(
        self,
        stdout: str,
        stderr: str,
        metrics: Dict[str, Any],
        code_summary: Optional[str] = None,
        goals: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation using llama3 model.

        Args:
            stdout: Standard output from execution
            stderr: Standard error from execution
            metrics: Execution metrics
            code_summary: Optional summary of the code
            goals: Optional goals and targets

        Returns:
            Evaluation result with scores
        """
        logger.info("Running comprehensive evaluation...")

        # Build code summary
        if code_summary is None:
            code_summary = f"Output:\n{stdout[:500]}"
            if stderr:
                code_summary += f"\n\nErrors:\n{stderr[:500]}"

        # Get evaluation from llama3
        response = self.client.evaluate(code_summary, metrics)

        # Try to parse JSON response
        evaluation = self._parse_evaluation_response(response)

        # Add metadata
        evaluation["type"] = "comprehensive"
        evaluation["model"] = "llama3"
        evaluation["metrics"] = metrics

        if goals:
            evaluation["goals"] = goals

        logger.info(f"✓ Evaluation complete: {evaluation.get('verdict', 'unknown')} "
                   f"(score: {evaluation.get('score_overall', 0):.2f})")

        return evaluation

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """
        Parse evaluation response, attempting to extract JSON.

        Args:
            response: Raw response from model

        Returns:
            Parsed evaluation dictionary
        """
        # Try to find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If no valid JSON, create default structure
        logger.warning("Could not parse evaluation as JSON, using defaults")

        # Try to extract score and verdict from text
        score = 0.5
        verdict = "unknown"

        score_match = re.search(r'score[_\s]*overall[:\s]*([\d.]+)', response, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                pass

        if "pass" in response.lower():
            verdict = "pass"
        elif "fail" in response.lower():
            verdict = "fail"

        return {
            "score_overall": score,
            "scores": {
                "correctness": 0.5,
                "latency": 0.5,
                "memory": 0.5,
                "robustness": 0.5
            },
            "verdict": verdict,
            "notes": response,
            "parsed": False
        }

    def evaluate_full(
        self,
        stdout: str,
        stderr: str,
        metrics: Dict[str, Any],
        code_summary: Optional[str] = None,
        goals: Optional[Dict[str, Any]] = None,
        targets: Optional[Dict[str, Any]] = None,
        use_triage: bool = True
    ) -> Dict[str, Any]:
        """
        Full evaluation pipeline: triage first, then comprehensive if needed.

        Args:
            stdout: Standard output
            stderr: Standard error
            metrics: Execution metrics
            code_summary: Optional code summary
            goals: Optional goals
            targets: Optional targets for triage
            use_triage: Whether to run triage first (default: True)

        Returns:
            Combined evaluation result
        """
        result = {
            "triage": None,
            "evaluation": None,
            "final_verdict": "unknown",
            "final_score": 0.0
        }

        # Quick triage first
        if use_triage:
            triage_result = self.triage(metrics, targets)
            result["triage"] = triage_result

            # If triage fails badly, might skip comprehensive eval
            if triage_result["verdict"] == "fail" and metrics.get("exit_code", -1) != 0:
                logger.info("Triage failed, skipping comprehensive evaluation")
                result["final_verdict"] = "fail"
                result["final_score"] = 0.0
                return result

        # Comprehensive evaluation
        evaluation = self.evaluate(stdout, stderr, metrics, code_summary, goals)
        result["evaluation"] = evaluation

        # Determine final verdict and score
        result["final_verdict"] = evaluation.get("verdict", "unknown")
        result["final_score"] = evaluation.get("score_overall", 0.0)

        return result

    def calculate_score_from_metrics(
        self,
        metrics: Dict[str, Any],
        targets: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate a simple score based on metrics and targets.

        Args:
            metrics: Execution metrics
            targets: Target thresholds

        Returns:
            Score between 0.0 and 1.0
        """
        if targets is None:
            targets = {
                "latency_ms": 200,
                "memory_mb": 64
            }

        score = 1.0

        # Exit code: must be 0
        if metrics.get("exit_code", -1) != 0:
            score *= 0.5

        # Latency score
        latency = metrics.get("latency_ms", 0)
        target_latency = targets.get("latency_ms", 200)
        if latency > target_latency:
            score *= max(0.5, target_latency / latency)

        # Memory score
        memory = metrics.get("memory_mb_peak", 0)
        target_memory = targets.get("memory_mb", 64)
        if memory > target_memory:
            score *= max(0.5, target_memory / memory)

        return min(1.0, max(0.0, score))
