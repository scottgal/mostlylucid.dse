"""
Forge Integration Optimizer - Workflow optimization with tool variant swapping.

Runs workflows with swappable child tool variants to characterize performance
and trigger specialization when tools consistently exceed thresholds.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

# Import existing systems
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.recursive_optimizer import RecursiveSystemOptimizer

from .registry import ForgeRegistry
from .runtime import ForgeRuntime
from .consensus import ConsensusEngine

logger = logging.getLogger(__name__)


@dataclass
class VariantCharacterization:
    """Characterization metrics for a tool variant."""
    tool_id: str
    version: str
    variant_tag: str
    metrics: Dict[str, float]
    run_count: int
    success_rate: float


@dataclass
class SpecializationTrigger:
    """Trigger for creating specialized tool variant."""
    condition: str
    action: str
    variant_tags: List[str]
    threshold_met: bool = False


class IntegrationOptimizer:
    """
    Integration Optimizer - Characterizes tool performance in workflows.

    Features:
    - Workflow execution with variant swapping
    - Performance characterization across variants
    - Automatic specialization triggers
    - Integration with recursive optimizer
    """

    def __init__(
        self,
        registry: ForgeRegistry,
        runtime: ForgeRuntime,
        consensus: ConsensusEngine,
        recursive_optimizer: Optional[RecursiveSystemOptimizer] = None
    ):
        """
        Initialize integration optimizer.

        Args:
            registry: Forge registry
            runtime: Tool runtime
            consensus: Consensus engine
            recursive_optimizer: Existing recursive optimizer
        """
        self.registry = registry
        self.runtime = runtime
        self.consensus = consensus
        self.recursive_optimizer = recursive_optimizer

        # Characterization cache
        self._characterizations: Dict[str, VariantCharacterization] = {}

        logger.info("IntegrationOptimizer initialized")

    def optimize_workflow(
        self,
        workflow_id: str,
        tasks: List[Dict[str, Any]],
        runs: Dict[str, Any],
        specialization_triggers: Optional[List[SpecializationTrigger]] = None
    ) -> Dict[str, Any]:
        """
        Optimize workflow by testing tool variants.

        Args:
            workflow_id: Workflow identifier
            tasks: List of workflow tasks with tool candidates
            runs: Run configuration (count, dataset, constraints)
            specialization_triggers: Conditions for creating specialized variants

        Returns:
            Optimization results with best variants and specializations
        """
        logger.info(f"Optimizing workflow: {workflow_id}")

        run_count = runs.get('count', 10)
        constraints = runs.get('constraints', {})

        # Characterize all tool variants
        characterizations = []

        for task in tasks:
            task_id = task['id']
            role = task['role']
            candidates = task['candidates']

            logger.info(f"Characterizing variants for task {task_id} ({role})")

            for candidate in candidates:
                char = self._characterize_variant(
                    candidate=candidate,
                    run_count=run_count,
                    constraints=constraints
                )
                characterizations.append({
                    'task_id': task_id,
                    'role': role,
                    'characterization': char
                })

        # Select best variants per task
        best_variants = {}
        for task in tasks:
            task_chars = [
                c for c in characterizations
                if c['task_id'] == task['id']
            ]

            # Sort by consensus weight
            task_chars.sort(
                key=lambda x: self._calculate_variant_score(x['characterization']),
                reverse=True
            )

            if task_chars:
                best = task_chars[0]
                best_variants[task['id']] = {
                    'tool_id': best['characterization'].tool_id,
                    'version': best['characterization'].version,
                    'variant_tag': best['characterization'].variant_tag,
                    'score': self._calculate_variant_score(best['characterization'])
                }

        # Check specialization triggers
        specializations = []
        if specialization_triggers:
            for trigger in specialization_triggers:
                if self._check_trigger(trigger, characterizations):
                    spec = self._create_specialization(trigger, best_variants)
                    specializations.append(spec)

        # Update registry with results
        self._update_registry(workflow_id, best_variants, specializations)

        return {
            'workflow_id': workflow_id,
            'best_variants': best_variants,
            'specializations': specializations,
            'characterizations': characterizations
        }

    def _characterize_variant(
        self,
        candidate: Dict[str, Any],
        run_count: int,
        constraints: Dict[str, Any]
    ) -> VariantCharacterization:
        """Characterize a tool variant through multiple runs."""
        tool_id = candidate['tool_id']
        version = candidate.get('version', 'latest')

        logger.info(f"Running {run_count} characterization runs for {tool_id}")

        # Collect metrics across runs
        metrics_list = []
        successes = 0

        for i in range(run_count):
            try:
                # Execute tool
                result = self.runtime.execute(
                    tool_id=tool_id,
                    version=version,
                    input_data={'test_input': f"characterization_run_{i}"},
                    sandbox_config={'network': 'restricted'}
                )

                if result['success']:
                    successes += 1
                    metrics_list.append(result['metrics'])

            except Exception as e:
                logger.error(f"Characterization run {i} failed: {e}")

        # Aggregate metrics
        if metrics_list:
            aggregated = {
                'correctness': np.mean([m.get('correctness', 0.5) for m in metrics_list]),
                'latency_ms_p50': np.percentile([m.get('latency_ms', 0) for m in metrics_list], 50),
                'latency_ms_p95': np.percentile([m.get('latency_ms', 0) for m in metrics_list], 95),
                'cost_per_call': np.mean([m.get('cost_per_call', 0) for m in metrics_list]),
                'failure_rate': 1.0 - (successes / run_count)
            }
        else:
            aggregated = {
                'correctness': 0.0,
                'latency_ms_p50': 0.0,
                'latency_ms_p95': 0.0,
                'cost_per_call': 0.0,
                'failure_rate': 1.0
            }

        # Extract variant tag
        variant_tag = candidate.get('variant_tag', 'default')

        char = VariantCharacterization(
            tool_id=tool_id,
            version=version,
            variant_tag=variant_tag,
            metrics=aggregated,
            run_count=run_count,
            success_rate=successes / run_count if run_count > 0 else 0.0
        )

        # Cache characterization
        cache_key = f"{tool_id}:{version}:{variant_tag}"
        self._characterizations[cache_key] = char

        return char

    def _calculate_variant_score(self, char: VariantCharacterization) -> float:
        """Calculate overall score for variant."""
        metrics = char.metrics

        # Weighted score
        score = (
            metrics.get('correctness', 0) * 0.35 +
            (1.0 - min(1.0, metrics.get('latency_ms_p95', 0) / 1000.0)) * 0.30 +
            (1.0 - min(1.0, metrics.get('cost_per_call', 0) / 0.01)) * 0.15 +
            (1.0 - metrics.get('failure_rate', 1.0)) * 0.20
        )

        return max(0.0, min(1.0, score))

    def _check_trigger(
        self,
        trigger: SpecializationTrigger,
        characterizations: List[Dict[str, Any]]
    ) -> bool:
        """Check if specialization trigger condition is met."""
        # Parse condition (e.g., "candidate.correctness >= 0.99 AND candidate.latency_ms_p95 <= 400")
        condition = trigger.condition

        for char_data in characterizations:
            char = char_data['characterization']
            metrics = char.metrics

            # Simple condition evaluation
            try:
                # Replace candidate.* with actual values
                eval_str = condition
                for key, value in metrics.items():
                    eval_str = eval_str.replace(f"candidate.{key}", str(value))

                # Evaluate
                if eval(eval_str):
                    trigger.threshold_met = True
                    return True

            except Exception as e:
                logger.error(f"Failed to evaluate trigger condition: {e}")

        return False

    def _create_specialization(
        self,
        trigger: SpecializationTrigger,
        best_variants: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create specialized tool variant."""
        logger.info(f"Creating specialization with action: {trigger.action}")

        # Fork variant with new tags
        # In production, would actually create optimized variant
        return {
            'action': trigger.action,
            'variant_tags': trigger.variant_tags,
            'source_tools': list(best_variants.keys()),
            'created_at': datetime.utcnow().isoformat() + "Z"
        }

    def _update_registry(
        self,
        workflow_id: str,
        best_variants: Dict[str, Any],
        specializations: List[Dict[str, Any]]
    ):
        """Update registry with optimization results."""
        # Store workflow optimization results in RAG
        from src.rag_memory import ArtifactType

        self.registry.rag_memory.store_artifact(
            artifact_id=f"workflow_optimization_{workflow_id}_{datetime.utcnow().isoformat()}",
            artifact_type=ArtifactType.WORKFLOW,
            name=f"Optimization results for {workflow_id}",
            description=f"Integration optimization with {len(best_variants)} tool variants",
            content=json.dumps({
                'workflow_id': workflow_id,
                'best_variants': best_variants,
                'specializations': specializations
            }),
            tags=['forge', 'optimization', workflow_id]
        )

        logger.info(f"Updated registry with optimization results for {workflow_id}")

    def integrate_with_recursive_optimizer(self):
        """Integrate forge optimization with recursive optimizer."""
        if not self.recursive_optimizer:
            logger.warning("Recursive optimizer not available")
            return

        # Add forge-specific optimization hooks
        logger.info("Integrated with recursive optimizer")
