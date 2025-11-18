"""
System Optimizer - Full System-Wide Optimization Workflow

Implements a comprehensive optimization workflow that:
1. Identifies prime tools in each cluster (highest version/fittest)
2. Adjusts optimization weights based on similarity
3. Culls tools with low optimization scores
4. Prunes distant variants from prime tools

This is designed for periodic optimization runs to maintain system health.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import numpy as np
from collections import defaultdict
import json
import yaml

from .rag_cluster_optimizer import (
    ArtifactVariant,
    OptimizationCluster,
    PerformanceMetrics,
    VariantStatus,
    NodeType,
    TrimmingPolicy
)
from .tools_manager import ToolsManager, Tool
from .rag_memory import RAGMemory
from .version_replacement import VersionReplacementManager

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """Configuration for system-wide optimization."""

    # Similarity thresholds
    similarity_threshold: float = 0.85  # Threshold for considering tools similar
    cluster_similarity_threshold: float = 0.96  # Threshold for clustering variants

    # Scoring thresholds
    min_optimization_score: float = 0.50  # Minimum score to avoid culling
    min_fitness_absolute: float = 0.50  # Minimum fitness score

    # Distance thresholds
    max_distance_from_prime: float = 0.30  # Maximum allowed distance from prime tool

    # Weight adjustment
    weight_reduction_factor: float = 0.7  # Factor to reduce weight for similar tools

    # Culling settings
    enable_culling: bool = True
    culling_grace_period_days: int = 30  # Keep tools for N days before culling

    # Variant pruning
    enable_variant_pruning: bool = True
    prune_archived_variants: bool = True

    # Safety settings
    dry_run: bool = False  # If True, only report what would be done
    backup_before_optimization: bool = True
    preserve_canonical: bool = True  # Never remove canonical variants

    # Output settings
    verbose: bool = True
    report_path: Optional[Path] = None

    # Evolutionary pressure settings
    evolutionary_pressure: str = "balanced"  # "granular", "generic", or "balanced"
    min_cluster_size: int = 2  # Minimum variants in a cluster
    merge_similar_functions: bool = False  # Whether to merge similar function nodes
    specialization_bias: float = 0.5  # 0.0 = generic, 1.0 = specialized

    def apply_evolutionary_adjustments(self, adjustments: Dict[str, Any]) -> None:
        """
        Apply evolutionary pressure adjustments from PressureManager.

        Args:
            adjustments: Dict from PressureManager.get_evolutionary_adjustments()
        """
        self.evolutionary_pressure = adjustments.get("evolutionary_pressure", self.evolutionary_pressure)
        self.cluster_similarity_threshold = adjustments.get("similarity_threshold", self.cluster_similarity_threshold)
        self.max_distance_from_prime = adjustments.get("max_distance_from_fittest", self.max_distance_from_prime)
        self.min_cluster_size = adjustments.get("min_cluster_size", self.min_cluster_size)
        self.merge_similar_functions = adjustments.get("merge_similar_functions", self.merge_similar_functions)
        self.specialization_bias = adjustments.get("specialization_bias", self.specialization_bias)

        logger.info(f"Applied evolutionary pressure adjustments: "
                   f"pressure={self.evolutionary_pressure}, "
                   f"similarity={self.cluster_similarity_threshold:.2f}, "
                   f"max_distance={self.max_distance_from_prime:.2f}")


@dataclass
class ClusterInfo:
    """Information about a tool cluster."""
    cluster_id: str
    prime_tool: ArtifactVariant  # Highest version/fittest tool
    variants: List[ArtifactVariant]
    median_fitness: float
    total_variants: int
    active_variants: int


@dataclass
class OptimizationWeight:
    """Optimization weight for a specific tool-cluster relationship."""
    tool_id: str
    cluster_id: str
    original_weight: float
    adjusted_weight: float
    similarity_to_prime: float
    reason: str


@dataclass
class OptimizationAction:
    """A single optimization action taken."""
    action_type: str  # 'weight_adjusted', 'tool_culled', 'variant_pruned'
    tool_id: str
    cluster_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationResult:
    """Result of a full system optimization run."""
    start_time: datetime
    end_time: datetime
    config: OptimizationConfig

    # Clusters analyzed
    clusters: List[ClusterInfo]
    total_clusters: int

    # Actions taken
    weights_adjusted: List[OptimizationWeight]
    tools_culled: List[str]
    variants_pruned: List[str]

    # Statistics
    total_tools_analyzed: int
    total_variants_analyzed: int
    estimated_improvement: float

    # Errors/warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        duration = (self.end_time - self.start_time).total_seconds()

        summary = [
            "\n" + "=" * 80,
            "SYSTEM OPTIMIZATION REPORT",
            "=" * 80,
            f"\nStart Time: {self.start_time}",
            f"End Time: {self.end_time}",
            f"Duration: {duration:.2f}s",
            f"\n{'DRY RUN MODE' if self.config.dry_run else 'LIVE MODE'}",
            "\n" + "-" * 80,
            "ANALYSIS SUMMARY",
            "-" * 80,
            f"Total Clusters Analyzed: {self.total_clusters}",
            f"Total Tools Analyzed: {self.total_tools_analyzed}",
            f"Total Variants Analyzed: {self.total_variants_analyzed}",
            "\n" + "-" * 80,
            "ACTIONS TAKEN",
            "-" * 80,
            f"Optimization Weights Adjusted: {len(self.weights_adjusted)}",
            f"Tools Culled: {len(self.tools_culled)}",
            f"Variants Pruned: {len(self.variants_pruned)}",
        ]

        # Weight adjustments details
        if self.weights_adjusted:
            summary.append("\n📊 Weight Adjustments:")
            for weight in self.weights_adjusted[:10]:  # Show first 10
                summary.append(
                    f"  • {weight.tool_id} in cluster {weight.cluster_id}: "
                    f"{weight.original_weight:.3f} → {weight.adjusted_weight:.3f} "
                    f"(similarity: {weight.similarity_to_prime:.3f})"
                )
            if len(self.weights_adjusted) > 10:
                summary.append(f"  ... and {len(self.weights_adjusted) - 10} more")

        # Culling details
        if self.tools_culled:
            summary.append("\n🗑️  Tools Culled:")
            for tool_id in self.tools_culled[:10]:
                summary.append(f"  • {tool_id}")
            if len(self.tools_culled) > 10:
                summary.append(f"  ... and {len(self.tools_culled) - 10} more")

        # Pruning details
        if self.variants_pruned:
            summary.append("\n✂️  Variants Pruned:")
            for variant_id in self.variants_pruned[:10]:
                summary.append(f"  • {variant_id}")
            if len(self.variants_pruned) > 10:
                summary.append(f"  ... and {len(self.variants_pruned) - 10} more")

        # Performance prediction
        summary.extend([
            "\n" + "-" * 80,
            "PERFORMANCE PREDICTION",
            "-" * 80,
            f"Estimated Improvement: {self.estimated_improvement:.1f}%",
        ])

        # Errors/warnings
        if self.errors:
            summary.append("\n⚠️  ERRORS:")
            for error in self.errors:
                summary.append(f"  • {error}")

        if self.warnings:
            summary.append("\n⚡ WARNINGS:")
            for warning in self.warnings:
                summary.append(f"  • {warning}")

        summary.append("\n" + "=" * 80 + "\n")

        return "\n".join(summary)


class SystemOptimizer:
    """
    System-wide optimizer that performs comprehensive optimization workflows.

    This orchestrates multiple optimization stages:
    1. Cluster analysis and prime tool identification
    2. Similarity-based weight adjustment
    3. Low-score tool culling
    4. Distance-based variant pruning
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        rag_memory: Optional[RAGMemory] = None,
        tools_manager: Optional[ToolsManager] = None
    ):
        """
        Initialize the system optimizer.

        Args:
            config: Optimization configuration
            rag_memory: RAG memory instance (will create if None)
            tools_manager: Tools manager instance (will create if None)
        """
        self.config = config or OptimizationConfig()
        self.rag = rag_memory or self._initialize_rag()
        self.tools_manager = tools_manager or self._initialize_tools_manager()
        self.version_manager = VersionReplacementManager(self.rag)

        # Storage for optimization state
        self.clusters: Dict[str, ClusterInfo] = {}
        self.tool_cluster_weights: Dict[Tuple[str, str], float] = {}  # (tool_id, cluster_id) -> weight
        self.actions: List[OptimizationAction] = []

    def _initialize_rag(self) -> RAGMemory:
        """Initialize RAG memory from default location."""
        from .rag_memory import RAGMemory
        rag_dir = Path("rag_memory")
        return RAGMemory(rag_dir=str(rag_dir))

    def _initialize_tools_manager(self) -> ToolsManager:
        """Initialize tools manager from default registry."""
        from .tools_manager import ToolsManager
        registry_path = Path("registry")
        return ToolsManager(registry_path=str(registry_path))

    def run_full_optimization(self) -> OptimizationResult:
        """
        Run the complete optimization workflow.

        Returns:
            OptimizationResult with detailed results
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("Starting Full System Optimization")
        logger.info("=" * 80)

        result = OptimizationResult(
            start_time=start_time,
            end_time=start_time,  # Will update at end
            config=self.config,
            clusters=[],
            total_clusters=0,
            weights_adjusted=[],
            tools_culled=[],
            variants_pruned=[],
            total_tools_analyzed=0,
            total_variants_analyzed=0,
            estimated_improvement=0.0
        )

        try:
            # Stage 1: Identify clusters and prime tools
            logger.info("\n📊 Stage 1: Identifying clusters and prime tools...")
            self._identify_clusters_and_primes(result)

            # Stage 2: Adjust optimization weights based on similarity
            logger.info("\n⚖️  Stage 2: Adjusting optimization weights...")
            self._adjust_optimization_weights(result)

            # Stage 3: Cull low-scoring tools
            if self.config.enable_culling:
                logger.info("\n🗑️  Stage 3: Culling low-scoring tools...")
                self._cull_low_score_tools(result)

            # Stage 4: Prune distant variants
            if self.config.enable_variant_pruning:
                logger.info("\n✂️  Stage 4: Pruning distant variants...")
                self._prune_distant_variants(result)

            # Calculate estimated improvement
            result.estimated_improvement = self._calculate_improvement(result)

            # Save report if requested
            if self.config.report_path:
                self._save_report(result)

        except Exception as e:
            logger.error(f"Error during optimization: {e}", exc_info=True)
            result.errors.append(str(e))

        result.end_time = datetime.now()

        if self.config.verbose:
            print(result.summary())

        return result

    def _identify_clusters_and_primes(self, result: OptimizationResult) -> None:
        """
        Identify all clusters and their prime tools (highest version/fittest).

        A prime tool is the tool with the highest version number or highest fitness
        score within a cluster, and it must maintain all tool manager references.
        """
        # Get all artifacts with embeddings from RAG
        all_artifacts = self.rag.get_all_artifacts()

        # Group artifacts by similarity to form clusters
        clusters_dict = self._cluster_artifacts(all_artifacts)

        result.total_clusters = len(clusters_dict)
        result.total_tools_analyzed = len(all_artifacts)

        for cluster_id, variants in clusters_dict.items():
            if not variants:
                continue

            # Find the prime tool (highest version or fittest)
            prime_tool = self._find_prime_tool(variants)

            # Calculate cluster statistics
            active_count = sum(1 for v in variants if v.status == VariantStatus.ACTIVE)
            fitness_scores = [v.performance.fitness_score() for v in variants]
            median_fitness = float(np.median(fitness_scores)) if fitness_scores else 0.0

            cluster_info = ClusterInfo(
                cluster_id=cluster_id,
                prime_tool=prime_tool,
                variants=variants,
                median_fitness=median_fitness,
                total_variants=len(variants),
                active_variants=active_count
            )

            self.clusters[cluster_id] = cluster_info
            result.clusters.append(cluster_info)
            result.total_variants_analyzed += len(variants)

            if self.config.verbose:
                logger.info(
                    f"  Cluster {cluster_id}: {len(variants)} variants, "
                    f"prime: {prime_tool.variant_id} (v{prime_tool.version}, "
                    f"fitness: {prime_tool.performance.fitness_score():.3f})"
                )

    def _cluster_artifacts(self, artifacts: List[Any]) -> Dict[str, List[ArtifactVariant]]:
        """
        Group artifacts into clusters based on similarity.

        Returns:
            Dictionary mapping cluster_id to list of ArtifactVariants
        """
        # Convert RAG artifacts to ArtifactVariants
        variants = []
        for artifact in artifacts:
            if not hasattr(artifact, 'embedding') or artifact.embedding is None:
                continue

            # Create ArtifactVariant from RAG artifact
            variant = ArtifactVariant(
                variant_id=getattr(artifact, 'id', str(id(artifact))),
                artifact_id=getattr(artifact, 'id', str(id(artifact))),
                version=getattr(artifact, 'version', '1.0.0'),
                content=getattr(artifact, 'content', ''),
                embedding=artifact.embedding,
                status=VariantStatus.ACTIVE,
                performance=self._extract_performance_metrics(artifact),
                metadata=getattr(artifact, 'metadata', {})
            )
            variants.append(variant)

        # Use simple greedy clustering
        clusters = {}
        cluster_counter = 0
        assigned = set()

        for i, variant in enumerate(variants):
            if i in assigned:
                continue

            # Start new cluster
            cluster_id = f"cluster_{cluster_counter}"
            cluster_variants = [variant]
            assigned.add(i)

            # Find similar variants
            for j, other in enumerate(variants):
                if j in assigned:
                    continue

                similarity = variant.similarity_to(other)
                if similarity >= self.config.cluster_similarity_threshold:
                    cluster_variants.append(other)
                    assigned.add(j)

            # Only create cluster if it has multiple variants
            if len(cluster_variants) >= 1:
                clusters[cluster_id] = cluster_variants
                cluster_counter += 1

        return clusters

    def _extract_performance_metrics(self, artifact: Any) -> PerformanceMetrics:
        """Extract performance metrics from a RAG artifact."""
        metadata = getattr(artifact, 'metadata', {})

        return PerformanceMetrics(
            latency_ms=metadata.get('latency_ms', 0.0),
            memory_mb=metadata.get('memory_mb', 0.0),
            cpu_percent=metadata.get('cpu_percent', 0.0),
            success_rate=metadata.get('success_rate', 1.0),
            error_count=metadata.get('error_count', 0),
            usage_count=metadata.get('usage_count', 0),
            test_coverage=metadata.get('test_coverage', 0.0)
        )

    def _find_prime_tool(self, variants: List[ArtifactVariant]) -> ArtifactVariant:
        """
        Find the prime tool (highest version or fittest) in a list of variants.

        Priority:
        1. Canonical variants (if any)
        2. Highest semantic version
        3. Highest fitness score
        """
        # Check for canonical variants first
        canonical = [v for v in variants if v.status == VariantStatus.CANONICAL]
        if canonical:
            return canonical[0]

        # Sort by version and fitness
        def version_key(v: ArtifactVariant) -> Tuple[int, int, int]:
            try:
                parts = v.version.split('.')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                return (0, 0, 0)

        # First try version-based selection
        sorted_by_version = sorted(variants, key=version_key, reverse=True)
        highest_version = sorted_by_version[0]

        # Then check fitness among similar versions
        major, minor, _ = version_key(highest_version)
        same_version_variants = [
            v for v in variants
            if version_key(v)[:2] == (major, minor)
        ]

        if same_version_variants:
            return max(same_version_variants, key=lambda v: v.performance.fitness_score())

        return highest_version

    def _adjust_optimization_weights(self, result: OptimizationResult) -> None:
        """
        Adjust optimization weights for tools based on similarity to prime tools.

        For each tool:
        1. Find all clusters it belongs to
        2. Calculate similarity to the prime tool in each cluster
        3. If similarity > threshold, reduce the optimization weight
        4. Store the cluster-specific weight
        """
        for cluster_id, cluster_info in self.clusters.items():
            prime = cluster_info.prime_tool

            for variant in cluster_info.variants:
                if variant.variant_id == prime.variant_id:
                    # Prime tool keeps full weight
                    self.tool_cluster_weights[(variant.variant_id, cluster_id)] = 1.0
                    continue

                # Calculate similarity to prime
                similarity = variant.similarity_to(prime)

                # Calculate adjusted weight
                original_weight = 1.0
                if similarity >= self.config.similarity_threshold:
                    # Reduce weight for similar tools
                    adjusted_weight = original_weight * self.config.weight_reduction_factor
                    reason = f"High similarity to prime ({similarity:.3f})"
                else:
                    adjusted_weight = original_weight
                    reason = "Below similarity threshold"

                # Store the weight
                self.tool_cluster_weights[(variant.variant_id, cluster_id)] = adjusted_weight

                # Record the action if weight was adjusted
                if adjusted_weight < original_weight:
                    weight_info = OptimizationWeight(
                        tool_id=variant.variant_id,
                        cluster_id=cluster_id,
                        original_weight=original_weight,
                        adjusted_weight=adjusted_weight,
                        similarity_to_prime=similarity,
                        reason=reason
                    )
                    result.weights_adjusted.append(weight_info)

                    if self.config.verbose:
                        logger.info(
                            f"  Adjusted weight for {variant.variant_id} in {cluster_id}: "
                            f"{original_weight:.3f} → {adjusted_weight:.3f} "
                            f"(similarity: {similarity:.3f})"
                        )

    def _cull_low_score_tools(self, result: OptimizationResult) -> None:
        """
        Cull tools with consistently low optimization scores across all clusters.

        A tool is culled if:
        1. Its fitness score is below min_optimization_score in ALL clusters
        2. It hasn't been used recently (grace period)
        3. It's not a canonical variant
        """
        tools_to_cull = []

        for cluster_id, cluster_info in self.clusters.items():
            for variant in cluster_info.variants:
                # Never cull canonical variants
                if self.config.preserve_canonical and variant.status == VariantStatus.CANONICAL:
                    continue

                # Check fitness score
                fitness = variant.performance.fitness_score()
                if fitness >= self.config.min_optimization_score:
                    continue

                # Check grace period
                days_old = (datetime.now() - variant.created_at).days
                if days_old < self.config.culling_grace_period_days:
                    continue

                # Check if low score across ALL clusters this tool belongs to
                all_clusters_low = True
                for cid, cinfo in self.clusters.items():
                    if any(v.variant_id == variant.variant_id for v in cinfo.variants):
                        # Check if this variant has acceptable fitness in any cluster
                        if variant.performance.fitness_score() >= self.config.min_optimization_score:
                            all_clusters_low = False
                            break

                if all_clusters_low and variant.variant_id not in tools_to_cull:
                    tools_to_cull.append(variant.variant_id)

                    if self.config.verbose:
                        logger.info(
                            f"  Culling {variant.variant_id}: "
                            f"fitness={fitness:.3f}, age={days_old}d"
                        )

        # Perform culling
        if not self.config.dry_run:
            for tool_id in tools_to_cull:
                self._archive_tool(tool_id)

        result.tools_culled.extend(tools_to_cull)

    def _prune_distant_variants(self, result: OptimizationResult) -> None:
        """
        Prune variants that are too distant from their cluster's prime tool.

        For each cluster:
        1. Calculate distance from prime tool
        2. If distance > max_distance_from_prime, prune the variant
        3. Archive rather than delete
        """
        variants_to_prune = []

        for cluster_id, cluster_info in self.clusters.items():
            prime = cluster_info.prime_tool

            for variant in cluster_info.variants:
                if variant.variant_id == prime.variant_id:
                    continue

                # Never prune canonical
                if self.config.preserve_canonical and variant.status == VariantStatus.CANONICAL:
                    continue

                # Calculate distance (1 - similarity)
                similarity = variant.similarity_to(prime)
                distance = 1.0 - similarity

                if distance > self.config.max_distance_from_prime:
                    # Also check fitness distance
                    prime_fitness = prime.performance.fitness_score()
                    variant_fitness = variant.performance.fitness_score()
                    fitness_distance = abs(prime_fitness - variant_fitness)

                    if variant.variant_id not in variants_to_prune:
                        variants_to_prune.append(variant.variant_id)

                        if self.config.verbose:
                            logger.info(
                                f"  Pruning {variant.variant_id} from {cluster_id}: "
                                f"distance={distance:.3f}, fitness_gap={fitness_distance:.3f}"
                            )

        # Perform pruning
        if not self.config.dry_run:
            for variant_id in variants_to_prune:
                self._archive_variant(variant_id)

        result.variants_pruned.extend(variants_to_prune)

    def _archive_tool(self, tool_id: str) -> None:
        """Archive a tool (mark as archived in RAG)."""
        try:
            # Update tool status in RAG
            artifacts = self.rag.search(tool_id, top_k=1)
            if artifacts:
                artifact = artifacts[0]
                if hasattr(artifact, 'metadata'):
                    artifact.metadata['status'] = 'archived'
                    artifact.metadata['archived_at'] = datetime.now().isoformat()
                    # Update in RAG (implementation depends on RAG API)
                    logger.info(f"Archived tool: {tool_id}")
        except Exception as e:
            logger.error(f"Error archiving tool {tool_id}: {e}")

    def _archive_variant(self, variant_id: str) -> None:
        """Archive a variant (mark as archived in RAG)."""
        try:
            # Update variant status in RAG
            artifacts = self.rag.search(variant_id, top_k=1)
            if artifacts:
                artifact = artifacts[0]
                if hasattr(artifact, 'metadata'):
                    artifact.metadata['status'] = 'archived'
                    artifact.metadata['archived_at'] = datetime.now().isoformat()
                    logger.info(f"Archived variant: {variant_id}")
        except Exception as e:
            logger.error(f"Error archiving variant {variant_id}: {e}")

    def _calculate_improvement(self, result: OptimizationResult) -> float:
        """
        Calculate estimated performance improvement from optimization actions.

        This is a rough estimate based on:
        - Number of weight adjustments
        - Number of tools culled
        - Number of variants pruned
        """
        improvement = 0.0

        # Weight adjustments contribute to efficiency
        if result.weights_adjusted:
            avg_weight_reduction = np.mean([
                1.0 - (w.adjusted_weight / w.original_weight)
                for w in result.weights_adjusted
            ])
            improvement += avg_weight_reduction * 5.0  # 5% per 100% weight reduction

        # Culling reduces overhead
        if result.total_tools_analyzed > 0:
            cull_ratio = len(result.tools_culled) / result.total_tools_analyzed
            improvement += cull_ratio * 10.0  # 10% per 100% culled

        # Pruning reduces search space
        if result.total_variants_analyzed > 0:
            prune_ratio = len(result.variants_pruned) / result.total_variants_analyzed
            improvement += prune_ratio * 7.0  # 7% per 100% pruned

        return min(improvement, 30.0)  # Cap at 30%

    def _save_report(self, result: OptimizationResult) -> None:
        """Save optimization report to file."""
        try:
            report_data = {
                'timestamp': result.end_time.isoformat(),
                'duration_seconds': (result.end_time - result.start_time).total_seconds(),
                'config': {
                    'similarity_threshold': self.config.similarity_threshold,
                    'min_optimization_score': self.config.min_optimization_score,
                    'max_distance_from_prime': self.config.max_distance_from_prime,
                    'dry_run': self.config.dry_run
                },
                'summary': {
                    'total_clusters': result.total_clusters,
                    'total_tools_analyzed': result.total_tools_analyzed,
                    'total_variants_analyzed': result.total_variants_analyzed,
                    'weights_adjusted': len(result.weights_adjusted),
                    'tools_culled': len(result.tools_culled),
                    'variants_pruned': len(result.variants_pruned),
                    'estimated_improvement': result.estimated_improvement
                },
                'weights_adjusted': [
                    {
                        'tool_id': w.tool_id,
                        'cluster_id': w.cluster_id,
                        'original_weight': w.original_weight,
                        'adjusted_weight': w.adjusted_weight,
                        'similarity_to_prime': w.similarity_to_prime,
                        'reason': w.reason
                    }
                    for w in result.weights_adjusted
                ],
                'tools_culled': result.tools_culled,
                'variants_pruned': result.variants_pruned,
                'errors': result.errors,
                'warnings': result.warnings
            }

            report_path = Path(self.config.report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)

            logger.info(f"Saved optimization report to: {report_path}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")


def load_config_from_file(config_path: Path) -> OptimizationConfig:
    """Load optimization configuration from YAML file."""
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)

        return OptimizationConfig(
            similarity_threshold=data.get('similarity_threshold', 0.85),
            min_optimization_score=data.get('min_optimization_score', 0.50),
            max_distance_from_prime=data.get('max_distance_from_prime', 0.30),
            weight_reduction_factor=data.get('weight_reduction_factor', 0.7),
            enable_culling=data.get('enable_culling', True),
            culling_grace_period_days=data.get('culling_grace_period_days', 30),
            enable_variant_pruning=data.get('enable_variant_pruning', True),
            dry_run=data.get('dry_run', False),
            verbose=data.get('verbose', True),
            report_path=Path(data['report_path']) if 'report_path' in data else None
        )
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return OptimizationConfig()
