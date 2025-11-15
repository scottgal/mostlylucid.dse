#!/usr/bin/env python3
"""
Simple test script for the flexible pattern recognizer node.

Demonstrates different pattern types:
- peaks: Detect peaks and valleys
- anomaly: Detect outliers
- cluster: Find clusters
- changepoint: Detect regime changes
- trend: Identify trends
- periodic: Find periodic patterns
- auto: Detect all pattern types
"""
import json
import subprocess
import sys
import math
from pathlib import Path


def run_pattern_recognizer(data, pattern_type='auto', sensitivity=2.0):
    """Run the pattern recognizer node."""
    node_path = Path(__file__).parent.parent / "nodes" / "pattern_recognizer_v1" / "main.py"

    if not node_path.exists():
        print(f"ERROR: Node not found at {node_path}")
        return None

    input_data = {
        "data": data,
        "pattern_type": pattern_type,
        "sensitivity": sensitivity
    }

    try:
        result = subprocess.run(
            [sys.executable, str(node_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"ERROR: Node failed with exit code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return None

        return json.loads(result.stdout)

    except Exception as e:
        print(f"ERROR: {e}")
        return None


def main():
    print("="*80)
    print("Flexible Pattern Recognizer - Test Suite")
    print("="*80)

    # Test case 1: Sine wave with peaks and valleys
    print("\n1. Testing PEAKS detection on sine wave...")
    sine_wave = [math.sin(x * 0.2) * 10 for x in range(100)]
    result = run_pattern_recognizer(sine_wave, pattern_type='peaks', sensitivity=1.5)
    if result:
        print(f"   Found {result['summary']['total_patterns']} patterns:")
        print(f"   - Peaks: {result['summary'].get('peak', 0)}")
        print(f"   - Valleys: {result['summary'].get('valley', 0)}")

    # Test case 2: Normal data with outliers
    print("\n2. Testing ANOMALY detection on data with outliers...")
    normal_data = [float(x % 10) for x in range(95)]
    normal_data += [100.0, 95.0, 98.0, 99.0, 97.0]  # Add outliers
    result = run_pattern_recognizer(normal_data, pattern_type='anomaly', sensitivity=2.0)
    if result:
        print(f"   Found {result['summary']['total_patterns']} anomalies")
        for p in result['patterns'][:5]:
            print(f"   - Index {p['index']}: value={p['value']:.2f}, confidence={p['confidence']:.2f}")

    # Test case 3: Step function with changepoints
    print("\n3. Testing CHANGEPOINT detection on step function...")
    step_data = [1.0] * 30 + [5.0] * 30 + [2.0] * 40
    result = run_pattern_recognizer(step_data, pattern_type='changepoint', sensitivity=1.0)
    if result:
        print(f"   Found {result['summary']['total_patterns']} changepoints:")
        for p in result['patterns'][:5]:
            print(f"   - Index {p['index']}: mean_change={p['mean_change']:.2f}, confidence={p['confidence']:.2f}")

    # Test case 4: Trend detection
    print("\n4. Testing TREND detection on increasing data...")
    trend_data = [x * 0.5 + math.sin(x * 0.1) for x in range(100)]
    result = run_pattern_recognizer(trend_data, pattern_type='trend')
    if result:
        print(f"   Trend: {result['patterns'][0]['trend']}")
        print(f"   Slope: {result['patterns'][0]['slope']:.4f}")
        print(f"   R²: {result['patterns'][0]['r_squared']:.4f}")

    # Test case 5: Periodic pattern
    print("\n5. Testing PERIODIC detection on seasonal data...")
    periodic_data = [math.sin(x * 0.3) + math.sin(x * 0.7) for x in range(200)]
    result = run_pattern_recognizer(periodic_data, pattern_type='periodic')
    if result:
        print(f"   Found {result['summary']['total_patterns']} periodic patterns:")
        for p in result['patterns'][:3]:
            print(f"   - Period: {p['period']:.2f}, strength={p['strength']:.2f}, confidence={p['confidence']:.2f}")

    # Test case 6: AUTO mode - detect all patterns
    print("\n6. Testing AUTO mode (all pattern types)...")
    mixed_data = [math.sin(x * 0.2) * 5 + x * 0.1 for x in range(100)]
    mixed_data[50] = 50.0  # Add an anomaly
    result = run_pattern_recognizer(mixed_data, pattern_type='auto', sensitivity=2.0)
    if result:
        print(f"   Total patterns found: {result['summary']['total_patterns']}")
        print(f"   Summary: {json.dumps(result['summary'], indent=2)}")

    # Test case 7: Flexible example - "recognize a pattern in this data of this type"
    print("\n7. Flexible usage example...")
    print("   Question: 'Recognize a pattern in this sales data of type changepoint'")

    sales_data = [100] * 20 + [150] * 20 + [120] * 20 + [180] * 20
    result = run_pattern_recognizer(sales_data, pattern_type='changepoint', sensitivity=1.5)

    if result:
        print(f"   Answer: Found {result['summary']['total_patterns']} changepoints in sales data")
        for p in result['patterns'][:3]:
            print(f"   - At index {p['index']}: sales changed by {p['mean_change']:.2f} (confidence: {p['confidence']:.2f})")

    print("\n" + "="*80)
    print("Pattern Recognizer Test Complete!")
    print("="*80)
    print("\nUsage examples:")
    print("  - detect_peaks: Find peaks/valleys in sensor data")
    print("  - detect_anomaly: Find outliers in metrics")
    print("  - detect_cluster: Group similar data points")
    print("  - detect_changepoint: Find regime changes in time series")
    print("  - detect_trend: Identify overall trends")
    print("  - detect_periodic: Find seasonal/cyclic patterns")
    print("  - auto: Detect all pattern types at once")
    print("="*80)


if __name__ == "__main__":
    main()
