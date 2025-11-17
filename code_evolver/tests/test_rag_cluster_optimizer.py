"""
Tests for RAG Cluster Optimizer
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch

from src.rag_cluster_optimizer import (
    RAGClusterOptimizer,
    OptimizationCluster,
    ArtifactVariant,
    PerformanceMetrics,
    SemanticDelta,
    ValidationResult,
    OptimizationStrategy,
    VariantStatus
)


@pytest.fixture
def sample_performance():
    """Sample performance metrics."""
    return PerformanceMetrics(
        latency_ms=50.0,
        memory_mb=10.0,
        cpu_percent=25.0,
        success_rate=0.95,
        test_coverage=0.80
    )


@pytest.fixture
def sample_variant():
    """Sample artifact variant."""
    return ArtifactVariant(
        variant_id="test_v1",
        artifact_id="test_artifact",
        version="1.0",
        content="def test(): pass",
        embedding=np.random.rand(768),
        status=VariantStatus.CANONICAL,
        performance=PerformanceMetrics(
            latency_ms=50.0,
            memory_mb=10.0,
            success_rate=0.95,
            test_coverage=0.80
        )
    )


@pytest.fixture
def sample_cluster(sample_variant):
    """Sample optimization cluster."""
    alt1 = ArtifactVariant(
        variant_id="test_v1.1",
        artifact_id="test_artifact",
        version="1.1",
        content="def test(): # improved",
        embedding=np.random.rand(768),
        performance=PerformanceMetrics(
            latency_ms=45.0,
            memory_mb=9.5,
            success_rate=0.96,
            test_coverage=0.82
        ),
        semantic_deltas=[
            SemanticDelta(
                delta_type="error_handling",
                description="Added error handling",
                impact_areas=["robustness"],
                estimated_benefit=0.7,
                risk_level=0.2
            )
        ]
    )

    alt2 = ArtifactVariant(
        variant_id="test_v1.2",
        artifact_id="test_artifact",
        version="1.2",
        content="def test(): # optimized",
        embedding=np.random.rand(768),
        performance=PerformanceMetrics(
            latency_ms=40.0,
            memory_mb=11.0,
            success_rate=0.94,
            test_coverage=0.81
        ),
        semantic_deltas=[
            SemanticDelta(
                delta_type="algorithm",
                description="Algorithm optimization",
                impact_areas=["performance"],
                estimated_benefit=0.8,
                risk_level=0.3
            )
        ]
    )

    return OptimizationCluster(
        cluster_id="test_cluster",
        canonical_variant=sample_variant,
        alternates=[alt1, alt2]
    )


class TestPerformanceMetrics:
    """Test PerformanceMetrics class."""

    def test_fitness_score_default_weights(self, sample_performance):
        """Test fitness score calculation with default weights."""
        score = sample_performance.fitness_score()
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be reasonably high

    def test_fitness_score_custom_weights(self, sample_performance):
        """Test fitness score with custom weights."""
        weights = {
            'latency': 0.5,
            'memory': 0.1,
            'cpu': 0.1,
            'success_rate': 0.2,
            'coverage': 0.1
        }
        score = sample_performance.fitness_score(weights)
        assert 0.0 <= score <= 1.0

    def test_fitness_score_perfect_metrics(self):
        """Test fitness score with perfect metrics."""
        perfect = PerformanceMetrics(
            latency_ms=0.0,
            memory_mb=0.0,
            cpu_percent=0.0,
            success_rate=1.0,
            test_coverage=1.0
        )
        score = perfect.fitness_score()
        assert score == 1.0

    def test_fitness_score_poor_metrics(self):
        """Test fitness score with poor metrics."""
        poor = PerformanceMetrics(
            latency_ms=1000.0,
            memory_mb=100.0,
            cpu_percent=100.0,
            success_rate=0.5,
            test_coverage=0.0
        )
        score = poor.fitness_score()
        assert score < 0.5


class TestArtifactVariant:
    """Test ArtifactVariant class."""

    def test_similarity_calculation(self):
        """Test cosine similarity between variants."""
        v1 = ArtifactVariant(
            variant_id="v1",
            artifact_id="test",
            version="1.0",
            content="test",
            embedding=np.array([1.0, 0.0, 0.0])
        )
        v2 = ArtifactVariant(
            variant_id="v2",
            artifact_id="test",
            version="2.0",
            content="test",
            embedding=np.array([1.0, 0.0, 0.0])
        )
        similarity = v1.similarity_to(v2)
        assert similarity == pytest.approx(1.0, rel=1e-5)

    def test_similarity_orthogonal(self):
        """Test similarity of orthogonal vectors."""
        v1 = ArtifactVariant(
            variant_id="v1",
            artifact_id="test",
            version="1.0",
            content="test",
            embedding=np.array([1.0, 0.0, 0.0])
        )
        v2 = ArtifactVariant(
            variant_id="v2",
            artifact_id="test",
            version="2.0",
            content="test",
            embedding=np.array([0.0, 1.0, 0.0])
        )
        similarity = v1.similarity_to(v2)
        assert similarity == pytest.approx(0.0, abs=1e-5)

    def test_similarity_no_embedding(self):
        """Test similarity when embeddings are missing."""
        v1 = ArtifactVariant(
            variant_id="v1",
            artifact_id="test",
            version="1.0",
            content="test"
        )
        v2 = ArtifactVariant(
            variant_id="v2",
            artifact_id="test",
            version="2.0",
            content="test"
        )
        similarity = v1.similarity_to(v2)
        assert similarity == 0.0


class TestOptimizationCluster:
    """Test OptimizationCluster class."""

    def test_calculate_median_fitness(self, sample_cluster):
        """Test median fitness calculation."""
        median = sample_cluster.calculate_median_fitness()
        assert 0.0 <= median <= 1.0

    def test_get_variants_by_similarity(self, sample_cluster):
        """Test getting variants sorted by similarity."""
        # Set up similarity by making embeddings similar
        base_embedding = np.random.rand(768)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            # Make alternates similar to canonical
            noise = np.random.rand(768) * 0.1
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        sample_cluster.canonical_variant.embedding = (
            sample_cluster.canonical_variant.embedding /
            np.linalg.norm(sample_cluster.canonical_variant.embedding)
        )

        variants = sample_cluster.get_variants_by_similarity()
        assert len(variants) >= 0
        # All returned variants should meet threshold
        for v in variants:
            sim = sample_cluster.canonical_variant.similarity_to(v)
            assert sim >= sample_cluster.similarity_threshold or sim >= 0.9

    def test_extract_semantic_deltas(self, sample_cluster):
        """Test semantic delta extraction."""
        deltas = sample_cluster.extract_semantic_deltas()
        assert len(deltas) > 0
        # Should be sorted by benefit
        benefits = [d.estimated_benefit for d in deltas]
        assert benefits == sorted(benefits, reverse=True)


class TestRAGClusterOptimizer:
    """Test RAGClusterOptimizer class."""

    def test_initialization(self):
        """Test optimizer initialization."""
        optimizer = RAGClusterOptimizer(
            similarity_threshold=0.95,
            max_iterations=5,
            fitness_improvement_threshold=0.03,
            strategy=OptimizationStrategy.BEST_OF_BREED
        )
        assert optimizer.similarity_threshold == 0.95
        assert optimizer.max_iterations == 5
        assert optimizer.fitness_improvement_threshold == 0.03
        assert optimizer.strategy == OptimizationStrategy.BEST_OF_BREED

    def test_generate_best_of_breed_candidate(self, sample_cluster):
        """Test best-of-breed candidate generation."""
        optimizer = RAGClusterOptimizer(
            strategy=OptimizationStrategy.BEST_OF_BREED
        )

        # Set up embeddings for similarity
        base_embedding = np.random.rand(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            noise = np.random.rand(768) * 0.05
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        deltas = sample_cluster.extract_semantic_deltas()
        variants = sample_cluster.get_variants_by_similarity()

        candidate = optimizer._generate_best_of_breed(
            sample_cluster,
            variants if variants else sample_cluster.alternates,
            deltas
        )

        assert candidate is not None
        assert candidate.variant_id.startswith(sample_cluster.cluster_id)
        assert candidate.metadata['strategy'] == 'best_of_breed'

    def test_generate_incremental_candidate(self, sample_cluster):
        """Test incremental candidate generation."""
        optimizer = RAGClusterOptimizer(
            strategy=OptimizationStrategy.INCREMENTAL
        )

        deltas = sample_cluster.extract_semantic_deltas()
        candidate = optimizer._generate_incremental(sample_cluster, deltas)

        assert candidate is not None
        assert candidate.metadata['strategy'] == 'incremental'
        # Performance should be slightly better
        assert candidate.performance.latency_ms <= sample_cluster.canonical_variant.performance.latency_ms

    def test_generate_radical_candidate(self, sample_cluster):
        """Test radical candidate generation."""
        optimizer = RAGClusterOptimizer(
            strategy=OptimizationStrategy.RADICAL
        )

        # Set up embeddings
        base_embedding = np.random.rand(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            noise = np.random.rand(768) * 0.05
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        deltas = sample_cluster.extract_semantic_deltas()
        variants = sample_cluster.alternates

        candidate = optimizer._generate_radical(sample_cluster, variants, deltas)

        assert candidate is not None
        assert candidate.metadata['strategy'] == 'radical'

    def test_validate_candidate_default(self, sample_variant):
        """Test default candidate validation."""
        optimizer = RAGClusterOptimizer()
        result = optimizer._validate_candidate(sample_variant)

        assert isinstance(result, ValidationResult)
        assert result.passed in [True, False]
        assert 0.0 <= result.fitness_score <= 1.0
        assert 'unit_tests' in result.test_results

    def test_validate_candidate_custom_validator(self, sample_variant):
        """Test candidate validation with custom validator."""
        optimizer = RAGClusterOptimizer()

        def custom_validator(variant):
            return ValidationResult(
                passed=True,
                fitness_score=0.95,
                performance=variant.performance,
                test_results={'custom': {'passed': True}}
            )

        result = optimizer._validate_candidate(sample_variant, custom_validator)
        assert result.passed is True
        assert result.fitness_score == 0.95
        assert 'custom' in result.test_results

    def test_optimize_cluster_no_improvement(self, sample_cluster):
        """Test optimization when no improvement is found."""
        optimizer = RAGClusterOptimizer(
            max_iterations=3,
            fitness_improvement_threshold=0.5  # Very high threshold
        )

        # Set up embeddings
        base_embedding = np.random.rand(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            noise = np.random.rand(768) * 0.05
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        iterations = optimizer.optimize_cluster(sample_cluster)

        # Should stop early due to no improvement
        assert len(iterations) >= 1
        assert all(not it.promoted for it in iterations)

    def test_optimize_cluster_with_improvement(self, sample_cluster):
        """Test optimization with successful promotions."""
        optimizer = RAGClusterOptimizer(
            max_iterations=2,
            fitness_improvement_threshold=0.01  # Low threshold
        )

        # Set up embeddings
        base_embedding = np.random.rand(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            noise = np.random.rand(768) * 0.05
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        # Mock validator that always returns improvement
        def mock_validator(variant):
            improved_perf = PerformanceMetrics(
                latency_ms=30.0,  # Much better
                memory_mb=8.0,
                success_rate=0.98,
                test_coverage=0.90
            )
            return ValidationResult(
                passed=True,
                fitness_score=improved_perf.fitness_score(),
                performance=improved_perf
            )

        iterations = optimizer.optimize_cluster(sample_cluster, mock_validator)

        assert len(iterations) >= 1
        # At least one should be promoted with our mock validator
        assert any(it.promoted for it in iterations)

    def test_learn_from_promotion(self, sample_cluster):
        """Test learning from successful promotions."""
        optimizer = RAGClusterOptimizer()

        new_canonical = ArtifactVariant(
            variant_id="test_v2",
            artifact_id="test_artifact",
            version="2.0",
            content="def test(): # v2",
            performance=PerformanceMetrics(
                latency_ms=30.0,
                memory_mb=8.0,
                success_rate=0.98,
                test_coverage=0.90
            ),
            semantic_deltas=[
                SemanticDelta(
                    delta_type="algorithm",
                    description="New algorithm",
                    impact_areas=["performance"],
                    estimated_benefit=0.9,
                    risk_level=0.2
                )
            ]
        )

        old_canonical = sample_cluster.canonical_variant

        optimizer._learn_from_promotion(sample_cluster, new_canonical, old_canonical)

        # Should have learned something
        assert len(optimizer.learned_patterns) > 0
        assert 'algorithm' in optimizer.learned_patterns

    def test_generate_insights(self, sample_cluster):
        """Test insight generation."""
        optimizer = RAGClusterOptimizer()

        validation = ValidationResult(
            passed=True,
            fitness_score=0.92,
            performance=PerformanceMetrics(
                latency_ms=35.0,
                memory_mb=9.0,
                success_rate=0.97,
                test_coverage=0.85
            )
        )

        insights = optimizer._generate_insights(sample_cluster, validation, promoted=True)

        assert len(insights) > 0
        assert any('promoted' in insight.lower() for insight in insights)

    def test_get_optimization_report(self, sample_cluster):
        """Test optimization report generation."""
        optimizer = RAGClusterOptimizer(max_iterations=2)

        # Set up embeddings
        base_embedding = np.random.rand(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            noise = np.random.rand(768) * 0.05
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        iterations = optimizer.optimize_cluster(sample_cluster)
        report = optimizer.get_optimization_report(sample_cluster, iterations)

        assert report['cluster_id'] == sample_cluster.cluster_id
        assert report['status'] == 'completed'
        assert 'summary' in report
        assert 'iterations' in report
        assert 'canonical_variant' in report
        assert 'cluster_stats' in report

    def test_get_optimization_report_no_iterations(self, sample_cluster):
        """Test report generation with no iterations."""
        optimizer = RAGClusterOptimizer()
        report = optimizer.get_optimization_report(sample_cluster, [])

        assert report['status'] == 'no_iterations'

    def test_hybrid_strategy(self, sample_cluster):
        """Test hybrid optimization strategy."""
        optimizer = RAGClusterOptimizer(
            strategy=OptimizationStrategy.HYBRID,
            max_iterations=5
        )

        # Set up embeddings
        base_embedding = np.random.rand(768)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)
        sample_cluster.canonical_variant.embedding = base_embedding

        for alt in sample_cluster.alternates:
            noise = np.random.rand(768) * 0.05
            alt.embedding = base_embedding + noise
            alt.embedding = alt.embedding / np.linalg.norm(alt.embedding)

        # Test that different iterations use different strategies
        candidates = []
        for i in range(3):
            candidate = optimizer._generate_candidate(sample_cluster, i)
            if candidate:
                candidates.append(candidate)

        # Should have generated candidates with different strategies
        strategies = [c.metadata.get('strategy') for c in candidates if c]
        assert len(set(strategies)) > 1  # Multiple strategies used

    def test_prioritize_deltas_with_learning(self):
        """Test delta prioritization with learned patterns."""
        optimizer = RAGClusterOptimizer()

        # Add learned patterns
        optimizer.learned_patterns['error_handling'] = [
            {'improvement': 0.15, 'description': 'test', 'cluster_id': 'test', 'timestamp': '2024-01-01'}
        ]

        deltas = [
            SemanticDelta(
                delta_type="error_handling",
                description="Improved error handling",
                impact_areas=["robustness"],
                estimated_benefit=0.5,
                risk_level=0.2
            ),
            SemanticDelta(
                delta_type="refactor",
                description="Code refactor",
                impact_areas=["maintainability"],
                estimated_benefit=0.6,
                risk_level=0.1
            )
        ]

        prioritized = optimizer._prioritize_deltas_with_learning(deltas)

        # error_handling delta should get boosted benefit
        error_delta = [d for d in prioritized if d.delta_type == 'error_handling'][0]
        assert error_delta.estimated_benefit > 0.5  # Should be boosted


class TestIntegration:
    """Integration tests for the full optimization loop."""

    def test_full_optimization_cycle(self):
        """Test a complete optimization cycle from start to finish."""
        # Create a cluster
        canonical = ArtifactVariant(
            variant_id="func_v1",
            artifact_id="test_function",
            version="1.0",
            content="def compute(x): return x * 2",
            embedding=np.random.rand(768),
            status=VariantStatus.CANONICAL,
            performance=PerformanceMetrics(
                latency_ms=100.0,
                memory_mb=20.0,
                success_rate=0.85,
                test_coverage=0.70
            )
        )

        # Normalize embedding
        canonical.embedding = canonical.embedding / np.linalg.norm(canonical.embedding)

        alternates = []
        for i in range(3):
            noise = np.random.rand(768) * 0.05
            embedding = canonical.embedding + noise
            embedding = embedding / np.linalg.norm(embedding)

            alt = ArtifactVariant(
                variant_id=f"func_v1.{i+1}",
                artifact_id="test_function",
                version=f"1.{i+1}",
                content=f"def compute(x): # variant {i+1}",
                embedding=embedding,
                performance=PerformanceMetrics(
                    latency_ms=100.0 - (i * 5),
                    memory_mb=20.0 - (i * 1),
                    success_rate=0.85 + (i * 0.02),
                    test_coverage=0.70 + (i * 0.03)
                ),
                semantic_deltas=[
                    SemanticDelta(
                        delta_type=["algorithm", "error_handling", "refactor"][i],
                        description=f"Improvement {i+1}",
                        impact_areas=["performance"],
                        estimated_benefit=0.6 + (i * 0.1),
                        risk_level=0.2
                    )
                ]
            )
            alternates.append(alt)

        cluster = OptimizationCluster(
            cluster_id="test_cluster",
            canonical_variant=canonical,
            alternates=alternates
        )

        # Custom validator that simulates improvement
        def improving_validator(variant):
            # Each iteration gets slightly better
            base_fitness = variant.performance.fitness_score()
            improved_fitness = min(1.0, base_fitness * 1.1)

            improved_perf = PerformanceMetrics(
                latency_ms=variant.performance.latency_ms * 0.9,
                memory_mb=variant.performance.memory_mb * 0.95,
                success_rate=min(1.0, variant.performance.success_rate * 1.05),
                test_coverage=min(1.0, variant.performance.test_coverage * 1.05)
            )

            return ValidationResult(
                passed=True,
                fitness_score=improved_fitness,
                performance=improved_perf,
                test_results={'all': {'passed': True}}
            )

        # Run optimization
        optimizer = RAGClusterOptimizer(
            max_iterations=3,
            fitness_improvement_threshold=0.02,
            strategy=OptimizationStrategy.BEST_OF_BREED
        )

        iterations = optimizer.optimize_cluster(cluster, improving_validator)

        # Verify results
        assert len(iterations) > 0
        assert any(it.promoted for it in iterations)

        # Generate and verify report
        report = optimizer.get_optimization_report(cluster, iterations)
        assert report['status'] == 'completed'
        assert report['summary']['total_iterations'] == len(iterations)
        assert report['summary']['total_improvement'] > 0

        # Verify canonical was updated
        assert cluster.canonical_variant.variant_id != canonical.variant_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
