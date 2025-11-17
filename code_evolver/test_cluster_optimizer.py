#!/usr/bin/env python3
"""Test RAG Cluster Optimizer"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.rag_cluster_optimizer import (
    RAGClusterOptimizer,
    NodeType,
    OptimizationStrategy,
    ArtifactVariant,
    PerformanceMetrics,
    VariantStatus
)

def test_cluster_optimizer():
    """Test the RAG cluster optimizer functionality"""
    print("=" * 60)
    print("Testing RAG Cluster Optimizer")
    print("=" * 60)

    # Create optimizer
    try:
        optimizer = RAGClusterOptimizer(
            similarity_threshold=0.96,
            max_iterations=3,
            strategy=OptimizationStrategy.INCREMENTAL
        )
        print("[OK] RAGClusterOptimizer initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize optimizer: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test fitness calculation with different performance metrics
    try:
        fitness_weights = {
            "latency": 0.30,
            "memory": 0.20,
            "success_rate": 0.30,
            "test_coverage": 0.20
        }

        perf1 = PerformanceMetrics(
            latency_ms=10.0,
            memory_mb=5.0,
            success_rate=0.95,
            test_coverage=0.80
        )

        perf2 = PerformanceMetrics(
            latency_ms=8.0,   # Better (lower)
            memory_mb=4.5,    # Better (lower)
            success_rate=0.98,  # Better (higher)
            test_coverage=0.85  # Better (higher)
        )

        fitness1 = optimizer.calculate_fitness(perf1, fitness_weights)
        fitness2 = optimizer.calculate_fitness(perf2, fitness_weights)

        print(f"[OK] Fitness calculation works")
        print(f"  Performance 1: fitness = {fitness1:.3f}")
        print(f"  Performance 2: fitness = {fitness2:.3f}")

        if fitness2 > fitness1:
            print(f"[OK] Better performance has higher fitness")
        else:
            print(f"[FAIL] Fitness scoring is reversed!")
            return False

    except Exception as e:
        print(f"[FAIL] Failed to calculate fitness: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test strategy enumeration
    try:
        strategies = list(OptimizationStrategy)
        print(f"[OK] Found {len(strategies)} optimization strategies:")
        for strategy in strategies:
            print(f"  - {strategy.value}")
    except Exception as e:
        print(f"[FAIL] Failed to enumerate strategies: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] All RAG cluster optimizer tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_cluster_optimizer()
    sys.exit(0 if success else 1)
