"""
RAG Cluster Optimizer - Iterative Self-Optimization Loop

Iterative self-optimization loop that makes the whole thing alive. Instead of just
picking one "best" version, the system moves outward from the core function, testing
alternates, folding in their performance data, and converging toward a fitter
canonical artifact.

🧠 Iterative Optimization Process:
- Core function anchor
  - Start with the current "best" implementation (canonical artifact).
  - Treat it as the root of the optimization tree.

- Alternate exploration
  - Pull all close variants (≥0.96 similarity cluster).
  - Extract semantic deltas (algorithm tweaks, error handling, refactors).
  - Each alternate carries perf data + usage stats.

- Iteration loop
  - Step 1: Generate candidate by combining alternates + perf insights.
  - Step 2: Validate candidate (functional tests, perf benchmarks, mutation tests).
  - Step 3: Compare fitness score against cluster median and canonical.
  - Step 4: If fitter, promote candidate to new canonical; archive weaker variants.
  - Step 5: Repeat outward — expand to next layer of alternates, re‑run loop.

- Self‑optimisation
  - Over time, the library converges toward high‑fitness implementations.
  - Weak or unused branches are archived, but lineage is preserved.
  - The system learns patterns: e.g., "error handling improvements often reduce
    latency spikes" or "hack‑style obfuscations correlate with regressions."

⚡ Example Flow:
- Core function: Cron parser v1.
- Alternates: v1.1 (better error handling), v1.2 (faster regex), v1.3 (memory‑optimized).
- Iteration:
  - Generate v2 by combining regex speed + error handling robustness.
  - Validate → coverage +5%, latency −12%.
  - Promote v2 as canonical.
  - Archive v1.x variants with lineage pointers.
- Next iteration: Explore v2's cluster for further refinements.

🧭 Guild Analogy:
It's like a guild master refining a ritual: start with the core chant, then test
variations from apprentices. Each cycle, the master keeps the strongest elements,
discards the weak, and the ritual evolves. Over time, the guild's library becomes
a living lineage of ever‑stronger spells.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple
import numpy as np
from collections import defaultdict
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """RAG artifact node types."""
    PLAN = "plan"
    FUNCTION = "function"
    SUB_WORKFLOW = "sub_workflow"
    WORKFLOW = "workflow"
    PROMPT = "prompt"
    PATTERN = "pattern"


@dataclass
class TrimmingPolicy:
    """
    Policy for trimming variants based on 'distance from fittest' and usage.

    Logic:
    - High performance + low usage = worth evaluating (keep)
    - Poor performance + far distance from fittest = prune
    - Can be overridden in config for each node type
    """
    node_type: NodeType

    # Distance thresholds (0.0-1.0, where 1.0 = identical to fittest)
    min_similarity_to_fittest: float = 0.70  # Prune if < this distance
    preserve_high_perf_threshold: float = 0.85  # Keep high-perf variants even if unused

    # Usage thresholds
    min_usage_count: int = 1  # Minimum usage to avoid pruning
    never_used_grace_period_days: int = 30  # Keep unused variants for N days

    # Fitness thresholds
    min_fitness_absolute: float = 0.50  # Prune variants below this fitness
    max_distance_from_fittest: float = 0.30  # Max fitness gap (0.0-1.0)

    # Special rules
    always_keep_canonical: bool = True
    keep_high_coverage_variants: bool = True  # Keep variants with >90% coverage

    preserve_lineage_endpoints: bool = True  # Keep leaf nodes in lineage tree

    def apply_evolutionary_adjustments(self, adjustments: Dict[str, Any]) -> None:
        """
        Apply evolutionary pressure adjustments from PressureManager.

        Args:
            adjustments: Dict from PressureManager.get_evolutionary_adjustments()
        """
        self.max_distance_from_fittest = adjustments.get("max_distance_from_fittest", self.max_distance_from_fittest)

        logger.debug(f"Applied evolutionary adjustments to {self.node_type.value} trimming policy: "
                    f"max_distance={self.max_distance_from_fittest:.2f}")

    def should_prune(
        self,
        variant: 'ArtifactVariant',
        fittest_variant: 'ArtifactVariant',
        cluster: 'OptimizationCluster'
    ) -> Tuple[bool, str]:
        """
        Determine if a variant should be pruned.

        Returns:
            (should_prune, reason)
        """
        # Never prune canonical
        if self.always_keep_canonical and variant.status == VariantStatus.CANONICAL:
            return False, "Canonical variant"

        # Calculate metrics
        variant_fitness = variant.performance.fitness_score()
        fittest_fitness = fittest_variant.performance.fitness_score()
        fitness_distance = abs(fittest_fitness - variant_fitness)
        similarity = variant.similarity_to(fittest_variant)

        days_since_creation = (datetime.now() - variant.created_at).days
        is_never_used = variant.performance.usage_count == 0

        # Rule 1: Poor performance + far distance = PRUNE
        if (variant_fitness < self.min_fitness_absolute and
            fitness_distance > self.max_distance_from_fittest):
            return True, f"Poor fitness ({variant_fitness:.2f}) and far from fittest ({fitness_distance:.2f})"

        # Rule 2: Low similarity to fittest = PRUNE (unless high performance)
        if similarity < self.min_similarity_to_fittest:
            if variant_fitness >= self.preserve_high_perf_threshold:
                return False, f"Low similarity but high fitness ({variant_fitness:.2f})"
            return True, f"Low similarity to fittest ({similarity:.2f})"

        # Rule 3: Never used + past grace period = PRUNE (unless high performance)
        if is_never_used and days_since_creation > self.never_used_grace_period_days:
            if variant_fitness >= self.preserve_high_perf_threshold:
                return False, f"Never used but high fitness ({variant_fitness:.2f}) - worth evaluating"
            return True, f"Never used after {days_since_creation} days"

        # Rule 4: High coverage variants = KEEP
        if self.keep_high_coverage_variants and variant.performance.test_coverage >= 0.90:
            return False, f"High test coverage ({variant.performance.test_coverage:.2f})"

        # Rule 5: Lineage endpoints = KEEP (for historical record)
        if self.preserve_lineage_endpoints and len(variant.children_ids) == 0:
            return False, "Lineage endpoint (leaf node)"

        # Rule 6: Good fitness and some usage = KEEP
        if (variant_fitness >= self.min_fitness_absolute and
            variant.performance.usage_count >= self.min_usage_count):
            return False, f"Acceptable fitness ({variant_fitness:.2f}) with usage ({variant.performance.usage_count})"

        # Default: KEEP (conservative approach)
        return False, "No pruning criteria met"


@dataclass
class NodeTypeOptimizerConfig:
    """Configuration for a node-type-specific optimizer."""
    node_type: NodeType
    enabled: bool = True

    # Optimization parameters
    similarity_threshold: float = 0.96
    max_iterations: int = 10
    fitness_improvement_threshold: float = 0.05
    strategy: OptimizationStrategy = None  # Will be set after OptimizationStrategy is defined

    # Trimming policy
    trimming_policy: Optional[TrimmingPolicy] = None

    # Node-type-specific weights for fitness calculation
    fitness_weights: Optional[Dict[str, float]] = None

    # Scheduling
    optimization_frequency: str = "daily"  # "hourly", "daily", "weekly", "manual"
    priority: int = 5  # 1-10, higher = more important

    def __post_init__(self):
        """Set defaults after initialization."""
        if self.strategy is None:
            self.strategy = OptimizationStrategy.BEST_OF_BREED

        if self.trimming_policy is None:
            self.trimming_policy = TrimmingPolicy(node_type=self.node_type)

        if self.fitness_weights is None:
            # Default weights vary by node type
            self.fitness_weights = self._get_default_weights()

    def _get_default_weights(self) -> Dict[str, float]:
        """Get default fitness weights for this node type."""
        # Different node types prioritize different metrics
        if self.node_type == NodeType.FUNCTION:
            return {
                'latency': 0.30,
                'memory': 0.20,
                'cpu': 0.15,
                'success_rate': 0.25,
                'coverage': 0.10
            }
        elif self.node_type == NodeType.WORKFLOW:
            return {
                'latency': 0.20,
                'memory': 0.10,
                'cpu': 0.10,
                'success_rate': 0.40,
                'coverage': 0.20
            }
        elif self.node_type == NodeType.PROMPT:
            return {
                'latency': 0.15,
                'memory': 0.05,
                'cpu': 0.05,
                'success_rate': 0.50,
                'coverage': 0.25
            }
        else:
            # Default balanced weights
            return {
                'latency': 0.25,
                'memory': 0.15,
                'cpu': 0.10,
                'success_rate': 0.30,
                'coverage': 0.20
            }

    def apply_evolutionary_adjustments(self, adjustments: Dict[str, Any]) -> None:
        """
        Apply evolutionary pressure adjustments from PressureManager.

        Args:
            adjustments: Dict from PressureManager.get_evolutionary_adjustments()
        """
        self.similarity_threshold = adjustments.get("similarity_threshold", self.similarity_threshold)

        # Apply adjustments to trimming policy if it exists
        if self.trimming_policy:
            self.trimming_policy.apply_evolutionary_adjustments(adjustments)

        logger.debug(f"Applied evolutionary adjustments to {self.node_type.value} optimizer config: "
                    f"similarity={self.similarity_threshold:.2f}")


class OptimizationStrategy(Enum):
    """Strategy for combining alternates into candidates."""
    BEST_OF_BREED = "best_of_breed"  # Take best features from each alternate
    INCREMENTAL = "incremental"  # Small changes from canonical
    RADICAL = "radical"  # Large experimental changes
    HYBRID = "hybrid"  # Mix of strategies


class VariantStatus(Enum):
    """Lifecycle status of a variant."""
    CANONICAL = "canonical"  # Current best
    ACTIVE = "active"  # In cluster, viable
    ARCHIVED = "archived"  # Preserved but not active
    DEPRECATED = "deprecated"  # Marked for removal


@dataclass
class PerformanceMetrics:
    """Performance data for an artifact variant."""
    latency_ms: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0
    usage_count: int = 0
    test_coverage: float = 0.0

    def fitness_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate composite fitness score (0.0-1.0).

        Higher is better. Normalizes metrics and applies weights.
        """
        if weights is None:
            weights = {
                'latency': 0.25,
                'memory': 0.15,
                'cpu': 0.10,
                'success_rate': 0.30,
                'coverage': 0.20
            }

        # Normalize metrics (higher is better)
        latency_score = max(0, 1.0 - (self.latency_ms / 1000.0))  # Assume 1s baseline
        memory_score = max(0, 1.0 - (self.memory_mb / 100.0))  # Assume 100MB baseline
        cpu_score = max(0, 1.0 - (self.cpu_percent / 100.0))
        success_score = self.success_rate
        coverage_score = self.test_coverage

        fitness = (
            weights['latency'] * latency_score +
            weights['memory'] * memory_score +
            weights['cpu'] * cpu_score +
            weights['success_rate'] * success_score +
            weights['coverage'] * coverage_score
        )

        return max(0.0, min(1.0, fitness))


