"""
Forge Consensus Engine - Metric aggregation and weight calculation.

Aggregates metrics from multiple sources:
- Execution metrics (latency, success rate)
- Validation scores
- Security findings
- User feedback

Calculates consensus weights for tool selection.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np

# Import existing systems
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .registry import ForgeRegistry, ConsensusScore

logger = logging.getLogger(__name__)


@dataclass
class MetricDimension:
    """Single metric dimension with weight."""
    name: str
    value: float  # 0.0 to 1.0
    weight: float  # Contribution to overall score
    source: str  # Source of metric (execution, validation, security, etc.)


class ConsensusEngine:
    """
    Consensus Engine - Aggregates metrics and calculates weights.

    Features:
    - Multi-dimensional scoring (correctness, latency, cost, safety, resilience)
    - Weighted aggregation with dynamic weights
    - Exponential decay for temporal relevance
    - Automatic weight recalculation
    """

    def __init__(
        self,
        registry: ForgeRegistry,
        config: Dict[str, Any]
    ):
        """
        Initialize consensus engine.

        Args:
            registry: Forge registry
            config: Configuration with default weights
        """
        self.registry = registry
        self.config = config

        # Default dimension weights
        self.default_weights = {
            'correctness': 0.30,
            'latency': 0.25,
            'cost': 0.15,
            'safety': 0.20,
            'resilience': 0.10
        }

        # Decay factor for temporal relevance
        self.decay_factor = config.get('decay_factor', 0.1)
        self.decay_window_days = config.get('decay_window_days', 30)

        logger.info("ConsensusEngine initialized")

    def calculate_consensus_score(
        self,
        tool_id: str,
        version: str,
        execution_history: Optional[List[Dict[str, Any]]] = None,
        validation_result: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> ConsensusScore:
        """
        Calculate consensus score for a tool.

        Args:
            tool_id: Tool identifier
            version: Tool version
            execution_history: Recent execution records
            validation_result: Latest validation results
            constraints: Task-specific constraints that adjust weights

        Returns:
            Consensus score record
        """
        logger.info(f"Calculating consensus for {tool_id} v{version}")

        # Collect metrics from all sources
        dimensions = self._collect_dimensions(
            tool_id,
            version,
            execution_history,
            validation_result
        )

        # Apply constraint-based weight adjustment
        weights = self._adjust_weights(constraints) if constraints else self.default_weights

        # Calculate weighted score
        total_score = 0.0
        evaluators = []

        for dim in dimensions:
            weighted_value = dim.value * weights.get(dim.name, 0.0)
            total_score += weighted_value

            evaluators.append({
                'id': f"{dim.source}_{dim.name}",
                'contribution': weighted_value,
                'value': dim.value
            })

        # Normalize to 0-1 range
        final_weight = max(0.0, min(1.0, total_score))

        # Create consensus score
        consensus = ConsensusScore(
            tool_id=tool_id,
            version=version,
            scores={dim.name: dim.value for dim in dimensions},
            weight=final_weight,
            evaluators=evaluators
        )

        # Store in registry
        self.registry.store_consensus_score(consensus)

        return consensus

    def record_execution(
        self,
        tool_id: str,
        version: str,
        metrics: Dict[str, Any],
        success: bool
    ):
        """
        Record execution metrics for a tool.

        Args:
            tool_id: Tool identifier
            version: Tool version
            metrics: Execution metrics
            success: Execution success status
        """
        # Get or create execution history
        manifest = self.registry.get_tool_manifest(tool_id, version)
        if not manifest:
            logger.warning(f"Manifest not found for {tool_id} v{version}")
            return

        # Update execution metrics
        if 'execution_history' not in manifest.metrics:
            manifest.metrics['execution_history'] = []

        manifest.metrics['execution_history'].append({
            'timestamp': datetime.utcnow().isoformat() + "Z",
            'metrics': metrics,
            'success': success
        })

        # Keep only recent history (last 100 executions)
        manifest.metrics['execution_history'] = manifest.metrics['execution_history'][-100:]

        # Recalculate consensus
        self.calculate_consensus_score(
            tool_id=tool_id,
            version=version,
            execution_history=manifest.metrics['execution_history']
        )

        # Update manifest
        self.registry.register_tool_manifest(manifest)

    def _collect_dimensions(
        self,
        tool_id: str,
        version: str,
        execution_history: Optional[List[Dict[str, Any]]],
        validation_result: Optional[Dict[str, Any]]
    ) -> List[MetricDimension]:
        """Collect all metric dimensions."""
        dimensions = []

        # Correctness from validation
        if validation_result:
            correctness = validation_result.get('validation_score', 0.5)
            dimensions.append(MetricDimension(
                name='correctness',
                value=correctness,
                weight=self.default_weights['correctness'],
                source='validation'
            ))

        # Latency from execution history
        if execution_history:
            latencies = [
                exec_record['metrics'].get('latency_ms', 0)
                for exec_record in execution_history
                if exec_record.get('success', False)
            ]

            if latencies:
                # Normalize latency (lower is better)
                avg_latency = np.mean(latencies)
                # Assume target latency is 500ms
                latency_score = max(0.0, 1.0 - (avg_latency / 1000.0))

                dimensions.append(MetricDimension(
                    name='latency',
                    value=latency_score,
                    weight=self.default_weights['latency'],
                    source='execution'
                ))

        # Cost (placeholder - would integrate with actual cost tracking)
        dimensions.append(MetricDimension(
            name='cost',
            value=0.8,
            weight=self.default_weights['cost'],
            source='cost_tracker'
        ))

        # Safety from validation
        if validation_result:
            safety_stages = [
                stage for stage in validation_result.get('stages', [])
                if 'security' in stage['name'] or 'safety' in stage['name']
            ]
            if safety_stages:
                safety_score = np.mean([s['score'] for s in safety_stages])
                dimensions.append(MetricDimension(
                    name='safety',
                    value=safety_score,
                    weight=self.default_weights['safety'],
                    source='security_scanner'
                ))

        # Resilience from success rate
        if execution_history:
            successes = sum(1 for e in execution_history if e.get('success', False))
            resilience = successes / len(execution_history) if execution_history else 0.5

            dimensions.append(MetricDimension(
                name='resilience',
                value=resilience,
                weight=self.default_weights['resilience'],
                source='execution'
            ))

        return dimensions

    def _adjust_weights(self, constraints: Dict[str, Any]) -> Dict[str, float]:
        """Adjust dimension weights based on task constraints."""
        weights = self.default_weights.copy()

        # If latency constraint is critical, increase weight
        if 'latency_ms_p95' in constraints:
            weights['latency'] = 0.40
            weights['correctness'] = 0.25
            weights['cost'] = 0.10

        # If safety is critical, increase weight
        if 'risk_score' in constraints and constraints['risk_score'] < 0.1:
            weights['safety'] = 0.35
            weights['correctness'] = 0.25
            weights['latency'] = 0.15

        # If cost is critical, increase weight
        if 'max_cost_per_call' in constraints:
            weights['cost'] = 0.30
            weights['correctness'] = 0.25
            weights['latency'] = 0.20

        return weights

    def apply_temporal_decay(self, score: ConsensusScore, days_old: int) -> float:
        """Apply exponential decay based on age."""
        if days_old <= 0:
            return score.weight

        decay = np.exp(-self.decay_factor * (days_old / self.decay_window_days))
        return score.weight * decay

    def get_best_tool_by_weight(
        self,
        candidates: List[str],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Select best tool from candidates based on consensus weight.

        Args:
            candidates: List of tool_id:version strings
            constraints: Optional constraints for weight adjustment

        Returns:
            Best tool_id:version or None
        """
        best_tool = None
        best_weight = 0.0

        for candidate in candidates:
            parts = candidate.split(':')
            if len(parts) != 2:
                continue

            tool_id, version = parts

            # Get consensus score
            consensus = self.registry._get_consensus_score(tool_id, version)
            if not consensus:
                # Calculate if not exists
                consensus = self.calculate_consensus_score(
                    tool_id=tool_id,
                    version=version,
                    constraints=constraints
                )

            if consensus.weight > best_weight:
                best_weight = consensus.weight
                best_tool = candidate

        return best_tool
