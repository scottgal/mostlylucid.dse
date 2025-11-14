"""
Evaluator LLM - Determines fitness of execution results.
Focused evaluation agent that assesses quality, correctness, and performance.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ollama_client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FitnessEvaluation:
    """Represents a fitness evaluation of an execution."""

    def __init__(
        self,
        evaluation_id: str,
        node_id: str,
        plan_id: Optional[str],
        overall_score: float,
        quality_score: float,
        speed_score: float,
        correctness_score: float,
        verdict: str,
        strengths: List[str],
        weaknesses: List[str],
        recommendations: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize fitness evaluation.

        Args:
            evaluation_id: Unique evaluation identifier
            node_id: Node that was evaluated
            plan_id: Plan that was executed (if any)
            overall_score: Overall fitness score (0.0-1.0)
            quality_score: Quality/correctness score (0.0-1.0)
            speed_score: Speed/performance score (0.0-1.0)
            correctness_score: Functional correctness score (0.0-1.0)
            verdict: Overall verdict (excellent/good/acceptable/poor/fail)
            strengths: List of identified strengths
            weaknesses: List of identified weaknesses
            recommendations: List of improvement recommendations
            metadata: Additional metadata
        """
        self.evaluation_id = evaluation_id
        self.node_id = node_id
        self.plan_id = plan_id
        self.overall_score = overall_score
        self.quality_score = quality_score
        self.speed_score = speed_score
        self.correctness_score = correctness_score
        self.verdict = verdict
        self.strengths = strengths
        self.weaknesses = weaknesses
        self.recommendations = recommendations
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "node_id": self.node_id,
            "plan_id": self.plan_id,
            "overall_score": self.overall_score,
            "quality_score": self.quality_score,
            "speed_score": self.speed_score,
            "correctness_score": self.correctness_score,
            "verdict": self.verdict,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class EvaluatorLlm:
    """
    Evaluator LLM responsible for fitness determination.
    Analyzes execution results and provides detailed quality assessment.
    """

    def __init__(
        self,
        client: Optional[OllamaClient] = None,
        model: str = "llama3"
    ):
        """
        Initialize evaluator LLM.

        Args:
            client: OllamaClient instance
            model: Model to use for evaluation
        """
        self.client = client or OllamaClient()
        self.model = model

    def evaluate_fitness(
        self,
        node_id: str,
        task_description: str,
        execution_result: Dict[str, Any],
        expected_output: Optional[Any] = None,
        plan_id: Optional[str] = None,
        quality_targets: Optional[Dict[str, float]] = None
    ) -> FitnessEvaluation:
        """
        Evaluate the fitness of an execution result.

        Args:
            node_id: Node identifier
            task_description: What the task was supposed to do
            execution_result: Execution results (stdout, stderr, metrics)
            expected_output: Expected output (if known)
            plan_id: Associated plan ID (if any)
            quality_targets: Target quality metrics

        Returns:
            FitnessEvaluation object
        """
        logger.info(f"Evaluating fitness for node {node_id}...")

        # Extract execution details
        stdout = execution_result.get("stdout", "")
        stderr = execution_result.get("stderr", "")
        metrics = execution_result.get("metrics", {})

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            task_description,
            stdout,
            stderr,
            metrics,
            expected_output,
            quality_targets or {}
        )

        # Get evaluation from LLM
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            temperature=0.3  # Lower temperature for more consistent evaluation
        )

        # Parse evaluation response
        eval_data = self._parse_evaluation_response(response)

        # Calculate composite scores
        overall_score = self._calculate_overall_score(eval_data, metrics, quality_targets)

        # Create FitnessEvaluation
        evaluation_id = f"eval_{node_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        evaluation = FitnessEvaluation(
            evaluation_id=evaluation_id,
            node_id=node_id,
            plan_id=plan_id,
            overall_score=overall_score,
            quality_score=eval_data.get("quality_score", 0.5),
            speed_score=eval_data.get("speed_score", 0.5),
            correctness_score=eval_data.get("correctness_score", 0.5),
            verdict=eval_data.get("verdict", "unknown"),
            strengths=eval_data.get("strengths", []),
            weaknesses=eval_data.get("weaknesses", []),
            recommendations=eval_data.get("recommendations", []),
            metadata={
                "metrics": metrics,
                "task_description": task_description
            }
        )

        logger.info(f"✓ Fitness evaluation complete: {evaluation.verdict} (score: {overall_score:.2f})")
        return evaluation

    def compare_solutions(
        self,
        evaluations: List[FitnessEvaluation],
        optimization_goal: str = "balanced"  # balanced, quality, speed
    ) -> FitnessEvaluation:
        """
        Compare multiple evaluations and select the best one.

        Args:
            evaluations: List of FitnessEvaluation objects
            optimization_goal: What to optimize for (balanced/quality/speed)

        Returns:
            Best FitnessEvaluation based on goal
        """
        if not evaluations:
            raise ValueError("No evaluations to compare")

        if len(evaluations) == 1:
            return evaluations[0]

        logger.info(f"Comparing {len(evaluations)} solutions (goal: {optimization_goal})...")

        if optimization_goal == "quality":
            best = max(evaluations, key=lambda e: e.quality_score)
        elif optimization_goal == "speed":
            best = max(evaluations, key=lambda e: e.speed_score)
        else:  # balanced
            best = max(evaluations, key=lambda e: e.overall_score)

        logger.info(f"✓ Selected best solution: {best.node_id} (score: {best.overall_score:.2f})")
        return best

    def _build_evaluation_prompt(
        self,
        task: str,
        stdout: str,
        stderr: str,
        metrics: Dict[str, Any],
        expected_output: Optional[Any],
        quality_targets: Dict[str, float]
    ) -> str:
        """Build evaluation prompt for LLM."""
        prompt = f"""You are an AI Fitness Evaluator responsible for assessing code execution results.

Task Description:
{task}

Execution Output:
{stdout[:1000] if stdout else "(no output)"}

Errors/Warnings:
{stderr[:500] if stderr else "(none)"}

Performance Metrics:
- Execution Time: {metrics.get('latency_ms', 0)}ms
- Memory Usage: {metrics.get('memory_mb_peak', 0)}MB
- Exit Code: {metrics.get('exit_code', -1)}
- Success: {metrics.get('success', False)}

Expected Output:
{json.dumps(expected_output, indent=2) if expected_output else "(not specified)"}

Quality Targets:
- Quality Target: {quality_targets.get('quality', 0.8)}
- Speed Target: {quality_targets.get('speed_ms', 1000)}ms
- Memory Target: {quality_targets.get('memory_mb', 128)}MB

Evaluate the FITNESS of this execution across multiple dimensions:

1. CORRECTNESS (0.0-1.0): Does it produce correct output?
2. QUALITY (0.0-1.0): Is the implementation robust and well-designed?
3. SPEED (0.0-1.0): How does performance compare to target?

Respond in JSON format:
{{
  "correctness_score": <0.0-1.0>,
  "quality_score": <0.0-1.0>,
  "speed_score": <0.0-1.0>,
  "verdict": "excellent|good|acceptable|poor|fail",
  "strengths": ["strength 1", "strength 2", ...],
  "weaknesses": ["weakness 1", "weakness 2", ...],
  "recommendations": ["recommendation 1", "recommendation 2", ...],
  "reasoning": "Detailed explanation of scores"
}}

Be specific and actionable in your feedback.
"""
        return prompt

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM evaluation response."""
        # Try to find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse evaluation JSON: {e}")

        # Fallback: extract scores from text
        logger.warning("Could not parse evaluation as JSON, using text extraction")

        def extract_score(pattern: str, default: float = 0.5) -> float:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    return max(0.0, min(1.0, score))
                except ValueError:
                    pass
            return default

        correctness = extract_score(r'correctness[_\s]*score[:\s]*([\d.]+)')
        quality = extract_score(r'quality[_\s]*score[:\s]*([\d.]+)')
        speed = extract_score(r'speed[_\s]*score[:\s]*([\d.]+)')

        # Determine verdict
        avg_score = (correctness + quality + speed) / 3
        if avg_score >= 0.9:
            verdict = "excellent"
        elif avg_score >= 0.75:
            verdict = "good"
        elif avg_score >= 0.6:
            verdict = "acceptable"
        elif avg_score >= 0.4:
            verdict = "poor"
        else:
            verdict = "fail"

        return {
            "correctness_score": correctness,
            "quality_score": quality,
            "speed_score": speed,
            "verdict": verdict,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "reasoning": response[:500],
            "parsed": False
        }

    def _calculate_overall_score(
        self,
        eval_data: Dict[str, Any],
        metrics: Dict[str, Any],
        quality_targets: Optional[Dict[str, float]]
    ) -> float:
        """
        Calculate overall fitness score.

        Combines LLM scores with objective metrics.
        """
        # LLM scores (70% weight)
        correctness = eval_data.get("correctness_score", 0.5)
        quality = eval_data.get("quality_score", 0.5)
        speed_score = eval_data.get("speed_score", 0.5)

        llm_score = (correctness * 0.4 + quality * 0.3 + speed_score * 0.3)

        # Objective metrics (30% weight)
        obj_score = 1.0

        # Exit code penalty
        if metrics.get("exit_code", -1) != 0:
            obj_score *= 0.5

        # Speed penalty
        if quality_targets and "speed_ms" in quality_targets:
            target_speed = quality_targets["speed_ms"]
            actual_speed = metrics.get("latency_ms", 0)
            if actual_speed > target_speed:
                obj_score *= max(0.5, target_speed / actual_speed)

        # Memory penalty
        if quality_targets and "memory_mb" in quality_targets:
            target_memory = quality_targets["memory_mb"]
            actual_memory = metrics.get("memory_mb_peak", 0)
            if actual_memory > target_memory:
                obj_score *= max(0.7, target_memory / actual_memory)

        # Combine scores
        overall = (llm_score * 0.7 + obj_score * 0.3)

        return max(0.0, min(1.0, overall))
