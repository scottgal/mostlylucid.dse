#!/usr/bin/env python3
"""
Simple test for evolutionary pressure configuration.

This script validates that the evolutionary pressure configuration
is properly set in the YAML config files.
"""

import yaml
from pathlib import Path


def test_config_files():
    """Test that evolutionary pressure is in both config files."""
    print("=" * 80)
    print("Testing Evolutionary Pressure Configuration")
    print("=" * 80)

    config_files = [
        "code_evolver/config.yaml",
        "code_evolver/config.unified.yaml"
    ]

    for config_file in config_files:
        print(f"\n📄 Testing: {config_file}")
        print("-" * 80)

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        optimization_pressure = config.get("optimization_pressure", {})

        # Test each pressure level
        pressure_levels = ["high", "medium", "low", "training"]

        for level in pressure_levels:
            level_config = optimization_pressure.get(level, {})
            evo_pressure = level_config.get("evolutionary_pressure")

            if evo_pressure:
                print(f"  ✓ {level:10s}: evolutionary_pressure = '{evo_pressure}'")
                assert evo_pressure in ["granular", "balanced", "generic"], \
                    f"Invalid evolutionary_pressure value: {evo_pressure}"
            else:
                print(f"  ✗ {level:10s}: MISSING evolutionary_pressure")
                raise AssertionError(f"Missing evolutionary_pressure for {level} in {config_file}")

    print("\n" + "=" * 80)
    print("✓ All configuration files have correct evolutionary_pressure settings!")
    print("=" * 80)

    # Print summary
    print("\nSummary of evolutionary pressure settings:")
    print("-" * 80)

    with open("code_evolver/config.yaml", 'r') as f:
        config = yaml.safe_load(f)
        optimization_pressure = config.get("optimization_pressure", {})

    print("\n  High Pressure    (fast, urgent):")
    print(f"    → evolutionary_pressure: {optimization_pressure['high']['evolutionary_pressure']}")
    print(f"    → Effect: Tends towards small, specific functions")

    print("\n  Medium Pressure  (balanced):")
    print(f"    → evolutionary_pressure: {optimization_pressure['medium']['evolutionary_pressure']}")
    print(f"    → Effect: Balanced approach")

    print("\n  Low Pressure     (full optimization):")
    print(f"    → evolutionary_pressure: {optimization_pressure['low']['evolutionary_pressure']}")
    print(f"    → Effect: Tends towards large, encompassing functions")

    print("\n  Training Mode:")
    print(f"    → evolutionary_pressure: {optimization_pressure['training']['evolutionary_pressure']}")
    print(f"    → Effect: Data collection with balanced approach")

    print("\n✓ Configuration test PASSED!\n")


if __name__ == "__main__":
    try:
        test_config_files()
    except Exception as e:
        print(f"\n✗ Test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
