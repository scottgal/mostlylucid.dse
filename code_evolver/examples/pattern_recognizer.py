#!/usr/bin/env python3
"""
Example: Generate and test a pattern recognizer node.

This node can detect various patterns in data streams:
- Peaks and valleys (using scipy)
- Trends and changepoints (using ruptures)
- Anomalies and outliers (using statistical methods)
- Repeated motifs (using stumpy for time series)

This example demonstrates the full workflow:
1. Generate code from a prompt using codellama
2. Execute the code with test inputs
3. Evaluate performance using llama3 and tiny
4. Store results in the registry
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import OllamaClient, Registry, NodeRunner, Evaluator


def main():
    print("="*80)
    print("Pattern Recognizer Example - Code Evolution System")
    print("="*80)

    # Initialize components
    print("\n1. Initializing components...")
    client = OllamaClient()
    registry = Registry("./registry")
    runner = NodeRunner("./nodes")
    evaluator = Evaluator(client)

    # Check Ollama connection
    print("\n2. Checking Ollama connection...")
    if not client.check_connection():
        print("ERROR: Cannot connect to Ollama. Please ensure:")
        print("  1. Ollama is installed")
        print("  2. Ollama server is running (ollama serve)")
        return 1

    # Check required models
    models = client.list_models()
    required = ["codellama", "llama3"]
    missing = [m for m in required if m not in models]

    if missing:
        print(f"WARNING: Missing models: {', '.join(missing)}")
        print("Install with:")
        for model in missing:
            print(f"  ollama pull {model}")
        print("\nContinuing anyway (may fail)...")

    # Define the node
    node_id = "pattern_recognizer_v1"
    title = "Pattern recognizer for data streams"

    print(f"\n3. Creating node '{node_id}'...")

    # Create node in registry
    node_def = registry.create_node(
        node_id=node_id,
        title=title,
        version="1.0.0",
        node_type="analyzer",
        tags=["pattern-recognition", "time-series", "anomaly-detection", "analysis"],
        goals={
            "primary": ["correctness", "comprehensive-detection"],
            "secondary": ["latency<500ms", "memory<128MB"]
        },
        inputs={"data": "array", "sensitivity": "float"},
        outputs={"patterns": "array", "summary": "object"},
        constraints={
            "timeout_ms": 10000,
            "max_memory_mb": 256
        }
    )

    # Generate code prompt
    print("\n4. Generating code with codellama...")
    prompt = """Write a Python module for pattern recognition in data streams with:

- def detect_peaks(data: list, threshold: float) -> dict: Detect peaks and valleys
- def detect_changepoints(data: list, penalty: float) -> dict: Detect trend changes
- def detect_anomalies(data: list, sensitivity: float) -> dict: Detect outliers
- def analyze_patterns(data: list, sensitivity: float = 2.0) -> dict: Main function

Use only these dependencies (install if needed):
- numpy for numerical operations
- scipy for peak detection
- ruptures for changepoint detection (optional, fallback to simple method)

Pattern detection should find:
1. Peaks: Local maxima above threshold
2. Valleys: Local minima below threshold
3. Changepoints: Where statistical properties change
4. Anomalies: Outliers using z-score method (> sensitivity * std dev)

Constraints:
- Handle arrays of floats/ints
- Return confidence scores (0.0 to 1.0)
- Target latency <500ms on 1000 data points
- Memory <128MB

Include __main__ section that:
1. Reads JSON from stdin with format: {"data": [1.0, 2.0, ...], "sensitivity": 2.0}
2. Calls analyze_patterns()
3. Prints JSON result with format:
   {
     "patterns": [
       {"type": "peak", "index": 10, "value": 5.2, "confidence": 0.95},
       {"type": "changepoint", "index": 50, "confidence": 0.87},
       {"type": "anomaly", "index": 75, "value": 10.5, "confidence": 0.92}
     ],
     "summary": {
       "total_patterns": 15,
       "peaks": 5,
       "valleys": 3,
       "changepoints": 4,
       "anomalies": 3,
       "data_length": 100
     }
   }