@dataclass
class SemanticDelta:
    """Semantic difference between variants."""
    delta_type: str  # e.g., 'algorithm', 'error_handling', 'refactor'
    description: str
    impact_areas: List[str]
    estimated_benefit: float  # 0.0-1.0
    risk_level: float  # 0.0-1.0


@dataclass
class ArtifactVariant:
    """A specific version/variant of an artifact."""
    variant_id: str
    artifact_id: str
    version: str
    content: str
    embedding: Optional[np.ndarray] = None
    status: VariantStatus = VariantStatus.ACTIVE
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    created_at: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None  # Lineage tracking
    children_ids: List[str] = field(default_factory=list)
    semantic_deltas: List[SemanticDelta] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def similarity_to(self, other: 'ArtifactVariant') -> float:
        """Calculate cosine similarity to another variant."""
        if self.embedding is None or other.embedding is None:
            return 0.0

        dot_product = np.dot(self.embedding, other.embedding)
        norm_a = np.linalg.norm(self.embedding)
        norm_b = np.linalg.norm(other.embedding)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))


@dataclass
class OptimizationCluster:
    """A cluster of similar artifact variants."""
    cluster_id: str
    canonical_variant: ArtifactVariant
    alternates: List[ArtifactVariant] = field(default_factory=list)
    similarity_threshold: float = 0.96
    median_fitness: float = 0.0
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    learned_patterns: Dict[str, Any] = field(default_factory=dict)

    def get_variants_by_similarity(self) -> List[ArtifactVariant]:
        """Get all variants sorted by similarity to canonical."""
        variants_with_sim = [
            (alt, self.canonical_variant.similarity_to(alt))
            for alt in self.alternates
        ]
        variants_with_sim.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in variants_with_sim if _ >= self.similarity_threshold]

    def calculate_median_fitness(self) -> float:
        """Calculate median fitness across all cluster variants."""
        all_variants = [self.canonical_variant] + self.alternates
        fitness_scores = [v.performance.fitness_score() for v in all_variants]
        if not fitness_scores:
            return 0.0
        return float(np.median(fitness_scores))

    def extract_semantic_deltas(self) -> List[SemanticDelta]:
        """Extract semantic differences from all alternates."""
        all_deltas = []
        for alt in self.alternates:
            all_deltas.extend(alt.semantic_deltas)

        # Deduplicate and prioritize by estimated benefit
        unique_deltas = {}
        for delta in all_deltas:
            key = f"{delta.delta_type}:{delta.description}"
            if key not in unique_deltas or delta.estimated_benefit > unique_deltas[key].estimated_benefit:
                unique_deltas[key] = delta

        return sorted(unique_deltas.values(), key=lambda d: d.estimated_benefit, reverse=True)


