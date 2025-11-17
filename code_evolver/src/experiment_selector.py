"""
Experiment Selector - Choose Best Result Based on Quality vs Speed

Balances quality and speed based on real data to select the best code
generation result from multiple parallel experiments.

Quality metrics:
- Test pass rate
- Code quality score (from evaluator)
- Error handling
- Code coverage

Speed metrics:
- Generation time
- Execution time
- Time to first success

The selector learns optimal weights over time based on user preferences
and task requirements.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import statistics

logger = logging.getLogger(__name__)


@dataclass
class SelectionCriteria:
    """Criteria for selecting best experiment result."""
    quality_weight: float = 0.7  # How much to prioritize quality
    speed_weight: float = 0.3  # How much to prioritize speed

    # Minimum thresholds
    min_quality_score: float = 0.5  # 0-1
    max_generation_time: float = 120.0  # seconds
    max_execution_time: float = 10.0  # seconds

    # Preferences
    prefer_consistency: bool = True  # Prefer low variance in results
    prefer_simplicity: bool = False  # Prefer shorter code


class ExperimentSelector:
    """
    Selects the best code generation result from multiple experiments.

    The selector:
    1. Filters results by minimum thresholds
    2. Scores each result on quality and speed
    3. Applies configurable weights
    4. Selects the best based on combined score
    5. Learns from selections to improve future choices
    """

    def __init__(
        self,
        criteria: Optional[SelectionCriteria] = None,
        learning_rate: float = 0.1
    ):
        """
        Initialize experiment selector.

        Args:
            criteria: Selection criteria (default: balanced 70/30)
            learning_rate: How fast to adapt weights (0-1)
        """
        self.criteria = criteria or SelectionCriteria()
        self.learning_rate = learning_rate

        # Track selection history for learning
        self.selection_history = []
        self.weight_adjustments = []

    def select_best(
        self,
        results: List[Dict[str, Any]],
        task_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Select the best result from parallel experiments.

        Args:
            results: List of experiment results
            task_context: Optional context about the task

        Returns:
            Best result, or None if none meet criteria
        """

        if not results:
            logger.warning("No results to select from")
            return None

        # Filter by minimum thresholds
        qualified = self._filter_by_thresholds(results)

        if not qualified:
            logger.warning("No results meet minimum thresholds")
            # Return best effort (highest quality, even if below threshold)
            return max(results, key=lambda r: r.get("quality_score", 0.0))

        # Score all qualified results
        scored_results = [
            self._score_result(r, task_context) for r in qualified
        ]

        # Select best
        best = max(scored_results, key=lambda r: r["combined_score"])

        # Record selection for learning
        self._record_selection(best, results, task_context)

        logger.info(
            f"Selected: {best.get('generator_name', 'unknown')} "
            f"(score: {best['combined_score']:.2f}, "
            f"quality: {best.get('quality_score', 0):.2f}, "
            f"speed: {best.get('generation_time', 0):.2f}s)"
        )

        return best

    def _filter_by_thresholds(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter results by minimum quality and maximum time thresholds."""

        qualified = []

        for result in results:
            # Must have succeeded
            if not result.get("success", False):
                continue

            # Must pass tests
            if not result.get("test_passed", False):
                continue

            # Quality threshold
            if result.get("quality_score", 0.0) < self.criteria.min_quality_score:
                continue

            # Generation time threshold
            if result.get("generation_time", float('inf')) > self.criteria.max_generation_time:
                continue

            # Execution time threshold
            if result.get("execution_time", float('inf')) > self.criteria.max_execution_time:
                continue

            qualified.append(result)

        return qualified

    def _score_result(
        self,
        result: Dict[str, Any],
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score a single result based on quality and speed.

        Returns:
            Result dict with added "combined_score" field
        """

        # Quality score (0-1)
        quality_score = self._compute_quality_score(result)

        # Speed score (0-1)
        speed_score = self._compute_speed_score(result)

        # Apply context-specific adjustments
        if task_context:
            quality_score, speed_score = self._adjust_for_context(
                quality_score, speed_score, task_context
            )

        # Combined score
        combined = (
            self.criteria.quality_weight * quality_score +
            self.criteria.speed_weight * speed_score
        )

        result["quality_component"] = quality_score
        result["speed_component"] = speed_score
        result["combined_score"] = combined

        return result

    def _compute_quality_score(self, result: Dict[str, Any]) -> float:
        """
        Compute quality score (0-1).

        Components:
        - Base quality score from evaluator (0-1)
        - Code simplicity bonus (if enabled)
        - Error handling bonus
        """

        base_quality = result.get("quality_score", 0.0)
        score = base_quality

        # Simplicity bonus
        if self.criteria.prefer_simplicity:
            code = result.get("code", "")
            lines = len(code.split('\n'))

            # Shorter is better (up to +0.1)
            if lines < 50:
                score += 0.1
            elif lines < 100:
                score += 0.05

        # Error handling bonus
        code = result.get("code", "")
        if "try:" in code and "except" in code:
            score += 0.05

        return min(1.0, score)

    def _compute_speed_score(self, result: Dict[str, Any]) -> float:
        """
        Compute speed score (0-1).

        Components:
        - Generation time (normalized)
        - Execution time (normalized)
        - Time to first success (if multiple attempts)
        """

        gen_time = result.get("generation_time", 0.0)
        exec_time = result.get("execution_time", 0.0)

        # Normalize generation time (< 10s = 1.0, > 60s = 0.0)
        gen_score = max(0.0, 1.0 - (gen_time / 60.0))

        # Normalize execution time (< 1s = 1.0, > 10s = 0.0)
        exec_score = max(0.0, 1.0 - (exec_time / 10.0))

        # Weighted average (favor generation speed)
        speed_score = (gen_score * 0.6) + (exec_score * 0.4)

        return speed_score

    def _adjust_for_context(
        self,
        quality_score: float,
        speed_score: float,
        context: Dict[str, Any]
    ) -> tuple:
        """
        Adjust scores based on task context.

        Context examples:
        - task_type: "api_integration" → prioritize quality
        - task_type: "simple_function" → prioritize speed
        - priority: "high" → strict quality requirements
        - deadline: "urgent" → prioritize speed
        """

        task_type = context.get("task_type", "")
        priority = context.get("priority", "normal")

        # API/critical tasks: boost quality importance
        if task_type in ["api_integration", "database", "security"]:
            quality_score *= 1.2
            speed_score *= 0.8

        # Simple tasks: boost speed importance
        elif task_type in ["simple_function", "utility", "helper"]:
            quality_score *= 0.9
            speed_score *= 1.1

        # High priority: strict quality
        if priority == "high":
            quality_score *= 1.1

        # Normalize back to 0-1
        quality_score = min(1.0, quality_score)
        speed_score = min(1.0, speed_score)

        return quality_score, speed_score

    def _record_selection(
        self,
        selected: Dict[str, Any],
        all_results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ):
        """Record selection for learning and analytics."""

        self.selection_history.append({
            "selected_generator": selected.get("generator_name"),
            "selected_score": selected.get("combined_score"),
            "num_candidates": len(all_results),
            "quality_weight": self.criteria.quality_weight,
            "speed_weight": self.criteria.speed_weight,
            "context": context
        })

        # Keep last 100 selections
        if len(self.selection_history) > 100:
            self.selection_history.pop(0)

    def learn_from_feedback(
        self,
        selected_result: Dict[str, Any],
        user_satisfaction: float
    ):
        """
        Adjust weights based on user feedback.

        Args:
            selected_result: The result that was selected
            user_satisfaction: User rating 0-1
        """

        # If user is satisfied, weights are good
        if user_satisfaction > 0.8:
            return

        # If user is dissatisfied, adjust weights
        # If quality was prioritized but user unhappy, maybe they wanted speed
        # If speed was prioritized but user unhappy, maybe they wanted quality

        current_quality_weight = self.criteria.quality_weight

        # Low satisfaction + high quality weight → reduce quality weight
        if user_satisfaction < 0.5 and current_quality_weight > 0.6:
            adjustment = -self.learning_rate * (1.0 - user_satisfaction)
            self.criteria.quality_weight = max(0.3, current_quality_weight + adjustment)
            self.criteria.speed_weight = 1.0 - self.criteria.quality_weight

        # Low satisfaction + high speed weight → reduce speed weight
        elif user_satisfaction < 0.5 and current_quality_weight < 0.4:
            adjustment = self.learning_rate * (1.0 - user_satisfaction)
            self.criteria.quality_weight = min(0.7, current_quality_weight + adjustment)
            self.criteria.speed_weight = 1.0 - self.criteria.quality_weight

        self.weight_adjustments.append({
            "satisfaction": user_satisfaction,
            "adjustment": adjustment,
            "new_quality_weight": self.criteria.quality_weight
        })

        logger.info(
            f"Adjusted weights based on feedback: "
            f"quality={self.criteria.quality_weight:.2f}, "
            f"speed={self.criteria.speed_weight:.2f}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about selections."""

        if not self.selection_history:
            return {"total_selections": 0}

        # Count generator selections
        generator_counts = {}
        for selection in self.selection_history:
            gen = selection["selected_generator"]
            generator_counts[gen] = generator_counts.get(gen, 0) + 1

        # Average scores
        scores = [s["selected_score"] for s in self.selection_history]

        return {
            "total_selections": len(self.selection_history),
            "generator_distribution": generator_counts,
            "average_score": statistics.mean(scores),
            "score_std_dev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "current_weights": {
                "quality": self.criteria.quality_weight,
                "speed": self.criteria.speed_weight
            },
            "total_adjustments": len(self.weight_adjustments)
        }

    def recommend_criteria(
        self,
        task_type: str
    ) -> SelectionCriteria:
        """
        Recommend selection criteria based on task type.

        Args:
            task_type: Type of task

        Returns:
            Recommended SelectionCriteria
        """

        # Default criteria
        criteria = SelectionCriteria()

        # Adjust based on task type
        if task_type in ["api_integration", "database", "security", "production"]:
            # Prioritize quality for critical tasks
            criteria.quality_weight = 0.85
            criteria.speed_weight = 0.15
            criteria.min_quality_score = 0.7

        elif task_type in ["simple_function", "utility", "helper", "prototype"]:
            # Prioritize speed for simple tasks
            criteria.quality_weight = 0.5
            criteria.speed_weight = 0.5
            criteria.min_quality_score = 0.4

        elif task_type in ["data_processing", "batch", "automation"]:
            # Balance for data tasks
            criteria.quality_weight = 0.6
            criteria.speed_weight = 0.4
            criteria.max_execution_time = 30.0  # Allow longer execution

        return criteria