Return only code, no explanations."""

    code = client.generate_code(prompt)

    if not code or len(code) < 50:
        print("ERROR: Failed to generate code")
        return 1

    print(f"✓ Generated {len(code)} characters of code")

    # Save the code
    print("\n5. Saving code...")
    code_path = runner.save_code(node_id, code)
    print(f"✓ Code saved to: {code_path}")

    # Test with sample inputs
    print("\n6. Testing with sample inputs...")

    # Create test cases with different patterns
    import math

    # Test case 1: Sine wave with noise (should detect peaks/valleys)
    sine_wave = [math.sin(x * 0.1) + (0.1 * (x % 3 - 1)) for x in range(100)]

    # Test case 2: Step function (should detect changepoints)
    step_function = [1.0] * 30 + [5.0] * 30 + [2.0] * 40

    # Test case 3: Normal data with outliers (should detect anomalies)
    normal_with_outliers = [float(x % 10) for x in range(90)] + [100.0, 95.0, 98.0, 2.0, 1.0, 3.0, 99.0, 2.0, 1.0, 2.0]

    test_cases = [
        {"data": sine_wave, "sensitivity": 2.0},
        {"data": step_function, "sensitivity": 2.0},
        {"data": normal_with_outliers, "sensitivity": 2.0},
    ]

    all_passed = True

    for i, test_input in enumerate(test_cases, 1):
        print(f"\n   Test case {i}: {len(test_input['data'])} data points...")

        # Run the node
        stdout, stderr, metrics = runner.run_node(
            node_id=node_id,
            input_payload=test_input,
            timeout_ms=node_def["constraints"]["timeout_ms"]
        )

        # Save metrics
        registry.save_metrics(node_id, metrics)

        # Print results
        if metrics["success"]:
            print(f"   ✓ Success: {metrics['latency_ms']}ms, {metrics['memory_mb_peak']:.2f}MB")
            if stdout:
                print(f"   Output: {stdout[:150]}...")
        else:
            print(f"   ✗ Failed: exit_code={metrics['exit_code']}")
            if stderr:
                print(f"   Error: {stderr[:200]}")
            all_passed = False

    # Evaluate the last run
    print("\n7. Evaluating performance...")

    result = evaluator.evaluate_full(
        stdout=stdout,
        stderr=stderr,
        metrics=metrics,
        code_summary=f"Pattern recognizer detecting peaks, changepoints, and anomalies. Last test: {len(test_input['data'])} points",
        goals=node_def["goals"],
        targets={
            "latency_ms": 500,
            "memory_mb": 128,
            "exit_code": 0
        }
    )

    # Save evaluation
    eval_data = {
        "score_overall": result["final_score"],
        "verdict": result["final_verdict"],
        "triage": result.get("triage"),
        "evaluation": result.get("evaluation")
    }
    registry.save_evaluation(node_id, eval_data)

    # Update index
    registry.update_index(
        node_id=node_id,
        version=node_def["version"],
        tags=node_def["tags"],
        score_overall=result["final_score"]
    )

    # Print evaluation results
    print(f"\n{'='*80}")
    print("EVALUATION RESULTS")
    print(f"{'='*80}")
    print(f"Overall Score: {result['final_score']:.2f}")
    print(f"Verdict: {result['final_verdict']}")

    if result.get("evaluation"):
        eval_data = result["evaluation"]
        if "scores" in eval_data:
            print(f"\nDetailed Scores:")
            for key, value in eval_data["scores"].items():
                print(f"  {key.capitalize()}: {value:.2f}")

        if "notes" in eval_data:
            print(f"\nNotes:\n{eval_data['notes'][:300]}")

    # Print registry location
    print(f"\n{'='*80}")
    print("Registry saved to:")
    print(f"  Node definition: {registry.get_node_dir(node_id) / 'node.json'}")
    print(f"  Metrics: {registry.get_node_dir(node_id) / 'metrics.json'}")
    print(f"  Evaluation: {registry.get_node_dir(node_id) / 'evaluation.json'}")
    print(f"  Code: {code_path}")
    print(f"{'='*80}")

    return 0 if all_passed and result["final_verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