@dataclass
class ValidationResult:
    """Result of validating a candidate variant."""
    passed: bool
    fitness_score: float
    performance: PerformanceMetrics
    test_results: Dict[str, Any] = field(default_factory=dict)
    benchmark_results: Dict[str, Any] = field(default_factory=dict)
    mutation_test_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class OptimizationIteration:
    """Single iteration of the optimization loop."""
    iteration_number: int
    candidate: ArtifactVariant
    validation_result: ValidationResult
    promoted: bool
    archived_variants: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class RAGClusterOptimizer:
    """
    Iterative self-optimization loop for artifact clusters.

    Treats the canonical artifact as the root of an optimization tree,
    explores variants, generates candidates, validates them, and promotes
    fitter implementations while archiving weaker ones.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.96,
        max_iterations: int = 10,
        fitness_improvement_threshold: float = 0.05,
        strategy: OptimizationStrategy = OptimizationStrategy.BEST_OF_BREED
    ):
        self.similarity_threshold = similarity_threshold
        self.max_iterations = max_iterations
        self.fitness_improvement_threshold = fitness_improvement_threshold
        self.strategy = strategy
        self.learned_patterns = defaultdict(list)

    def optimize_cluster(
        self,
        cluster: OptimizationCluster,
        validator_fn: Optional[callable] = None
    ) -> List[OptimizationIteration]:
        """
        Run the iterative optimization loop on a cluster.

        Args:
            cluster: The cluster to optimize
            validator_fn: Optional function to validate candidates
                         Should return ValidationResult

        Returns:
            List of optimization iterations performed
        """
        logger.info(f"Starting cluster optimization for {cluster.cluster_id}")
        iterations = []

        for i in range(self.max_iterations):
            logger.info(f"Iteration {i+1}/{self.max_iterations}")

            # Step 1: Generate candidate
            candidate = self._generate_candidate(cluster, i)
            if candidate is None:
                logger.info("No viable candidate generated, stopping")
                break

            # Step 2: Validate candidate
            validation = self._validate_candidate(candidate, validator_fn)

            # Step 3: Compare fitness
            canonical_fitness = cluster.canonical_variant.performance.fitness_score()
            median_fitness = cluster.calculate_median_fitness()
            candidate_fitness = validation.fitness_score

            logger.info(f"Fitness scores - Canonical: {canonical_fitness:.3f}, "
                       f"Median: {median_fitness:.3f}, Candidate: {candidate_fitness:.3f}")

            # Step 4: Promote if fitter
            promoted = False
            archived = []

            if candidate_fitness > canonical_fitness + self.fitness_improvement_threshold:
                logger.info(f"Promoting candidate (improvement: {candidate_fitness - canonical_fitness:.3f})")

                # Archive old canonical
                old_canonical = cluster.canonical_variant
                old_canonical.status = VariantStatus.ARCHIVED
                archived.append(old_canonical.variant_id)

                # Promote candidate
                candidate.status = VariantStatus.CANONICAL
                candidate.parent_id = old_canonical.variant_id
                old_canonical.children_ids.append(candidate.variant_id)

                cluster.canonical_variant = candidate
                promoted = True

                # Archive weak variants
                for alt in cluster.alternates[:]:
                    alt_fitness = alt.performance.fitness_score()
                    if alt_fitness < candidate_fitness - 0.1:
                        alt.status = VariantStatus.ARCHIVED
                        cluster.alternates.remove(alt)
                        archived.append(alt.variant_id)

                # Learn patterns from successful promotion
                self._learn_from_promotion(cluster, candidate, old_canonical)

            # Record iteration
            iteration = OptimizationIteration(
                iteration_number=i + 1,
                candidate=candidate,
                validation_result=validation,
                promoted=promoted,
                archived_variants=archived,
                insights=self._generate_insights(cluster, validation, promoted)
            )
            iterations.append(iteration)
            cluster.optimization_history.append({
                'iteration': i + 1,
                'promoted': promoted,
                'fitness': candidate_fitness,
                'timestamp': iteration.timestamp.isoformat()
            })

            # Step 5: Expand to next layer if promoted
            if not promoted:
                logger.info("No improvement, stopping iterations")
                break

        # Update cluster median
        cluster.median_fitness = cluster.calculate_median_fitness()

        logger.info(f"Optimization complete. {len(iterations)} iterations, "
                   f"{sum(1 for it in iterations if it.promoted)} promotions")

        return iterations

    def _generate_candidate(
        self,
        cluster: OptimizationCluster,
        iteration: int
    ) -> Optional[ArtifactVariant]:
        """
        Generate a candidate by combining alternates + perf insights.

        Strategy depends on self.strategy and iteration number.
        """
        logger.info(f"Generating candidate using strategy: {self.strategy.value}")

        # Get high-similarity alternates
        similar_variants = cluster.get_variants_by_similarity()
        if not similar_variants:
            logger.warning("No similar variants found")
            return None

        # Extract semantic deltas
        deltas = cluster.extract_semantic_deltas()

        # Apply learned patterns
        prioritized_deltas = self._prioritize_deltas_with_learning(deltas)

        # Generate candidate based on strategy
        if self.strategy == OptimizationStrategy.BEST_OF_BREED:
            return self._generate_best_of_breed(cluster, similar_variants, prioritized_deltas)
        elif self.strategy == OptimizationStrategy.INCREMENTAL:
            return self._generate_incremental(cluster, prioritized_deltas)
        elif self.strategy == OptimizationStrategy.RADICAL:
            return self._generate_radical(cluster, similar_variants, prioritized_deltas)
        else:  # HYBRID
            # Alternate between strategies based on iteration
            if iteration % 3 == 0:
                return self._generate_best_of_breed(cluster, similar_variants, prioritized_deltas)
            elif iteration % 3 == 1:
                return self._generate_incremental(cluster, prioritized_deltas)
            else:
                return self._generate_radical(cluster, similar_variants, prioritized_deltas)

    def _generate_best_of_breed(
        self,
        cluster: OptimizationCluster,
        variants: List[ArtifactVariant],
        deltas: List[SemanticDelta]
    ) -> ArtifactVariant:
        """Generate candidate by combining best features from alternates."""
        # Find best variant for each performance metric
        best_latency = min(variants, key=lambda v: v.performance.latency_ms)
        best_memory = min(variants, key=lambda v: v.performance.memory_mb)
        best_success = max(variants, key=lambda v: v.performance.success_rate)
        best_coverage = max(variants, key=lambda v: v.performance.test_coverage)

        # Create candidate variant
        candidate = ArtifactVariant(
            variant_id=f"{cluster.cluster_id}_candidate_{datetime.now().timestamp()}",
            artifact_id=cluster.canonical_variant.artifact_id,
            version=f"{cluster.canonical_variant.version}_optimized",
            content=f"# Optimized variant combining best features\n{cluster.canonical_variant.content}",
            parent_id=cluster.canonical_variant.variant_id,
            metadata={
                'strategy': 'best_of_breed',
                'source_variants': [v.variant_id for v in [best_latency, best_memory, best_success, best_coverage]],
                'applied_deltas': [d.description for d in deltas[:3]]
            }
        )

        # Estimate performance (would be measured in validation)
        candidate.performance = PerformanceMetrics(
            latency_ms=best_latency.performance.latency_ms * 0.95,
            memory_mb=best_memory.performance.memory_mb * 0.95,
            success_rate=min(1.0, best_success.performance.success_rate * 1.02),
            test_coverage=min(1.0, best_coverage.performance.test_coverage * 1.02)
        )

        # Add semantic deltas from top improvements
        candidate.semantic_deltas = deltas[:3]

        return candidate

    def _generate_incremental(
        self,
        cluster: OptimizationCluster,
        deltas: List[SemanticDelta]
    ) -> ArtifactVariant:
        """Generate candidate with small incremental changes from canonical."""
        # Take top delta with lowest risk
        safe_deltas = [d for d in deltas if d.risk_level < 0.3]
        if not safe_deltas:
            safe_deltas = deltas[:1]

        top_delta = safe_deltas[0] if safe_deltas else None

        candidate = ArtifactVariant(
            variant_id=f"{cluster.cluster_id}_candidate_{datetime.now().timestamp()}",
            artifact_id=cluster.canonical_variant.artifact_id,
            version=f"{cluster.canonical_variant.version}_incremental",
            content=f"# Incremental optimization\n{cluster.canonical_variant.content}",
            parent_id=cluster.canonical_variant.variant_id,
            metadata={
                'strategy': 'incremental',
                'applied_delta': top_delta.description if top_delta else None
            }
        )

        # Small performance improvement
        canonical_perf = cluster.canonical_variant.performance
        candidate.performance = PerformanceMetrics(
            latency_ms=canonical_perf.latency_ms * 0.98,
            memory_mb=canonical_perf.memory_mb * 0.99,
            success_rate=min(1.0, canonical_perf.success_rate * 1.01),
            test_coverage=min(1.0, canonical_perf.test_coverage * 1.01)
        )

        if top_delta:
            candidate.semantic_deltas = [top_delta]

        return candidate

    def _generate_radical(
        self,
        cluster: OptimizationCluster,
        variants: List[ArtifactVariant],
        deltas: List[SemanticDelta]
    ) -> ArtifactVariant:
        """Generate candidate with experimental/radical changes."""
        # Take high-benefit, high-risk deltas
        radical_deltas = [d for d in deltas if d.estimated_benefit > 0.7]
        if not radical_deltas:
            radical_deltas = deltas[:2]

        candidate = ArtifactVariant(
            variant_id=f"{cluster.cluster_id}_candidate_{datetime.now().timestamp()}",
            artifact_id=cluster.canonical_variant.artifact_id,
            version=f"{cluster.canonical_variant.version}_radical",
            content=f"# Radical optimization experiment\n{cluster.canonical_variant.content}",
            parent_id=cluster.canonical_variant.variant_id,
            metadata={
                'strategy': 'radical',
                'applied_deltas': [d.description for d in radical_deltas]
            }
        )

        # Higher variance in performance (could be much better or worse)
        canonical_perf = cluster.canonical_variant.performance
        improvement_factor = np.random.uniform(0.85, 1.15)

        candidate.performance = PerformanceMetrics(
            latency_ms=canonical_perf.latency_ms * improvement_factor,
            memory_mb=canonical_perf.memory_mb * improvement_factor,
            success_rate=max(0.5, min(1.0, canonical_perf.success_rate * improvement_factor)),
            test_coverage=max(0.5, min(1.0, canonical_perf.test_coverage * improvement_factor))
        )

        candidate.semantic_deltas = radical_deltas

        return candidate

    def _validate_candidate(
        self,
        candidate: ArtifactVariant,
        validator_fn: Optional[callable] = None
    ) -> ValidationResult:
        """
        Validate candidate through tests, benchmarks, and mutation tests.

        If validator_fn is provided, use it. Otherwise, use default validation.
        """
        if validator_fn is not None:
            try:
                return validator_fn(candidate)
            except Exception as e:
                logger.error(f"Validator function failed: {e}")
                return ValidationResult(
                    passed=False,
                    fitness_score=0.0,
                    performance=candidate.performance,
                    errors=[str(e)]
                )

        # Default validation (simplified)
        logger.info("Running default validation")

        # Simulate validation
        test_results = {
            'unit_tests': {'passed': True, 'coverage': candidate.performance.test_coverage},
            'integration_tests': {'passed': True},
            'functional_tests': {'passed': candidate.performance.success_rate >= 0.9}
        }

        benchmark_results = {
            'latency_ms': candidate.performance.latency_ms,
            'memory_mb': candidate.performance.memory_mb,
            'cpu_percent': candidate.performance.cpu_percent
        }

        mutation_results = {
            'mutation_score': 0.85,
            'killed_mutants': 85,
            'survived_mutants': 15
        }

        all_passed = all(
            result.get('passed', True) for result in test_results.values()
        )

        fitness = candidate.performance.fitness_score()

        return ValidationResult(
            passed=all_passed,
            fitness_score=fitness,
            performance=candidate.performance,
            test_results=test_results,
            benchmark_results=benchmark_results,
            mutation_test_results=mutation_results,
            warnings=[] if all_passed else ["Some tests failed"]
        )

    def _prioritize_deltas_with_learning(
        self,
        deltas: List[SemanticDelta]
    ) -> List[SemanticDelta]:
        """Apply learned patterns to prioritize deltas."""
        # Check learned patterns
        for pattern_type, pattern_data in self.learned_patterns.items():
            for delta in deltas:
                if delta.delta_type == pattern_type:
                    # Boost benefit based on historical success
                    avg_improvement = np.mean([p['improvement'] for p in pattern_data])
                    delta.estimated_benefit = min(1.0, delta.estimated_benefit * (1 + avg_improvement))

        # Re-sort by estimated benefit
        return sorted(deltas, key=lambda d: d.estimated_benefit, reverse=True)

    def _learn_from_promotion(
        self,
        cluster: OptimizationCluster,
        new_canonical: ArtifactVariant,
        old_canonical: ArtifactVariant
    ) -> None:
        """Learn patterns from successful promotions."""
        improvement = (
            new_canonical.performance.fitness_score() -
            old_canonical.performance.fitness_score()
        )

        # Record patterns
        for delta in new_canonical.semantic_deltas:
            self.learned_patterns[delta.delta_type].append({
                'improvement': improvement,
                'description': delta.description,
                'cluster_id': cluster.cluster_id,
                'timestamp': datetime.now().isoformat()
            })

        # Add to cluster's learned patterns
        cluster.learned_patterns[datetime.now().isoformat()] = {
            'delta_types': [d.delta_type for d in new_canonical.semantic_deltas],
            'improvement': improvement,
            'strategy': new_canonical.metadata.get('strategy')
        }

        logger.info(f"Learned pattern: {new_canonical.semantic_deltas[0].delta_type if new_canonical.semantic_deltas else 'unknown'} "
                   f"led to {improvement:.3f} improvement")

    def _generate_insights(
        self,
        cluster: OptimizationCluster,
        validation: ValidationResult,
        promoted: bool
    ) -> List[str]:
        """Generate insights from iteration results."""
        insights = []

        if promoted:
            insights.append("Candidate promoted to canonical - significant improvement detected")
        else:
            insights.append("Candidate not promoted - insufficient improvement")

        # Check learned patterns
        if len(self.learned_patterns.get('error_handling', [])) > 3:
            avg_improvement = np.mean([
                p['improvement'] for p in self.learned_patterns['error_handling']
            ])
            if avg_improvement > 0.05:
                insights.append(
                    f"Pattern detected: error_handling improvements correlate with "
                    f"{avg_improvement:.1%} average fitness gain"
                )

        # Performance insights
        if validation.performance.latency_ms < cluster.canonical_variant.performance.latency_ms:
            reduction = (
                cluster.canonical_variant.performance.latency_ms -
                validation.performance.latency_ms
            )
            insights.append(f"Latency reduced by {reduction:.1f}ms")

        if validation.performance.test_coverage > cluster.canonical_variant.performance.test_coverage:
            improvement = (
                validation.performance.test_coverage -
                cluster.canonical_variant.performance.test_coverage
            )
            insights.append(f"Test coverage improved by {improvement:.1%}")

        return insights

    def get_optimization_report(
        self,
        cluster: OptimizationCluster,
        iterations: List[OptimizationIteration]
    ) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        if not iterations:
            return {
                'cluster_id': cluster.cluster_id,
                'status': 'no_iterations',
                'message': 'No optimization iterations performed'
            }

        total_iterations = len(iterations)
        total_promotions = sum(1 for it in iterations if it.promoted)
        total_archived = sum(len(it.archived_variants) for it in iterations)

        initial_fitness = iterations[0].validation_result.fitness_score
        final_fitness = cluster.canonical_variant.performance.fitness_score()
        total_improvement = final_fitness - initial_fitness

        return {
            'cluster_id': cluster.cluster_id,
            'status': 'completed',
            'summary': {
                'total_iterations': total_iterations,
                'total_promotions': total_promotions,
                'total_archived': total_archived,
                'initial_fitness': round(initial_fitness, 3),
                'final_fitness': round(final_fitness, 3),
                'total_improvement': round(total_improvement, 3),
                'improvement_percentage': round(total_improvement / max(initial_fitness, 0.01) * 100, 1)
            },
            'iterations': [
                {
                    'iteration': it.iteration_number,
                    'promoted': it.promoted,
                    'fitness': round(it.validation_result.fitness_score, 3),
                    'insights': it.insights,
                    'timestamp': it.timestamp.isoformat()
                }
                for it in iterations
            ],
            'learned_patterns': dict(self.learned_patterns),
            'canonical_variant': {
                'variant_id': cluster.canonical_variant.variant_id,
                'version': cluster.canonical_variant.version,
                'fitness': round(cluster.canonical_variant.performance.fitness_score(), 3),
                'performance': {
                    'latency_ms': round(cluster.canonical_variant.performance.latency_ms, 2),
                    'memory_mb': round(cluster.canonical_variant.performance.memory_mb, 2),
                    'success_rate': round(cluster.canonical_variant.performance.success_rate, 3),
                    'test_coverage': round(cluster.canonical_variant.performance.test_coverage, 3)
                }
            },
            'cluster_stats': {
                'total_variants': len(cluster.alternates) + 1,
                'active_variants': sum(1 for v in cluster.alternates if v.status == VariantStatus.ACTIVE),
                'archived_variants': sum(1 for v in cluster.alternates if v.status == VariantStatus.ARCHIVED),
                'median_fitness': round(cluster.median_fitness, 3)
            }
        }

    def trim_cluster(
        self,
        cluster: OptimizationCluster,
        trimming_policy: Optional[TrimmingPolicy] = None
    ) -> Dict[str, Any]:
        """
        Apply trimming policy to remove weak/unused variants.

        Returns report of pruning actions.
        """
        if trimming_policy is None:
            # Use default policy
            trimming_policy = TrimmingPolicy(node_type=NodeType.FUNCTION)

        # Find fittest variant in cluster
        all_variants = [cluster.canonical_variant] + cluster.alternates
        fittest_variant = max(
            all_variants,
            key=lambda v: v.performance.fitness_score()
        )

        pruned = []
        kept = []

        for variant in cluster.alternates[:]:  # Copy list to allow removal
            should_prune, reason = trimming_policy.should_prune(
                variant, fittest_variant, cluster
            )

            if should_prune:
                variant.status = VariantStatus.DEPRECATED
                cluster.alternates.remove(variant)
                pruned.append({
                    'variant_id': variant.variant_id,
                    'reason': reason,
                    'fitness': variant.performance.fitness_score(),
                    'usage_count': variant.performance.usage_count
                })
                logger.info(f"Pruned variant {variant.variant_id}: {reason}")
            else:
                kept.append({
                    'variant_id': variant.variant_id,
                    'reason': reason,
                    'fitness': variant.performance.fitness_score(),
                    'usage_count': variant.performance.usage_count
                })

        return {
            'cluster_id': cluster.cluster_id,
            'fittest_variant': fittest_variant.variant_id,
            'fittest_fitness': fittest_variant.performance.fitness_score(),
            'pruned_count': len(pruned),
            'kept_count': len(kept),
            'pruned_variants': pruned,
            'kept_variants': kept,
            'remaining_alternates': len(cluster.alternates)
        }


class NodeTypeOptimizer:
    """
    Node-type-specific optimizer with custom policies.

    Each RAG node type (PLAN, FUNCTION, WORKFLOW, etc.) can have its own:
    - Optimization strategy
    - Fitness weights
    - Trimming policy
    - Iteration limits
    """

    def __init__(self, config: NodeTypeOptimizerConfig):
        self.config = config
        self.optimizer = RAGClusterOptimizer(
            similarity_threshold=config.similarity_threshold,
            max_iterations=config.max_iterations,
            fitness_improvement_threshold=config.fitness_improvement_threshold,
            strategy=config.strategy
        )

    def optimize_cluster(
        self,
        cluster: OptimizationCluster,
        validator_fn: Optional[callable] = None
    ) -> List[OptimizationIteration]:
        """Run optimization with node-type-specific configuration."""
        if not self.config.enabled:
            logger.info(f"Optimization disabled for {self.config.node_type.value}")
            return []

        logger.info(f"Optimizing {self.config.node_type.value} cluster: {cluster.cluster_id}")

        # Run optimization
        iterations = self.optimizer.optimize_cluster(cluster, validator_fn)

        # Apply trimming after optimization
        if self.config.trimming_policy:
            trim_report = self.optimizer.trim_cluster(
                cluster,
                self.config.trimming_policy
            )
            logger.info(
                f"Trimmed cluster {cluster.cluster_id}: "
                f"pruned {trim_report['pruned_count']}, "
                f"kept {trim_report['kept_count']}"
            )

        return iterations

    def get_fitness_weights(self) -> Dict[str, float]:
        """Get node-type-specific fitness weights."""
        return self.config.fitness_weights


class OptimizerConfigManager:
    """
    Manages configuration for all node-type optimizers.

    Loads policies from YAML config and provides per-node-type optimizers.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.node_configs: Dict[NodeType, NodeTypeOptimizerConfig] = {}
        self.optimizers: Dict[NodeType, NodeTypeOptimizer] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                self._parse_config(config_data)
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
                self._create_default_configs()
        else:
            self._create_default_configs()

        # Create optimizers for each node type
        for node_type, config in self.node_configs.items():
            self.optimizers[node_type] = NodeTypeOptimizer(config)

    def _create_default_configs(self):
        """Create default configurations for all node types."""
        for node_type in NodeType:
            self.node_configs[node_type] = self._get_default_config(node_type)

    def _get_default_config(self, node_type: NodeType) -> NodeTypeOptimizerConfig:
        """Get default configuration for a node type."""
        # Customize defaults by node type
        if node_type == NodeType.FUNCTION:
            return NodeTypeOptimizerConfig(
                node_type=node_type,
                enabled=True,
                similarity_threshold=0.96,
                max_iterations=10,
                fitness_improvement_threshold=0.05,
                strategy=OptimizationStrategy.BEST_OF_BREED,
                optimization_frequency="daily",
                priority=8
            )
        elif node_type == NodeType.WORKFLOW:
            return NodeTypeOptimizerConfig(
                node_type=node_type,
                enabled=True,
                similarity_threshold=0.94,
                max_iterations=15,
                fitness_improvement_threshold=0.08,
                strategy=OptimizationStrategy.INCREMENTAL,
                optimization_frequency="weekly",
                priority=9
            )
        elif node_type == NodeType.PROMPT:
            return NodeTypeOptimizerConfig(
                node_type=node_type,
                enabled=True,
                similarity_threshold=0.92,
                max_iterations=8,
                fitness_improvement_threshold=0.06,
                strategy=OptimizationStrategy.HYBRID,
                optimization_frequency="daily",
                priority=7
            )
        else:
            # Default config for PLAN, SUB_WORKFLOW, PATTERN
            return NodeTypeOptimizerConfig(
                node_type=node_type,
                enabled=True,
                similarity_threshold=0.95,
                max_iterations=10,
                fitness_improvement_threshold=0.05,
                strategy=OptimizationStrategy.BEST_OF_BREED,
                optimization_frequency="daily",
                priority=5
            )

    def _parse_config(self, config_data: Dict[str, Any]):
        """Parse configuration from loaded YAML."""
        node_configs_data = config_data.get('node_type_optimizers', {})

        for node_type_str, node_config_data in node_configs_data.items():
            try:
                node_type = NodeType(node_type_str)

                # Parse strategy
                strategy_str = node_config_data.get('strategy', 'best_of_breed')
                strategy = OptimizationStrategy(strategy_str)

                # Parse trimming policy
                trimming_data = node_config_data.get('trimming_policy', {})
                trimming_policy = TrimmingPolicy(
                    node_type=node_type,
                    min_similarity_to_fittest=trimming_data.get('min_similarity_to_fittest', 0.70),
                    preserve_high_perf_threshold=trimming_data.get('preserve_high_perf_threshold', 0.85),
                    min_usage_count=trimming_data.get('min_usage_count', 1),
                    never_used_grace_period_days=trimming_data.get('never_used_grace_period_days', 30),
                    min_fitness_absolute=trimming_data.get('min_fitness_absolute', 0.50),
                    max_distance_from_fittest=trimming_data.get('max_distance_from_fittest', 0.30),
                    always_keep_canonical=trimming_data.get('always_keep_canonical', True),
                    keep_high_coverage_variants=trimming_data.get('keep_high_coverage_variants', True),
                    preserve_lineage_endpoints=trimming_data.get('preserve_lineage_endpoints', True)
                )

                # Create config
                config = NodeTypeOptimizerConfig(
                    node_type=node_type,
                    enabled=node_config_data.get('enabled', True),
                    similarity_threshold=node_config_data.get('similarity_threshold', 0.96),
                    max_iterations=node_config_data.get('max_iterations', 10),
                    fitness_improvement_threshold=node_config_data.get('fitness_improvement_threshold', 0.05),
                    strategy=strategy,
                    trimming_policy=trimming_policy,
                    fitness_weights=node_config_data.get('fitness_weights'),
                    optimization_frequency=node_config_data.get('optimization_frequency', 'daily'),
                    priority=node_config_data.get('priority', 5)
                )

                self.node_configs[node_type] = config

            except (ValueError, KeyError) as e:
                logger.error(f"Failed to parse config for node type {node_type_str}: {e}")

        # Fill in missing node types with defaults
        for node_type in NodeType:
            if node_type not in self.node_configs:
                self.node_configs[node_type] = self._get_default_config(node_type)

    def get_optimizer(self, node_type: NodeType) -> NodeTypeOptimizer:
        """Get optimizer for a specific node type."""
        return self.optimizers.get(node_type)

    def get_config(self, node_type: NodeType) -> NodeTypeOptimizerConfig:
        """Get configuration for a specific node type."""
        return self.node_configs.get(node_type)

    def export_config(self, output_path: str):
        """Export current configuration to YAML file."""
        config_data = {
            'node_type_optimizers': {}
        }

        for node_type, config in self.node_configs.items():
            config_data['node_type_optimizers'][node_type.value] = {
                'enabled': config.enabled,
                'similarity_threshold': config.similarity_threshold,
                'max_iterations': config.max_iterations,
                'fitness_improvement_threshold': config.fitness_improvement_threshold,
                'strategy': config.strategy.value,
                'optimization_frequency': config.optimization_frequency,
                'priority': config.priority,
                'fitness_weights': config.fitness_weights,
                'trimming_policy': {
                    'min_similarity_to_fittest': config.trimming_policy.min_similarity_to_fittest,
                    'preserve_high_perf_threshold': config.trimming_policy.preserve_high_perf_threshold,
                    'min_usage_count': config.trimming_policy.min_usage_count,
                    'never_used_grace_period_days': config.trimming_policy.never_used_grace_period_days,
                    'min_fitness_absolute': config.trimming_policy.min_fitness_absolute,
                    'max_distance_from_fittest': config.trimming_policy.max_distance_from_fittest,
                    'always_keep_canonical': config.trimming_policy.always_keep_canonical,
                    'keep_high_coverage_variants': config.trimming_policy.keep_high_coverage_variants,
                    'preserve_lineage_endpoints': config.trimming_policy.preserve_lineage_endpoints
                }
            }

        with open(output_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Exported configuration to {output_path}")


# Example usage and integration
if __name__ == "__main__":
    # Example: Optimizing a cron parser cluster

    # Create canonical variant (v1)
    canonical = ArtifactVariant(
        variant_id="cron_parser_v1",
        artifact_id="cron_parser",
        version="1.0",
        content="def parse_cron(expr): ...",
        status=VariantStatus.CANONICAL,
        performance=PerformanceMetrics(
            latency_ms=50.0,
            memory_mb=10.0,
            success_rate=0.92,
            test_coverage=0.75
        )
    )

    # Create alternates
    alt1 = ArtifactVariant(
        variant_id="cron_parser_v1.1",
        artifact_id="cron_parser",
        version="1.1",
        content="def parse_cron(expr): # better error handling",
        performance=PerformanceMetrics(
            latency_ms=52.0,
            memory_mb=10.5,
            success_rate=0.96,
            test_coverage=0.78
        ),
        semantic_deltas=[
            SemanticDelta(
                delta_type="error_handling",
                description="Added try/except for invalid expressions",
                impact_areas=["robustness"],
                estimated_benefit=0.7,
                risk_level=0.2
            )
        ]
    )

    alt2 = ArtifactVariant(
        variant_id="cron_parser_v1.2",
        artifact_id="cron_parser",
        version="1.2",
        content="def parse_cron(expr): # faster regex",
        performance=PerformanceMetrics(
            latency_ms=38.0,
            memory_mb=11.0,
            success_rate=0.93,
            test_coverage=0.76
        ),
        semantic_deltas=[
            SemanticDelta(
                delta_type="algorithm",
                description="Optimized regex compilation",
                impact_areas=["performance"],
                estimated_benefit=0.8,
                risk_level=0.3
            )
        ]
    )

    # Create cluster
    cluster = OptimizationCluster(
        cluster_id="cron_parser_cluster",
        canonical_variant=canonical,
        alternates=[alt1, alt2]
    )

    # Run optimization
    optimizer = RAGClusterOptimizer(
        similarity_threshold=0.96,
        max_iterations=5,
        fitness_improvement_threshold=0.05,
        strategy=OptimizationStrategy.BEST_OF_BREED
    )

    iterations = optimizer.optimize_cluster(cluster)

    # Generate report
    report = optimizer.get_optimization_report(cluster, iterations)

    print("\n=== RAG Cluster Optimization Report ===")
    print(f"Cluster: {report['cluster_id']}")
    print(f"Status: {report['status']}")
    print(f"\nSummary:")
    for key, value in report['summary'].items():
        print(f"  {key}: {value}")
    print(f"\nFinal canonical variant: {report['canonical_variant']['variant_id']}")
    print(f"Final fitness: {report['canonical_variant']['fitness']}")
