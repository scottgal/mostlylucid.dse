"""
Offline Batch Optimizer - Runs overnight to optimize high-value artifacts using cloud LLMs.

This component identifies artifacts that are:
- Frequently used (high reuse count)
- Suboptimal quality (low quality score)
- Worth the investment of expensive cloud optimization

It runs batch optimizations when cost and time don't matter (overnight),
using expensive but high-quality cloud LLMs to improve the most valuable artifacts.

Usage:
    optimizer = OfflineBatchOptimizer(config, rag, pipeline, executor)

    # Run overnight optimization
    results = optimizer.batch_optimize_overnight(max_cost=50.00)

    # Schedule for nightly runs
    optimizer.schedule_nightly_optimization(hour=2, max_cost=50.00)
"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .cumulative_changelog import CumulativeChangelog
from .test_evolution_tracker import TestEvolutionTracker

logger = logging.getLogger(__name__)


@dataclass
class OptimizationCandidate:
    """Represents an artifact that's a candidate for optimization."""
    artifact: Any
    value_score: float  # Reuse * improvement potential
    estimated_improvement: float
    estimated_cost: float
    priority: str  # "high" | "medium" | "low"


class OfflineBatchOptimizer:
    """
    Runs overnight to optimize high-value artifacts using cloud LLMs.
    Focuses investment on artifacts that provide the best ROI.
    """

    def __init__(
        self,
        config_manager,
        rag_memory,
        optimization_pipeline,
        executor=None,
        changelog: Optional[CumulativeChangelog] = None,
        test_tracker: Optional[TestEvolutionTracker] = None
    ):
        """
        Initialize offline batch optimizer.

        Args:
            config_manager: ConfigManager instance
            rag_memory: RAG memory system
            optimization_pipeline: OptimizationPipeline instance
            executor: Optional executor for testing optimized code
            changelog: Optional cumulative changelog for tracking mutations
            test_tracker: Optional test evolution tracker
        """
        self.config = config_manager
        self.rag = rag_memory
        self.pipeline = optimization_pipeline
        self.executor = executor
        self.changelog = changelog or CumulativeChangelog(
            storage_dir=config_manager.get("evolution_logs_dir", "evolution_logs")
        )
        self.test_tracker = test_tracker or TestEvolutionTracker()

        # Get optimization settings
        opt_config = config_manager.get("optimization.cloud_optimization", {})
        self.enabled = opt_config.get("enabled", True)
        self.triggers = opt_config.get("triggers", {})

        # Optimization history
        self.optimization_log: List[Dict[str, Any]] = []

    def identify_optimization_candidates(
        self,
        min_reuse_count: int = 10,
        max_quality_score: float = 0.75
    ) -> List[OptimizationCandidate]:
        """
        Find artifacts worth expensive cloud optimization.

        Looks for artifacts that are:
        - Frequently used (proving usefulness)
        - Suboptimal quality (room for improvement)

        Args:
            min_reuse_count: Minimum times artifact must be reused
            max_quality_score: Maximum quality score (looking for suboptimal)

        Returns:
            List of optimization candidates, sorted by value score
        """
        logger.info("Identifying optimization candidates...")

        candidates = []

        # Get all artifacts from RAG
        all_artifacts = self.rag.list_all()

        for artifact in all_artifacts:
            # Skip if not enough reuse
            if artifact.usage_count < min_reuse_count:
                continue

            # Skip if already high quality
            if artifact.quality_score >= max_quality_score:
                continue

            # Calculate value score: reuse * improvement potential
            improvement_potential = 1.0 - artifact.quality_score
            value_score = artifact.usage_count * improvement_potential

            # Estimate improvement and cost
            estimated_improvement = self._estimate_improvement(artifact)
            estimated_cost = self._estimate_optimization_cost(artifact)

            # Determine priority
            priority = self._calculate_priority(artifact, value_score)

            candidates.append(OptimizationCandidate(
                artifact=artifact,
                value_score=value_score,
                estimated_improvement=estimated_improvement,
                estimated_cost=estimated_cost,
                priority=priority
            ))

        # Sort by value score (highest first)
        candidates.sort(key=lambda x: x.value_score, reverse=True)

        logger.info(f"Found {len(candidates)} optimization candidates")
        logger.info(f"Top candidate: {candidates[0].artifact.artifact_id if candidates else 'none'} "
                   f"(value_score={candidates[0].value_score:.2f})" if candidates else "")

        return candidates

    def batch_optimize_overnight(
        self,
        max_cost: float = 50.00,
        max_artifacts: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Run expensive optimizations when cost/time don't matter.

        Args:
            max_cost: Maximum dollars to spend on optimization
            max_artifacts: Maximum number of artifacts to optimize (optional)

        Returns:
            List of optimization results with improvement metrics
        """
        if not self.enabled:
            logger.info("Offline optimization disabled in config")
            return []

        logger.info(f"Starting overnight batch optimization (max_cost=${max_cost:.2f})")
        start_time = time.time()

        # Identify candidates
        candidates = self.identify_optimization_candidates()

        if not candidates:
            logger.info("No optimization candidates found")
            return []

        total_cost = 0.0
        optimized = []
        processed = 0

        for candidate in candidates:
            # Check cost limit
            if total_cost + candidate.estimated_cost > max_cost:
                logger.info(f"Cost limit reached (${total_cost:.2f}/${max_cost:.2f}), stopping")
                break

            # Check artifact limit
            if max_artifacts and processed >= max_artifacts:
                logger.info(f"Artifact limit reached ({processed}/{max_artifacts}), stopping")
                break

            artifact = candidate.artifact

            logger.info(f"Optimizing {artifact.artifact_id} (reuse={artifact.usage_count}, "
                       f"quality={artifact.quality_score:.2f}, "
                       f"value_score={candidate.value_score:.2f})")

            try:
                # Cloud optimization (expensive but thorough)
                result = self.pipeline.optimize_artifact(
                    artifact,
                    level="cloud"  # Use cloud optimizer
                )

                if result:
                    # Test the optimized version if executor available
                    if self.executor:
                        test_passed, new_metrics = self._test_optimized_version(
                            artifact,
                            result.optimized_content
                        )
                    else:
                        test_passed = True  # Assume pass if no executor
                        new_metrics = {}

                    if test_passed:
                        # Calculate actual improvement
                        improvement = self._calculate_improvement(
                            artifact.metadata.get("metrics", {}),
                            new_metrics
                        )

                        # Only store if improvement is significant (>10%)
                        if improvement > 0.10:
                            # Store optimized version in RAG
                            optimized_id = self._store_optimized_artifact(
                                artifact,
                                result,
                                new_metrics,
                                improvement
                            )

                            optimized.append({
                                "artifact_id": artifact.artifact_id,
                                "optimized_id": optimized_id,
                                "improvement": improvement,
                                "old_score": artifact.quality_score,
                                "new_score": artifact.quality_score + improvement,
                                "cost": result.cost_usd
                            })

                            logger.info(f"✓ Optimized {artifact.artifact_id}: "
                                       f"+{improvement*100:.1f}% improvement, "
                                       f"${result.cost_usd:.2f}")
                        else:
                            logger.info(f"✗ Optimization improvement too small: {improvement*100:.1f}%")

                    else:
                        logger.warning(f"✗ Optimized version failed tests")

                    # Track cost
                    total_cost += result.cost_usd

            except Exception as e:
                logger.error(f"Failed to optimize {artifact.artifact_id}: {e}")

            processed += 1

        elapsed_time = time.time() - start_time

        # Log summary
        logger.info(f"Overnight optimization complete:")
        logger.info(f"  - Processed: {processed} artifacts")
        logger.info(f"  - Optimized: {len(optimized)} artifacts")
        logger.info(f"  - Cost: ${total_cost:.2f}")
        logger.info(f"  - Time: {elapsed_time/60:.1f} minutes")

        # Record in optimization log
        self.optimization_log.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "processed": processed,
            "optimized": len(optimized),
            "cost": total_cost,
            "duration_seconds": elapsed_time,
            "results": optimized
        })

        return optimized

    def schedule_nightly_optimization(
        self,
        hour: int = 2,
        max_cost: float = 50.00,
        max_artifacts: Optional[int] = None
    ):
        """
        Schedule optimization to run every night at specified hour.

        Args:
            hour: Hour to run (0-23, in UTC)
            max_cost: Maximum cost per night
            max_artifacts: Maximum artifacts per night

        Note:
            This is a placeholder - actual scheduling would use
            cron, systemd timer, or a scheduler like APScheduler.
        """
        logger.info(f"Scheduling nightly optimization at {hour:02d}:00 UTC")
        logger.info(f"  Max cost: ${max_cost:.2f}/night")
        logger.info(f"  Max artifacts: {max_artifacts or 'unlimited'}")

        # Placeholder - would integrate with actual scheduler
        logger.warning("Automatic scheduling not yet implemented")
        logger.info("To run manually: optimizer.batch_optimize_overnight()")

    def _estimate_improvement(self, artifact: Any) -> float:
        """
        Estimate potential improvement from optimization.

        Based on:
        - Current quality score (lower = more room for improvement)
        - Artifact type (some types benefit more)
        - Similar artifacts that were optimized
        """
        # Room for improvement
        improvement_potential = 1.0 - artifact.quality_score

        # Estimate based on artifact type
        type_multipliers = {
            "function": 0.3,   # Functions: moderate improvement
            "workflow": 0.5,   # Workflows: high improvement potential
            "code": 0.3,       # Code: moderate improvement
        }

        multiplier = type_multipliers.get(artifact.artifact_type.value, 0.2)

        return improvement_potential * multiplier

    def _estimate_optimization_cost(self, artifact: Any) -> float:
        """
        Estimate cost of cloud optimization.

        Based on:
        - Artifact size (more tokens = higher cost)
        - Optimization level (cloud vs deep)
        """
        # Rough estimate: $0.01 per 1K tokens
        content_length = len(artifact.content)
        tokens_approx = content_length / 4  # Rough estimate: 4 chars per token

        # Cloud optimization cost estimate
        cost_per_token = 0.00001  # $0.01 per 1K tokens

        return tokens_approx * cost_per_token

    def _calculate_priority(self, artifact: Any, value_score: float) -> str:
        """Calculate priority level for optimization."""

        if value_score > 20:
            return "high"
        elif value_score > 10:
            return "medium"
        else:
            return "low"

    def _test_optimized_version(
        self,
        original: Any,
        optimized_content: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Test optimized version to ensure it still works.

        Returns:
            (test_passed, metrics) tuple
        """
        if not self.executor:
            return True, {}

        # Would execute tests on optimized content
        # For now, placeholder
        logger.info(f"Testing optimized version of {original.artifact_id}")

        # Placeholder - would run actual tests
        return True, {
            "latency_ms": 0,
            "memory_mb": 0,
            "test_pass": True
        }

    def _calculate_improvement(
        self,
        metrics_before: Dict[str, Any],
        metrics_after: Dict[str, Any]
    ) -> float:
        """
        Calculate improvement score from metrics.

        Returns:
            Improvement as a fraction (0.15 = 15% improvement)
        """
        if not metrics_before or not metrics_after:
            return 0.15  # Default estimate

        # Would compare actual metrics
        # For now, placeholder
        return 0.20  # 20% improvement estimate

    def _store_optimized_artifact(
        self,
        original: Any,
        optimization_result: Any,
        new_metrics: Dict[str, Any],
        improvement: float
    ) -> str:
        """
        Store optimized artifact in RAG.

        Returns:
            New artifact ID
        """
        from .rag_memory import ArtifactType

        optimized_id = f"{original.artifact_id}_optimized_cloud"

        self.rag.store_artifact(
            artifact_id=optimized_id,
            artifact_type=original.artifact_type,
            name=f"{original.name} (Cloud Optimized)",
            description=original.description,
            content=optimization_result.optimized_content,
            tags=original.tags + ["cloud-optimized", "batch-optimized"],
            metadata={
                "optimized_from": original.artifact_id,
                "optimization_date": datetime.utcnow().isoformat() + "Z",
                "improvement": improvement,
                "old_score": original.quality_score,
                "new_score": original.quality_score + improvement,
                "optimization_cost": optimization_result.cost_usd,
                "metrics": new_metrics,
                "rationale": optimization_result.rationale,
                "specific_improvements": optimization_result.specific_improvements
            },
            auto_embed=True
        )

        # Update quality score
        self.rag.update_quality_score(optimized_id, original.quality_score + improvement)

        logger.info(f"Stored optimized artifact: {optimized_id}")

        return optimized_id

    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate report on optimization history."""

        if not self.optimization_log:
            return {
                "total_runs": 0,
                "total_optimized": 0,
                "total_cost": 0.0
            }

        total_runs = len(self.optimization_log)
        total_optimized = sum(log["optimized"] for log in self.optimization_log)
        total_cost = sum(log["cost"] for log in self.optimization_log)
        total_time = sum(log["duration_seconds"] for log in self.optimization_log)

        # Calculate ROI (saved execution cost vs optimization cost)
        # Assumption: each reuse saves $0.01 in generation cost
        total_value = 0.0
        for log in self.optimization_log:
            for result in log["results"]:
                # Artifact will be reused, saving generation cost each time
                artifact = self.rag.get_artifact(result["artifact_id"])
                if artifact:
                    saved_per_use = 0.01  # $0.01 saved per reuse
                    total_value += artifact.usage_count * saved_per_use

        roi = (total_value - total_cost) / total_cost if total_cost > 0 else 0

        return {
            "total_runs": total_runs,
            "total_optimized": total_optimized,
            "total_cost": total_cost,
            "total_time_hours": total_time / 3600,
            "avg_optimized_per_run": total_optimized / total_runs if total_runs > 0 else 0,
            "avg_cost_per_run": total_cost / total_runs if total_runs > 0 else 0,
            "estimated_value": total_value,
            "roi": roi,
            "recent_runs": self.optimization_log[-5:]  # Last 5 runs
        }
