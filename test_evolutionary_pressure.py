#!/usr/bin/env python3
"""
Test script for evolutionary pressure configuration.

This script validates that the evolutionary pressure configuration
is properly loaded and applied to the optimizer.
"""

import sys
from pathlib import Path

# Add code_evolver to path
sys.path.insert(0, str(Path(__file__).parent / "code_evolver"))

from src.config_manager import ConfigManager
from src.pressure_manager import PressureManager, PressureLevel
from src.system_optimizer import OptimizationConfig
from src.rag_cluster_optimizer import NodeTypeOptimizerConfig, NodeType, TrimmingPolicy


def test_config_loading():
    """Test that evolutionary pressure is loaded from config."""
    print("=" * 80)
    print("TEST 1: Configuration Loading")
    print("=" * 80)

    config_manager = ConfigManager(config_path="code_evolver/config.yaml")
    pressure_config = config_manager.get("optimization_pressure", {})

    # Check each pressure level has evolutionary_pressure
    for level in ["high", "medium", "low", "training"]:
        level_config = pressure_config.get(level, {})
        evo_pressure = level_config.get("evolutionary_pressure")
        print(f"✓ {level.upper():10s}: evolutionary_pressure = {evo_pressure}")
        assert evo_pressure is not None, f"Missing evolutionary_pressure for {level}"

    print("\n✓ Configuration loading test PASSED\n")


def test_pressure_manager():
    """Test that PressureManager computes evolutionary adjustments."""
    print("=" * 80)
    print("TEST 2: PressureManager Adjustments")
    print("=" * 80)

    config_manager = ConfigManager(config_path="code_evolver/config.yaml")
    pressure_manager = PressureManager(config_manager)

    # Test each pressure level
    for pressure_level in [PressureLevel.HIGH, PressureLevel.MEDIUM, PressureLevel.LOW]:
        print(f"\n{pressure_level.value.upper()} Pressure:")
        print("-" * 40)

        adjustments = pressure_manager.get_evolutionary_adjustments(pressure_level)

        print(f"  Evolutionary Pressure:     {adjustments['evolutionary_pressure']}")
        print(f"  Similarity Threshold:      {adjustments['similarity_threshold']:.3f}")
        print(f"  Max Distance from Fittest: {adjustments['max_distance_from_fittest']:.3f}")
        print(f"  Min Cluster Size:          {adjustments['min_cluster_size']}")
        print(f"  Merge Similar Functions:   {adjustments['merge_similar_functions']}")
        print(f"  Specialization Bias:       {adjustments['specialization_bias']:.2f}")

        assert "evolutionary_pressure" in adjustments
        assert "similarity_threshold" in adjustments
        assert "max_distance_from_fittest" in adjustments

    print("\n✓ PressureManager adjustments test PASSED\n")


def test_optimization_config():
    """Test that OptimizationConfig applies evolutionary adjustments."""
    print("=" * 80)
    print("TEST 3: OptimizationConfig Application")
    print("=" * 80)

    config_manager = ConfigManager(config_path="code_evolver/config.yaml")
    pressure_manager = PressureManager(config_manager)

    # Test granular pressure (HIGH)
    print("\nApplying GRANULAR pressure to OptimizationConfig:")
    print("-" * 40)
    config = OptimizationConfig()
    print(f"  Before: similarity={config.cluster_similarity_threshold:.3f}, "
          f"max_distance={config.max_distance_from_prime:.3f}")

    adjustments = pressure_manager.get_evolutionary_adjustments(PressureLevel.HIGH)
    config.apply_evolutionary_adjustments(adjustments)

    print(f"  After:  similarity={config.cluster_similarity_threshold:.3f}, "
          f"max_distance={config.max_distance_from_prime:.3f}")
    print(f"  Evolutionary pressure: {config.evolutionary_pressure}")
    assert config.evolutionary_pressure == "granular"
    assert config.cluster_similarity_threshold > 0.96  # Tighter for granular

    # Test generic pressure (LOW)
    print("\nApplying GENERIC pressure to OptimizationConfig:")
    print("-" * 40)
    config = OptimizationConfig()
    print(f"  Before: similarity={config.cluster_similarity_threshold:.3f}, "
          f"max_distance={config.max_distance_from_prime:.3f}")

    adjustments = pressure_manager.get_evolutionary_adjustments(PressureLevel.LOW)
    config.apply_evolutionary_adjustments(adjustments)

    print(f"  After:  similarity={config.cluster_similarity_threshold:.3f}, "
          f"max_distance={config.max_distance_from_prime:.3f}")
    print(f"  Evolutionary pressure: {config.evolutionary_pressure}")
    assert config.evolutionary_pressure == "generic"
    assert config.cluster_similarity_threshold < 0.96  # Looser for generic

    print("\n✓ OptimizationConfig application test PASSED\n")


