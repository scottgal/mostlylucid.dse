"""
Neighbor-Based Optimizer - Test-Driven Optimization with Closest Neighbors

This module implements advanced optimization that:
1. Tests tools against their 10 closest neighbors (near or higher performance)
2. Uses interface matching to find compatible neighbors
3. Applies mutation-based optimization
4. Identifies clusters based on score ranking
5. Supports version-aware tool calling and automatic cluster formation

The optimization loop:
- Find 10 closest neighbors with matching interfaces
- Test current tool against each neighbor
- If neighbor performs better, mutate current with neighbor's improvements
- Repeat until no improvement from top 10 neighbors
- If new variant outperforms prime, promote it to prime
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple, Callable
from pathlib import Path
import numpy as np
from collections import defaultdict
import json

from .rag_cluster_optimizer import (
    ArtifactVariant,
    OptimizationCluster,
    PerformanceMetrics,
    VariantStatus,
    NodeType,
    ValidationResult
)
from .system_optimizer import (
    SystemOptimizer,
    OptimizationConfig,
    ClusterInfo,
    OptimizationResult
)
from .tools_manager import ToolsManager, Tool, ToolType
from .rag_memory import RAGMemory

logger = logging.getLogger(__name__)


@dataclass
class ToolInterface:
    """
    Represents the interface/signature of a tool.

    Used for matching compatible tools that can be compared.
    """
    input_parameters: Dict[str, str]  # param_name -> type
    output_type: str
    constraints: Set[str]  # Set of constraint names

    def matches(self, other: 'ToolInterface', strict: bool = False) -> bool:
        """
        Check if this interface matches another.

        Args:
            other: Other interface to compare
            strict: If True, requires exact match. If False, allows compatible matches.

        Returns:
            True if interfaces are compatible
        """
        if strict:
            return (
                self.input_parameters == other.input_parameters and
                self.output_type == other.output_type and
                self.constraints == other.constraints
            )

        # Compatible match: same parameters (ignoring order), compatible output
        self_params = set(self.input_parameters.keys())
        other_params = set(other.input_parameters.keys())

        # Must have at least 80% parameter overlap
        if not self_params or not other_params:
            return False

        overlap = len(self_params & other_params)
        min_size = min(len(self_params), len(other_params))

        if overlap / min_size < 0.8:
            return False

        # Output types should match (or be compatible)
        if self.output_type != other.output_type:
            # Allow some compatible types
            compatible_pairs = [
                ('str', 'text'),
                ('int', 'number'),
                ('float', 'number'),
                ('dict', 'object'),
                ('list', 'array')
            ]
            if not any(
                (self.output_type in pair and other.output_type in pair)
                for pair in compatible_pairs
            ):
                return False

        return True

    def similarity_score(self, other: 'ToolInterface') -> float:
        """
        Calculate similarity score (0.0-1.0) between interfaces.

        Returns:
            Similarity score
        """
        if not self.matches(other):
            return 0.0

        self_params = set(self.input_parameters.keys())
        other_params = set(other.input_parameters.keys())

        if not self_params and not other_params:
            return 1.0

        # Jaccard similarity on parameters
        intersection = len(self_params & other_params)
        union = len(self_params | other_params)
        param_sim = intersection / union if union > 0 else 0.0

        # Output type match
        output_sim = 1.0 if self.output_type == other.output_type else 0.7

        # Constraint match
        constraint_sim = 1.0
        if self.constraints or other.constraints:
            intersection = len(self.constraints & other.constraints)
            union = len(self.constraints | other.constraints)
            constraint_sim = intersection / union if union > 0 else 0.5

        # Weighted average
        return 0.5 * param_sim + 0.3 * output_sim + 0.2 * constraint_sim


@dataclass
class Neighbor:
    """Represents a neighbor tool for comparison."""
    variant: ArtifactVariant
    similarity: float  # Similarity to current tool
    interface_match: float  # Interface compatibility score
    performance_score: float  # Performance/fitness score
    distance: float  # Overall distance (1 - combined score)


@dataclass
class MutationResult:
    """Result of mutating a tool with neighbor improvements."""
    success: bool
    mutated_variant: Optional[ArtifactVariant]
    performance_improvement: float
    mutations_applied: List[str]
    test_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NeighborTestResult:
    """Result of testing against a neighbor."""
    neighbor: Neighbor
    test_passed: bool
    performance_delta: float  # Improvement over current
    worth_mutating: bool
    insights: List[str] = field(default_factory=list)


class NeighborOptimizer(SystemOptimizer):
    """
    Enhanced optimizer with neighbor-based testing and mutation.

    Extends SystemOptimizer with:
    - Interface-based neighbor finding
    - Iterative testing against top 10 neighbors
    - Mutation-based improvement
    - Version-aware clustering
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        rag_memory: Optional[RAGMemory] = None,
        tools_manager: Optional[ToolsManager] = None,
        test_function: Optional[Callable] = None
    ):
        """
        Initialize the neighbor optimizer.

        Args:
            config: Optimization configuration
            rag_memory: RAG memory instance
            tools_manager: Tools manager instance
            test_function: Function to test tool variants (optional)
                          Signature: fn(variant) -> ValidationResult
        """
        super().__init__(config, rag_memory, tools_manager)
        self.test_function = test_function or self._default_test_function

        # Track interface signatures for all tools
        self.tool_interfaces: Dict[str, ToolInterface] = {}

        # Version-based clustering
        self.version_clusters: Dict[str, List[ArtifactVariant]] = defaultdict(list)

    def _default_test_function(self, variant: ArtifactVariant) -> ValidationResult:
        """Default test function (placeholder)."""
        # In real implementation, this would run actual tests
        return ValidationResult(
            passed=True,
            fitness_score=variant.performance.fitness_score(),
            performance=variant.performance
        )

    def extract_interface(self, variant: ArtifactVariant) -> ToolInterface:
        """
        Extract the interface/signature from a tool variant.

        Args:
            variant: Tool variant

        Returns:
            ToolInterface describing the variant's signature
        """
        # Check cache first
        if variant.variant_id in self.tool_interfaces:
            return self.tool_interfaces[variant.variant_id]

        # Extract from metadata or parse from content
        metadata = variant.metadata

        input_params = metadata.get('parameters', {})
        output_type = metadata.get('output_type', 'any')
        constraints = set(metadata.get('constraints', {}).keys())

        # If not in metadata, try to parse from content (simplified)
        if not input_params and variant.content:
            # This is a simplified parser - in practice, use AST
            input_params = self._parse_parameters_from_content(variant.content)

        interface = ToolInterface(
            input_parameters=input_params,
            output_type=output_type,
            constraints=constraints
        )

        # Cache it
        self.tool_interfaces[variant.variant_id] = interface

        return interface

    def _parse_parameters_from_content(self, content: str) -> Dict[str, str]:
        """
        Parse function parameters from content (simplified).

        In production, use AST parsing or function inspection.
        """
        # Placeholder implementation
        # In practice, parse actual function signatures
        params = {}

        # Simple regex-based parsing (very basic)
        import re

        # Look for function definitions
        func_pattern = r'def\s+\w+\s*\((.*?)\)'
        matches = re.findall(func_pattern, content)

        if matches:
            param_str = matches[0]
            # Parse parameters (simplified)
            for param in param_str.split(','):
                param = param.strip()
                if ':' in param:
                    name, type_hint = param.split(':', 1)
                    params[name.strip()] = type_hint.strip()
                elif param and param != 'self':
                    params[param] = 'any'

        return params

    def find_nearest_neighbors(
        self,
        variant: ArtifactVariant,
        cluster: ClusterInfo,
        k: int = 10,
        min_performance: Optional[float] = None
    ) -> List[Neighbor]:
        """
        Find k nearest neighbors with matching interfaces.

        Args:
            variant: Current variant to find neighbors for
            cluster: Cluster containing potential neighbors
            k: Number of neighbors to find (default: 10)
            min_performance: Minimum performance score (filters lower performers)

        Returns:
            List of k nearest neighbors, sorted by combined similarity score
        """
        current_interface = self.extract_interface(variant)
        current_fitness = variant.performance.fitness_score()

        if min_performance is None:
            min_performance = current_fitness  # Only consider equal or better

        neighbors = []

        for candidate in cluster.variants:
            if candidate.variant_id == variant.variant_id:
                continue

            # Check performance threshold
            candidate_fitness = candidate.performance.fitness_score()
            if candidate_fitness < min_performance:
                continue

            # Check interface compatibility
            candidate_interface = self.extract_interface(candidate)
            if not current_interface.matches(candidate_interface):
                continue

            # Calculate similarity scores
            interface_sim = current_interface.similarity_score(candidate_interface)
            embedding_sim = variant.similarity_to(candidate)
            performance_score = candidate_fitness

            # Combined score (weighted)
            combined_sim = (
                0.4 * embedding_sim +
                0.4 * interface_sim +
                0.2 * (performance_score / (current_fitness + 1e-6))
            )

            distance = 1.0 - combined_sim

            neighbor = Neighbor(
                variant=candidate,
                similarity=embedding_sim,
                interface_match=interface_sim,
                performance_score=performance_score,
                distance=distance
            )

            neighbors.append(neighbor)

        # Sort by distance (ascending) and take top k
        neighbors.sort(key=lambda n: n.distance)
        return neighbors[:k]

    def test_against_neighbor(
        self,
        current: ArtifactVariant,
        neighbor: Neighbor,
        test_fn: Optional[Callable] = None
    ) -> NeighborTestResult:
        """
        Test current variant against a neighbor.

        Args:
            current: Current variant
            neighbor: Neighbor to test against
            test_fn: Optional test function override

        Returns:
            NeighborTestResult with test outcomes
        """
        test_fn = test_fn or self.test_function

        # Run tests on both
        current_result = test_fn(current)
        neighbor_result = test_fn(neighbor.variant)

        # Compare performance
        current_fitness = current_result.fitness_score
        neighbor_fitness = neighbor_result.fitness_score

        performance_delta = neighbor_fitness - current_fitness

        # Determine if worth mutating
        # Mutation is worth it if neighbor improves by at least 5%
        improvement_threshold = 0.05
        worth_mutating = performance_delta > improvement_threshold

        insights = []
        if worth_mutating:
            insights.append(
                f"Neighbor improves performance by {performance_delta*100:.1f}%"
            )

        if neighbor_result.performance.latency_ms < current_result.performance.latency_ms:
            latency_improvement = (
                current_result.performance.latency_ms -
                neighbor_result.performance.latency_ms
            )
            insights.append(f"Latency reduced by {latency_improvement:.1f}ms")

        return NeighborTestResult(
            neighbor=neighbor,
            test_passed=neighbor_result.passed,
            performance_delta=performance_delta,
            worth_mutating=worth_mutating,
            insights=insights
        )

    def mutate_with_neighbor(
        self,
        current: ArtifactVariant,
        neighbor: Neighbor,
        test_fn: Optional[Callable] = None
    ) -> MutationResult:
        """
        Mutate current variant by incorporating improvements from neighbor.

        This is a simplified version - in practice, use LLM-based code synthesis.

        Args:
            current: Current variant to mutate
            neighbor: Neighbor with better performance
            test_fn: Optional test function

        Returns:
            MutationResult with mutated variant
        """
        test_fn = test_fn or self.test_function

        mutations_applied = []

        # Create a new variant (mutated version)
        # In practice, this would use LLM to synthesize improvements
        mutated = ArtifactVariant(
            variant_id=f"{current.variant_id}_mutated_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            artifact_id=current.artifact_id,
            version=self._bump_patch_version(current.version),
            content=self._synthesize_mutation(current, neighbor),
            embedding=None,  # Will be regenerated
            status=VariantStatus.ACTIVE,
            performance=PerformanceMetrics(),  # Will be measured
            parent_id=current.variant_id,
            metadata=current.metadata.copy()
        )

        # Test the mutated variant
        result = test_fn(mutated)
        mutated.performance = result.performance

        # Check if mutation improved performance
        current_fitness = current.performance.fitness_score()
        mutated_fitness = result.fitness_score

        improvement = mutated_fitness - current_fitness

        if improvement > 0:
            mutations_applied.append(f"Incorporated improvements from {neighbor.variant.variant_id}")
            if result.passed:
                return MutationResult(
                    success=True,
                    mutated_variant=mutated,
                    performance_improvement=improvement,
                    mutations_applied=mutations_applied,
                    test_results=result.test_results
                )

        return MutationResult(
            success=False,
            mutated_variant=None,
            performance_improvement=improvement,
            mutations_applied=mutations_applied,
            test_results=result.test_results
        )

    def _synthesize_mutation(
        self,
        current: ArtifactVariant,
        neighbor: Neighbor
    ) -> str:
        """
        Synthesize a mutated version combining current + neighbor improvements.

        In practice, this would use an LLM to intelligently combine code.
        This is a placeholder implementation.
        """
        # Placeholder: In real implementation, use LLM-based synthesis
        return f"""
# Mutated version combining:
# - Base: {current.variant_id}
# - Improvements from: {neighbor.variant.variant_id}

{current.content}

# TODO: LLM-based synthesis would go here
# For now, this is a placeholder
"""

    def _bump_patch_version(self, version: str) -> str:
        """Bump patch version (1.0.0 -> 1.0.1)."""
        try:
            parts = version.split('.')
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{major}.{minor}.{patch + 1}"
        except:
            return "1.0.1"

    def optimize_with_neighbors(
        self,
        variant: ArtifactVariant,
        cluster: ClusterInfo,
        max_iterations: int = 10
    ) -> Tuple[ArtifactVariant, List[str]]:
        """
        Optimize a variant by testing against nearest neighbors.

        Algorithm:
        1. Find 10 closest neighbors with matching interfaces
        2. Test against each neighbor
        3. If neighbor is better, mutate current with neighbor's improvements
        4. Repeat until no improvement or max iterations
        5. If final variant beats prime, promote it

        Args:
            variant: Variant to optimize
            cluster: Cluster containing potential neighbors
            max_iterations: Maximum optimization iterations

        Returns:
            (optimized_variant, optimization_log)
        """
        current = variant
        optimization_log = []

        for iteration in range(max_iterations):
            logger.info(f"Optimization iteration {iteration + 1}/{max_iterations}")

            # Find nearest neighbors
            neighbors = self.find_nearest_neighbors(
                current,
                cluster,
                k=10,
                min_performance=current.performance.fitness_score()
            )

            if not neighbors:
                optimization_log.append(f"Iteration {iteration + 1}: No compatible neighbors found")
                break

            optimization_log.append(
                f"Iteration {iteration + 1}: Found {len(neighbors)} compatible neighbors"
            )

            # Test against each neighbor
            improved = False
            for neighbor in neighbors:
                test_result = self.test_against_neighbor(current, neighbor)

                if test_result.worth_mutating:
                    # Try mutation
                    mutation_result = self.mutate_with_neighbor(current, neighbor)

                    if mutation_result.success:
                        current = mutation_result.mutated_variant
                        improved = True
                        optimization_log.append(
                            f"  ✓ Mutation successful: "
                            f"+{mutation_result.performance_improvement*100:.1f}% improvement"
                        )
                        optimization_log.extend(f"    - {m}" for m in mutation_result.mutations_applied)
                        break  # Move to next iteration with improved variant
                    else:
                        optimization_log.append(
                            f"  ✗ Mutation failed for neighbor {neighbor.variant.variant_id}"
                        )

            if not improved:
                optimization_log.append(
                    f"Iteration {iteration + 1}: No improvement found, stopping"
                )
                break

        # Check if optimized variant should become new prime
        prime = cluster.prime_tool
        if current.performance.fitness_score() > prime.performance.fitness_score():
            optimization_log.append(
                f"🏆 New prime! {current.variant_id} beats {prime.variant_id} "
                f"({current.performance.fitness_score():.3f} > {prime.performance.fitness_score():.3f})"
            )
            current.status = VariantStatus.CANONICAL

        return current, optimization_log

    def identify_version_clusters(self) -> Dict[str, List[ClusterInfo]]:
        """
        Identify clusters based on tool name and version.

        Groups tools by:
        1. Tool name (base name without version)
        2. Major.minor version (allowing different patches)

        Returns:
            Dictionary mapping tool_name -> list of version clusters
        """
        version_clusters = defaultdict(list)

        for cluster_id, cluster_info in self.clusters.items():
            # Extract base tool name and version from variants
            for variant in cluster_info.variants:
                base_name = self._extract_base_name(variant.artifact_id)
                version_prefix = self._extract_version_prefix(variant.version)

                key = f"{base_name}@{version_prefix}"
                version_clusters[key].append(variant)

        # Convert to ClusterInfo objects
        result = {}
        for key, variants in version_clusters.items():
            if len(variants) > 1:
                prime = self._find_prime_tool(variants)
                fitness_scores = [v.performance.fitness_score() for v in variants]
                median_fitness = float(np.median(fitness_scores)) if fitness_scores else 0.0

                cluster_info = ClusterInfo(
                    cluster_id=key,
                    prime_tool=prime,
                    variants=variants,
                    median_fitness=median_fitness,
                    total_variants=len(variants),
                    active_variants=sum(1 for v in variants if v.status == VariantStatus.ACTIVE)
                )

                result[key] = [cluster_info]

        return result

    def _extract_base_name(self, artifact_id: str) -> str:
        """Extract base name from artifact_id (remove version suffix)."""
        # Remove version-like suffixes
        import re
        # Match patterns like _v1, _v1.0, _1.0.0, @1.0.0
        base = re.sub(r'[@_]v?\d+\.\d+.*$', '', artifact_id)
        return base

    def _extract_version_prefix(self, version: str) -> str:
        """Extract major.minor from version (1.2.3 -> 1.2)."""
        try:
            parts = version.split('.')
            return f"{parts[0]}.{parts[1]}"
        except:
            return "1.0"

    def run_full_optimization_with_neighbors(self) -> OptimizationResult:
        """
        Run full optimization workflow with neighbor-based testing.

        Extends the base optimization with:
        1. Neighbor-based testing for each cluster
        2. Mutation-based improvement
        3. Version-aware cluster formation

        Returns:
            OptimizationResult with detailed results
        """
        # First run base optimization
        result = super().run_full_optimization()

        # Then apply neighbor-based optimization
        logger.info("\n🧬 Stage 5: Neighbor-based optimization...")

        neighbor_optimizations = []

        for cluster_id, cluster_info in self.clusters.items():
            if cluster_info.total_variants < 2:
                continue  # Need at least 2 variants for neighbor testing

            logger.info(f"\nOptimizing cluster {cluster_id}...")

            # Optimize each variant in the cluster
            for variant in cluster_info.variants:
                if variant.status == VariantStatus.CANONICAL:
                    # Skip canonical for now, we'll optimize alternates first
                    continue

                try:
                    optimized, log = self.optimize_with_neighbors(
                        variant,
                        cluster_info,
                        max_iterations=10
                    )

                    neighbor_optimizations.append({
                        'cluster_id': cluster_id,
                        'original_variant': variant.variant_id,
                        'optimized_variant': optimized.variant_id,
                        'improvement': (
                            optimized.performance.fitness_score() -
                            variant.performance.fitness_score()
                        ),
                        'log': log
                    })

                    if self.config.verbose:
                        for log_entry in log:
                            logger.info(f"  {log_entry}")

                except Exception as e:
                    logger.error(f"Error optimizing {variant.variant_id}: {e}")
                    result.errors.append(f"Neighbor optimization failed for {variant.variant_id}: {e}")

        # Store neighbor optimization results in result metadata
        if not hasattr(result, 'neighbor_optimizations'):
            result.neighbor_optimizations = neighbor_optimizations

        # Recalculate improvement estimate
        if neighbor_optimizations:
            avg_neighbor_improvement = np.mean([
                opt['improvement'] for opt in neighbor_optimizations
                if opt['improvement'] > 0
            ])
            result.estimated_improvement += avg_neighbor_improvement * 100  # Add to base estimate

        return result