def test_node_type_optimizer_config():
    """Test that NodeTypeOptimizerConfig applies evolutionary adjustments."""
    print("=" * 80)
    print("TEST 4: NodeTypeOptimizerConfig Application")
    print("=" * 80)

    config_manager = ConfigManager(config_path="code_evolver/config.yaml")
    pressure_manager = PressureManager(config_manager)

    # Test with FUNCTION node type
    print("\nApplying adjustments to FUNCTION node type:")
    print("-" * 40)

    node_config = NodeTypeOptimizerConfig(
        node_type=NodeType.FUNCTION,
        enabled=True
    )

    print(f"  Before: similarity={node_config.similarity_threshold:.3f}")

    adjustments = pressure_manager.get_evolutionary_adjustments(PressureLevel.HIGH)
    node_config.apply_evolutionary_adjustments(adjustments)

    print(f"  After:  similarity={node_config.similarity_threshold:.3f}")

    assert node_config.similarity_threshold == adjustments["similarity_threshold"]

    print("\n✓ NodeTypeOptimizerConfig application test PASSED\n")


def test_trimming_policy():
    """Test that TrimmingPolicy applies evolutionary adjustments."""
    print("=" * 80)
    print("TEST 5: TrimmingPolicy Application")
    print("=" * 80)

    config_manager = ConfigManager(config_path="code_evolver/config.yaml")
    pressure_manager = PressureManager(config_manager)

    print("\nApplying adjustments to TrimmingPolicy:")
    print("-" * 40)

    policy = TrimmingPolicy(node_type=NodeType.FUNCTION)

    print(f"  Before: max_distance={policy.max_distance_from_fittest:.3f}")

    adjustments = pressure_manager.get_evolutionary_adjustments(PressureLevel.HIGH)
    policy.apply_evolutionary_adjustments(adjustments)

    print(f"  After:  max_distance={policy.max_distance_from_fittest:.3f}")

    assert policy.max_distance_from_fittest == adjustments["max_distance_from_fittest"]

    print("\n✓ TrimmingPolicy application test PASSED\n")


def test_evolutionary_pressure_variations():
    """Test that different evolutionary pressures produce different results."""
    print("=" * 80)
    print("TEST 6: Evolutionary Pressure Variations")
    print("=" * 80)

    config_manager = ConfigManager(config_path="code_evolver/config.yaml")
    pressure_manager = PressureManager(config_manager)

    # Get adjustments for each pressure type
    granular_adj = pressure_manager.get_evolutionary_adjustments(PressureLevel.HIGH)
    balanced_adj = pressure_manager.get_evolutionary_adjustments(PressureLevel.MEDIUM)
    generic_adj = pressure_manager.get_evolutionary_adjustments(PressureLevel.LOW)

    print("\nComparing similarity thresholds:")
    print("-" * 40)
    print(f"  Granular: {granular_adj['similarity_threshold']:.3f}")
    print(f"  Balanced: {balanced_adj['similarity_threshold']:.3f}")
    print(f"  Generic:  {generic_adj['similarity_threshold']:.3f}")

    # Granular should have highest (tightest) similarity threshold
    assert granular_adj['similarity_threshold'] >= balanced_adj['similarity_threshold']
    assert balanced_adj['similarity_threshold'] >= generic_adj['similarity_threshold']

    print("\nComparing max distance from fittest:")
    print("-" * 40)
    print(f"  Granular: {granular_adj['max_distance_from_fittest']:.3f}")
    print(f"  Balanced: {balanced_adj['max_distance_from_fittest']:.3f}")
    print(f"  Generic:  {generic_adj['max_distance_from_fittest']:.3f}")

    # Generic should have highest (most permissive) max distance
    assert generic_adj['max_distance_from_fittest'] >= balanced_adj['max_distance_from_fittest']
    assert balanced_adj['max_distance_from_fittest'] >= granular_adj['max_distance_from_fittest']

    print("\nComparing specialization bias:")
    print("-" * 40)
    print(f"  Granular: {granular_adj['specialization_bias']:.2f}")
    print(f"  Balanced: {balanced_adj['specialization_bias']:.2f}")
    print(f"  Generic:  {generic_adj['specialization_bias']:.2f}")

    # Granular should have highest specialization bias
    assert granular_adj['specialization_bias'] > generic_adj['specialization_bias']

    print("\n✓ Evolutionary pressure variations test PASSED\n")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "EVOLUTIONARY PRESSURE TEST SUITE" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    try:
        test_config_loading()
        test_pressure_manager()
        test_optimization_config()
        test_node_type_optimizer_config()
        test_trimming_policy()
        test_evolutionary_pressure_variations()

        print("=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nEvolutionary pressure configuration is working correctly.\n")
        return 0

    except AssertionError as e:
        print("\n" + "=" * 80)
        print("✗ TEST FAILED!")
        print("=" * 80)
        print(f"\nError: {e}\n")
        return 1

    except Exception as e:
        print("\n" + "=" * 80)
        print("✗ UNEXPECTED ERROR!")
        print("=" * 80)
        print(f"\nError: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
